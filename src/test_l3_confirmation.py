# -*- coding: utf-8 -*-
"""
直接測試 L3 危險操作的確認機制：故意不透過完整LLM選工具（power_op目前故意不開放給LLM選，
因為還沒有真的實作動作本體），只單獨測「_voice_confirm 面對 L3 決策時的行為」本身。

測兩種情境：
1. 使用者隨口說「對啊好」（一般L2那種輕鬆同意）-> 應該被拒絕，因為L3不接受單純的「是」
2. 使用者真的講出關鍵字「確認執行」-> 應該被接受
"""
import sys, json, wave
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from listen_loop import ListenLoop, CHUNK, SR
from policy.policy_engine import PolicyEngine

def read_wav(path):
    with wave.open(str(path), "rb") as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16)

def silence(seconds):
    return np.zeros(int(seconds * SR), dtype=np.int16)

policy = PolicyEngine()
decision = policy.evaluate("power_op", {"action": "shutdown"})
print("decision level:", decision.level.name, "requires_typed_confirmation:", decision.requires_typed_confirmation, file=sys.stderr)

results = {}

for label, reply_file in [("casual_yes", "confirm_l3_casual_16k.wav"), ("keyword", "confirm_l3_keyword_16k.wav")]:
    reply_audio = read_wav(Path(__file__).parent / reply_file)
    stream = np.concatenate([silence(0.3), reply_audio, silence(2.0)])
    pos = [0]
    def next_chunk():
        i = pos[0]
        pos[0] += CHUNK
        if i + CHUNK > len(stream):
            return np.zeros(CHUNK, dtype=np.int16)
        return stream[i:i + CHUNK]

    events = []
    loop = ListenLoop(on_event=lambda e: events.append(e), chunk_source=next_chunk)
    approved = loop._voice_confirm(decision)
    results[label] = {"approved": approved, "events": events}

with open(Path(__file__).parent / "l3_confirmation_result.txt", "w", encoding="utf-8") as f:
    for label, r in results.items():
        f.write(f"=== {label} ===\n")
        f.write(f"approved: {r['approved']}\n")
        for e in r["events"]:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
        f.write("\n")

print("done")
