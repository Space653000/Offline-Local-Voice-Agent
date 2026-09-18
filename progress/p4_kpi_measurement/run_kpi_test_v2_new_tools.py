# -*- coding: utf-8 -*-
"""
延伸 run_kpi_test.py 的「工具執行成功率」量測——原本那批20句是2026-09-17測的，
只涵蓋當時已實作的17個工具，這次補測後來新增的4個工具（task_scheduler_op/
startup_program_op/driver_op/photo_edit），一樣走真實文字輸入->LLM判斷->
PolicyEngine->Executor完整流程，不是直接呼叫底層函式繞過LLM判斷這一段。

task_scheduler_op/startup_program_op是L2敏感操作，會先卡在確認關卡，這裡用
command_processor.confirm_desktop_command()自動同意繼續——跟test_p3_safety.py
測close_window（L2）的做法一致，這是內部量測工具本身能不能正確執行，不是要
繞過安全機制本身（真實語音/文字使用者還是會被要求確認）。
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from command_processor import run_desktop_command, confirm_desktop_command
from executor import audit_db

SESSION_ID = "kpi-v2-" + str(int(time.time()))
TEST_PHOTO = str(Path.home() / "_va_kpi_test_photo.png")

TEST_COMMANDS = [
    ("列出目前有哪些排程工作", "task_scheduler_op"),
    ("看看開機自動啟動有哪些程式", "startup_program_op"),
    ("幫我查一下顯示卡驅動版本", "driver_op"),
    (f"把{TEST_PHOTO}轉成灰階", "photo_edit"),
]

results = []
for text, expected_tool in TEST_COMMANDS:
    t0 = time.time()
    r = run_desktop_command(text, SESSION_ID)
    if r["status"] == "needs_confirmation":
        r = confirm_desktop_command(r["call"]["tool"], r["call"]["args"], approved=True, session_id=SESSION_ID)
    round_trip_ms = (time.time() - t0) * 1000
    actual_tool = r["history"][0]["tool"] if r.get("history") else None
    executed = r["history"][0]["result"].get("executed") if r.get("history") else None
    results.append({
        "text": text, "expected_tool": expected_tool, "actual_tool": actual_tool,
        "tool_match": actual_tool == expected_tool, "executed": executed,
        "round_trip_ms": round(round_trip_ms, 1), "status": r["status"],
        "result_detail": (r["history"][0]["result"].get("result") or r["history"][0]["result"].get("reason")) if r.get("history") else r.get("reason"),
    })

n = len(results)
tool_match_count = sum(1 for r in results if r["tool_match"])
executed_count = sum(1 for r in results if r["executed"])

summary = {
    "n_commands": n,
    "tool_routing_accuracy": round(tool_match_count / n, 4),
    "tool_execution_success_rate": round(executed_count / n, 4),
    "combined_with_v1": {
        "note": "v1(20句,17工具,2026-09-17) + v2(這4句,4個新工具) 合併起來的整體成功率",
        "n_total": 20 + n,
        "executed_total": 20 + executed_count,  # v1是20/20全部成功
        "success_rate_total": round((20 + executed_count) / (20 + n), 4),
    },
}

import json
output = {"session_id": SESSION_ID, "summary": summary, "per_command": results}
out_path = Path(__file__).parent / "kpi_result_v2_new_tools.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

for r in results:
    print(r["text"], "->", r["actual_tool"], "| executed:", r["executed"], "| detail:", r["result_detail"])
print()
print("summary:", json.dumps(summary, ensure_ascii=False, indent=2))
print("done ->", out_path)
