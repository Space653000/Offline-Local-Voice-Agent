# -*- coding: utf-8 -*-
"""
測試 L2 確認流程：喚醒 -> 「把Wi-Fi關掉」(network_toggle 現在是L2) -> 助理問要不要繼續 ->
回答「不要，先取消」-> 應該被正確拒絕，Wi-Fi不會真的被關掉。
這個測試刻意用「拒絕」分支，不用「同意」分支，避免真的觸發會影響使用者網路的動作。
"""
import sys, json, wave
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from listen_loop import ListenLoop, CHUNK, SR

events = []
def on_event(e): events.append(e)

def read_wav(path):
    with wave.open(str(path), "rb") as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16)

def silence(seconds):
    return np.zeros(int(seconds * SR), dtype=np.int16)

wake_audio = read_wav(Path(__file__).parent / "sim_wake_16k.wav")
cmd_audio = read_wav(Path(__file__).parent / "confirm_cmd_16k.wav")
reply_audio = read_wav(Path(__file__).parent / "confirm_no_16k.wav")

# 完整串流：喚醒 -> 停頓 -> 指令(關Wi-Fi) -> 停頓(等助理問完問題) -> 回答(不要) -> 靜音
stream = np.concatenate([
    silence(1.5), wake_audio, silence(0.5), cmd_audio, silence(2.0),
    reply_audio, silence(2.0),
])

pos = [0]
def next_chunk():
    i = pos[0]
    pos[0] += CHUNK
    if i + CHUNK > len(stream):
        return np.zeros(CHUNK, dtype=np.int16)
    return stream[i:i + CHUNK]

loop = ListenLoop(on_event=on_event, chunk_source=next_chunk)

# 先確認Wi-Fi目前狀態（測試前後應該完全沒變化，因為這次測的是拒絕分支）
import sys as _s
_s.path.insert(0, str(Path(__file__).parent))
from tools import basic_tools
before_state = None
try:
    result = __import__("subprocess").run(["netsh", "interface", "show", "interface"],
                                           capture_output=True, text=True, encoding="utf-8", errors="ignore")
    before_state = result.stdout
except Exception as e:
    before_state = f"讀取失敗: {e}"

utterance = None
for i in range(0, len(stream) - CHUNK, CHUNK):
    result = loop.process_chunk(next_chunk())
    if result is not None:
        utterance = result
        break
if utterance is not None:
    loop.handle_utterance(utterance)

after_state = __import__("subprocess").run(["netsh", "interface", "show", "interface"],
                                            capture_output=True, text=True, encoding="utf-8", errors="ignore").stdout

with open(Path(__file__).parent / "voice_confirmation_test_result.txt", "w", encoding="utf-8") as f:
    for e in events:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    f.write("\nWi-Fi介面狀態測試前後是否相同: " + str(before_state == after_state) + "\n")

print("done")
