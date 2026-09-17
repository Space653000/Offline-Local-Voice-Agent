# -*- coding: utf-8 -*-
"""
用SAPI合成語音停止指令的測試音檔（16kHz/16bit/mono，跟 sim_cmd_16k.wav 等其他模擬測試音檔格式一致），
給 test_stop_command_simulated.py 用，驗證「停止」「取消」真的能被 is_stop_command() 辨識並打斷流程。
"""
import win32com.client
from pathlib import Path

ROOT = Path(__file__).parent
SAFT16kHz16BitMono = 19  # SpeechLib enum值，34是錯的（第一次寫錯，結果SAPI退回預設44.1kHz輸出，害ASR測試吃到取樣率不合的音檔）

phrases = {
    "stop_16k.wav": "停止",
    "cancel_16k.wav": "取消",
}

voice = win32com.client.Dispatch("SAPI.SpVoice")
for v in voice.GetVoices():
    if "Hanhan" in v.GetDescription():
        voice.Voice = v
        break

for fname, text in phrases.items():
    stream = win32com.client.Dispatch("SAPI.SpFileStream")
    fmt = win32com.client.Dispatch("SAPI.SpAudioFormat")
    fmt.Type = SAFT16kHz16BitMono
    stream.Format = fmt
    out_path = str(ROOT / fname)
    stream.Open(out_path, 3)  # SSFMCreateForWrite
    voice.AudioOutputStream = stream
    voice.Speak(text)
    stream.Close()
    print("wrote", out_path)
