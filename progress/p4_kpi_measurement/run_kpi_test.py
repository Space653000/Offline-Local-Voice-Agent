# -*- coding: utf-8 -*-
"""
對照 docs/01 藍圖第17節 Performance KPI，補測「工具執行成功率≥98%」跟「ASR→Tool決策延遲<2秒」
這兩項——docs/07 進度報告第9節指出這兩項完全沒測過。

方法：用文字輸入路徑（command_processor.run_desktop_command）跑一批涵蓋17個已實作工具的
真實指令，全部走完整的 LLM 判斷+PolicyEngine+Executor 流程，不是假資料。全部挑L0/L1
（免確認）的指令，避免測試中卡在確認關卡；每個指令的執行時間直接從 audit_db 的
duration_ms 欄位讀（這是這次盤點剛補上的真實量測資料，不是重新發明）。

誠實的量測範圍：這裡測的是「文字輸入 -> LLM判斷 -> Executor執行」這一段，不含真實語音的
Wake Word/ASR（那段在P1階段已經另外測過，medium模型0.34~1.6秒，記錄在docs/06）。
"""
import sys, json, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from command_processor import run_desktop_command
from executor import audit_db

SESSION_ID = "kpi-test-" + str(int(time.time()))

# 涵蓋17個已實作工具的真實指令，全部是L0/L1（免確認），刻意避開需要確認的動作，
# 避免測試流程卡在確認關卡；每個標注預期工具，用來算「指令路由準確率」這個附帶指標。
TEST_COMMANDS = [
    ("現在幾點", "get_datetime"),
    ("現在是幾點幾分", "get_datetime"),
    ("把音量調到50%", "set_volume"),
    ("把音量調到70%", "set_volume"),
    ("音量調高一點", "set_volume"),
    ("幫我截圖", "take_screenshot"),
    ("螢幕截圖", "take_screenshot"),
    ("算一下25乘以4", "calculator"),
    ("100除以4等於多少", "calculator"),
    ("3加5再乘以2", "calculator"),
    ("唸出這句話：現在開始量測", "text_to_speech_op"),
    ("把這句話翻譯成英文：你好嗎", "translate"),
    ("幫我整理重點：今天天氣很好，適合出門走走，記得帶雨傘以防萬一", "summarize_doc"),
    ("顯示桌面", "window_op"),
    ("切換到下一個視窗", "window_op"),
    ("複製這段文字到剪貼簿：hello world", "clipboard_op"),
    ("貼上剪貼簿的內容", "clipboard_op"),
    ("查詢目前最前面的視窗是什麼", "get_active_window"),
    ("列出目前開著的所有視窗", "list_windows"),
    ("按下escape鍵", "press_key"),
]

results = []
for text, expected_tool in TEST_COMMANDS:
    t0 = time.time()
    r = run_desktop_command(text, SESSION_ID)
    round_trip_ms = (time.time() - t0) * 1000
    actual_tool = r["history"][0]["tool"] if r.get("history") else None
    executed = r["history"][0]["result"].get("executed") if r.get("history") else None
    results.append({
        "text": text, "expected_tool": expected_tool, "actual_tool": actual_tool,
        "tool_match": actual_tool == expected_tool, "executed": executed,
        "round_trip_ms": round(round_trip_ms, 1), "status": r["status"],
    })

# 從 audit_db 撈這個session的真實 duration_ms（Executor實際執行工具的時間，不含LLM決策時間）
with audit_db.get_conn() as conn:
    import sqlite3
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT tool, executed, duration_ms, error FROM action_audit WHERE session_id=? ORDER BY id",
        (SESSION_ID,),
    ).fetchall()
    exec_rows = [dict(row) for row in rows]

# 把每筆結果對上同一筆audit_db紀錄（依序一一對應，因為每個測試指令都只產生一筆action_audit）
for r, row in zip(results, exec_rows):
    r["executor_duration_ms"] = row["duration_ms"]
    # 「決策延遲」= 整個HTTP往返時間 - 工具本身執行花的時間，這樣才不會把「唸一句話本身要花
    # 多少秒」這種工具天生的執行時間，誤算成「LLM決策卡了多久」——兩者是不同性質的東西，
    # 藍圖KPI講的「ASR→Tool決策」指的是決策這一段，不是工具動作本身要跑多久。
    r["decision_latency_ms"] = round(r["round_trip_ms"] - (row["duration_ms"] or 0), 1)

n = len(results)
tool_match_count = sum(1 for r in results if r["tool_match"])
executed_count = sum(1 for r in results if r["executed"])
round_trip_times = sorted(r["round_trip_ms"] for r in results)
decision_times = sorted(r["decision_latency_ms"] for r in results)
duration_times = sorted(row["duration_ms"] for row in exec_rows if row["duration_ms"] is not None)


def percentile(sorted_list, p):
    if not sorted_list:
        return None
    idx = min(len(sorted_list) - 1, int(len(sorted_list) * p))
    return sorted_list[idx]


summary = {
    "n_commands": n,
    "tool_routing_accuracy": round(tool_match_count / n, 4),
    "tool_execution_success_rate": round(executed_count / n, 4),
    "round_trip_ms": {
        "note": "整個HTTP往返（LLM決策+工具真的執行完）時間，工具執行時間依動作本身性質可能差很多（例如唸一長句子）",
        "avg": round(sum(round_trip_times) / n, 1),
        "min": round_trip_times[0], "max": round_trip_times[-1],
        "p50": percentile(round_trip_times, 0.5), "p95": percentile(round_trip_times, 0.95),
    },
    "decision_latency_ms": {
        "note": "只算LLM判斷該呼叫哪個工具的時間，扣掉工具本身執行時間——對應藍圖「ASR→Tool決策」這一段",
        "avg": round(sum(decision_times) / n, 1),
        "min": decision_times[0], "max": decision_times[-1],
        "p50": percentile(decision_times, 0.5), "p95": percentile(decision_times, 0.95),
    },
    "executor_duration_ms": {
        "avg": round(sum(duration_times) / len(duration_times), 2) if duration_times else None,
        "min": duration_times[0] if duration_times else None,
        "max": duration_times[-1] if duration_times else None,
    },
    "kpi_targets_from_blueprint": {
        "tool_execution_success_rate_target": ">= 0.98",
        "tool_execution_success_rate_actual": round(executed_count / n, 4),
        "tool_execution_success_rate_pass": (executed_count / n) >= 0.98,
        "asr_to_tool_decision_target_ms": "< 2000",
        "decision_latency_p95_ms": percentile(decision_times, 0.95),
        "decision_latency_p95_under_2s": percentile(decision_times, 0.95) < 2000,
    },
}

output = {"session_id": SESSION_ID, "summary": summary, "per_command": results, "audit_db_rows": exec_rows}
out_path = Path(__file__).parent / "kpi_result.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("done ->", out_path)
