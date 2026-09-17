# -*- coding: utf-8 -*-
"""
完整迴圈：文字指令（來自ASR或手打）-> LLM判斷tool+args -> PolicyEngine -> Executor -> 真實動作。
只有已經在 executor/executor.py TOOL_IMPLEMENTATIONS 裡的工具會真的執行，其餘工具會被判斷出來
但 Executor 會回報「尚未實作」，不會假裝執行成功。

對照 docs/07 進度報告第2節P6的發現：原本這裡只能「一句話對應一個工具呼叫」，沒有規劃能力，
藍圖P6要求的「找到Downloads裡最新的PDF，打開它，然後把檔名告訴我」這種需要依賴前一步真實結果
才能決定下一步參數的複合指令完全做不到。這次補上 PlanRunner：多數單步驟指令維持原本一次
LLM呼叫就結束（不增加延遲），只有LLM自己判斷「這句話還有後續」時才會進入逐步詢問下一步的迴圈，
且每一步都是根據前一步「真實執行結果」決定下一步參數，不是LLM自己瞎猜。
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
- file_op：本機檔案操作。args: {"action": "find", "name": "關鍵字(選填)", "search_dir": "選填，預設家目錄",
  "extension": "選填，例如pdf/txt/jpg", "newest_only": true/false(選填，true時只回傳修改時間最新的一個檔案)}
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
  （像記事本這種主要編輯區沒有明顯標籤文字時，control_name可以填"內容"）
- uia_select：在某個視窗的清單/下拉選單裡選擇一個項目。
  args: {"pid": 數字, "control_name": "清單/下拉選單的名稱", "item_name": "要選的項目文字"}
- press_key：按一個單獨的鍵（例如Enter、Escape、Tab、方向鍵、F1-F12）。args: {"key": "enter"}
- hotkey：按一個組合鍵（例如存檔Ctrl+S、復原Ctrl+Z）。args: {"keys": "ctrl+s"}
  （不接受 Win+R、Win+L 這類會繞過安全機制或過度干擾的組合鍵）
- speech_to_text_op：把一份已經存在的.wav錄音檔轉成文字。args: {"audio_path": "檔案路徑"}
- record_screen：開始或停止螢幕錄影。args: {"action": "start"|"stop"}
"""

TOOL_ENUM = ["open_app", "close_window", "get_datetime",
             "take_screenshot", "set_volume", "clipboard_op",
             "window_op", "media_control", "network_toggle",
             "calculator", "text_to_speech_op", "translate",
             "summarize_doc", "text_input_op", "file_op", "power_op",
             "get_active_window", "list_windows", "focus_window",
             "uia_click", "uia_set_text", "uia_select",
             "press_key", "hotkey", "speech_to_text_op", "record_screen"]

SCHEMA = {
    # 注意：「args」故意放在properties/required的最後一個——llama.cpp把JSON Schema轉成GBNF
    # 語法時，一個沒有限定properties的開放式object（"args": {"type":"object"}）如果後面還有
    # 其他必填欄位，語法解析會在args這裡卡住並產生亂碼胡言亂語（實測抓到，不是猜的：把args放最後
    # 問題就消失）。之後如果要再加新的必填欄位，一定要加在args之前，不能加在args後面。
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": TOOL_ENUM},
        "needs_followup": {"type": "boolean"},
        "args": {"type": "object"},
    },
    "required": ["tool", "needs_followup", "args"],
}


def understand(text: str) -> dict:
    system_prompt = (
        f"你是語音助理，把使用者的指令轉成工具呼叫。可用工具：\n{IMPLEMENTED_TOOLS_SPEC}\n"
        "needs_followup欄位：這句話除了這個動作之外，還需要根據這個動作的真實結果才能決定後續動作嗎？"
        "（例如「找到最新的PDF然後打開它」：要先找到才知道打開哪個檔案，這裡填true）"
        "絕大多數單一動作的句子（例如「現在幾點」「把音量調到50%」）這裡都應該填false，不要濫用true。"
        "只輸出JSON。"
    )
    body = {
        "model": "local",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "call", "schema": SCHEMA}},
        "max_tokens": 150, "temperature": 0.0,
    }
    r = requests.post(URL, json=body, timeout=30)
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


