# -*- coding: utf-8 -*-
"""
安全關鍵測試：使用者2026-09-18明確要求，取代原本規劃的8小時無人值守誤觸發測試——
不是去統計「多久誤觸發一次」，而是直接保證「喚醒開關沒打勾，誤觸發本身就不可能導致
任何動作」。這個測試用跟test_listen_loop_simulated.py一樣的真實合成喚醒詞音檔，
驗證這個保證真的成立，不是憑空宣稱。

這是安全機制，之後任何人改動listen_loop.py的process_chunk()都不該讓這個測試失敗——
一旦失敗，代表「喚醒開關關閉時電腦仍可能自己做事」這個使用者明確要求的保證被破壞了。
"""
import sys, wave
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from wake_setting import set_wake_word_enabled, is_wake_word_enabled
from listen_loop import ListenLoop, CHUNK, SR


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16)


def silence(seconds):
    return np.zeros(int(seconds * SR), dtype=np.int16)


wake_audio = read_wav(Path(__file__).parent / "sim_wake_16k.wav")
cmd_audio = read_wav(Path(__file__).parent / "sim_cmd_16k.wav")
stream = np.concatenate([silence(1.5), wake_audio, silence(0.5), cmd_audio, silence(2.0)])


def run_stream():
    events = []
    loop = ListenLoop(on_event=lambda e: events.append(e))
    for i in range(0, len(stream) - CHUNK, CHUNK):
        loop.process_chunk(stream[i:i + CHUNK])
    return events


original_setting = is_wake_word_enabled()
try:
    print("=== 測試1：喚醒開關關閉（預設值），講真的喚醒詞音檔應該完全沒有任何事件觸發 ===")
    set_wake_word_enabled(False)
    assert is_wake_word_enabled() is False
    events_off = run_stream()
    print("觸發的事件數量:", len(events_off))
    assert len(events_off) == 0, f"安全性bug：開關關閉時仍觸發了事件 {events_off}"
    print("通過\n")

    print("=== 測試2：新建的ListenLoop在開關關閉時，預設狀態也必須是IDLE，不能繞過關閉狀態直接動作 ===")
    from listen_loop import State
    loop2 = ListenLoop(on_event=lambda e: None)
    assert loop2.state == State.IDLE
    print("通過\n")

    print("=== 測試3：喚醒開關打開後，同一段真實音檔要能正常喚醒+聽完指令（確認開關本身沒有把功能弄壞）===")
    set_wake_word_enabled(True)
    assert is_wake_word_enabled() is True
    events_on = run_stream()
    types = [e["type"] for e in events_on]
    print("事件類型:", types)
    assert "wake_detected" in types, "開關打開時，喚醒詞應該要能正常觸發"
    assert "utterance_end" in types, "開關打開時，應該要能正常錄完一句指令"
    print("通過\n")

    print("全部3個喚醒開關安全測試通過。")
finally:
    set_wake_word_enabled(original_setting)
