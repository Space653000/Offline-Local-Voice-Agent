# -*- coding: utf-8 -*-
"""
稽核資料庫：對照 docs/01 藍圖第13節(Memory)跟第14節(Logging)要求的資料表。
單一 SQLite 檔案，全部存在本機，不上雲端。

對照 docs/07 進度報告第7、8節抓到的落差，這次補上：
- Logging：session_id（把conversation_log跟action_audit串起來）、duration_ms、error 三個原本缺的欄位
- Memory：known_apps / known_folders / session_context / user_preferences 四張原本沒有的表
- 修正一個真實bug：log_conversation() 原本定義了卻從來沒有任何地方呼叫過，conversation_log
  資料表存在但一直是空的（實測confirmed：0 rows），對話紀錄這個藍圖要求的記憶類別形同沒做。
"""
import sqlite3
import json as _json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "voice_agent.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    session_id TEXT,
    heard_text TEXT NOT NULL,      -- ASR 聽到的文字（或文字輸入的原文）
    reply_text TEXT,               -- AI 的回覆（若有）
    asr_model TEXT,
    asr_latency_ms REAL
);

CREATE TABLE IF NOT EXISTS action_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    session_id TEXT,
    intent TEXT,                   -- 對照藍圖第14節「Intent」：這個動作是為了達成使用者哪句話/哪個目標
    tool TEXT NOT NULL,
    args_json TEXT,
    risk_level INTEGER NOT NULL,
    required_confirmation INTEGER NOT NULL,
    user_confirmed INTEGER,        -- NULL=不需要, 0=拒絕, 1=同意
    executed INTEGER NOT NULL,     -- 0=沒執行(被擋或被拒絕), 1=執行了
    duration_ms REAL,              -- 對照藍圖第14節「Duration」：這個動作實際執行花了多久
    error TEXT,                    -- 對照藍圖第14節「Error」：失敗原因（跟result_summary分開，方便單純查錯誤）
    result_summary TEXT
);

CREATE TABLE IF NOT EXISTS policy_rules (
    tool TEXT PRIMARY KEY,
    risk_level INTEGER NOT NULL,
    note TEXT
);

-- 對照藍圖第13節 Memory 的「Known Apps」：記錄真的成功開過的應用程式，跟 basic_tools.py
-- 裡的白名單(KNOWN_APPS)是兩件事——白名單是安全邊界(只能開白名單裡的)，這張表只是
-- 「用過的紀錄」，不會反過來放寬白名單。
CREATE TABLE IF NOT EXISTS known_apps (
    app_name TEXT PRIMARY KEY,
    first_opened_ts TEXT NOT NULL,
    last_opened_ts TEXT NOT NULL,
    open_count INTEGER NOT NULL DEFAULT 1
);

-- 對照藍圖第13節 Memory 的「Known Folders」：記錄file_op真的操作過的資料夾路徑。
CREATE TABLE IF NOT EXISTS known_folders (
    folder_path TEXT PRIMARY KEY,
    first_used_ts TEXT NOT NULL,
    last_used_ts TEXT NOT NULL,
    use_count INTEGER NOT NULL DEFAULT 1
);

-- 對照藍圖第13節 Memory 的「Session Context」：每個對話session目前的簡單狀態，
-- 不是完整逐字稿(那是conversation_log的事)，只存「最近在做什麼」這種摘要資訊。
CREATE TABLE IF NOT EXISTS session_context (
    session_id TEXT PRIMARY KEY,
    started_ts TEXT NOT NULL,
    last_activity_ts TEXT NOT NULL,
    last_tool TEXT,
    last_instruction TEXT
);

