# -*- coding: utf-8 -*-
"""
喚醒詞開關：使用者2026-09-18明確要求「取消8小時無人值守測試，改成主介面一個勾選開關，
關閉時電腦不能在使用者不知情的狀況下自己做任何小事」——這個檔案就是那個開關的真實狀態。

安全設計核心：
1. 預設關閉（檔案不存在、或讀取失敗，一律當作關閉）——不能因為設定檔案遺失/損毀，
   就意外變成「開啟」，寧可保守地什麼都不做，也不能反過來變成沒人同意就開始聽。
2. 這個開關獨立於memory_op/user_preferences那套一般記憶機制，LLM沒有工具能直接改動它
   （不在full_pipeline.py的TOOL_ENUM裡），只有companion.html的勾選框（使用者手動操作）
   能改變這個值，避免被一般對話「不小心」講出什麼觸發改動。
3. 故意用獨立的輕量模組（不依賴openwakeword/whisper等重量級套件），讓serve.py（網頁伺服器，
   本身不需要載入語音模型）也能低成本import來讀寫這個檔案，不用連帶載入listen_loop.py
   整套重量級依賴。
"""
import json
from pathlib import Path

_SETTING_FILE = Path(__file__).resolve().parents[1] / "console" / "wake_word_setting.json"


def is_wake_word_enabled() -> bool:
    if not _SETTING_FILE.exists():
        return False
    try:
        data = json.loads(_SETTING_FILE.read_text(encoding="utf-8"))
        return bool(data.get("enabled", False))
    except Exception:
        return False


def set_wake_word_enabled(enabled: bool):
    _SETTING_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _SETTING_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"enabled": bool(enabled)}, ensure_ascii=False), encoding="utf-8")
    tmp.replace(_SETTING_FILE)
