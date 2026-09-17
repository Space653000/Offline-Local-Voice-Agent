# -*- coding: utf-8 -*-
"""
常駐監聽迴圈：麥克風 -> VAD -> 喚醒詞「嗨小助理」-> 錄下你講的話 -> whisper.cpp ASR ->
模式分流 -> (桌面操作: Executor真的執行 / 聲學工程問題: 交給Front Desk引導)

這個檔案設計成「處理一個音訊chunk」的邏輯跟「音訊從哪裡來」分開，
所以同一套邏輯可以接麥克風即時輸入，也可以接錄好的wav檔案（方便自動化測試，
不需要真人對著麥克風講話就能驗證整條管線邏輯是否正確）。
"""
import sys, subprocess, tempfile, wave, time, json
from pathlib import Path
from enum import Enum, auto
import numpy as np
import onnxruntime as ort

# Windows主控台預設用系統內碼（繁中通常是Big5），print emoji/中文可能會炸掉，
# 不能只靠呼叫者自己設定 PYTHONIOENCODING，這支程式未來會被其他東西（例如開機自動啟動）直接呼叫，
# 所以在程式碼裡自己保證輸出用 UTF-8，不依賴外部環境變數。
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "frontdesk"))

ROOT = Path(__file__).parent.parent
WHISPER_CLI = ROOT / "progress/p0/build/whisper.cpp/build/bin/whisper-cli.exe"
WHISPER_MODEL = ROOT / "progress/p0/build/whisper.cpp/models/ggml-medium.bin"
WAKEWORD_ONNX = Path(__file__).parent / "wakeword" / "hai_xiao_zhuli_wakeword.onnx"
VAD_ONNX = ROOT / "progress/p1_vad_wakeword/silero_vad.onnx"

CHUNK = 1280  # 80ms @ 16kHz，跟VAD/喚醒詞的streaming介面對齊
SR = 16000
WAKE_THRESHOLD = 0.5
END_OF_SPEECH_SILENCE_CHUNKS = 10  # 連續10個chunk(=0.8秒)偵測不到語音就當作講完了
MAX_RECORDING_CHUNKS = 150  # 最長錄12秒，避免一直錄下去
QUIET_CHUNKS_TO_CONFIRM_WAKE_ENDED = 4   # 喚醒後要先連續偵測到這麼多安靜chunk，才算喚醒詞自己的尾音真的講完了
MAX_WAIT_FOR_QUIET_CHUNKS = 40           # 最多等3.2秒讓喚醒詞尾音安靜下來，避免異常狀況卡死在這個階段
# 設計筆記（實測踩過的坑）：一開始用「固定緩衝期跳過0.4秒」想避開喚醒詞自己的尾音殘留，
# 但實測發現喚醒詞常常在還沒講完就提早觸發（例如「嗨小助理」講到「嗨小」就已經觸發），
# 觸發後還有將近1.4秒的尾音，固定0.4秒的緩衝期完全不夠，導致尾音的安靜段被誤判成「指令講完了」，
# 永遠等不到使用者真正開始講指令。改成「動態等到真的安靜下來，才開始正式聆聽指令」，不管尾音多長都能正確處理。


class State(Enum):
    IDLE = auto()               # 等待喚醒詞
    WAITING_FOR_QUIET = auto()  # 喚醒詞剛觸發，還在等喚醒詞自己的尾音安靜下來
    LISTENING = auto()          # 已經安靜過一次，正式在聽使用者講指令


