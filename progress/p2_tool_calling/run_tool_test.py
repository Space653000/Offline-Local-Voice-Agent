# -*- coding: utf-8 -*-
import subprocess, json, time, sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from tools_and_labels import TOOLS, LABELS

ROOT = Path("C:/0_JN1_Offline-Local-Voice-Agent")
LLAMA_DIR = ROOT / "progress/p0/build/llama.cpp"
CLI = LLAMA_DIR / "build/bin/llama-cli.exe"
MODEL = LLAMA_DIR / "models-test/qwen2.5-0.5b-instruct-q4_k_m.gguf"
SENT_FILE = ROOT / "progress/p1_asr_bench/sentences.txt"

SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": TOOLS},
        "args": {"type": "object"}
    },
    "required": ["tool"]
}

SYSTEM_PROMPT = (
    "你是一個語音助理的意圖判斷模組。使用者會用中文說一句指令，你只能從下面的工具清單中選一個最符合的工具，"
    "並輸出符合 JSON schema 的結果，不要輸出任何解釋文字，只輸出 JSON。可用工具：" + ", ".join(TOOLS)
)

def main():
    env = os.environ.copy()
    env["PATH"] = r"C:\Program Files\LLVM\bin;" + env.get("PATH", "")
    sentences = [s.strip() for s in SENT_FILE.read_text(encoding="utf-8").splitlines() if s.strip()]

    correct = 0
    results = []
    for idx, sent in enumerate(sentences, start=1):
        expected = LABELS.get(idx, "UNKNOWN")
        t0 = time.perf_counter()
        p = subprocess.run(
            [str(CLI), "-m", str(MODEL), "-sys", SYSTEM_PROMPT, "-p", sent,
             "-j", json.dumps(SCHEMA, ensure_ascii=False), "-n", "80", "-ngl", "99", "-st"],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", env=env, cwd=str(LLAMA_DIR),
        )
        elapsed = time.perf_counter() - t0
        raw = p.stdout.strip()
        predicted = None
        try:
            # llama-cli prints extra logs; find the last JSON-looking line
            for line in reversed(raw.splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    predicted = json.loads(line).get("tool")
                    break
        except Exception:
            predicted = None
        ok = predicted == expected
        if ok:
            correct += 1
        results.append({"idx": idx, "sentence": sent, "expected": expected, "predicted": predicted, "ok": ok, "elapsed_s": round(elapsed, 3)})
        print(f"[{idx}/{len(sentences)}] expected={expected} predicted={predicted} ok={ok}", file=sys.stderr)

    acc = correct / len(sentences)
    print(f"\nTool selection accuracy: {correct}/{len(sentences)} = {acc:.4f}", file=sys.stderr)
    out = {"accuracy": acc, "n": len(sentences), "results": results}
    (ROOT / "progress/p2_tool_calling/results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
