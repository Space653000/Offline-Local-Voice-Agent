# -*- coding: utf-8 -*-
"""
最基本、風險最低的幾個工具的真實實作（對照 P2 的 tools_and_labels_v2.py）。
禁止 execute_any_shell_command 這種萬用工具（CLAUDE.md 施工鐵則）——
每個工具都是獨立、參數固定、能單獨稽核的函式，不是丟一串字串去執行。
"""
import subprocess
import datetime
from pathlib import Path

KNOWN_APPS = {
    "notepad": "notepad.exe",
    "記事本": "notepad.exe",
    "calculator": "calc.exe",
    "小算盤": "calc.exe",
    "explorer": "explorer.exe",
    "檔案總管": "explorer.exe",
    "settings": "ms-settings:",
    "設定": "ms-settings:",
}


# Windows 11 上有些內建程式（記事本、小算盤...）現在是 MSIX 封裝的商店應用程式，
# system32 裡的 .exe 只是個轉發殼層，啟動後會馬上結束，真正的視窗跑在完全不同的 PID 底下。
# 直接信任 Popen 回傳的 pid 會抓錯（P3 實測踩到的坑），改成比對啟動前後的行程差異來抓到真正的 PID。
REAL_PROCESS_NAME = {
    "notepad.exe": "Notepad.exe",
    "calc.exe": "CalculatorApp.exe",
}


def _running_pids(process_name: str) -> set:
    import psutil
    return {p.pid for p in psutil.process_iter(["name"]) if (p.info["name"] or "").lower() == process_name.lower()}


def open_app(app_name: str) -> dict:
    """回傳真正視窗的 process id（不是轉發殼層的 pid），之後關閉一定要用這個 pid 精確指定。"""
    import time
    exe = KNOWN_APPS.get(app_name.lower()) or KNOWN_APPS.get(app_name)
    if not exe:
        raise ValueError(f"不在白名單內的應用程式：{app_name}（安全設計：只能開白名單裡的程式，不接受任意字串）")

    real_name = REAL_PROCESS_NAME.get(exe, exe)
    before = _running_pids(real_name)
    subprocess.Popen(["cmd", "/c", "start", "", exe] if exe.endswith(":") else [exe])

    real_pid = None
    for _ in range(30):  # 最多等 3 秒
        time.sleep(0.1)
        new_pids = _running_pids(real_name) - before
        if new_pids:
            real_pid = new_pids.pop()
            break
    if real_pid is None:
        raise RuntimeError(f"啟動 {app_name} 後 3 秒內偵測不到新的行程，可能啟動失敗")
    return {"message": f"已開啟 {app_name}", "pid": real_pid}


def close_app_by_pid(pid: int) -> str:
    """
    安全設計（P3 實測踩過的坑）：絕對不能用「視窗標題包含某段文字」去找視窗來關，
    因為使用者電腦上可能剛好有其他無關視窗標題相符，會誤關使用者自己正在用的東西。
    只能用 open_app 回傳的、我們自己開啟的那個 process 的 pid 來精確指定要關哪一個。

    踩坑記錄：如果視窗被最小化過（例如剛叫過 window_minimize_current 或 window_show_desktop），
    pywinauto 的 top_window() 有時找不到「頂層可見視窗」而丟例外，即使行程明明還在跑。
    這種情況下改用 psutil 直接依 pid 結束行程當備援——因為呼叫方一定是傳我們自己 open_app
    追蹤到的真實 pid，不是使用者其他無關的行程，所以這個備援手段一樣是安全的。
    """
    from pywinauto import Application
    try:
        app = Application(backend="uia").connect(process=pid)
        title = app.top_window().window_text()
        app.top_window().close()
        return f"已關閉 pid={pid}（{title}）"
    except Exception as e:
        import psutil
        try:
            p = psutil.Process(pid)
            name = p.name()
            p.terminate()
            return f"已關閉 pid={pid}（{name}，視窗已最小化找不到頂層視窗，改用行程終止的備援方式：{e}）"
        except psutil.NoSuchProcess:
            return f"pid={pid} 已經不存在，可能已經被關掉了"


