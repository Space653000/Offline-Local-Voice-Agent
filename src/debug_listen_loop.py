# -*- coding: utf-8 -*-
import sys, wave
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from listen_loop import ListenLoop, VADStreamer, CHUNK, SR, VAD_ONNX, WAKEWORD_ONNX

def read_wav(path):
    with wave.open(str(path), "rb") as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16)

def silence(seconds):
    return np.zeros(int(seconds * SR), dtype=np.int16)

wake_audio = read_wav(Path(__file__).parent / "sim_wake_16k.wav")
cmd_audio = read_wav(Path(__file__).parent / "sim_cmd_16k.wav")

stream = np.concatenate([
    silence(1.5), wake_audio, silence(0.5), cmd_audio, silence(2.0),
])

from openwakeword.model import Model
wake_model = Model(wakeword_models=[str(WAKEWORD_ONNX)], inference_framework="onnx")
wake_name = list(wake_model.models.keys())[0]
vad = VADStreamer(VAD_ONNX)

lines = []
wake_end_idx = 1.5*SR + len(wake_audio)
pause_end_idx = wake_end_idx + 0.5*SR
cmd_end_idx = pause_end_idx + len(cmd_audio)

triggered = False
for idx, i in enumerate(range(0, len(stream) - CHUNK, CHUNK)):
    chunk = stream[i:i+CHUNK]
    t = i / SR
    phase = "silence1" if i < 1.5*SR else "wake" if i < wake_end_idx else "pause" if i < pause_end_idx else "cmd" if i < cmd_end_idx else "silence2"
    rms = np.sqrt(np.mean(chunk.astype(np.float64)**2))
    wake_score = wake_model.predict(chunk)[wake_name]
    is_speech = vad.is_speech(chunk)
    lines.append(f"chunk{idx:3d} t={t:5.2f}s phase={phase:9s} rms={rms:7.1f} wake_score={wake_score:.3f} vad_speech={is_speech}")
    if wake_score > 0.5 and not triggered:
        lines.append(f"  ^^^ WAKE TRIGGERED at chunk{idx} t={t:.2f}s")
        triggered = True

Path(__file__).parent.joinpath("debug_listen_loop_result.txt").write_text("\n".join(lines), encoding="utf-8")
print("done")
