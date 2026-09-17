# -*- coding: utf-8 -*-
"""
完整模擬測試 VoiceFrontDesk：用預先合成好的三句回答，模擬使用者用語音回答三輪問題，
驗證整個 Front Desk 引導流程真的能用講的走完，最後產生 ORDER.md。
"""
import sys, json, wave
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from voice_dialog import VoiceFrontDesk
from listen_loop import CHUNK, SR

events = []
def on_event(e):
    events.append(e)

def read_wav(path):
    with wave.open(str(path), "rb") as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16)

def silence(seconds):
    return np.zeros(int(seconds * SR), dtype=np.int16)

ROOT = Path(__file__).parent
answer1 = read_wav(ROOT / "vfd_answer1_16k.wav")
answer2 = read_wav(ROOT / "vfd_answer2_16k.wav")
answer3 = read_wav(ROOT / "vfd_answer3_16k.wav")

# 每句回答前後都留夠長的靜音，確保錄音邏輯能正確切出這一句
stream = np.concatenate([
    silence(0.3), answer1, silence(2.0),
    silence(0.3), answer2, silence(2.0),
    silence(0.3), answer3, silence(2.0),
    silence(5.0),  # 保險多留一點，避免流跑完
])

pos = [0]
def next_chunk():
    i = pos[0]
    pos[0] += CHUNK
    if i + CHUNK > len(stream):
        return np.zeros(CHUNK, dtype=np.int16)  # 流跑完了就補靜音，不要炸掉
    return stream[i:i + CHUNK]

vfd = VoiceFrontDesk(next_chunk, on_event=on_event)
result = vfd.run("我的筆電喇叭低頻聲音怪怪的", input_mode="voice",
                  handoff_dir=Path("C:/0_JN1_AERIS_HANDOFF/orders"))

with open(ROOT / "voice_frontdesk_test_result.txt", "w", encoding="utf-8") as f:
    for e in events:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    f.write(f"\nFINAL RESULT: {json.dumps(result, ensure_ascii=False)}\n")

print("done:", result)