FOLLOWUP_SCHEMA = {
    # 跟SCHEMA同樣的教訓：開放式的"args" object一定要放在properties的最後一個。
    "type": "object",
    "properties": {
        "done": {"type": "boolean"},
        "tool": {"type": "string", "enum": TOOL_ENUM},
        "summary": {"type": "string"},
        "args": {"type": "object"},
    },
    "required": ["done"],
}


def next_step(instruction: str, history: list) -> dict:
    """
    根據原始目標跟「已經真實執行過的步驟結果」，決定下一步。history 裡的 result 都是
    Executor真的跑過的結果，不是LLM自己想像的，所以「打開剛剛找到的檔案」這種指令，
    LLM在這裡看到的是find_file真正回傳的檔名，不是憑空瞎猜。
    """
    if history:
        history_text = "\n".join(
            f"步驟{i + 1}：呼叫 {h['tool']}(args={json.dumps(h['args'], ensure_ascii=False)}) -> 結果：{h['result']}"
            for i, h in enumerate(history)
        )
    else:
        history_text = "（還沒執行過任何步驟）"
    user_content = (
        f"使用者的目標：{instruction}\n\n已經執行的步驟：\n{history_text}\n\n"
        "請把使用者這句話拆成一個個具體動作（通常用逗號或「然後」分開，例如「找到X，打開它，"
        "告訴我Y」= 動作1:找到X、動作2:打開它、動作3:告訴我Y），逐一核對：\n"
        "- 「找到／搜尋／打開／調整」這種需要真的操作電腦才能完成的動作，一定要先出現在"
        "「已經執行的步驟」清單裡才算做過，不能跳過、不能假設已經做了。\n"
        "- 「告訴我／講出來／回報」這種單純陳述結果的動作，不需要呼叫工具，答案已經在"
        "上面「已經執行的步驟」的結果裡了，直接摘要進summary即可，不要為它去猜一個不存在的工具。\n"
        "只要清單裡還缺任何一個「需要真的操作電腦」的動作，就必須繼續給下一步的tool/args，"
        "不能提前done=true。"
    )
    body = {
        "model": "local",
        "messages": [
            {"role": "system", "content": f"你是任務規劃者，可用工具：\n{IMPLEMENTED_TOOLS_SPEC}\n只輸出JSON。"},
            {"role": "user", "content": user_content},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "next_step", "schema": FOLLOWUP_SCHEMA}},
        "max_tokens": 200, "temperature": 0.0,
    }
    r = requests.post(URL, json=body, timeout=30)
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


