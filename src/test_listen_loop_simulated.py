# -*- coding: utf-8 -*-
"""
用合成音訊模擬麥克風即時輸入，驗證 listen_loop.py 整條邏輯（不需要真人對麥克風講話）：
靜音 -> 喚醒詞「嗨小助理」-> 停頓 -> 指令「現在幾點」-> 靜音
一塊一塊(80ms)餵進去，跟正式麥克風輸入的處理方式完全一樣。
"""
import sys, json, wave
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from listen_loop import ListenLoop, CHUNK, SR

events = []


def on_event(e):
    events.append(e)


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16)


def silence(seconds):
    return np.zeros(int(seconds * SR), dtype=np.int16)


wake_audio = read_wav(Path(__file__).parent / "sim_wake_16k.wav")
cmd_audio = read_wav(Path(__file__).parent / "sim_cmd_16k.wav")

stream = np.concatenate([
    silence(1.5),   # 開始先靜音，模擬待命狀態
    wake_audio,     # 講喚醒詞
    silence(0.5),   # 喚醒詞講完到開始講指令中間的自然停頓
    cmd_audio,      # 講指令
    silence(2.0),   # 講完後的靜音，應該觸發「講完了」判斷
])

loop = ListenLoop(on_event=on_event)
utterance = None
for i in range(0, len(stream) - CHUNK, CHUNK):
    chunk = stream[i:i + CHUNK]
    result = loop.process_chunk(chunk)
    if result is not None:
        utterance = result
        break

if utterance is not None:
    loop.handle_utterance(utterance)
else:
    events.append({"type": "ERROR", "note": "整個模擬串流跑完，從沒有偵測到「講完一句話」，喚醒詞可能沒被觸發"})

with open(Path(__file__).parent / "listen_loop_test_result.txt", "w", encoding="utf-8") as f:
    for e in events:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")

print("done")
