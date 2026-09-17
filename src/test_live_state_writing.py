# -*- coding: utf-8 -*-
"""
直接驗證 LiveStateWriter 真的會在整個事件序列中，把正確的狀態依序寫進 console/live_state.json。
用模擬音訊（跟test_listen_loop_simulated.py一樣），但這次改用run_live()裡完全一樣的on_event邏輯，
在每個關鍵時間點把 live_state.json 的當下內容記錄下來，最後印出完整的狀態變化序列。
"""
import sys, json, wave, time
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from listen_loop import ListenLoop, LiveStateWriter, CHUNK, SR, LIVE_STATE_FILE

def read_wav(path):
    with wave.open(str(path), "rb") as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16)

def silence(seconds):
    return np.zeros(int(seconds * SR), dtype=np.int16)

wake_audio = read_wav(Path(__file__).parent / "sim_wake_16k.wav")
cmd_audio = read_wav(Path(__file__).parent / "sim_cmd_16k.wav")
stream = np.concatenate([silence(1.5), wake_audio, silence(0.5), cmd_audio, silence(2.0)])

state = LiveStateWriter()
state.update("idle", "待命中，說「嗨小助理」開始")
state_snapshots = [json.loads(LIVE_STATE_FILE.read_text(encoding="utf-8"))]

def on_event(e):
    # 這裡故意跟 run_live() 裡的 on_event 邏輯保持一致（對照 docs/07 進度報告，之前兩邊各自
    # 維護一份，run_live() 改了PlanRunner事件格式但這裡沒跟著改，導致這個測試沒抓到真實bug）。
    et = e.get("type")
    if et == "wake_detected":
        state.update("wake_detected", "我聽到你了！")
    elif et == "wake_tail_ended":
        state.update("listening_command", "請說出你想做的事")
    elif et == "utterance_end":
        state.update("thinking", "我在想...")
    elif et == "asr_result":
        state.update("thinking", "我在想...", transcript=e["text"])
    elif et == "executing":
        state.update("executing", "正在執行你的指令...")
    elif et == "action_result":
        msg = e.get("summary") or e.get("error") or "完成了"
        state.update("idle", "待命中，說「嗨小助理」開始", response=str(msg))
    elif et == "needs_confirmation":
        state.update("waiting_confirmation", f"這個動作需要確認：{e['reason']}")
    elif et == "stopped_by_voice":
        state.update("idle", "好，已經取消了，說「嗨小助理」重新開始")
    state_snapshots.append(json.loads(LIVE_STATE_FILE.read_text(encoding="utf-8")))

loop = ListenLoop(on_event=on_event)
utterance = None
for i in range(0, len(stream) - CHUNK, CHUNK):
    result = loop.process_chunk(stream[i:i+CHUNK])
    if result is not None:
        utterance = result
        break
if utterance is not None:
    loop.handle_utterance(utterance)

with open(Path(__file__).parent / "live_state_sequence_result.txt", "w", encoding="utf-8") as f:
    for s in state_snapshots:
        f.write(json.dumps(s, ensure_ascii=False) + "\n")
print("done, snapshots:", len(state_snapshots))
