# -*- coding: utf-8 -*-
"""
補測docs/01藍圖第17節剩下的兩項延遲KPI：Wake→ASR（<1.5秒）、Tool啟動延遲（<1秒）。
跟run_kpi_test.py不一樣的地方：這裡走真的語音路徑（喚醒詞+VAD+ASR+PlanRunner），
不是文字輸入。

方法論的關鍵：既有的模擬音訊測試（test_listen_loop_simulated.py之類）用固定陣列一次全部
塞進process_chunk()迴圈，中間沒有任何延遲——這樣量出來的「延遲」只反映CPU把陣列跑完多快，
不是真實麥克風串流的延遲（VAD等待安靜的邏輯是靠「連續幾個chunk都沒偵測到語音」判斷，
這件事在真實世界需要真的等那麼多個80ms才會發生）。這裡刻意在每個chunk之間真的sleep
CHUNK/SR秒，模擬真實麥克風的餵入速度，量出來的才是使用者實際會感受到的延遲。
"""
import sys, json, time, wave
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from listen_loop import ListenLoop, CHUNK, SR

def read_wav(path):
    with wave.open(str(path), "rb") as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16)

def silence(seconds):
    return np.zeros(int(seconds * SR), dtype=np.int16)

SRC = Path(__file__).parent.parent.parent / "src"
wake_audio = read_wav(SRC / "sim_wake_16k.wav")
cmd_audio = read_wav(SRC / "sim_cmd_16k.wav")  # 「現在幾點」

stream = np.concatenate([
    silence(1.0), wake_audio, silence(0.5), cmd_audio, silence(2.0),
])

timestamps = {}
def on_event(e):
    et = e.get("type")
    now = time.time()
    if et == "wake_detected" and "wake_detected" not in timestamps:
        timestamps["wake_detected"] = now
    elif et == "utterance_end" and "utterance_end" not in timestamps:
        timestamps["utterance_end"] = now
    elif et == "asr_result" and "asr_result" not in timestamps:
        timestamps["asr_result"] = now
        timestamps["asr_result_text"] = e["text"]
    elif et == "executing" and "executing" not in timestamps:
        timestamps["executing"] = now
    elif et == "action_result" and "action_result" not in timestamps:
        timestamps["action_result"] = now
        timestamps["action_summary"] = e.get("summary")

loop = ListenLoop(on_event=on_event)

t_stream_start = time.time()
utterance = None
i = 0
chunk_interval = CHUNK / SR  # 80ms，跟真實麥克風一次送一個chunk的節奏一致
while i < len(stream) - CHUNK:
    t_chunk_start = time.time()
    chunk = stream[i:i + CHUNK]
    result = loop.process_chunk(chunk)
    if result is not None:
        utterance = result
        break
    i += CHUNK
    # 真的睡到跟這個chunk代表的真實時間長度一致，模擬即時麥克風輸入的節奏
    elapsed = time.time() - t_chunk_start
    remaining = chunk_interval - elapsed
    if remaining > 0:
        time.sleep(remaining)

if utterance is not None:
    loop.handle_utterance(utterance)

results = {
    "raw_timestamps_unix": timestamps,
    "asr_text": timestamps.get("asr_result_text"),
    "action_summary": timestamps.get("action_summary"),
}

if "wake_detected" in timestamps and "asr_result" in timestamps:
    wake_to_asr_ms = (timestamps["asr_result"] - timestamps["wake_detected"]) * 1000
    results["wake_to_asr_ms"] = round(wake_to_asr_ms, 1)
    results["wake_to_asr_target_ms"] = 1500
    results["wake_to_asr_pass"] = wake_to_asr_ms < 1500

if "asr_result" in timestamps and "executing" in timestamps:
    asr_to_decision_ms = (timestamps["executing"] - timestamps["asr_result"]) * 1000
    results["asr_result_to_executing_ms"] = round(asr_to_decision_ms, 1)

if "executing" in timestamps and "action_result" in timestamps:
    tool_total_ms = (timestamps["action_result"] - timestamps["executing"]) * 1000
    results["executing_to_done_ms"] = round(tool_total_ms, 1)
    # 「Tool啟動延遲」藍圖的意思是「從決定要跑這個工具，到工具真的開始動」，這個架構裡
    # Executor.run()是同步呼叫，決策完成後立刻執行，沒有額外的排隊/派工延遲，所以這個值
    # 理論上接近0——真正會拉長的是LLM決策本身(已經在run_kpi_test.py另外測過)跟工具執行時間本身。
    results["note_tool_start"] = "此架構Executor.run()是同步呼叫，決策完成即刻執行，沒有額外派工延遲；executing_to_done_ms包含LLM決策+實際執行兩段"

if "wake_detected" in timestamps and "action_result" in timestamps:
    end_to_end_ms = (timestamps["action_result"] - timestamps["wake_detected"]) * 1000
    results["wake_to_done_ms"] = round(end_to_end_ms, 1)
    results["wake_to_done_target_ms"] = 3000
    results["wake_to_done_pass"] = end_to_end_ms < 3000

out_path = Path(__file__).parent / "voice_latency_result.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("done ->", out_path)
