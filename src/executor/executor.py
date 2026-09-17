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
    "translate": lambda args: basic_tools.translate(_require(args, "text", "translate"), args.get("target_language", "英文")),
    "summarize_doc": lambda args: basic_tools.summarize_doc(_require(args, "text", "summarize_doc")),
    "text_input_op": lambda args: basic_tools.type_text(_require(args, "text", "text_input_op")),
    "file_op": lambda args: basic_tools.file_op(_require(args, "action", "file_op"), **{k: v for k, v in args.items() if k != "action"}),
    "power_op": lambda args: basic_tools.power_action(_require(args, "action", "power_op")),
}


class ConfirmationRequired(Exception):
    def __init__(self, decision):
        self.decision = decision
        super().__init__(decision.reason)


class Executor:
    def __init__(self):
        self.policy = PolicyEngine()

    def run(self, tool: str, args: dict, user_confirmed: bool = None):
        """
        user_confirmed:
          None  -> 呼叫方還沒問過使用者（第一次呼叫）
          True  -> 使用者已經按了同意
          False -> 使用者拒絕，不執行
        """
        decision = self.policy.evaluate(tool, args)

        if decision.requires_confirmation and user_confirmed is None:
            audit_db.log_action(tool, args, decision.level, True, None, executed=False,
                                 result_summary="等待使用者確認")
            raise ConfirmationRequired(decision)

        if decision.requires_confirmation and user_confirmed is False:
            audit_db.log_action(tool, args, decision.level, True, False, executed=False,
                                 result_summary="使用者拒絕")
            return {"executed": False, "reason": "使用者拒絕執行"}

        impl = TOOL_IMPLEMENTATIONS.get(tool)
        if impl is None:
            audit_db.log_action(tool, args, decision.level, decision.requires_confirmation, user_confirmed,
                                 executed=False, result_summary="尚未實作這個工具")
            return {"executed": False, "reason": f"工具 '{tool}' 尚未實作（只是意圖判斷，還沒接真正動作）"}

        try:
            result = impl(args)
            audit_db.log_action(tool, args, decision.level, decision.requires_confirmation, user_confirmed,
                                 executed=True, result_summary=str(result))
            return {"executed": True, "result": result}
        except Exception as e:
            audit_db.log_action(tool, args, decision.level, decision.requires_confirmation, user_confirmed,
                                 executed=False, result_summary=f"執行失敗: {e}")
            return {"executed": False, "reason": str(e)}