-- 對照藍圖第13節 Memory 的「User Preferences」：簡單的key-value設定表。
CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_ts TEXT NOT NULL
);
"""

# 既有資料庫檔案可能是舊版schema建的（沒有session_id/duration_ms/error/intent這幾欄），
# CREATE TABLE IF NOT EXISTS 不會幫舊表補欄位，要自己檢查、缺就補——這樣才不會弄丟舊資料。
_MIGRATIONS = {
    "conversation_log": ["session_id TEXT"],
    "action_audit": ["session_id TEXT", "intent TEXT", "duration_ms REAL", "error TEXT"],
}


def _migrate(conn):
    for table, columns in _MIGRATIONS.items():
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for col_def in columns:
            col_name = col_def.split()[0]
            if col_name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_conversation(heard_text, reply_text=None, asr_model=None, asr_latency_ms=None, session_id=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO conversation_log (ts, session_id, heard_text, reply_text, asr_model, asr_latency_ms) VALUES (?,?,?,?,?,?)",
            (_now(), session_id, heard_text, reply_text, asr_model, asr_latency_ms),
        )


def log_action(tool, args, risk_level, required_confirmation, user_confirmed, executed, result_summary="",
                session_id=None, intent=None, duration_ms=None, error=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO action_audit (ts, session_id, intent, tool, args_json, risk_level, required_confirmation, "
            "user_confirmed, executed, duration_ms, error, result_summary) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                _now(), session_id, intent, tool, _json.dumps(args, ensure_ascii=False),
                int(risk_level), int(required_confirmation),
                None if user_confirmed is None else int(user_confirmed),
                int(executed), duration_ms, error, result_summary,
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


# ---- Memory: Known Apps / Known Folders ----

def record_known_app(app_name: str):
    now = _now()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO known_apps (app_name, first_opened_ts, last_opened_ts, open_count) VALUES (?,?,?,1) "
            "ON CONFLICT(app_name) DO UPDATE SET last_opened_ts=excluded.last_opened_ts, open_count=open_count+1",
            (app_name, now, now),
        )


def record_known_folder(folder_path: str):
    now = _now()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO known_folders (folder_path, first_used_ts, last_used_ts, use_count) VALUES (?,?,?,1) "
            "ON CONFLICT(folder_path) DO UPDATE SET last_used_ts=excluded.last_used_ts, use_count=use_count+1",
            (folder_path, now, now),
        )


def list_known_apps() -> list:
    with get_conn() as conn:
        return [dict(row) for row in _rows_as_dicts(conn, "SELECT * FROM known_apps ORDER BY last_opened_ts DESC")]


def list_known_folders() -> list:
    with get_conn() as conn:
        return [dict(row) for row in _rows_as_dicts(conn, "SELECT * FROM known_folders ORDER BY last_used_ts DESC")]


def _rows_as_dicts(conn, sql):
    conn.row_factory = sqlite3.Row
    return conn.execute(sql).fetchall()


# ---- Memory: Session Context ----

def touch_session(session_id: str, last_tool: str = None, last_instruction: str = None):
    now = _now()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO session_context (session_id, started_ts, last_activity_ts, last_tool, last_instruction) "
            "VALUES (?,?,?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET last_activity_ts=excluded.last_activity_ts, "
            "last_tool=COALESCE(excluded.last_tool, session_context.last_tool), "
            "last_instruction=COALESCE(excluded.last_instruction, session_context.last_instruction)",
            (session_id, now, now, last_tool, last_instruction),
        )


def get_session_context(session_id: str) -> dict:
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM session_context WHERE session_id=?", (session_id,)).fetchone()
        return dict(row) if row else None


# ---- 對話紀錄瀏覽（參考ChatGPT/Gemini等雲端AI助理「側邊欄看過去對話」的做法，使用者明確
# 授權「功能可以參考雲端AI，運算留在本機」——conversation_log這張表本身其實在更早的階段
# 就已經存在且真的有在寫入，只是完全沒有任何地方把它讀出來給使用者看，等於資料存了但沒用。----

def list_conversation_sessions(limit: int = 30) -> list:
    """
    列出最近有對話紀錄的session，每個session附上第一句話當摘要（給列表用，不用整段載入）、
    訊息則數、最後活動時間——同一個session_id可能橫跨很多筆conversation_log記錄。
    """
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT session_id, MIN(ts) AS started_ts, MAX(ts) AS last_ts, COUNT(*) AS n_messages, "
            "(SELECT heard_text FROM conversation_log c2 WHERE c2.session_id = c1.session_id ORDER BY c2.ts LIMIT 1) AS first_message "
            "FROM conversation_log c1 WHERE session_id IS NOT NULL "
            "GROUP BY session_id ORDER BY last_ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_session_messages(session_id: str) -> list:
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT ts, heard_text, reply_text FROM conversation_log WHERE session_id=? ORDER BY ts",
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]


# ---- Memory: User Preferences ----

def set_preference(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_preferences (key, value, updated_ts) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_ts=excluded.updated_ts",
            (key, value, _now()),
        )


def get_preference(key: str, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM user_preferences WHERE key=?", (key,)).fetchone()
        return row[0] if row else default