def get_datetime() -> str:
    now = datetime.datetime.now()
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    return f"現在是 {now.strftime('%Y-%m-%d %H:%M:%S')}，星期{weekdays[now.weekday()]}"


def take_screenshot(save_dir: str = None) -> str:
    from PIL import ImageGrab
    save_dir = Path(save_dir) if save_dir else Path.home() / "Pictures" / "voice_agent_screenshots"
    save_dir.mkdir(parents=True, exist_ok=True)
    fname = save_dir / f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    ImageGrab.grab().save(fname)
    return str(fname)


def _volume_interface():
    from pycaw.pycaw import AudioUtilities
    return AudioUtilities.GetSpeakers().EndpointVolume


def get_volume() -> int:
    vol = _volume_interface()
    return round(vol.GetMasterVolumeLevelScalar() * 100)


def set_volume(level: int = None, delta: int = None) -> str:
    """
    安全設計：只接受絕對值(level, 0-100)或相對調整(delta)，兩者擇一。
    不接受「靜音全部裝置」這種模糊指令——靜音要透過 level=0 明確表達。

    踩坑記錄：Windows 音量有「數值」跟「靜音旗標」兩個獨立狀態——按過靜音鍵之後，
    就算把音量數值調到50%，只要靜音旗標還是開著，還是完全沒聲音。使用者體感上會覺得
    「明明說了調到50%怎麼還是沒聲音」，所以設定明確音量時要順便解除靜音旗標。
    """
    vol = _volume_interface()
    if level is not None:
        level = max(0, min(100, int(level)))
        vol.SetMasterVolumeLevelScalar(level / 100.0, None)
        if level > 0 and vol.GetMute():
            vol.SetMute(0, None)
        return f"音量已設定為 {level}%"
    if delta is not None:
        current = vol.GetMasterVolumeLevelScalar() * 100
        new_level = max(0, min(100, current + delta))
        vol.SetMasterVolumeLevelScalar(new_level / 100.0, None)
        if new_level > 0 and vol.GetMute():
            vol.SetMute(0, None)
        return f"音量從 {round(current)}% 調整到 {round(new_level)}%"
    raise ValueError("set_volume 必須指定 level 或 delta 其中一個")


def clipboard_copy(text: str) -> str:
    import pyperclip
    pyperclip.copy(text)
    return f"已複製到剪貼簿：{text[:30]}{'...' if len(text) > 30 else ''}"


def clipboard_paste() -> str:
    import pyperclip
    return pyperclip.paste()


# ---- window_op：只操作「目前作用中」的視窗，不用標題模糊比對去找視窗（Notepad事件學到的教訓）----

def window_minimize_current() -> str:
    import win32gui, win32con
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    return f"已將「{title}」最小化"


