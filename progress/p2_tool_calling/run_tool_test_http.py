# -*- coding: utf-8 -*-
import requests, json, time, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from tools_and_labels import TOOLS, LABELS

ROOT = Path("C:/0_JN1_Offline-Local-Voice-Agent")
SENT_FILE = ROOT / "progress/p1_asr_bench/sentences.txt"
URL = "http://127.0.0.1:8811/v1/chat/completions"

SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": TOOLS},
        "args": {"type": "object"}
    },
    "required": ["tool"]
}

SYSTEM_PROMPT = (
    "你是語音助理的意圖判斷模組。使用者會用中文說一句指令，你只能從下面的工具清單中選一個最符合的工具，"
    "並輸出符合 JSON schema 的結果。可用工具：" + ", ".join(TOOLS)
)

def ask(sentence):
    body = {
        "model": "qwen2.5-0.5b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": sentence},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "tool_call", "schema": SCHEMA}},
        "max_tokens": 60,
        "temperature": 0.0,
    }
    r = requests.post(URL, json=body, timeout=30)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    return content

def main(limit=None):
    sentences = [s.strip() for s in SENT_FILE.read_text(encoding="utf-8").splitlines() if s.strip()]
    if limit:
        sentences = sentences[:limit]
    correct = 0
    results = []
    for idx, sent in enumerate(sentences, start=1):
        expected = LABELS.get(idx, "UNKNOWN")
        t0 = time.perf_counter()
        try:
            content = ask(sent)
            predicted = json.loads(content).get("tool")
        except Exception as e:
            predicted = None
            content = f"ERROR: {e}"
        elapsed = time.perf_counter() - t0
        ok = predicted == expected
        if ok:
            correct += 1
        results.append({"idx": idx, "sentence": sent, "expected": expected, "predicted": predicted, "ok": ok, "elapsed_s": round(elapsed, 3), "raw": content})
        print(f"[{idx}] {sent} -> expected={expected} predicted={predicted} ok={ok} ({elapsed:.2f}s)", file=sys.stderr)

    n = len(sentences)
    acc = correct / n
    print(f"\nTool selection accuracy: {correct}/{n} = {acc:.4f}", file=sys.stderr)
    out = {"accuracy": acc, "n": n, "results": results}
    (ROOT / "progress/p2_tool_calling/results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    import sys as _sys
    lim = int(_sys.argv[1]) if len(_sys.argv) > 1 else None
    main(lim)