class VADStreamer:
    """對照 P1 踩過的坑：silero-vad v5+ 需要前一個chunk最後64個sample當context一起餵，不能只餵單獨512samples。"""
    def __init__(self, onnx_path):
        self.sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        self.reset()

    def reset(self):
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.context = np.zeros(64, dtype=np.float32)

    def is_speech(self, chunk_1280: np.ndarray) -> bool:
        """1280 samples (80ms) 切成 512-sample 為主的sub-windows逐一判斷，只要有一個窗判定是語音就算。"""
        audio = chunk_1280.astype(np.float32) / 32768.0
        sr = np.array(16000, dtype=np.int64)
        any_speech = False
        for i in range(0, len(audio) - 512 + 1, 512):
            raw = audio[i:i + 512]
            full_input = np.concatenate([self.context, raw]).reshape(1, -1)
            out = self.sess.run(None, {"input": full_input, "sr": sr, "state": self.state})
            prob, self.state = out[0], out[1]
            self.context = raw[-64:]
            if float(prob[0][0]) > 0.5:
                any_speech = True
        return any_speech


class UtteranceRecorder:
    """
    共用的「錄到使用者講完一句話」邏輯，抽出來給 listen_loop 的喚醒後錄音、
    跟 Front Desk 多輪語音對話的每一輪都能重複使用，不要各寫一份。
    用法：每個chunk呼叫 feed()，回傳 None 表示還在錄，回傳 ndarray 表示這句話錄完了。
    """
    def __init__(self, vad: "VADStreamer", silence_chunks=END_OF_SPEECH_SILENCE_CHUNKS, max_chunks=MAX_RECORDING_CHUNKS):
        self.vad = vad
        self.silence_chunks = silence_chunks
        self.max_chunks = max_chunks
        self.reset()

    def reset(self):
        self.buffer = []
        self.silence_run = 0
        self.heard_speech = False
        self.vad.reset()

    def feed(self, chunk: np.ndarray):
        self.buffer.append(chunk)
        speech = self.vad.is_speech(chunk)
        if speech:
            self.silence_run = 0
            self.heard_speech = True
        else:
            self.silence_run += 1
        too_long = len(self.buffer) >= self.max_chunks
        enough_silence = self.heard_speech and self.silence_run >= self.silence_chunks
        if too_long or enough_silence:
            audio = np.concatenate(self.buffer)
            self.reset()
            return audio
        return None


STOP_PHRASES = ("停止", "取消", "不要執行", "不要", "算了")


def is_stop_command(text: str) -> bool:
    """
    對照 docs/01 第10節：「停止」「取消」「不要執行」要能直接打斷正在進行的流程。
    熱鍵(Ctrl+Shift+F12)才是最高優先級、保證瞬間生效；語音停止指令是次要防線，
    只在「使用者剛好講完一句完整的話、系統正要處理」這些檢查點生效，不是真正的即時中斷
    （要做到真正任意時刻的語音中斷，需要整個管線改成可隨時取消的非同步架構，這裡先做
    最實際、涵蓋大多數真實情境的版本：每次聽完一句話，先檢查是不是要喊停）。
    """
    stripped = text.strip().rstrip("。！.!")
    return stripped in STOP_PHRASES or any(stripped == p for p in STOP_PHRASES)


