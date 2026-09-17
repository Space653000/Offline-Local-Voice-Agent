# -*- coding: utf-8 -*-
"""
文字輸入的指令處理器——給網頁版文字輸入框用，跟 listen_loop.py 的語音路徑共用同一套
mode_classifier / full_pipeline / Executor / FrontDeskDialog，只是換成「HTTP請求/回應」
的無狀態互動方式，而不是語音那種「連續串流+callback」的方式。

對照 AERIS 藍圖第27.1節：Front Desk 要同時支援語音跟文字輸入，語音只是輸入方式之一，
不能因為做了語音就漏了文字。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "frontdesk"))

# Front Desk 多輪對話需要在多次 HTTP 請求之間保留狀態（使用者打完一句話後，
# 下一輪HTTP請求才會送出回答），這裡用記憶體裡的 dict 存正在進行中的對話，
# 用 session_id 對應——本機單人使用場景，不需要真正的資料庫或分散式session store。
_FRONTDESK_SESSIONS = {}


def classify(text: str) -> dict:
    from mode_classifier import classify as _classify
    return _classify(text)


def run_desktop_command(text: str) -> dict:
    from full_pipeline import understand
    from executor.executor import Executor, ConfirmationRequired
    from executor import audit_db
    audit_db.sync_policy_rules()
    ex = Executor()
    call = understand(text)
    try:
        result = ex.run(call["tool"], call["args"])
        return {"status": "done", "call": call, "result": result}
    except ConfirmationRequired as e:
        return {
            "status": "needs_confirmation", "call": call, "reason": e.decision.reason,
            "level": e.decision.level.name, "requires_typed_confirmation": e.decision.requires_typed_confirmation,
        }


def confirm_desktop_command(tool: str, args: dict, approved: bool, typed_keyword: str = None) -> dict:
    """
    文字版確認：L3(危險操作)一樣要求打出關鍵字「確認執行」，不能只回 true/false，
    跟語音版 _voice_confirm 的安全設計原則一致（不能只按/說「是」就等於同意危險操作）。
    """
    from executor.executor import Executor
    from executor import audit_db
    from policy.policy_engine import PolicyEngine
    audit_db.sync_policy_rules()
    decision = PolicyEngine().evaluate(tool, args)
    if decision.requires_typed_confirmation:
        approved = approved and (typed_keyword or "").replace(" ", "") == "確認執行"
    ex = Executor()
    result = ex.run(tool, args, user_confirmed=approved)
    return {"status": "done", "result": result}


def process_text(text: str, session_id: str) -> dict:
    """
    文字輸入的統一入口：先分流（跟listen_loop.handle_utterance邏輯一致)，
    再導向桌面控制或Front Desk文字問答。網頁的 /api/command 直接呼叫這個就好，
    不用自己重做一次分流判斷。
    """
    mode = classify(text)
    if mode["mode"] == "desktop_control":
        result = run_desktop_command(text)
        result["mode"] = "desktop_control"
        return result
    else:
        result = start_frontdesk_text(text, session_id)
        result["mode"] = "acoustic_engineering"
        return result


def start_frontdesk_text(text: str, session_id: str) -> dict:
    from dialog_state_machine import FrontDeskDialog
    dlg = FrontDeskDialog()
    step = dlg.capture(text, input_mode="text")
    _FRONTDESK_SESSIONS[session_id] = dlg
    return {"status": "frontdesk", "session_id": session_id, "step": step}


def continue_frontdesk_text(session_id: str, reply: str) -> dict:
    dlg = _FRONTDESK_SESSIONS.get(session_id)
    if dlg is None:
        return {"status": "error", "reason": "找不到這個對話（可能已經逾時或重啟過），請重新開始"}

    # 注意：dialog_state_machine.py 的 session.state 存的是「下一步要等待的輸入」，
    # 不是目前這輪回傳給使用者的 step["state"]（例如 capture() 回傳 step state=DIVERGE，
    # 但 session.state 這時已經被設成 CONVERGE，因為下一步要呼叫的是 converge()）。
    state_name = dlg.session.state.name
    if state_name == "CONVERGE":
        options = [o for o in reply.split("、") if o] or [reply]
        step = dlg.converge(chosen_directions=options)
        if step["state"] != "EVIDENCE":
            del _FRONTDESK_SESSIONS[session_id]
        return {"status": "frontdesk", "session_id": session_id, "step": step}
    elif state_name == "EVIDENCE":
        evidence = [e for e in reply.split("、") if e]
        step = dlg.evidence(available=evidence)
        return {"status": "frontdesk", "session_id": session_id, "step": step}
    elif state_name == "CONFIRM":
        approved = reply.strip() in ("是", "對", "好", "確認", "yes", "y", "可以")
        result = dlg.confirm(approved=approved, handoff_dir=Path("C:/0_JN1_AERIS_HANDOFF/orders"))
        del _FRONTDESK_SESSIONS[session_id]
        return {"status": "frontdesk_done", "result": result}
    else:
        del _FRONTDESK_SESSIONS[session_id]
        return {"status": "error", "reason": f"對話已經在 {state_name} 狀態，無法繼續"}
