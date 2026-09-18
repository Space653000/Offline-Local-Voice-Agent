# -*- coding: utf-8 -*-
"""
Executor：LLM 只能輸出「想呼叫哪個工具＋參數」，真正碰電腦的只有這裡。
流程：PolicyEngine 判斷 -> (需要的話等使用者確認) -> 呼叫對應工具函式 -> 寫入稽核紀錄。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from policy.policy_engine import PolicyEngine
from executor import audit_db
from tools import basic_tools

def _require(args, key, tool):
    if key not in args or args[key] is None:
        raise ValueError(f"{tool} 需要參數 '{key}'")
    return args[key]


TOOL_IMPLEMENTATIONS = {
    "open_app": lambda args: basic_tools.open_app(args["app_name"]),
    "close_window": lambda args: basic_tools.close_app_by_pid(args["pid"]),  # 一定要用pid，不接受標題模糊比對
    "get_datetime": lambda args: basic_tools.get_datetime(),
    "take_screenshot": lambda args: basic_tools.take_screenshot(),
    "set_volume": lambda args: basic_tools.set_volume(level=args.get("level"), delta=args.get("delta")),
    "clipboard_op": lambda args: (
        basic_tools.clipboard_copy(args["text"]) if args.get("action") == "copy"
        else basic_tools.clipboard_paste() if args.get("action") == "paste"
        else (_ for _ in ()).throw(ValueError("clipboard_op 需要 action=copy 或 paste"))
    ),
    "window_op": lambda args: {
        "minimize": basic_tools.window_minimize_current,
        "show_desktop": basic_tools.window_show_desktop,
        "switch_next": basic_tools.window_switch_next,
    }.get(_require(args, "action", "window_op"), lambda: (_ for _ in ()).throw(
        ValueError(f"window_op 不支援的 action：{args.get('action')}（只接受 minimize/show_desktop/switch_next）")))(),
    "media_control": lambda args: basic_tools.media_key(_require(args, "action", "media_control")),
    "adjust_brightness": lambda args: basic_tools.set_brightness(level=args.get("level"), delta=args.get("delta")),
    "network_toggle": lambda args: (
        basic_tools.wifi_toggle(bool(args.get("on")))
        if args.get("device", "wifi") == "wifi"
        else (_ for _ in ()).throw(ValueError("network_toggle 目前只支援 device=wifi（藍牙沒有可靠的命令列介面）"))
    ),
    "calculator": lambda args: basic_tools.calculate(_require(args, "expression", "calculator")),
    "text_to_speech_op": lambda args: basic_tools.text_to_speech(_require(args, "text", "text_to_speech_op")),
    "translate": lambda args: basic_tools.translate(
        text=args.get("text"), target_language=args.get("target_language", "英文"), path=args.get("path")),
    "summarize_doc": lambda args: basic_tools.summarize_doc(text=args.get("text"), path=args.get("path")),
    "text_input_op": lambda args: basic_tools.type_text(_require(args, "text", "text_input_op")),
    "file_op": lambda args: basic_tools.file_op(_require(args, "action", "file_op"), **{k: v for k, v in args.items() if k != "action"}),
    "power_op": lambda args: basic_tools.power_action(_require(args, "action", "power_op")),
    "get_active_window": lambda args: basic_tools.get_active_window(),
    "list_windows": lambda args: basic_tools.list_windows(),
    "focus_window": lambda args: basic_tools.focus_window(pid=args.get("pid"), title=args.get("title")),
    "uia_click": lambda args: basic_tools.uia_click(_require(args, "pid", "uia_click"), _require(args, "control_name", "uia_click")),
    "uia_set_text": lambda args: basic_tools.uia_set_text(_require(args, "pid", "uia_set_text"), _require(args, "control_name", "uia_set_text"), _require(args, "text", "uia_set_text")),
    "uia_select": lambda args: basic_tools.uia_select(_require(args, "pid", "uia_select"), _require(args, "control_name", "uia_select"), _require(args, "item_name", "uia_select")),
    "press_key": lambda args: basic_tools.press_key(_require(args, "key", "press_key")),
    "hotkey": lambda args: basic_tools.hotkey(_require(args, "keys", "hotkey")),
    "speech_to_text_op": lambda args: basic_tools.speech_to_text(_require(args, "audio_path", "speech_to_text_op")),
    "record_screen": lambda args: basic_tools.record_screen(_require(args, "action", "record_screen")),
    "task_scheduler_op": lambda args: basic_tools.task_scheduler_op(
        _require(args, "action", "task_scheduler_op"), name=args.get("name"), command=args.get("command"),
        schedule=args.get("schedule"), time=args.get("time")),
    "startup_program_op": lambda args: basic_tools.startup_program_op(
        _require(args, "action", "startup_program_op"), name=args.get("name"), path=args.get("path")),
    "driver_op": lambda args: basic_tools.driver_op(args.get("action", "list"), keyword=args.get("keyword")),
    "photo_edit": lambda args: basic_tools.photo_edit(
        _require(args, "path", "photo_edit"), _require(args, "action", "photo_edit"),
        **{k: v for k, v in args.items() if k not in ("path", "action")}),
    "git_op": lambda args: basic_tools.git_op(
        _require(args, "action", "git_op"), repo_path=args.get("repo_path"),
        message=args.get("message"), path=args.get("path")),
    "print_or_scan": lambda args: basic_tools.print_or_scan(
        _require(args, "action", "print_or_scan"), path=args.get("path")),
}


class ConfirmationRequired(Exception):
    def __init__(self, decision):
        self.decision = decision
        super().__init__(decision.reason)


class Executor:
    def __init__(self):
        self.policy = PolicyEngine()

    def run(self, tool: str, args: dict, user_confirmed: bool = None, session_id: str = None, intent: str = None):
        """
        user_confirmed:
          None  -> 呼叫方還沒問過使用者（第一次呼叫）
          True  -> 使用者已經按了同意
          False -> 使用者拒絕，不執行

        session_id/intent：對照 docs/07 進度報告第8節抓到的Logging缺口——
        原本 conversation_log 跟 action_audit 兩張表沒有共同ID串連，也沒有紀錄
        「這個動作是為了達成使用者哪句話」，這裡補上讓兩張表能join、也知道intent。
        """
        import time
        decision = self.policy.evaluate(tool, args)

        if decision.requires_confirmation and user_confirmed is None:
            audit_db.log_action(tool, args, decision.level, True, None, executed=False,
                                 result_summary="等待使用者確認", session_id=session_id, intent=intent)
            raise ConfirmationRequired(decision)

        if decision.requires_confirmation and user_confirmed is False:
            audit_db.log_action(tool, args, decision.level, True, False, executed=False,
                                 result_summary="使用者拒絕", error="使用者拒絕執行",
                                 session_id=session_id, intent=intent)
            return {"executed": False, "reason": "使用者拒絕執行"}

        impl = TOOL_IMPLEMENTATIONS.get(tool)
        if impl is None:
            audit_db.log_action(tool, args, decision.level, decision.requires_confirmation, user_confirmed,
                                 executed=False, result_summary="尚未實作這個工具", error="工具尚未實作",
                                 session_id=session_id, intent=intent)
            return {"executed": False, "reason": f"工具 '{tool}' 尚未實作（只是意圖判斷，還沒接真正動作）"}

        t0 = time.time()
        try:
            result = impl(args)
            duration_ms = (time.time() - t0) * 1000
            audit_db.log_action(tool, args, decision.level, decision.requires_confirmation, user_confirmed,
                                 executed=True, result_summary=str(result), duration_ms=duration_ms,
                                 session_id=session_id, intent=intent)
            if tool == "open_app" and isinstance(result, dict) and "pid" in result:
                audit_db.record_known_app(args.get("app_name", ""))
            if tool == "file_op":
                self._record_touched_folders(args)
            return {"executed": True, "result": result}
        except Exception as e:
            duration_ms = (time.time() - t0) * 1000
            audit_db.log_action(tool, args, decision.level, decision.requires_confirmation, user_confirmed,
                                 executed=False, result_summary=f"執行失敗: {e}", error=str(e),
                                 duration_ms=duration_ms, session_id=session_id, intent=intent)
            return {"executed": False, "reason": str(e)}

    @staticmethod
    def _record_touched_folders(args: dict):
        """把file_op真的動到的資料夾記進known_folders（對照藍圖第13節Memory的Known Folders）。
        create_folder的path本身就是資料夾，其餘(open/rename/delete/move/copy的src/dst)
        則取檔案路徑的上層目錄——這幾個都是「檔案」路徑，不是資料夾路徑本身。"""
        paths = []
        if args.get("action") == "create_folder" and args.get("path"):
            paths.append(args["path"])
        else:
            for key in ("path", "src", "dst", "search_dir"):
                if args.get(key):
                    paths.append(args[key])
        for p in paths:
            try:
                resolved = basic_tools._resolve_under_home(p)
                folder = resolved if resolved.is_dir() else resolved.parent
                audit_db.record_known_folder(str(folder))
            except Exception:
                pass  # 記錄「用過哪些資料夾」是輔助資訊，這裡失敗不該影響工具本身已經執行成功的結果
