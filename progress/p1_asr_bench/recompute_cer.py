import json, re
from pathlib import Path
from opencc import OpenCC

ROOT = Path("C:/0_JN1_Offline-Local-Voice-Agent")
cc = OpenCC('s2t')  # normalize everything to Traditional

def norm(s: str) -> str:
    s = cc.convert(s)
    return re.sub(r"[\s,.,。，!?！？、]", "", s)

def cer(ref: str, hyp: str) -> float:
    ref, hyp = norm(ref), norm(hyp)
    if len(ref) == 0:
        return 0.0 if len(hyp) == 0 else 1.0
    n, m = len(ref), len(hyp)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, m + 1):
            tmp = dp[j]
            dp[j] = prev if ref[i-1] == hyp[j-1] else 1 + min(prev, dp[j], dp[j-1])
            prev = tmp
    return dp[m] / n

results = json.loads((ROOT / "progress/p1_asr_bench/results.json").read_text(encoding="utf-8"))
summary = {}
for model, data in results.items():
    total_cer = 0.0
    for row in data["per_sentence"]:
        c = cer(row["ref"], row["hyp"])
        row["cer_script_normalized"] = round(c, 4)
        total_cer += c
    n = data["n_sentences"]
    summary[model] = {
        "avg_cer_raw": data["avg_cer"],
        "avg_cer_script_normalized": round(total_cer / n, 4),
        "avg_latency_s": data["avg_latency_s"],
        "real_time_factor": data["real_time_factor"],
    }

(ROOT / "progress/p1_asr_bench/results_normalized.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
(ROOT / "progress/p1_asr_bench/summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(summary, ensure_ascii=False, indent=2))
