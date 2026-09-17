# -*- coding: utf-8 -*-
"""
用真正的部署路徑測試：openwakeword.Model 載入我們訓練的 onnx 檔，
餵真實音檔（streaming chunk方式，跟正式運作時一樣），不是走訓練時的捷徑。
"""
import sys, wave
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from openwakeword.model import Model

ROOT = Path(__file__).parent
model = Model(wakeword_models=[str(ROOT / "hai_xiao_zhuli_wakeword.onnx")], inference_framework="onnx")
model_name = list(model.models.keys())[0]
print(f"載入的模型名稱: {model_name}", file=sys.stderr)


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16)


def max_score_for_clip(path, chunk=1280):
    model.reset()
    audio = read_wav(path)
    max_score = 0.0
    for i in range(0, len(audio) - chunk, chunk):
        pred = model.predict(audio[i:i + chunk])
        max_score = max(max_score, pred[model_name])
    return max_score


results = []

# held-out 正樣本（訓練時完全沒用過的 rate 變化）
for f in sorted((ROOT / "test_positive_16k").glob("*.wav")):
    s = max_score_for_clip(f)
    results.append((f.name, "應觸發(喚醒詞)", s, s > 0.5))

# 混淆詞負樣本（訓練時已經看過，屬於樣本內測試，僅供參考）
for f in sorted((ROOT / "negative_16k").glob("*.wav"))[:5]:
    s = max_score_for_clip(f)
    results.append((f.name, "不應觸發(近似詞,訓練時看過)", s, s <= 0.5))

# 完全沒看過的一般語句（P1的103句，我們只用了前80句訓練，測後面幾句)
general_dir = Path("C:/0_JN1_Offline-Local-Voice-Agent/progress/p1_asr_bench/wav_16k")
for f in sorted(general_dir.glob("*.wav"))[80:95]:
    s = max_score_for_clip(f)
    results.append((f.name, "不應觸發(一般語句,held-out)", s, s <= 0.5))

with open(ROOT / "real_inference_result.txt", "w", encoding="utf-8") as out:
    correct = 0
    for name, label, score, ok in results:
        line = f"{name:20s} {label:28s} score={score:.3f} {'OK' if ok else 'FAIL'}"
        out.write(line + "\n")
        if ok:
            correct += 1
    out.write(f"\n總計: {correct}/{len(results)} = {correct/len(results):.1%}\n")

print("done", file=sys.stderr)
