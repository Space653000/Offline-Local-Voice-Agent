# -*- coding: utf-8 -*-
"""
驗證 docs/01 第10節：使用者講「停止/取消」要能真的透過 ASR 被辨識出來，並且：
1. listen_loop.ListenLoop.handle_utterance() 遇到停止指令會直接發出 stopped_by_voice 事件，不會誤判成一般指令
2. frontdesk.voice_dialog.VoiceFrontDesk 在多輪引導流程中途聽到停止指令，會中斷並回傳 CANCELLED_BY_USER

用真的合成語音(SAPI) -> 真的跑 whisper.cpp ASR -> 真的餵進 is_stop_command()，不是直接塞字串進去，
避免「以為ASR會辨識成『停止』結果其實辨識成別的字」這種沒驗證過的假設。
"""
import sys, json, wave
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from listen_loop import ListenLoop, run_asr, is_stop_command, CHUNK, SR

ROOT = Path(__file__).parent


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16)


results = {}

# --- Test 1: ASR真的能把合成的「停止」「取消」音檔辨識出可被is_stop_command抓到的文字 ---
for fname in ["stop_16k.wav", "cancel_16k.wav"]:
    audio = read_wav(ROOT / fname)
    text = run_asr(audio)
    results[f"asr_{fname}"] = {"text": text, "is_stop": is_stop_command(text)}

# --- Test 2: ListenLoop.handle_utterance 對停止語音的反應 ---
events = []
loop = ListenLoop(on_event=lambda e: events.append(e))
stop_audio = read_wav(ROOT / "stop_16k.wav")
loop.handle_utterance(stop_audio)
results["handle_utterance_events"] = events

# --- Test 3: VoiceFrontDesk 中途聽到停止指令會中斷 ---
sys.path.insert(0, str(ROOT / "frontdesk"))
from voice_dialog import VoiceFrontDesk

answer1 = read_wav(ROOT / "frontdesk" / "vfd_answer1_16k.wav")


def silence(seconds):
    return np.zeros(int(seconds * SR), dtype=np.int16)


# 第一輪先回答問題（正常流程），第二輪講「停止」，驗證能在流程中途打斷
stream = np.concatenate([
    silence(0.3), answer1, silence(2.0),
    silence(0.3), stop_audio, silence(2.0),
    silence(5.0),
])
pos = [0]


def next_chunk():
    i = pos[0]
    pos[0] += CHUNK
    if i + CHUNK > len(stream):
        return np.zeros(CHUNK, dtype=np.int16)
    return stream[i:i + CHUNK]


vfd_events = []
vfd = VoiceFrontDesk(next_chunk, on_event=lambda e: vfd_events.append(e))
vfd_result = vfd.run("我的筆電喇叭低頻聲音怪怪的", input_mode="voice",
                      handoff_dir=Path("C:/0_JN1_AERIS_HANDOFF/orders"))
results["voice_frontdesk_events"] = vfd_events
results["voice_frontdesk_result"] = vfd_result

with open(ROOT / "stop_command_test_result.txt", "w", encoding="utf-8") as f:
    f.write(json.dumps(results, ensure_ascii=False, indent=2))

print("done")
print(json.dumps({k: v for k, v in results.items() if k != "voice_frontdesk_events"}, ensure_ascii=False, indent=2))
