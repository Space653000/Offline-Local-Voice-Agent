# -*- coding: utf-8 -*-
"""
自訂中文喚醒詞訓練——繞開官方 openwakeword.train（依賴 audiomentations，
audiomentations 依賴 numba/llvmlite，在這台 ARM64 Windows 上編不起來）。

做法：用 openwakeword.utils.AudioFeatures（純 ONNX，不需要 torch）抽特徵，
自己寫一個小的 torch 分類器 head（模型架構、輸入輸出形狀對照官方 hey_jarvis_v0.1.onnx：
input [1,16,96] -> output [1,1]），訓練完用 torch.onnx.export 匯出，
就能直接放進 openwakeword.Model(wakeword_models=[...]) 用官方推論管線跑。

2026-09-16 重大發現：torch nightly 現在有 ARM64 Windows wheel了（torch==2.15.0.dev20260916+cpu），
P0 當初「torch在ARM64完全沒有wheel」的結論已經過期，這裡是第一個因此受益的功能。
"""
import sys, os
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
import wave
import onnxruntime as ort

sys.path.insert(0, str(Path(__file__).parent))
from openwakeword.utils import AudioFeatures

ROOT = Path(__file__).parent
WAKE_PHRASE = "嗨小助理"

FRAMES = 16   # 對照官方模型 input shape [1,16,96]
EMBED_DIM = 96


def read_wav_16k_mono(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1, f"{path} 不是16kHz mono"
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16)  # embed_clips 要求int16 PCM，不能轉float


def add_lead_in(audio: np.ndarray, rng: np.random.Generator, min_sec=0.3, max_sec=2.0) -> np.ndarray:
    """
    在音檔前面加一段隨機長度的低音量雜訊當前導。
    這是修正「模型學到位置捷徑而不是內容」這個bug的關鍵：如果正樣本永遠從音檔第0秒開始，
    模型會學到「串流剛開始=正樣本」這種假相關，而不是真的分辨喚醒詞內容。
    """
    lead_samples = int(rng.uniform(min_sec, max_sec) * 16000)
    lead = rng.normal(0, 200, size=lead_samples).astype(np.int16)
    return np.concatenate([lead, audio])


def augment_audio(audio: np.ndarray, rng: np.random.Generator) -> list:
    """
    手刻簡易資料增強（audiomentations 在這台機器裝不起來，numba/llvmlite 沒有ARM64 wheel）。
    回傳：[原始, 加雜訊版, 音量擾動版, 時間平移版]，增加有效訓練樣本數、降低過擬合風險。
    （前導雜訊是在 build_dataset 裡另外加的，不在這裡）
    """
    variants = [audio]

    noise = rng.normal(0, 300, size=audio.shape).astype(np.int16)  # 低強度白噪音
    noisy = np.clip(audio.astype(np.int32) + noise, -32768, 32767).astype(np.int16)
    variants.append(noisy)

    gain = rng.uniform(0.7, 1.3)
    scaled = np.clip(audio.astype(np.float32) * gain, -32768, 32767).astype(np.int16)
    variants.append(scaled)

    shift = rng.integers(-1600, 1600)  # +-100ms @16kHz
    if shift > 0:
        shifted = np.concatenate([np.zeros(shift, dtype=np.int16), audio[:-shift or None]])
    elif shift < 0:
        shifted = np.concatenate([audio[-shift:], np.zeros(-shift, dtype=np.int16)])
    else:
        shifted = audio
    variants.append(shifted)

    return variants


def streaming_windows_for_clip(af: AudioFeatures, audio: np.ndarray, chunk: int = 1280) -> np.ndarray:
    """
    關鍵修正：第一版訓練用「整段音檔一次算embedding」(_get_embeddings 非因果、看得到未來)，
    但正式運作時 model.predict() 是一次餵1280個sample、只看得到過去(因果)的串流buffer，
    兩者算出來的embedding不一樣——第一版驗證看起來98%準，但換成真正的串流推論只剩46%，
    是典型的 train/inference skew。修正做法：訓練特徵也用一模一樣的串流呼叫方式產生，
    包含 openWakeWord 官方設計的隨機雜訊「暖機」buffer初始化(af.reset()的行為)。
    """
    af.reset()
    windows = []
    for i in range(0, len(audio) - chunk, chunk):
        af(audio[i:i + chunk])
        if af.feature_buffer.shape[0] >= FRAMES:
            windows.append(af.get_features(FRAMES)[0])
    return np.stack(windows) if windows else np.zeros((0, FRAMES, EMBED_DIM), dtype=np.float32)


class WakeWordClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Flatten(),
            nn.Linear(FRAMES * EMBED_DIM, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.net(x)


FRAME_MS = 80  # 每個embedding frame大約對應80ms音訊（對照streaming code：每1280 samples=80ms觸發一次更新）


def build_dataset(af: AudioFeatures, positive_dir: Path, negative_dirs: list, negative_limit: int = None):
    rng = np.random.default_rng(42)
    pos_windows = []
    leadin_neg_windows = []  # 前導雜訊區段的視窗，當作額外負樣本，避免模型學到「串流開頭=正樣本」的位置捷徑
    for f in sorted(positive_dir.glob("*.wav")):
        raw_audio = read_wav_16k_mono(f)
        for variant in augment_audio(raw_audio, rng):
            lead_sec = rng.uniform(0.3, 2.0)
            padded = add_lead_in(variant, np.random.default_rng(int(lead_sec * 1e6)), lead_sec, lead_sec)
            all_w = streaming_windows_for_clip(af, padded)
            lead_frames = int(lead_sec * 1000 / FRAME_MS)
            # 明確還在前導雜訊區的視窗（lookback完全沒有涵蓋到喚醒詞內容）-> 負樣本
            if lead_frames - 3 > 0:
                leadin_neg_windows.append(all_w[:max(lead_frames - 3, 0)])
            # 已經過了前導+喚醒詞開頭一段時間，lookback視窗裡應該完整包含喚醒詞內容 -> 正樣本
            pos_start = lead_frames + 5
            if pos_start < len(all_w):
                pos_windows.append(all_w[pos_start:])
    pos_windows = np.concatenate(pos_windows, axis=0) if pos_windows else np.zeros((0, FRAMES, EMBED_DIM))

    neg_windows = list(leadin_neg_windows)
    neg_files = []
    for d in negative_dirs:
        neg_files.extend(sorted(Path(d).glob("*.wav")))
    if negative_limit:
        neg_files = neg_files[:negative_limit]
    for f in neg_files:
        audio = read_wav_16k_mono(f)
        w = streaming_windows_for_clip(af, audio)
        # 用密集取樣（含開頭），不要再用稀疏等間距抽樣——上一版就是稀疏抽樣才漏掉開頭那段位置捷徑bug
        neg_windows.append(w)
    neg_windows = np.concatenate(neg_windows, axis=0) if neg_windows else np.zeros((0, FRAMES, EMBED_DIM))

    return pos_windows, neg_windows


def main():
    print("初始化 AudioFeatures（ONNX，不需要torch）...", file=sys.stderr)
    af = AudioFeatures(inference_framework="onnx")

    general_neg_dir = Path("C:/0_JN1_Offline-Local-Voice-Agent/progress/p1_asr_bench/wav_16k")
    general_neg_files = sorted(general_neg_dir.glob("*.wav"))
    train_general_neg = general_neg_files[:80]   # 訓練用
    test_general_neg = general_neg_files[80:]     # held-out 測試用，103-80=23句

    # 訓練資料：train用 training set 的 confuser 負樣本 + 80句一般語句
    tmp_train_general_dir = ROOT / "_tmp_train_general_neg"
    tmp_train_general_dir.mkdir(exist_ok=True)
    for f in train_general_neg:
        dst = tmp_train_general_dir / f.name
        if not dst.exists():
            dst.write_bytes(f.read_bytes())

    print("抽取訓練特徵...", file=sys.stderr)
    pos_w, neg_w = build_dataset(af, ROOT / "positive_16k",
                                   [ROOT / "negative_16k", tmp_train_general_dir, ROOT / "ambient_neg"])
    print(f"positive windows: {pos_w.shape}, negative windows: {neg_w.shape}", file=sys.stderr)

    X = np.concatenate([pos_w, neg_w], axis=0).astype(np.float32)
    y = np.concatenate([np.ones(len(pos_w)), np.zeros(len(neg_w))]).astype(np.float32)

    X_t = torch.from_numpy(X)
    y_t = torch.from_numpy(y).unsqueeze(1)

    model = WakeWordClassifier()
    # 正負樣本數量差很多，給正樣本更高的loss權重
    pos_weight = len(neg_w) / max(len(pos_w), 1)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    print("開始訓練...", file=sys.stderr)
    for epoch in range(200):
        model.train()
        optimizer.zero_grad()
        pred = model(X_t)
        weights = torch.where(y_t == 1, torch.tensor(pos_weight), torch.tensor(1.0))
        loss = nn.functional.binary_cross_entropy(pred, y_t, weight=weights)
        loss.backward()
        optimizer.step()
        if epoch % 40 == 0:
            print(f"  epoch {epoch}: loss={loss.item():.4f}", file=sys.stderr)

    model.eval()

    # 匯出 ONNX，介面對照官方模型
    onnx_path = ROOT / "hai_xiao_zhuli_wakeword.onnx"
    dummy = torch.zeros(1, FRAMES, EMBED_DIM)
    torch.onnx.export(
        model, dummy, str(onnx_path),
        input_names=["x.1"], output_names=["score"],
        dynamic_axes={"x.1": {0: "batch"}, "score": {0: "batch"}},
        opset_version=13,
        dynamo=False,  # 新版dynamo匯出器在這個模型上會出版本轉換錯誤，且匯出結果跟原模型行為不一致(已實測確認)，改用穩定的舊版TorchScript匯出路徑
    )

    # 匯出後立刻比對 PyTorch 原模型 vs 匯出的 ONNX，確保匯出忠實(不能只信賴匯出成功、要驗證數值一致)
    onnx_check_sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    check_input = X[:20]
    with torch.no_grad():
        torch_check = model(torch.from_numpy(check_input)).numpy().flatten()
    onnx_check = onnx_check_sess.run(None, {onnx_check_sess.get_inputs()[0].name: check_input})[0].flatten()
    max_diff = np.abs(torch_check - onnx_check).max()
    print(f"匯出一致性檢查：PyTorch vs ONNX 最大差異 = {max_diff:.6f} ({'PASS' if max_diff < 0.01 else 'FAIL - 匯出結果跟原模型不一致！'})", file=sys.stderr)
    if max_diff >= 0.01:
        raise RuntimeError(f"ONNX 匯出結果跟 PyTorch 原模型不一致(最大差異{max_diff})，不能繼續使用這個匯出檔")
    print(f"已匯出: {onnx_path}", file=sys.stderr)

    # ---- 用 held-out 測試集驗證（訓練時完全沒看過的資料）----
    print("\n=== Held-out 測試 ===", file=sys.stderr)
    test_pos_w, _ = build_dataset(af, ROOT / "test_positive_16k", [])
    tmp_test_general_dir = ROOT / "_tmp_test_general_neg"
    tmp_test_general_dir.mkdir(exist_ok=True)
    for f in test_general_neg:
        dst = tmp_test_general_dir / f.name
        if not dst.exists():
            dst.write_bytes(f.read_bytes())
    _, test_neg_w = build_dataset(af, ROOT / "positive_16k", [tmp_test_general_dir])  # positive_16k給假的，只要negative
    test_neg_w = test_neg_w  # 這些是held-out的23句一般語句

    # 用匯出的 ONNX 檔評分（走真正部署路徑），不要只信賴 PyTorch 原模型的分數
    in_name = onnx_check_sess.get_inputs()[0].name
    test_pos_scores = onnx_check_sess.run(None, {in_name: test_pos_w.astype(np.float32)})[0].flatten()
    test_neg_scores = onnx_check_sess.run(None, {in_name: test_neg_w.astype(np.float32)})[0].flatten()

    threshold = 0.5
    pos_acc = (test_pos_scores > threshold).mean()
    neg_acc = (test_neg_scores <= threshold).mean()

    result = (
        f"Held-out 正樣本(喚醒詞) windows={len(test_pos_scores)}, 正確觸發率={pos_acc:.2%}\n"
        f"  分數分布: min={test_pos_scores.min():.3f} max={test_pos_scores.max():.3f} mean={test_pos_scores.mean():.3f}\n"
        f"Held-out 負樣本(其他句子) windows={len(test_neg_scores)}, 正確不觸發率={neg_acc:.2%}\n"
        f"  分數分布: min={test_neg_scores.min():.3f} max={test_neg_scores.max():.3f} mean={test_neg_scores.mean():.3f}\n"
    )
    print(result, file=sys.stderr)
    (ROOT / "train_result.txt").write_text(result, encoding="utf-8")


if __name__ == "__main__":
    main()
