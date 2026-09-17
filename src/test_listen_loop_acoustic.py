# -*- coding: utf-8 -*-
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
cmd_audio = read_wav(Path(__file__).parent / "sim_cmd2_16k.wav")

stream = np.concatenate([silence(1.5), wake_audio, silence(0.5), cmd_audio, silence(2.0)])

loop = ListenLoop(on_event=on_event)
utterance = None
for i in range(0, len(stream) - CHUNK, CHUNK):
    result = loop.process_chunk(stream[i:i+CHUNK])
    if result is not None:
        utterance = result
        break

if utterance is not None:
    loop.handle_utterance(utterance)
else:
    events.append({"type": "ERROR", "note": "沒有偵測到講完一句話"})

with open(Path(__file__).parent / "listen_loop_acoustic_result.txt", "w", encoding="utf-8") as f:
    for e in events:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
print("done")