def run_asr(audio_int16: np.ndarray) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    with wave.open(str(tmp_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(audio_int16.tobytes())

    import os
    env = os.environ.copy()
    env["PATH"] = r"C:\Program Files\LLVM\bin;" + env.get("PATH", "")
    p = subprocess.run(
        [str(WHISPER_CLI), "-m", str(WHISPER_MODEL), "-f", str(tmp_path), "-l", "zh", "-nt"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore", env=env,
        cwd=str(WHISPER_CLI.parent.parent),
    )
    tmp_path.unlink(missing_ok=True)
    return p.stdout.strip()


class ListenLoop:
    def __init__(self, on_event=print, chunk_source=None):
        """chunk_source: 可選，一個callable每次回傳下一個80ms chunk。有給的話，
        偵測到聲學工程問題時會真的啟動 Front Desk 語音多輪引導（例如接麥克風的 run_live）；
        沒給的話（例如單元測試用固定的模擬音訊）就只記錄文字，不會嘗試繼續拉取更多音訊。"""
        from openwakeword.model import Model
        import uuid
        self.wake_model = Model(wakeword_models=[str(WAKEWORD_ONNX)], inference_framework="onnx")
        self.wake_model_name = list(self.wake_model.models.keys())[0]
        self.vad = VADStreamer(VAD_ONNX)
        self.on_event = on_event  # callback，方便測試時攔截事件而不是直接print
        self.chunk_source = chunk_source
        # 對照 docs/07 進度報告第8節Logging缺口：每次啟動常駐監聽都給一個獨立session_id，
        # 讓這次執行期間的conversation_log/action_audit能用同一個ID串起來查。
        self.session_id = "voice-" + uuid.uuid4().hex[:12]
        self.reset_to_idle()

    def reset_to_idle(self):
        self.state = State.IDLE
        self.recording_buffer = []
        self.silence_run = 0
        self.heard_speech = False
        self.quiet_run = 0
        self.wait_chunks = 0
        self.wake_model.reset()

    def process_chunk(self, chunk: np.ndarray):
        """處理一個80ms的音訊chunk。回傳這次處理後有沒有觸發完整的一次「使用者說完一句話」事件。"""
        if self.state == State.IDLE:
            pred = self.wake_model.predict(chunk)
            score = pred[self.wake_model_name]
            if score > WAKE_THRESHOLD:
                self.on_event({"type": "wake_detected", "score": float(score)})
                self.state = State.WAITING_FOR_QUIET
                self.quiet_run = 0
                self.wait_chunks = 0
                self.vad.reset()
            return None

        elif self.state == State.WAITING_FOR_QUIET:
            # 喚醒詞剛觸發，可能還有一段尾音沒講完（實測發現常常提早觸發，尾音可能長達1秒多）。
            # 這段期間不錄音、不計入指令內容，只是單純等它安靜下來，安靜夠久才代表喚醒詞真的講完了。
            self.wait_chunks += 1
            speech = self.vad.is_speech(chunk)
            self.quiet_run = 0 if speech else self.quiet_run + 1
            if self.quiet_run >= QUIET_CHUNKS_TO_CONFIRM_WAKE_ENDED or self.wait_chunks >= MAX_WAIT_FOR_QUIET_CHUNKS:
                self.on_event({"type": "wake_tail_ended", "waited_chunks": self.wait_chunks})
                self.state = State.LISTENING
                self.recording_buffer = []
                self.silence_run = 0
                self.heard_speech = False
            return None

        elif self.state == State.LISTENING:
            self.recording_buffer.append(chunk)
            speech = self.vad.is_speech(chunk)
            if speech:
                self.silence_run = 0
                self.heard_speech = True
            else:
                self.silence_run += 1

            too_long = len(self.recording_buffer) >= MAX_RECORDING_CHUNKS
            # 一定要先真的聽到指令語音，安靜夠久才算講完；否則使用者才剛開口沒多久就被誤判結束
            enough_silence = self.heard_speech and self.silence_run >= END_OF_SPEECH_SILENCE_CHUNKS
            if too_long or enough_silence:
                full_audio = np.concatenate(self.recording_buffer)
                self.reset_to_idle()
                self.on_event({"type": "utterance_end", "n_samples": len(full_audio)})
                return full_audio
            return None

    def _voice_confirm(self, decision) -> bool:
        """
        L2/L3 需要使用者確認時的語音確認流程。
        安全原則：沒有真的收到音源（例如單元測試用固定模擬音訊跑完就結束）一律當作拒絕，
        不能因為「沒聽到回覆」就預設放行——寧可誤拒，不能誤放行敏感/危險操作。
        L3（危險操作）刻意要求使用者複誦關鍵字「確認執行」，不接受單純「對」或「好」，
        對照 risk_levels.py 原始設計「不能只按是，要求輸入關鍵字才算確認」的精神。
        """
        from frontdesk.voice_dialog import speak, yes_no
        if self.chunk_source is None:
            return False

        is_l3 = decision.requires_typed_confirmation
        if is_l3:
            speak(f"{decision.reason}。這是比較危險的操作，如果真的要繼續，請說「確認執行」")
        else:
            speak(f"{decision.reason}，要繼續嗎？")

        recorder = UtteranceRecorder(self.vad)
        recorder.reset()
        while True:
            chunk = self.chunk_source()
            audio = recorder.feed(chunk)
            if audio is not None:
                reply = run_asr(audio)
                self.on_event({"type": "user_said", "text": reply})
                break

        if is_stop_command(reply):
            self.on_event({"type": "stopped_by_voice", "text": reply})
            speak("好，已經取消了")
            return False

        if is_l3:
            approved = "確認執行" in reply.replace(" ", "")
        else:
            approved = yes_no(reply)
        speak("好，已經取消了" if not approved else "好，執行")
        return approved

    def handle_utterance(self, audio: np.ndarray):
        """喚醒詞觸發+講完一句話後的完整處理：ASR -> 分流 -> 執行"""
        t0 = time.time()
        text = run_asr(audio)
        asr_ms = (time.time() - t0) * 1000
        self.on_event({"type": "asr_result", "text": text, "elapsed_ms": asr_ms})

        if not text.strip():
            self.on_event({"type": "empty_asr", "note": "沒聽清楚，回到待命狀態"})
            return

        if is_stop_command(text):
            self.on_event({"type": "stopped_by_voice", "text": text})
            return

        from mode_classifier import classify
        from executor import audit_db
        mode = classify(text)
        self.on_event({"type": "mode", "mode": mode})

        if mode["mode"] == "desktop_control":
            from full_pipeline import PlanRunner
            from executor.executor import Executor
            audit_db.sync_policy_rules()
            audit_db.touch_session(self.session_id, last_instruction=text)
            runner = PlanRunner(text, Executor(), session_id=self.session_id)
            self.on_event({"type": "executing", "text": text})
            plan_result = runner.run()
            while plan_result["status"] == "plan_needs_confirmation":
                self.on_event({"type": "needs_confirmation", "reason": plan_result["reason"], "level": plan_result["level"]})
                approved = self._voice_confirm(runner.pending_decision)
                plan_result = runner.resume(approved=approved)
            if plan_result["status"] == "plan_done":
                self.on_event({"type": "action_result", "history": plan_result["history"], "summary": plan_result["summary"]})
                reply_text = str(plan_result["summary"])
            else:
                self.on_event({"type": "action_result", "history": plan_result.get("history", []), "error": plan_result.get("reason")})
                reply_text = plan_result.get("reason")
            audit_db.log_conversation(text, reply_text=reply_text, asr_model="whisper.cpp",
                                       asr_latency_ms=asr_ms, session_id=self.session_id)
        else:
            self.on_event({"type": "acoustic_case_started", "text": text})
            audit_db.touch_session(self.session_id, last_instruction=text, last_tool="frontdesk")
            audit_db.log_conversation(text, reply_text="（進入Front Desk多輪引導，逐輪對話另外記在voice_dialog事件裡）",
                                       asr_model="whisper.cpp", asr_latency_ms=asr_ms, session_id=self.session_id)
            if self.chunk_source is not None:
                from frontdesk.voice_dialog import VoiceFrontDesk
                vfd = VoiceFrontDesk(self.chunk_source, on_event=self.on_event)
                vfd.run(text, input_mode="voice")
            else:
                self.on_event({"type": "front_desk_skipped",
                                "note": "這個呼叫沒有提供chunk_source（例如單元測試用固定模擬音訊），不會真的啟動多輪語音對話"})


LIVE_STATE_FILE = Path(__file__).parent.parent / "console" / "live_state.json"


# 對照 docs/01 藍圖第18節：UI 只需要5個canonical狀態（Listening/Thinking/Executing/
# Waiting confirmation/Stopped）。docs/07 進度報告第10節指出這裡原本沒有明確對應——
# 細顆粒度的status（wake_detected/listening_command等）留著給companion.html的動畫用，
# 另外加一個canonical_state欄位對應藍圖要求的5態，兩者並存，不用二選一。
CANONICAL_STATE_MAP = {
    "idle": "Listening",
    "wake_detected": "Listening",
    "listening_command": "Listening",
    "thinking": "Thinking",
    "executing": "Executing",
    "speaking": "Executing",       # Front Desk 問問題/複誦內容，本質是正在執行多輪引導任務
    "front_desk": "Executing",
    "waiting_confirmation": "Waiting confirmation",
    "stopped": "Stopped",
    "not_running": "Stopped",
}


class LiveStateWriter:
    """
    把技術性事件翻成新手看得懂的白話狀態，寫進一個小檔案，讓網頁版的「即時陪伴」介面可以顯示
    （不是每個人都要盯著終端機看一堆 JSON log）。用「寫到暫存檔再改名」保證網頁那邊不會讀到寫一半的檔案。
    """
    def __init__(self, path: Path = LIVE_STATE_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.transcript = ""
        self.response = ""

    def update(self, status: str, message: str, transcript: str = None, response: str = None):
        if transcript is not None:
            self.transcript = transcript
        if response is not None:
            self.response = response
        data = {
            "status": status, "message": message,
            "canonical_state": CANONICAL_STATE_MAP.get(status, "Listening"),
            "transcript": self.transcript, "response": self.response,
            "updated_at": time.time(),
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)


def run_live(device: int = None):
    """
    真的接麥克風即時監聽。Ctrl+C 停止。
    用 sounddevice 的 InputStream + queue，讓收音跟處理分開執行緒，避免處理速度跟不上導致漏音。
    """
    import sounddevice as sd
    import queue

    q: "queue.Queue" = queue.Queue()
    state = LiveStateWriter()
    state.update("idle", "待命中，說「嗨小助理」開始")

    def audio_callback(indata, frames, time_info, status):
        if status:
            print(f"[警告] 麥克風狀態: {status}", file=sys.stderr)
        q.put(indata[:, 0].copy())

    def on_event(e):
        et = e.get("type")
        if et == "wake_detected":
            print(f"\n🎤 偵測到喚醒詞（信心度 {e['score']:.2f}）— 開始聽你說話...")
            state.update("wake_detected", "我聽到你了！")
        elif et == "wake_tail_ended":
            print("   （喚醒詞講完了，換你說指令）")
            state.update("listening_command", "請說出你想做的事")
        elif et == "utterance_end":
            print(f"   （錄到 {e['n_samples']/SR:.1f} 秒，開始辨識...）")
            state.update("thinking", "我在想...")
        elif et == "asr_result":
            print(f"👂 聽到：「{e['text']}」（{e['elapsed_ms']:.0f}ms）")
            state.update("thinking", "我在想...", transcript=e["text"])
        elif et == "empty_asr":
            print("   （沒聽清楚，回到待命）")
            state.update("idle", "沒聽清楚，可以再說一次「嗨小助理」")
        elif et == "mode":
            pass
        elif et == "executing":
            print(f"⚙️  正在執行：「{e['text']}」")
            state.update("executing", "正在執行你的指令...")
        elif et == "action_result":
            # 對照PlanRunner整合後的事件格式（history=真實執行過的每一步，summary=完成時的結果文字，
            # error=沒完成時的原因）——這裡原本還在用改版前的e['result']欄位，會在這裡直接丟KeyError，
            # 是這次盤點施工時順便抓到的真實bug，不是新寫的功能才有的問題。
            msg = e.get("summary") or e.get("error") or "完成了"
            print(f"✅ {msg}")
            state.update("idle", "待命中，說「嗨小助理」開始", response=str(msg))
        elif et == "needs_confirmation":
            print(f"⚠️  這個動作需要你確認：{e['reason']}")
            state.update("waiting_confirmation", f"這個動作需要確認：{e['reason']}")
        elif et == "stopped_by_voice":
            # 之前完全沒接這個事件——使用者講「停止」之後，畫面會停在原本的狀態沒有更新，
            # 使用者講完看畫面完全沒反應，這是這次盤點順便抓到的真實UI落差。
            print(f"🛑 語音停止指令：「{e['text']}」")
            state.update("idle", "好，已經取消了，說「嗨小助理」重新開始")
        elif et == "acoustic_case_started":
            print(f"🔧 這聽起來是聲學工程問題，交給 AERIS Front Desk 引導...")
            state.update("front_desk", "這聽起來是專業問題，讓我多問你幾句...")
        elif et == "asking":
            print(f"🗣️  {e['question']}")
            state.update("speaking", e["question"])
        elif et == "user_said":
            print(f"👂 你說：「{e['text']}」")
            state.update("thinking", "我在想...", transcript=e["text"])
        elif et == "preview":
            print(f"📋 確認內容：{e['summary']}")
        elif et == "front_desk_done":
            print(f"✅ Front Desk 完成：{e['result']}")
            state.update("idle", "待命中，說「嗨小助理」開始", response="已經幫你整理好送出去了")
        elif et == "front_desk_skipped":
            pass

    loop = ListenLoop(on_event=on_event, chunk_source=q.get)

    # ---- 緊急停止熱鍵（P4安全需求，對照 docs/01 第10節：必須是 Ctrl+Shift+F12）----
    EMERGENCY_HOTKEY = "ctrl+shift+f12"
    stop_flag = {"stop": False}

    def emergency_stop():
        stop_flag["stop"] = True
        print(f"\n🛑 緊急停止熱鍵觸發（{EMERGENCY_HOTKEY}），立刻停止監聽")
        state.update("stopped", "已緊急停止，重新執行程式才會再開始監聽")

    try:
        import keyboard
        keyboard.add_hotkey(EMERGENCY_HOTKEY, emergency_stop)
        hotkey_ready = True
    except Exception as e:
        print(f"[警告] 緊急停止熱鍵註冊失敗：{e}（仍然可以用 Ctrl+C 停止）", file=sys.stderr)
        hotkey_ready = False

    print("=== 語音代理人開始監聽（本機GPU，完全離線）===")
    print(f'說「嗨小助理」開始，例如：「嗨小助理，現在幾點」')
    if hotkey_ready:
        print(f"緊急停止：隨時按 {EMERGENCY_HOTKEY}")
    print("按 Ctrl+C 停止\n")

    # ---- 休眠/闔蓋偵測（P4安全需求）：筆電闔蓋通常會讓系統休眠，音訊串流會中斷一段時間，
    # 用「兩個chunk之間隔太久」間接判斷發生過休眠，避免使用者開蓋當下環境音被誤判成指令 ----
    SLEEP_GAP_THRESHOLD_SEC = 5.0
    last_chunk_time = [time.time()]

    with sd.InputStream(samplerate=SR, channels=1, dtype="int16", blocksize=CHUNK,
                         device=device, callback=audio_callback):
        try:
            while not stop_flag["stop"]:
                chunk = q.get()
                now = time.time()
                gap = now - last_chunk_time[0]
                last_chunk_time[0] = now
                if gap > SLEEP_GAP_THRESHOLD_SEC:
                    print(f"\n💤 偵測到 {gap:.1f} 秒的音訊中斷（可能是闔蓋/休眠過），重新回到待命狀態，不處理這段空檔")
                    loop.reset_to_idle()
                    state.update("idle", "剛剛可能休眠過，已重新待命，說「嗨小助理」開始")
                    continue
                utterance = loop.process_chunk(chunk)
                if utterance is not None:
                    loop.handle_utterance(utterance)
        except KeyboardInterrupt:
            print("\n停止監聽")
        finally:
            if hotkey_ready:
                import keyboard
                keyboard.remove_hotkey(EMERGENCY_HOTKEY)
            if stop_flag["stop"]:
                state.update("stopped", "已緊急停止，重新執行程式才會再開始監聽")
            else:
                state.update("not_running", "")


if __name__ == "__main__":
    run_live()
