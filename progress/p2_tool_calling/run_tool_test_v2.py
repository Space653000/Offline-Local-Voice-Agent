# -*- coding: utf-8 -*-
import requests, json, time, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from tools_and_labels_v2 import TOOLS, TOOL_SPECS, FEWSHOT, LABELS, AMBIGUOUS

ROOT = Path("C:/0_JN1_Offline-Local-Voice-Agent")
SENT_FILE = ROOT / "progress/p1_asr_bench/sentences.txt"
URL = "http://127.0.0.1:8811/v1/chat/completions"

SCHEMA = {
    "type": "object",
    "properties": {"tool": {"type": "string", "enum": TOOLS}, "args": {"type": "object"}},
    "required": ["tool"],
}

tool_desc_lines = "\n".join(f"- {name}：{desc}" for name, desc in TOOL_SPECS.items())
fewshot_lines = "\n".join(f'使用者說「{s}」→ {{"tool": "{t}"}}' for s, t in FEWSHOT)

SYSTEM_PROMPT = f"""你是語音助理的意圖判斷模組。使用者會用中文說一句指令，你要從下面的工具清單中選一個「最符合」的工具，並輸出符合 JSON schema 的結果。

可用工具與說明：
{tool_desc_lines}

範例：
{fewshot_lines}

注意特別容易混淆的地方：
- 「開啟/打開某個系統視窗或程式」一律是 open_app，即使那個視窗名字聽起來像別的工具（例如工作排程器、裝置管理員、命令提示字元都只是 open_app）
- task_scheduler_op 只用在「新增/管理排程任務」這種動作本身，不是「打開排程器視窗」
- 藍牙/Wi-Fi 開關是 network_toggle，不是 power_op（power_op 專指整台電腦的開機/關機/休眠）
"""

def ask(sentence):
    body = {
        "model": "qwen2.5-7b",
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
    return r.json()["choices"][0]["message"]["content"]

def main():
    sentences = [s.strip() for s in SENT_FILE.read_text(encoding="utf-8").splitlines() if s.strip()]
    correct = 0
    results = []
    for idx, sent in enumerate(sentences, start=1):
        expected = LABELS.get(idx, "UNKNOWN")
        t0 = time.perf_counter()
        try:
            content = ask(sent)
            predicted = json.loads(content).get("tool")
        except Exception as e:
            predicted, content = None, f"ERROR: {e}"
        elapsed = time.perf_counter() - t0
        ok = predicted == expected
        if ok:
            correct += 1
        results.append({"idx": idx, "sentence": sent, "expected": expected, "predicted": predicted, "ok": ok, "elapsed_s": round(elapsed, 3)})
        print(f"[{idx}] expected={expected} predicted={predicted} ok={ok} ({elapsed:.2f}s)", file=sys.stderr)

    n = len(sentences)
    acc = correct / n
    clean = [x for x in results if x["idx"] not in AMBIGUOUS]
    acc_clean = sum(1 for x in clean if x["ok"]) / len(clean)
    print(f"\nAll {n}: {correct}/{n} = {acc:.4f}", file=sys.stderr)
    print(f"Excluding {len(AMBIGUOUS)} ambiguous: {sum(1 for x in clean if x['ok'])}/{len(clean)} = {acc_clean:.4f}", file=sys.stderr)
    (ROOT / "progress/p2_tool_calling/results_v2_7b.json").write_text(
        json.dumps({"accuracy": acc, "accuracy_clean": acc_clean, "n": n, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8")

if __name__ == "__main__":
    main()
