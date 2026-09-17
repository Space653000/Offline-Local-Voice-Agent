# -*- coding: utf-8 -*-
"""
完整迴圈：文字指令（來自ASR或手打）-> LLM判斷tool+args -> PolicyEngine -> Executor -> 真實動作。
只有已經在 executor/executor.py TOOL_IMPLEMENTATIONS 裡的工具會真的執行，其餘工具會被判斷出來
但 Executor 會回報「尚未實作」，不會假裝執行成功。
"""
import sys, json, requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from executor.executor import Executor, ConfirmationRequired

URL = "http://127.0.0.1:8811/v1/chat/completions"

# 只列出目前真的有實作的工具，並明確告訴 LLM 每個工具需要什麼參數欄位
IMPLEMENTED_TOOLS_SPEC = """
- open_app：開啟應用程式。args: {"app_name": "notepad"|"calculator"|"explorer"|"settings"}
- close_window：關閉一個視窗。args: {"pid": 數字}（只有在對話中前面已經用open_app開過、拿到pid時才能用這個工具）
- get_datetime：查詢現在時間。args: {}
- take_screenshot：螢幕截圖。args: {}
- set_volume：調整音量。args: {"level": 0-100的絕對值} 或 {"delta": 正負數的相對調整}
- clipboard_op：剪貼簿操作。args: {"action": "copy", "text": "要複製的文字"} 或 {"action": "paste"}
- window_op：視窗操作。args: {"action": "minimize"|"show_desktop"|"switch_next"}
- media_control：媒體播放控制。args: {"action": "play_pause"|"next"|"prev"|"mute"}
  （注意：「暫停」「播放」都是 play_pause，不是 mute；mute 專指「靜音」這個字眼本身才用）
- network_toggle：Wi-Fi開關。args: {"device": "wifi", "on": true或false}
- calculator：數學計算。args: {"expression": "3+5*2"}（只能是數字跟+-*/()運算，不能有文字）
- text_to_speech_op：把文字唸出來。args: {"text": "要唸的內容"}
- translate：翻譯句子。args: {"text": "原文", "target_language": "英文"}
- summarize_doc：整理內容成摘要重點。args: {"text": "要摘要的內容"}
- text_input_op：把文字輸入到目前作用中的欄位。args: {"text": "要輸入的內容"}
- file_op：本機檔案操作。args: {"action": "find", "name": "關鍵字", "search_dir": "選填，預設家目錄"}
  或 {"action": "open", "path": "檔案路徑"}
  或 {"action": "move"/"copy", "src": "來源路徑", "dst": "目的地路徑"}
  或 {"action": "rename", "path": "檔案路徑", "new_name": "新檔名（只能是檔名，不能含路徑）"}
  或 {"action": "create_folder", "path": "資料夾路徑"}
  或 {"action": "delete", "path": "檔案路徑"}（只能刪單一檔案，不支援刪資料夾；會進資源回收桶不是永久刪除）
  （move/copy/rename/create_folder/delete 只能操作使用者家目錄底下的路徑，不接受系統目錄）
- power_op：電腦整體電源狀態。args: {"action": "shutdown"|"restart"|"sleep"|"cancel"}
  （shutdown/restart 會先排程30秒延遲執行，cancel 可以在30秒內中止排程）
- get_active_window：查詢目前作用中(最前面)的視窗。args: {}
- list_windows：列出目前所有開著的視窗跟它們的pid。args: {}
- focus_window：切換到指定視窗。args: {"pid": 數字} 或 {"title": "視窗標題關鍵字"}
- uia_click：點擊某個視窗裡的按鈕/控制項（用視窗內容真正的文字定位，不是滑鼠座標）。
  args: {"pid": 數字, "control_name": "要點的按鈕/控制項上顯示的文字"}
- uia_set_text：把文字設定到某個視窗裡指定的輸入欄位（不是打到目前游標位置，是精確指定欄位）。
  args: {"pid": 數字, "control_name": "欄位名稱或標籤文字", "text": "要填入的內容"}
- uia_select：在某個視窗的清單/下拉選單裡選擇一個項目。
  args: {"pid": 數字, "control_name": "清單/下拉選單的名稱", "item_name": "要選的項目文字"}
- press_key：按一個單獨的鍵（例如Enter、Escape、Tab、方向鍵、F1-F12）。args: {"key": "enter"}
- hotkey：按一個組合鍵（例如存檔Ctrl+S、復原Ctrl+Z）。args: {"keys": "ctrl+s"}
  （不接受 Win+R、Win+L 這類會繞過安全機制或過度干擾的組合鍵）
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": ["open_app", "close_window", "get_datetime",
                                              "take_screenshot", "set_volume", "clipboard_op",
                                              "window_op", "media_control", "network_toggle",
                                              "calculator", "text_to_speech_op", "translate",
                                              "summarize_doc", "text_input_op", "file_op", "power_op",
                                              "get_active_window", "list_windows", "focus_window",
                                              "uia_click", "uia_set_text", "uia_select",
                                              "press_key", "hotkey"]},
        "args": {"type": "object"},
    },
    "required": ["tool", "args"],
}


def understand(text: str) -> dict:
    body = {
        "model": "local",
        "messages": [
            {"role": "system", "content": f"你是語音助理，把使用者的指令轉成工具呼叫。可用工具：\n{IMPLEMENTED_TOOLS_SPEC}\n只輸出JSON。"},
            {"role": "user", "content": text},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "call", "schema": SCHEMA}},
        "max_tokens": 100, "temperature": 0.0,
    }
    r = requests.post(URL, json=body, timeout=30)
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


def run_command(text: str, ex: Executor):
    call = understand(text)
    try:
        result = ex.run(call["tool"], call["args"])
        return {"input": text, "call": call, "outcome": result}
    except ConfirmationRequired as e:
        return {"input": text, "call": call, "outcome": {"needs_confirmation": True, "reason": e.decision.reason}}


if __name__ == "__main__":
    from executor import audit_db
    audit_db.sync_policy_rules()
    ex = Executor()

    commands = [
        "現在幾點",
        "把音量調到20%",
        "幫我截圖",
        "複製這段文字：測試完整迴圈",
    ]
    out = []
    for c in commands:
        out.append(run_command(c, ex))

    with open(Path(__file__).parent / "full_pipeline_result.txt", "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False, indent=2) + "\n\n")
    print("done")
