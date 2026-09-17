# -*- coding: utf-8 -*-
"""
Front Desk 多輪語音對話控制器：把 dialog_state_machine（文字版問答邏輯）接上真正的
語音輸入/輸出，讓聲學工程案例可以整段用講的走完 S1-S8，不用打字。

設計：每一輪都是「助理講問題 -> 錄使用者回答 -> ASR -> 用LLM把自由回答對應回選項 -> 進下一輪」。
跟 listen_loop.py 共用 UtteranceRecorder（錄到講完一句話）跟 run_asr（whisper.cpp GPU）。
"""
import sys, json, requests
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from dialog_state_machine import FrontDeskDialog
from listen_loop import UtteranceRecorder, VADStreamer, VAD_ONNX, run_asr, CHUNK, SR, is_stop_command

LLM_URL = "http://127.0.0.1:8811/v1/chat/completions"


class StoppedByUser(Exception):
    """對照 docs/01 第10節：使用者講「停止/取消/不要執行」要能直接打斷正在進行的引導流程。"""
    pass


def speak(text: str):
    """直接用 SAPI 播放到喇叭，不寫檔案——語音助理要能即時講話，不是每次開個PowerShell行程。"""
    import win32com.client
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    for v in voice.GetVoices():
        if "Hanhan" in v.GetDescription():
            voice.Voice = v
            break
    voice.Speak(text)


def match_choice(user_reply: str, options: list) -> list:
    """
    把使用者自由講的回答，對應回選項清單裡的項目（可能選多個）。
    用LLM做語意比對，不是死板的字串完全比對——使用者可能講「應該是漏氣那個」而不是選項的精確字眼。
    """
    schema = {
        "type": "object",
        "properties": {"selected": {"type": "array", "items": {"type": "string", "enum": options}}},
        "required": ["selected"],
    }
    body = {
        "model": "local",
        "messages": [
            {"role": "system", "content": f"使用者的回答要對應到下面哪些選項（可能選一個或多個，語意相近就算）：\n{chr(10).join(options)}"},
            {"role": "user", "content": user_reply},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "m", "schema": schema}},
        "max_tokens": 60, "temperature": 0.0,
    }
    r = requests.post(LLM_URL, json=body, timeout=30)
    r.raise_for_status()
    result = json.loads(r.json()["choices"][0]["message"]["content"])
    return result.get("selected", [])


def yes_no(user_reply: str) -> bool:
    schema = {"type": "object", "properties": {"agree": {"type": "boolean"}}, "required": ["agree"]}
    body = {
        "model": "local",
        "messages": [
            {"role": "system", "content": "判斷使用者是同意/確認，還是不同意/取消。只輸出JSON。"},
            {"role": "user", "content": user_reply},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "m", "schema": schema}},
        "max_tokens": 20, "temperature": 0.0,
    }
    r = requests.post(LLM_URL, json=body, timeout=30)
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])["agree"]


class VoiceFrontDesk:
    def __init__(self, mic_chunk_source, on_event=print):
        """mic_chunk_source: 一個callable，每次呼叫回傳下一個80ms音訊chunk（跟listen_loop對接用）"""
        self.next_chunk = mic_chunk_source
        self.on_event = on_event
        self.vad = VADStreamer(VAD_ONNX)
        self.recorder = UtteranceRecorder(self.vad)

    def _listen_one_utterance(self) -> str:
        self.recorder.reset()
        while True:
            chunk = self.next_chunk()
            audio = self.recorder.feed(chunk)
            if audio is not None:
                text = run_asr(audio)
                self.on_event({"type": "user_said", "text": text})
                if is_stop_command(text):
                    raise StoppedByUser(text)
                return text

    def run(self, initial_text: str, input_mode: str = "voice", handoff_dir=None):
        """從使用者第一句話（已經觸發acoustic_engineering分流）開始，走完整個引導流程。"""
        try:
            return self._run(initial_text, input_mode, handoff_dir)
        except StoppedByUser as e:
            self.on_event({"type": "stopped_by_voice", "text": str(e)})
            speak("好，已經取消這次的問題引導了")
            return {"state": "CANCELLED_BY_USER"}

    def _run(self, initial_text: str, input_mode: str, handoff_dir):
        dlg = FrontDeskDialog()
        step = dlg.capture(initial_text, input_mode=input_mode)

        # DIVERGE
        q = f"{step['question']} " + "、".join(step["options"])
        self.on_event({"type": "asking", "question": q})
        speak(step["question"] + "，你可以說：" + "、".join(step["options"][:4]) + "等等")
        reply = self._listen_one_utterance()
        chosen = match_choice(reply, step["options"]) or [step["options"][0]]
        step = dlg.converge(chosen_directions=chosen)

        # EVIDENCE
        self.on_event({"type": "asking", "question": step["question"]})
        speak(step["question"] + "，你可以說：" + "、".join(step["options"][:4]))
        reply = self._listen_one_utterance()
        evidence = match_choice(reply, step["options"])
        step = dlg.evidence(available=evidence)

        # PREVIEW + CONFIRM
        summary = step["summary"]
        preview_text = (f"整理一下：產品是{summary['product']}，問題是{summary['user_goal']}，"
                         f"方向是{summary['direction']}，這樣送給AERIS處理可以嗎？")
        self.on_event({"type": "preview", "summary": summary})
        speak(preview_text)
        reply = self._listen_one_utterance()
        approved = yes_no(reply)

        result = dlg.confirm(approved=approved, handoff_dir=handoff_dir)
        if result["state"] == "ORDER_LOCKED":
            speak("好，已經幫你送出給AERIS處理了")
        else:
            speak("好，先取消這次")
        self.on_event({"type": "front_desk_done", "result": result})
        return result