def window_show_desktop() -> str:
    """顯示桌面（最小化全部視窗），這是標準Windows功能鍵(Win+D)，不會關閉或動到個別視窗內容。"""
    import win32api, win32con
    win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
    win32api.keybd_event(ord('D'), 0, 0, 0)
    win32api.keybd_event(ord('D'), 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
    return "已顯示桌面"


def window_switch_next() -> str:
    """模擬 Alt+Tab 切換到下一個視窗（標準操作，使用者自己按這個鍵也是一樣效果，完全可逆）。"""
    import win32api, win32con
    win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
    win32api.keybd_event(win32con.VK_TAB, 0, 0, 0)
    win32api.keybd_event(win32con.VK_TAB, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
    return "已切換到下一個視窗"


# ---- media_control：標準媒體鍵，跟鍵盤上的播放/暫停鍵完全一樣效果 ----

def media_key(action: str) -> str:
    import win32api, win32con
    KEYS = {
        "play_pause": win32con.VK_MEDIA_PLAY_PAUSE, "next": win32con.VK_MEDIA_NEXT_TRACK,
        "prev": win32con.VK_MEDIA_PREV_TRACK, "mute": win32con.VK_VOLUME_MUTE,
    }
    if action not in KEYS:
        raise ValueError(f"不支援的媒體控制動作：{action}（只接受 play_pause/next/prev/mute）")
    vk = KEYS[action]
    win32api.keybd_event(vk, 0, 0, 0)
    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
    LABELS = {"play_pause": "播放/暫停", "next": "下一首", "prev": "上一首", "mute": "靜音切換"}
    return f"已送出媒體鍵：{LABELS[action]}"


# ---- adjust_brightness：透過 WMI，筆電螢幕標準介面 ----

def get_brightness() -> int:
    import wmi
    c = wmi.WMI(namespace="wmi")
    return c.WmiMonitorBrightness()[0].CurrentBrightness


def set_brightness(level: int = None, delta: int = None) -> str:
    import wmi
    c = wmi.WMI(namespace="wmi")
    methods = c.WmiMonitorBrightnessMethods()[0]
    current = get_brightness()
    if level is not None:
        new_level = max(0, min(100, int(level)))
    elif delta is not None:
        new_level = max(0, min(100, current + delta))
    else:
        raise ValueError("set_brightness 必須指定 level 或 delta 其中一個")
    methods.WmiSetBrightness(new_level, 0)
    return f"螢幕亮度從 {current}% 調整到 {new_level}%"


# ---- network_toggle：只做 Wi-Fi 開關（藍牙開關Windows沒有對應的簡單命令列介面，先不做，避免用不可靠的方式假裝有效）----

def wifi_toggle(on: bool) -> str:
    """用 netsh 控制 Wi-Fi 介面卡的啟用/停用狀態，這是標準系統管理指令，效果跟去設定裡手動切換一樣。"""
    interface_name = _get_wifi_interface_name()
    action = "enable" if on else "disable"
    result = subprocess.run(
        ["netsh", "interface", "set", "interface", interface_name, action],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    if result.returncode != 0:
        raise RuntimeError(f"Wi-Fi 切換失敗：{result.stderr or result.stdout}")
    return f"Wi-Fi 已{'開啟' if on else '關閉'}"


def _get_wifi_interface_name() -> str:
    result = subprocess.run(["netsh", "interface", "show", "interface"],
                             capture_output=True, text=True, encoding="utf-8", errors="ignore")
    for line in result.stdout.splitlines():
        if "Wi-Fi" in line or "無線" in line:
            parts = line.split()
            return " ".join(parts[3:]) if len(parts) > 3 else "Wi-Fi"
    return "Wi-Fi"


# ---- calculator：不透過開計算機App模擬按鍵（不可靠），直接用受限的算式運算 ----

def calculate(expression: str) -> str:
    """
    安全設計：只允許數字跟基本運算符號，用 AST 白名單方式運算，不是 eval() 任意字串
    （eval 任意字串等於變相的 execute_any_shell_command，CLAUDE.md 明確禁止這種萬用工具）。
    """
    import ast, operator
    OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg, ast.Mod: operator.mod}

    def eval_node(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return OPS[type(node.op)](eval_node(node.left), eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            return OPS[type(node.op)](eval_node(node.operand))
        raise ValueError(f"算式包含不允許的內容：{expression}")

    tree = ast.parse(expression, mode="eval")
    result = eval_node(tree.body)
    return f"{expression} = {result}"


# ---- text_to_speech_op：跟 voice_dialog.py 的 speak() 共用同一支 SAPI 介面 ----

def text_to_speech(text: str) -> str:
    import win32com.client
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    for v in voice.GetVoices():
        if "Hanhan" in v.GetDescription():
            voice.Voice = v
            break
    voice.Speak(text)
    return f"已唸出：{text[:30]}{'...' if len(text) > 30 else ''}"


# ---- translate / summarize_doc：借用已經常駐在跑的 llama-server（GPU），純本機、不上雲端 ----

def _llm_complete(system_prompt: str, user_content: str, max_tokens=300) -> str:
    import requests
    body = {
        "model": "local",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
        "max_tokens": max_tokens, "temperature": 0.2,
    }
    r = requests.post("http://127.0.0.1:8811/v1/chat/completions", json=body, timeout=30)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def translate(text: str, target_language: str = "英文") -> str:
    return _llm_complete(f"把使用者的句子翻譯成{target_language}，只輸出翻譯結果，不要解釋。", text, max_tokens=200)


def summarize_doc(text: str) -> str:
    return _llm_complete("把使用者提供的內容整理成重點摘要，條列3-5點，繁體中文。", text, max_tokens=400)


# ---- text_input_op：把文字輸入到目前作用中的欄位（使用者自己要確保游標在正確的地方）----

def type_text(text: str) -> str:
    import win32com.client
    shell = win32com.client.Dispatch("WScript.Shell")
    # SendKeys 對特殊字元(+^%~(){}[])有特殊意義，要逐一逸出，避免打字內容被誤解成快速鍵
    escaped = "".join(f"{{{c}}}" if c in "+^%~(){}[]" else c for c in text)
    shell.SendKeys(escaped)
    return f"已輸入文字：{text[:30]}{'...' if len(text) > 30 else ''}"


# ---- file_op：本機檔案操作（藍圖第7節明文列出的 find_file/open_file/move_file/copy_file/rename_file/create_folder）----
# 安全設計：搬移/複製/改名/建資料夾/刪除這幾個會「真的改變檔案系統狀態」的動作，一律限制在使用者
# 自己的家目錄底下（Path.home()，例如 C:\Users\xxx），不接受操作系統目錄（C:\Windows、C:\Program Files
# 等）路徑，防止LLM判斷錯誤或使用者口誤，不小心對系統檔案動手。find_file/open_file 是唯讀操作，不在此限。

def _resolve_under_home(path_str: str) -> Path:
    """
    使用者講話（或LLM填參數）常常不會給絕對路徑，例如「建一個叫done的資料夾」——
    這種相對路徑如果直接用 Path().resolve() 展開，會相對於「這個常駐服務行程的目前工作目錄」
    展開（例如 console/），不是使用者直覺以為的「我的家目錄」，導致明明合理的請求被安全檢查擋下。
    這裡統一規則：只有使用者/LLM主動給了絕對路徑才照字面用，其餘一律當成「相對於家目錄」。
    """
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = Path.home() / p
    return p.resolve()


def _require_safe_path(path_str: str, action: str) -> Path:
    safe_root = Path.home().resolve()
    p = _resolve_under_home(path_str)
    try:
        p.relative_to(safe_root)
    except ValueError:
        raise ValueError(f"{action} 只允許操作使用者家目錄（{safe_root}）底下的檔案，不允許：{p}")
    return p


def find_file(name: str, search_dir: str = None) -> str:
    search_root = _resolve_under_home(search_dir) if search_dir else Path.home()
    if not search_root.exists():
        raise ValueError(f"搜尋目錄不存在：{search_root}")
    matches = []
    for p in search_root.rglob(f"*{name}*"):
        matches.append(str(p))
        if len(matches) >= 20:
            break
    if not matches:
        return f"在 {search_root} 底下找不到包含「{name}」的檔案或資料夾"
    return f"找到 {len(matches)} 個符合的項目：\n" + "\n".join(matches)


def open_file(path: str) -> str:
    import os
    p = _resolve_under_home(path)
    if not p.exists():
        raise ValueError(f"檔案不存在：{p}")
    os.startfile(str(p))
    return f"已開啟：{p}"


def move_file(src: str, dst: str) -> str:
    import shutil
    src_p = _require_safe_path(src, "move_file（來源）")
    if not src_p.exists():
        raise ValueError(f"來源不存在：{src_p}")
    dst_p = _require_safe_path(dst, "move_file（目的地）")
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_p), str(dst_p))
    return f"已搬移 {src_p} -> {dst_p}"


def copy_file(src: str, dst: str) -> str:
    import shutil
    src_p = _require_safe_path(src, "copy_file（來源）")
    if not src_p.exists():
        raise ValueError(f"來源不存在：{src_p}")
    dst_p = _require_safe_path(dst, "copy_file（目的地）")
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    if src_p.is_dir():
        shutil.copytree(str(src_p), str(dst_p))
    else:
        shutil.copy2(str(src_p), str(dst_p))
    return f"已複製 {src_p} -> {dst_p}"


def rename_file(path: str, new_name: str) -> str:
    p = _require_safe_path(path, "rename_file")
    if not p.exists():
        raise ValueError(f"檔案不存在：{p}")
    if "/" in new_name or "\\" in new_name:
        raise ValueError("new_name 只能是檔名本身，不能包含路徑分隔符（要移動位置請用 move_file）")
    new_p = p.parent / new_name
    p.rename(new_p)
    return f"已重新命名：{p.name} -> {new_name}"


def create_folder(path: str) -> str:
    p = _require_safe_path(path, "create_folder")
    p.mkdir(parents=True, exist_ok=True)
    return f"已建立資料夾：{p}"


def delete_file(path: str) -> str:
    """
    這是 file_op 底下唯一會被 ESCALATION_RULES 拉高到 L3 的動作（risk_levels.py 已經設定
    ("file_op","delete") -> L3_DANGEROUS），一定要走過使用者「確認執行」複誦才會執行到這裡。
    用 send2trash 送進資源回收桶，不是 os.remove 那種永久刪除，使用者反悔還能復原。
    只支援刪單一檔案，不支援遞迴刪整個資料夾（安全設計，降低一次誤刪的損失範圍，
    要刪資料夾請使用者自己去檔案總管操作）。
    """
    import send2trash
    p = _require_safe_path(path, "delete_file")
    if not p.exists():
        raise ValueError(f"檔案不存在：{p}")
    if p.is_dir():
        raise ValueError("delete_file 不支援刪除整個資料夾，只能刪單一檔案（安全設計，降低誤刪範圍）")
    send2trash.send2trash(str(p))
    return f"已將 {p} 移到資源回收桶（不是永久刪除，還能從回收桶復原）"


def file_op(action: str, **kwargs) -> str:
    handlers = {
        "find": lambda: find_file(kwargs["name"], kwargs.get("search_dir")),
        "open": lambda: open_file(kwargs["path"]),
        "move": lambda: move_file(kwargs["src"], kwargs["dst"]),
        "copy": lambda: copy_file(kwargs["src"], kwargs["dst"]),
        "rename": lambda: rename_file(kwargs["path"], kwargs["new_name"]),
        "create_folder": lambda: create_folder(kwargs["path"]),
        "delete": lambda: delete_file(kwargs["path"]),
    }
    if action not in handlers:
        raise ValueError(f"file_op 不支援的 action：{action}（只接受 find/open/move/copy/rename/create_folder/delete）")
    return handlers[action]()


# ---- power_op：整台電腦的電源狀態（藍圖第9節L3危險操作，一定要走typed confirmation）----
# 安全設計：shutdown/restart 都用 Windows 標準的 `shutdown /t 30` 排程延遲執行，不是立刻斷電——
# 給使用者30秒反悔空間，反悔時說「取消關機」會呼叫 action=cancel（shutdown /a）中止排程。

def power_action(action: str) -> str:
    import subprocess
    if action == "shutdown":
        subprocess.run(["shutdown", "/s", "/t", "30"], check=True)
        return "已排程關機，30秒後執行。如果要反悔，趕快說「取消關機」"
    if action == "restart":
        subprocess.run(["shutdown", "/r", "/t", "30"], check=True)
        return "已排程重新啟動，30秒後執行。如果要反悔，趕快說「取消關機」"
    if action == "cancel":
        subprocess.run(["shutdown", "/a"], check=True)
        return "已取消排程中的關機/重新啟動"
    if action == "sleep":
        import ctypes
        ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
        return "已進入睡眠模式"
    raise ValueError(f"power_op 不支援的 action：{action}（只接受 shutdown/restart/sleep/cancel）")
