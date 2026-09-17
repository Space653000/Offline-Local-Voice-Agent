# -*- coding: utf-8 -*-
"""
稽核資料庫：對照 console 頁面上「後端與資料庫」說明的三張表。
單一 SQLite 檔案，全部存在本機，不上雲端。
"""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "voice_agent.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    heard_text TEXT NOT NULL,      -- ASR 聽到的文字
    reply_text TEXT,               -- AI 的回覆（若有）
    asr_model TEXT,
    asr_latency_ms REAL
);

CREATE TABLE IF NOT EXISTS action_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    tool TEXT NOT NULL,
    args_json TEXT,
    risk_level INTEGER NOT NULL,
    required_confirmation INTEGER NOT NULL,
    user_confirmed INTEGER,        -- NULL=不需要, 0=拒絕, 1=同意
    executed INTEGER NOT NULL,     -- 0=沒執行(被擋或被拒絕), 1=執行了
    result_summary TEXT
);

CREATE TABLE IF NOT EXISTS policy_rules (
    tool TEXT PRIMARY KEY,
    risk_level INTEGER NOT NULL,
    note TEXT
);
"""


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def log_conversation(heard_text, reply_text=None, asr_model=None, asr_latency_ms=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO conversation_log (ts, heard_text, reply_text, asr_model, asr_latency_ms) VALUES (?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), heard_text, reply_text, asr_model, asr_latency_ms),
        )


def log_action(tool, args, risk_level, required_confirmation, user_confirmed, executed, result_summary=""):
    import json
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO action_audit (ts, tool, args_json, risk_level, required_confirmation, user_confirmed, executed, result_summary) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                datetime.now(timezone.utc).isoformat(), tool, json.dumps(args, ensure_ascii=False),
                int(risk_level), int(required_confirmation),
                None if user_confirmed is None else int(user_confirmed),
                int(executed), result_summary,
            ),
        )


def sync_policy_rules():
    from policy.risk_levels import TOOL_RISK_TABLE
    with get_conn() as conn:
        for tool, level in TOOL_RISK_TABLE.items():
            conn.execute(
                "INSERT INTO policy_rules (tool, risk_level, note) VALUES (?,?,?) "
                "ON CONFLICT(tool) DO UPDATE SET risk_level=excluded.risk_level",
                (tool, int(level), level.name),
            )
