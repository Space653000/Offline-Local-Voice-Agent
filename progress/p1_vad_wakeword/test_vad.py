import numpy as np, onnxruntime as ort, wave, sys, time
from pathlib import Path

MODEL = Path(__file__).parent / "silero_vad.onnx"
WAV_DIR = Path("C:/0_JN1_Offline-Local-Voice-Agent/progress/p1_asr_bench/wav_16k")

def read_wav(path):
    with wave.open(str(path), "rb") as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1
        data = w.readframes(w.getnframes())
    audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    return audio

sess = ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])

window = 512
context_size = 64
sr = np.array(16000, dtype=np.int64)

wavs = sorted(WAV_DIR.glob("*.wav"))[:20]
total_t = 0.0
detected = 0
for wav in wavs:
    audio = read_wav(wav)
    state = np.zeros((2, 1, 128), dtype=np.float32)
    context = np.zeros(context_size, dtype=np.float32)
    max_prob = 0.0
    t0 = time.perf_counter()
    for i in range(0, len(audio) - window, window):
        raw_chunk = audio[i:i+window]
        full_input = np.concatenate([context, raw_chunk]).reshape(1, -1)
        out = sess.run(None, {"input": full_input, "sr": sr, "state": state})
        prob, state = out[0], out[1]
        context = raw_chunk[-context_size:]
        max_prob = max(max_prob, float(prob[0][0]))
    elapsed = time.perf_counter() - t0
    total_t += elapsed
    is_speech = max_prob > 0.5
    if is_speech:
        detected += 1
    print(f"{wav.name}: max_speech_prob={max_prob:.3f} speech_detected={is_speech} time={elapsed*1000:.1f}ms", file=sys.stderr)

print(f"\nDetected speech in {detected}/{len(wavs)} clips (all should be speech since they're synthesized sentences)", file=sys.stderr)
print(f"Avg processing time per clip: {total_t/len(wavs)*1000:.2f}ms", file=sys.stderr)
