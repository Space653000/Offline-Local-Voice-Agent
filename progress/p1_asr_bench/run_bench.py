import subprocess, time, json, sys, re
from pathlib import Path

ROOT = Path("C:/0_JN1_Offline-Local-Voice-Agent")
WHISPER_DIR = ROOT / "progress/p0/build/whisper.cpp"
CLI = WHISPER_DIR / "build/bin/whisper-cli.exe"
WAV_DIR = ROOT / "progress/p1_asr_bench/wav_16k"
SENT_FILE = ROOT / "progress/p1_asr_bench/sentences.txt"
MODELS = {
    "tiny":   WHISPER_DIR / "models/ggml-tiny.bin",
    "base":   WHISPER_DIR / "models/ggml-base.bin",
    "small":  WHISPER_DIR / "models/ggml-small.bin",
    "medium": WHISPER_DIR / "models/ggml-medium.bin",
}

def cer(ref: str, hyp: str) -> float:
    ref = re.sub(r"[\s,.,。，!?！？、]", "", ref)
    hyp = re.sub(r"[\s,.,。，!?！？、]", "", hyp)
    if len(ref) == 0:
        return 0.0 if len(hyp) == 0 else 1.0
    n, m = len(ref), len(hyp)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, m + 1):
            tmp = dp[j]
            if ref[i-1] == hyp[j-1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j-1])
            prev = tmp
    return dp[m] / n

def wav_duration_sec(path: Path) -> float:
    import wave
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()

def run_one(model_path: Path, wav_path: Path, env):
    t0 = time.perf_counter()
    p = subprocess.run(
        [str(CLI), "-m", str(model_path), "-f", str(wav_path), "-l", "zh", "-nt"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore", env=env,
        cwd=str(WHISPER_DIR),
    )
    elapsed = time.perf_counter() - t0
    text = p.stdout.strip()
    return text, elapsed

def main():
    import os
    env = os.environ.copy()
    env["PATH"] = r"C:\Program Files\LLVM\bin;" + env.get("PATH", "")

    sentences = [s.strip() for s in SENT_FILE.read_text(encoding="utf-8").splitlines() if s.strip()]
    wavs = sorted(WAV_DIR.glob("*.wav"))
    assert len(wavs) == len(sentences), f"{len(wavs)} wavs vs {len(sentences)} sentences"

    results = {}
    for model_name, model_path in MODELS.items():
        if not model_path.exists():
            print(f"SKIP {model_name}: model not downloaded yet", file=sys.stderr)
            continue
        print(f"=== running model: {model_name} ===", file=sys.stderr)
        per_sentence = []
        total_time = 0.0
        total_audio = 0.0
        total_cer = 0.0
        for ref, wav in zip(sentences, wavs):
            hyp, elapsed = run_one(model_path, wav, env)
            dur = wav_duration_sec(wav)
            c = cer(ref, hyp)
            per_sentence.append({
                "file": wav.name, "ref": ref, "hyp": hyp,
                "cer": round(c, 4), "elapsed_s": round(elapsed, 3), "audio_s": round(dur, 3),
            })
            total_time += elapsed
            total_audio += dur
            total_cer += c
        n = len(sentences)
        results[model_name] = {
            "n_sentences": n,
            "avg_cer": round(total_cer / n, 4),
            "avg_latency_s": round(total_time / n, 4),
            "total_time_s": round(total_time, 2),
            "total_audio_s": round(total_audio, 2),
            "real_time_factor": round(total_time / total_audio, 4),
            "per_sentence": per_sentence,
        }
        print(f"  avg_cer={results[model_name]['avg_cer']}  avg_latency={results[model_name]['avg_latency_s']}s  RTF={results[model_name]['real_time_factor']}", file=sys.stderr)

    out_path = ROOT / "progress/p1_asr_bench/results.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}", file=sys.stderr)

if __name__ == "__main__":
    main()