class PlanRunner:
    """
    對照 docs/07 進度報告第2節P6的缺口：讓一句話能對應多個依序執行的工具呼叫，而不是只能一個。
    設計取捨：第一步沿用單次LLM呼叫（跟原本的understand()一樣快，不拖慢絕大多數單步驟指令的延遲），
    只有LLM自己判斷 needs_followup=true 時才進入「問下一步」的迴圈，且每一步都基於前一步的
    真實執行結果，不是LLM一次規劃好全部步驟（那樣會在還不知道find_file真正找到什麼檔案的情況下，
    就要LLM瞎猜open_file的路徑參數，不可靠）。
    """

    MAX_STEPS = 5  # 安全上限，防止LLM判斷一直卡在needs_followup=true造成無限迴圈

    def __init__(self, instruction: str, executor: Executor, session_id: str = None):
        self.instruction = instruction
        self.ex = executor
        self.session_id = session_id
        self.history = []
        self.pending_call = None
        self.pending_decision = None

    def run(self) -> dict:
        if self.pending_call is None and not self.history:
            first = understand(self.instruction)
            return self._execute_and_continue(first["tool"], first["args"], bool(first.get("needs_followup")))
        return self._continue_loop()

    def resume(self, approved: bool, typed_keyword: str = None) -> dict:
        """
        L2/L3確認之後繼續跑：把這一步的結果記進history，再回到迴圈問下一步。

        typed_keyword=None代表呼叫方（例如語音路徑的_voice_confirm）已經自己驗證過L3關鍵字，
        這裡不用再檢查一次；只有真的傳了typed_keyword（文字/網頁路徑，使用者打的原始文字，
        還沒驗證過）才需要在這裡做「一定要打出確認執行」的檢查。不這樣分兩種情況會導致語音
        路徑已經驗證過的True，在這裡被錯誤地又檢查一次typed_keyword=None，永遠變成False。
        """
        tool, args = self.pending_call["tool"], self.pending_call["args"]
        if self.pending_decision.requires_typed_confirmation and typed_keyword is not None:
            approved = approved and typed_keyword.replace(" ", "") == "確認執行"
        result = self.ex.run(tool, args, user_confirmed=approved, session_id=self.session_id, intent=self.instruction)
        self.history.append({"tool": tool, "args": args, "result": result})
        self.pending_call, self.pending_decision = None, None
        return self._continue_loop()

    def _execute_and_continue(self, tool: str, args: dict, needs_followup: bool) -> dict:
        try:
            result = self.ex.run(tool, args, session_id=self.session_id, intent=self.instruction)
        except ConfirmationRequired as e:
            self.pending_call = {"tool": tool, "args": args}
            self.pending_decision = e.decision
            return {
                "status": "plan_needs_confirmation", "call": self.pending_call,
                "reason": e.decision.reason, "level": e.decision.level.name,
                "requires_typed_confirmation": e.decision.requires_typed_confirmation,
                "history": self.history,
            }
        self.history.append({"tool": tool, "args": args, "result": result})
        if not needs_followup:
            summary = result.get("result") if result.get("executed") else result.get("reason", str(result))
            return {"status": "plan_done", "summary": summary, "history": self.history}
        return self._continue_loop()

    def _continue_loop(self) -> dict:
        for _ in range(self.MAX_STEPS - len(self.history)):
            decision = next_step(self.instruction, self.history)
            if decision.get("done"):
                return {"status": "plan_done", "summary": decision.get("summary", ""), "history": self.history}
            if "tool" not in decision:
                # 規劃者既沒有標記done=true，也沒有給下一步的工具——與其硬把這種模糊回應當成
                # 錯誤丟給使用者，不如當作「其實已經做完了，只是忘了標記」，用上一步真實執行過的
                # 結果當摘要。真的完全沒有history（第一次呼叫就這樣）才算是真的失敗，需要誠實回報。
                if self.history:
                    last = self.history[-1]["result"]
                    summary = last.get("result") if last.get("executed") else last.get("reason", str(last))
                    return {"status": "plan_done", "summary": summary, "history": self.history}
                return {"status": "plan_incomplete", "reason": "規劃者沒有標記完成，也沒有給下一步的工具，先停下來", "history": self.history}
            try:
                result = self.ex.run(decision["tool"], decision.get("args", {}), session_id=self.session_id, intent=self.instruction)
            except ConfirmationRequired as e:
                self.pending_call = {"tool": decision["tool"], "args": decision.get("args", {})}
                self.pending_decision = e.decision
                return {
                    "status": "plan_needs_confirmation", "call": self.pending_call,
                    "reason": e.decision.reason, "level": e.decision.level.name,
                    "requires_typed_confirmation": e.decision.requires_typed_confirmation,
                    "history": self.history,
                }
            self.history.append({"tool": decision["tool"], "args": decision.get("args", {}), "result": result})
        return {"status": "plan_incomplete", "reason": f"超過{self.MAX_STEPS}步還沒完成，可能陷入循環，先停下來", "history": self.history}


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
