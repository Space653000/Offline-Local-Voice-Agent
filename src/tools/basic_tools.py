# -*- coding: utf-8 -*-
"""
最基本、風險最低的幾個工具的真實實作（對照 P2 的 tools_and_labels_v2.py）。
禁止 execute_any_shell_command 這種萬用工具（CLAUDE.md 施工鐵則）——
每個工具都是獨立、參數固定、能單獨稽核的函式，不是丟一串字串去執行。
"""
import subprocess
import sys
import ctypes
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config_loader import load_tools_config

# 對照 docs/07 進度報告第11節：這兩張表原本寫死在這裡，現在外部化到 config/tools.yaml，
# 使用者可以直接改YAML調整能開哪些App，不需要碰程式碼。這是白名單（安全邊界），跟
# executor/audit_db.py 的 known_apps 表（單純「用過的紀錄」）是兩件事。
_tools_cfg = load_tools_config()
KNOWN_APPS = _tools_cfg.get("known_apps") or {}
REAL_PROCESS_NAME = _tools_cfg.get("real_process_name") or {}


def _running_pids(process_name: str) -> set:
    import psutil
    return {p.pid for p in psutil.process_iter(["name"]) if (p.info["name"] or "").lower() == process_name.lower()}


def open_app(app_name: str) -> dict:
    """回傳真正視窗的 process id（不是轉發殼層的 pid），之後關閉一定要用這個 pid 精確指定。"""
    import time
    exe = KNOWN_APPS.get(app_name.lower()) or KNOWN_APPS.get(app_name)
    if not exe:
        raise ValueError(f"不在白名單內的應用程式：{app_name}（安全設計：只能開白名單裡的程式，不接受任意字串）")

    # exe現在可能是完整路徑（例如 C:\Windows\System32\notepad.exe），REAL_PROCESS_NAME這張表
    # 的key是短檔名，要用basename去對照，不能拿完整路徑字串直接查表。
    exe_basename = Path(exe).name if not exe.endswith(":") else exe
    real_name = REAL_PROCESS_NAME.get(exe_basename, exe_basename)
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


def find_file(name: str = None, search_dir: str = None, extension: str = None, newest_only: bool = False) -> str:
    """
    對照 docs/07 進度報告P6缺口：藍圖範例「找到Downloads裡最新的PDF」需要「依修改時間排序、
    只回報最新一個」的能力，原本只會回傳一堆符合名稱的項目，不知道哪個最新——
    加上 extension（副檔名篩選）+ newest_only（只回傳修改時間最新的一個）之後才補上這個能力。
    """
    search_root = _resolve_under_home(search_dir) if search_dir else Path.home()
    if not search_root.exists():
        raise ValueError(f"搜尋目錄不存在：{search_root}")

    pattern = f"*{name}*" if name else "*"
    ext = ("." + extension.lstrip(".")).lower() if extension else None

    matches = []
    for p in search_root.rglob(pattern):
        if not p.is_file():
            continue
        if ext and p.suffix.lower() != ext:
            continue
        matches.append(p)

    if not matches:
        return f"在 {search_root} 底下找不到符合條件的檔案（name={name}, extension={extension}）"

    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    if newest_only:
        newest = matches[0]
        mtime = datetime.datetime.fromtimestamp(newest.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return f"最新的符合檔案是：{newest}（修改時間：{mtime}）"

    listed = matches[:20]
    return f"找到 {len(matches)} 個符合的項目（依修改時間新到舊排序）：\n" + "\n".join(str(p) for p in listed)


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
        "find": lambda: find_file(kwargs.get("name"), kwargs.get("search_dir"), kwargs.get("extension"), bool(kwargs.get("newest_only"))),
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


# ---- UIA 原語：對照 docs/01 藍圖第7節，讓LLM能操作「使用者自己開啟的任意應用程式」，
# 不再侵限於白名單裡的4個app。這是這次盤點報告(docs/07)抓到的最大缺口——之前完全沒有實作。
# 安全設計延續 close_app_by_pid 的教訓：只要牽涉「鎖定要操作哪一個視窗」，一律優先要求pid，
# 不接受單純的標題模糊比對；如果非用標題，一定要求唯一比對到剛好一個結果，模糊就直接拒絕。

def get_active_window() -> dict:
    import win32gui, win32process
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    return {"title": title, "pid": pid}


def list_windows() -> str:
    import win32gui, win32process
    results = []

    def _cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            results.append((win32gui.GetWindowText(hwnd), pid))
        return True

    win32gui.EnumWindows(_cb, None)
    if not results:
        return "目前沒有偵測到任何有標題的可見視窗"
    return "目前開著的視窗：\n" + "\n".join(f"- {t} (pid={p})" for t, p in results)


def focus_window(pid: int = None, title: str = None) -> str:
    import win32gui, win32process, win32con
    if pid is None and not title:
        raise ValueError("focus_window 需要 pid 或 title 其中一個")

    matches = []

    def _cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        t = win32gui.GetWindowText(hwnd)
        if not t:
            return True
        _, p = win32process.GetWindowThreadProcessId(hwnd)
        if pid is not None:
            if p == pid:
                matches.append((hwnd, t))
        elif title.lower() in t.lower():
            matches.append((hwnd, t))
        return True

    win32gui.EnumWindows(_cb, None)
    if not matches:
        raise ValueError(f"找不到符合的視窗（pid={pid}, title={title}）")
    if len(matches) > 1:
        names = "、".join(t for _, t in matches)
        raise ValueError(f"符合條件的視窗有 {len(matches)} 個（{names}），無法判斷要切到哪一個，請用 pid 精確指定")

    hwnd, window_title = matches[0]
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    _force_set_foreground(hwnd)

    if win32gui.GetForegroundWindow() != hwnd:
        raise RuntimeError(f"已嘗試切換到「{window_title}」，但Windows拒絕把它設為最前面視窗（焦點竊取保護），實際上沒有真的切過去")
    return f"已切換到視窗：{window_title}"


def _force_set_foreground(hwnd) -> None:
    """
    Windows 預設會擋掉「背景行程搶走最前面視窗焦點」（SetForegroundWindow直接呼叫在這種情況下
    會丟出 pywintypes.error，這是實測抓到的真實限制，不是猜的）。標準合法的繞過方式是先用
    AttachThreadInput 把呼叫端執行緒跟目標視窗的輸入狀態接起來，讓Windows把呼叫端也當作
    「使用者正在操作的那個」，SetForegroundWindow才會成功，結束後要記得解除綁定。
    """
    import win32gui, win32process, win32api
    import ctypes
    user32 = ctypes.windll.user32

    current_thread = win32api.GetCurrentThreadId()
    target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
    fg_hwnd = win32gui.GetForegroundWindow()
    fg_thread, _ = win32process.GetWindowThreadProcessId(fg_hwnd) if fg_hwnd else (0, 0)

    attached_fg = fg_thread and fg_thread != current_thread and user32.AttachThreadInput(current_thread, fg_thread, True)
    attached_target = target_thread and target_thread != current_thread and user32.AttachThreadInput(current_thread, target_thread, True)
    try:
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass  # 就算這裡還是失敗，外層會用 GetForegroundWindow() 的實際結果來判斷成功與否
    finally:
        if attached_fg:
            user32.AttachThreadInput(current_thread, fg_thread, False)
        if attached_target:
            user32.AttachThreadInput(current_thread, target_thread, False)


def _connect_uia_top_window(pid: int):
    """
    只能透過pid連接（不接受標題模糊比對）——跟 close_app_by_pid 的安全原則一致：
    呼叫方一定是傳 open_app 或 get_active_window/list_windows 取得的真實pid，
    不是靠標題字串在整台電腦裡亂猜要操作哪一個視窗。
    """
    from pywinauto import Application
    try:
        app = Application(backend="uia").connect(process=pid)
    except Exception as e:
        raise ValueError(f"無法連接到 pid={pid} 的視窗（可能已經關閉或不是這個pid）：{e}")
    return app.top_window()


_MAIN_TEXT_AREA_KEYWORDS = ("內容", "編輯區", "文字區", "document", "editor", "正文")


def _find_uia_control(top_window, name: str):
    """
    對照docs/07進度報告P3驗收劇本實測時發現的真實情況：像記事本的主要編輯區這種控制項，
    UIA的window_text()本身是空字串（不是沒有名稱可以顯示，是這個控制項本身就沒有文字標籤，
    跟按鈕不一樣）——如果直接照字面比對名稱，永遠找不到。加一個備援：如果呼叫方用這幾個
    常見的「主要內容區」關鍵字，且視窗裡剛好只有一個Document/Edit類型的控制項，就直接給那個，
    不需要使用者/LLM知道UIA內部把它叫做空字串這種實作細節。
    """
    all_ctrls = top_window.descendants()
    name_lower = name.strip().lower()
    if name_lower in _MAIN_TEXT_AREA_KEYWORDS:
        text_areas = [c for c in all_ctrls if c.element_info.control_type in ("Document", "Edit")]
        if len(text_areas) == 1:
            return text_areas[0]
        if len(text_areas) > 1:
            raise ValueError(f"這個視窗裡有 {len(text_areas)} 個文字編輯區，無法判斷要操作哪一個")

    candidates = [c for c in all_ctrls if name in (c.window_text() or "")]
    if not candidates:
        raise ValueError(f"在這個視窗裡找不到名稱包含「{name}」的控制項")
    if len(candidates) > 1:
        # 常見情況1：一個按鈕(Button)底下常常跟著一個顯示同樣文字的子元素(Static/Text)，
        # UIA會把兩個都列成「名稱包含這個字」的候選——這不是真的兩個不同東西可以選，
        # 只要其中剛好只有一個是可互動的類型(Button/MenuItem/ListItem/TabItem等)，
        # 就是使用者真正想操作的那個，不用因為這種UIA樹狀結構的細節就報錯要求更精確名稱。
        interactive = [c for c in candidates
                       if c.element_info.control_type in ("Button", "MenuItem", "ListItem", "TabItem", "CheckBox", "RadioButton")]
        if len(interactive) == 1:
            return interactive[0]
        # 常見情況2：像選單裡「儲存」跟「全部儲存」這種一個名稱是另一個的子字串，substring
        # 比對會誤抓到兩個完全不同的選項——如果剛好有「文字完全相等」的候選，那個才是使用者
        # 真正要的，不該被「文字比較長但也包含這個字」的其他選項卡到變成假的模糊不清。
        exact = [c for c in interactive if (c.window_text() or "").strip() == name.strip()]
        if len(exact) == 1:
            return exact[0]
        raise ValueError(f"名稱包含「{name}」的控制項有 {len(candidates)} 個，無法判斷要操作哪一個，請給更精確的名稱")
    return candidates[0]


def uia_click(pid: int, control_name: str) -> str:
    top = _connect_uia_top_window(pid)
    ctrl = _find_uia_control(top, control_name)
    ctrl.click_input()
    return f"已點擊控制項：{control_name}"


def uia_set_text(pid: int, control_name: str, text: str) -> str:
    """
    跟 text_input_op 的差別：這裡是真的用UIA找到指定的輸入欄位再設值，不是SendKeys盲打到
    目前作用中欄位——如果游標不在正確位置，SendKeys會打錯地方，這個工具不會有這個問題。

    實測踩坑記錄（P3驗收劇本用記事本測試時抓到，兩個真實bug）：
    1. pywinauto的`set_text()`不是每種UIA控制項都有——記事本的主編輯區被歸類成"Document"
       類型，pywinauto把它包成通用的UIAWrapper，沒有`set_text()`這個方法，直接呼叫會丟
       AttributeError。改成分層嘗試處理。
    2. **更關鍵的一個**：一開始改用UIA的ValuePattern直接設值（`iface_value.SetValue()`），
       這樣呼叫確實會把文字設進去、畫面上也看得到，但**這個控制項並沒有真的取得鍵盤輸入焦點**
       ——之後送出的`hotkey()`/`press_key()`（底層用`win32api.keybd_event`）完全沒有反應
       （測試過送Ctrl+S要存檔、送單一字元'a'，記事本內容跟存檔狀態都毫無變化）。實測換成
       pywinauto的`click_input()`（真的模擬滑鼠點擊）之後再操作，同一個視窗就正常回應了——
       證實问题是「視窗在最前面」跟「視窗裡的某個控制項真的有輸入焦點」是兩件不同的事，
       尤其對新版WinUI/XAML應用程式（新版記事本就是）更明顯。修法：一律先真的點擊一次
       目標控制項建立焦點，再決定要用哪種方式設值，之後的hotkey/press_key才會生效。
    """
    top = _connect_uia_top_window(pid)
    ctrl = _find_uia_control(top, control_name)
    ctrl.click_input()  # 先建立真正的輸入焦點，不只是讓視窗在最前面

    if hasattr(ctrl, "set_text"):
        ctrl.set_text(text)
        return f"已將「{control_name}」的內容設定為：{text[:30]}{'...' if len(text) > 30 else ''}"

    try:
        value_pattern = ctrl.iface_value
        value_pattern.SetValue(text)
        return f"已將「{control_name}」的內容設定為：{text[:30]}{'...' if len(text) > 30 else ''}"
    except Exception:
        pass

    escaped = "".join(f"{{{c}}}" if c in "+^%~(){}[]" else c for c in text)
    ctrl.type_keys(escaped, with_spaces=True)
    return f"已將「{control_name}」的內容設定為：{text[:30]}{'...' if len(text) > 30 else ''}（用模擬打字，因為這個控制項不支援直接設值)"


def uia_select(pid: int, control_name: str, item_name: str) -> str:
    top = _connect_uia_top_window(pid)
    ctrl = _find_uia_control(top, control_name)
    ctrl.select(item_name)
    return f"已在「{control_name}」選擇：{item_name}"


# ---- press_key / hotkey：通用鍵盤原語，藍圖第7節列出的最底層building block ----
# 安全設計：維護一個明確的黑名單，擋掉「等同繞過Policy Engine執行任意命令」或
# 「過度干擾且不可逆」的組合鍵（例如 Win+R 開執行對話框、Win+L 鎖定電腦），
# 其餘一般按鍵（存檔/復原/切換視窗等）才放行——這是唯一需要特別把關的鍵盤操作，
# 因為藍圖P3自己定義的驗收劇本（記事本存檔）就是靠 Ctrl+S 這個組合鍵完成的。

_BLOCKED_HOTKEYS = {
    frozenset({"win", "r"}): "會開啟「執行」對話框，等同繞過Policy Engine執行任意命令，安全設計禁止",
    frozenset({"win", "l"}): "會鎖定電腦畫面，過度干擾且需要密碼才能解鎖，不允許",
}


def _vk_map():
    import win32con
    m = {
        "enter": win32con.VK_RETURN, "esc": win32con.VK_ESCAPE, "escape": win32con.VK_ESCAPE,
        "tab": win32con.VK_TAB, "space": win32con.VK_SPACE, "backspace": win32con.VK_BACK,
        "delete": win32con.VK_DELETE, "up": win32con.VK_UP, "down": win32con.VK_DOWN,
        "left": win32con.VK_LEFT, "right": win32con.VK_RIGHT, "home": win32con.VK_HOME, "end": win32con.VK_END,
        "ctrl": win32con.VK_CONTROL, "alt": win32con.VK_MENU, "shift": win32con.VK_SHIFT, "win": win32con.VK_LWIN,
    }
    for i in range(1, 13):
        m[f"f{i}"] = getattr(win32con, f"VK_F{i}")
    for c in "abcdefghijklmnopqrstuvwxyz0123456789":
        m[c] = ord(c.upper())
    return m


def _parse_key_combo(keys: str):
    parts = [p.strip().lower() for p in keys.replace("+", " ").split() if p.strip()]
    if not parts:
        raise ValueError("沒有指定要按的按鍵")
    combo = frozenset(parts)
    if combo in _BLOCKED_HOTKEYS:
        raise ValueError(f"不允許送出這個組合鍵（{keys}）：{_BLOCKED_HOTKEYS[combo]}")
    vk_map = _vk_map()
    vks = []
    for p in parts:
        if p not in vk_map:
            raise ValueError(f"不認識的按鍵：{p}")
        vks.append(vk_map[p])
    return vks


# 實測踩坑記錄（P3驗收劇本用記事本測試時抓到的關鍵bug）：press_key/hotkey原本用
# win32api.keybd_event()（舊式、低階的鍵盤事件模擬API）送鍵，這對小畫家這種傳統Win32
# 應用程式沒問題（補UIA原語那批已經測過Ctrl+Z/Escape都正確送達），但對新版記事本這種
# WinUI/XAML應用程式完全沒有反應——連最簡單的單一字元'a'都送不進去、Ctrl+S/Ctrl+N這種
# 視窗層級的快捷鍵也毫無反應，即使當時視窗確實在最前面。改用SendInput（Windows官方建議
# 取代keybd_event的現代API，pywinauto的type_keys()底層也是用這個）之後，同一個記事本
# 視窗才正常回應。這代表keybd_event這個底層機制沒辦法穩定送達所有應用程式，SendInput是
# 更可靠、更廣泛相容的做法。

_PUL = ctypes.POINTER(ctypes.c_ulong)


class _KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", _PUL)]


class _InputUnion(ctypes.Union):
    _fields_ = [("ki", _KeyBdInput)]


class _Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", _InputUnion)]


def _send_input_key(vk: int, key_up: bool = False):
    extra = ctypes.c_ulong(0)
    ii = _InputUnion()
    ii.ki = _KeyBdInput(vk, 0, 0x0002 if key_up else 0, 0, ctypes.pointer(extra))
    inp = _Input(1, ii)  # type=1 是 INPUT_KEYBOARD
    ctypes.windll.user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))


def press_key(key: str) -> str:
    vks = _parse_key_combo(key)
    if len(vks) != 1:
        raise ValueError("press_key 只能按單一按鍵，組合鍵請用 hotkey")
    _send_input_key(vks[0])
    _send_input_key(vks[0], key_up=True)
    return f"已按下：{key}"


def hotkey(keys: str) -> str:
    vks = _parse_key_combo(keys)
    for vk in vks:
        _send_input_key(vk)
    for vk in reversed(vks):
        _send_input_key(vk, key_up=True)
    return f"已送出組合鍵：{keys}"


# ---- speech_to_text_op：把一份已經存在的錄音檔轉成文字（對照35工具表，唯讀L0）----
# 跟 listen_loop.py 的 run_asr() 是兩件事：run_asr() 處理的是「即時麥克風錄到的一段話」，
# 這裡處理的是「使用者指定一個已經存在的.wav檔案」，兩者共用同一顆whisper.cpp medium模型，
# 但輸入來源不同，所以獨立成一個工具而不是直接重用 run_asr()（它的參數是numpy陣列不是檔案路徑）。
# 安全設計：這裡刻意用_require_safe_path（限使用者家目錄），不是open_file那種較寬鬆的
# _resolve_under_home——open_file只是請Windows用預設程式打開，這裡會把檔案內容（轉成文字）
# 回傳到LLM/對話紀錄裡，等於「讀取檔案內容」而不只是「顯示」，風險層級比open_file更接近
# file_op的move/copy，所以套用一樣的家目錄邊界。

def speech_to_text(audio_path: str) -> str:
    import subprocess, os
    p = _require_safe_path(audio_path, "speech_to_text_op")
    if not p.exists():
        raise ValueError(f"找不到錄音檔：{p}")
    if p.suffix.lower() != ".wav":
        raise ValueError("目前只支援.wav格式的錄音檔（whisper.cpp原生支援的格式）")

    repo_root = Path(__file__).resolve().parents[2]
    whisper_cli = repo_root / "progress/p0/build/whisper.cpp/build/bin/whisper-cli.exe"
    whisper_model = repo_root / "progress/p0/build/whisper.cpp/models/ggml-medium.bin"
    if not whisper_cli.exists():
        raise RuntimeError(f"找不到whisper.cpp執行檔：{whisper_cli}（P0驗證用的build是否還在？）")

    env = os.environ.copy()
    env["PATH"] = r"C:\Program Files\LLVM\bin;" + env.get("PATH", "")
    result = subprocess.run(
        [str(whisper_cli), "-m", str(whisper_model), "-f", str(p), "-l", "zh", "-nt"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore", env=env,
        cwd=str(whisper_cli.parent.parent),
    )
    text = result.stdout.strip()
    if not text:
        raise RuntimeError(f"whisper.cpp沒有輸出任何文字（可能是空白錄音，或參數/模型有問題）")
    return text


# ---- record_screen：用Windows內建Xbox Game Bar切換螢幕錄影（對照35工具表）----
# 設計：Win+Alt+R是Xbox Game Bar內建的「開始/停止錄影」切換鍵，同一個鍵兩個動作都送，
# 沒有辦法從我們這端單獨區分「現在是開始還是停止」——這是Windows本身的設計，Game Bar
# 才知道目前是不是正在錄，我們只是送出使用者自己按這個鍵也會發生的同一個標準快捷鍵。
#
# 誠實記錄：實測時發現這台機器（這個工作環境）送出Win+Alt+R之後，Videos\Captures資料夾
# 沒有產生任何檔案、也沒有偵測到Xbox Game Bar相關行程啟動。docs/07第11次更新已重新查證：
# 這跟記事本/小算盤先前的PATH解析問題（已修正）是不同根因——Game Bar背景服務本身沒有
# 啟動（GameDVR_Enabled=1但無對應行程），屬於獨立、尚未解決的環境限制，不是這個工具實作
# 本身的bug（hotkey()機制已經用小畫家驗證過真的能正確送出組合鍵）。

def record_screen(action: str) -> str:
    if action not in ("start", "stop"):
        raise ValueError(f"record_screen 不支援的 action：{action}（只接受 start/stop）")
    hotkey("win+alt+r")
    verb = "開始" if action == "start" else "停止"
    return f"已送出螢幕錄影切換快捷鍵（Win+Alt+R），如果Xbox Game Bar正常回應，錄影應該已經{verb}"


# ---- task_scheduler_op：Windows工作排程器（docs/08§5點名的「風險可控」候選工具之一）----
# 先前判斷這16個未實作工具「需要外部服務整合」而排除，重新檢視發現這個判斷是錯的：
# 工作排程器是Windows內建功能，schtasks.exe是系統既有二進位檔，不需要任何外部服務或網路連線，
# 完全符合專案的100%離線原則。用固定二進位檔+受控參數呼叫subprocess，跟power_action()呼叫
# shutdown.exe是同一種模式，不是CLAUDE.md禁止的「execute_any_shell_command萬用工具」。

def task_scheduler_op(action: str, name: str = None, command: str = None,
                       schedule: str = None, time: str = None) -> str:
    import subprocess
    if action == "list":
        result = subprocess.run(["schtasks", "/query", "/fo", "CSV", "/nh"],
                                 capture_output=True, text=True, encoding="utf-8", errors="ignore")
        names = []
        for line in result.stdout.splitlines():
            parts = line.split('","')
            if not parts:
                continue
            task_name = parts[0].strip('"')
            if task_name and not task_name.startswith("\\Microsoft\\"):
                names.append(task_name)
        if not names:
            return "目前沒有非系統內建的排程工作"
        return "目前的排程工作：" + "、".join(names[:30]) + (f"（共{len(names)}項，只列前30）" if len(names) > 30 else "")
    if action == "create":
        if not name or not command:
            raise ValueError("task_scheduler_op 的 create 動作需要 name 跟 command")
        sc = (schedule or "ONCE").upper()
        args = ["schtasks", "/create", "/tn", name, "/tr", command, "/sc", sc, "/f"]
        if time:
            args += ["/st", time]
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if result.returncode != 0:
            raise RuntimeError(f"建立排程工作失敗：{result.stderr.strip() or result.stdout.strip()}")
        return f"已建立排程工作「{name}」（{sc}{'，' + time if time else ''}）：{command}"
    if action == "delete":
        if not name:
            raise ValueError("task_scheduler_op 的 delete 動作需要 name")
        result = subprocess.run(["schtasks", "/delete", "/tn", name, "/f"],
                                 capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if result.returncode != 0:
            raise RuntimeError(f"刪除排程工作失敗：{result.stderr.strip() or result.stdout.strip()}")
        return f"已刪除排程工作「{name}」"
    raise ValueError(f"task_scheduler_op 不支援的 action：{action}（只接受 list/create/delete）")


# ---- startup_program_op：開機自動啟動項目（docs/08§5點名的另一個「風險可控」候選）----
# 用使用者自己的「啟動」資料夾（shell:startup，%APPDATA%\...\Startup）放捷徑檔，不碰登錄檔的
# Run機碼——原因：使用者自己的啟動資料夾只影響「這個使用者帳號」，登錄檔Run機碼(尤其是
# HKLM底下的)會影響所有使用者、且更難被使用者自己用檔案總管直接看到/清掉，前者對這個專案
# 「操作要容易復原、使用者要能理解系統做了什麼」的原則更友善。

def _startup_folder() -> Path:
    import os
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def startup_program_op(action: str, name: str = None, path: str = None) -> str:
    folder = _startup_folder()
    if action == "list":
        items = [p.stem for p in folder.glob("*.lnk")]
        if not items:
            return "目前「啟動」資料夾裡沒有任何項目"
        return "開機自動啟動項目：" + "、".join(items)
    if action == "add":
        if not name or not path:
            raise ValueError("startup_program_op 的 add 動作需要 name 跟 path")
        target = _resolve_under_home(path) if not Path(path).is_absolute() else Path(path)
        if not target.exists():
            raise ValueError(f"找不到要加入啟動項的程式：{target}")
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(folder / f"{name}.lnk"))
        shortcut.TargetPath = str(target)
        shortcut.WorkingDirectory = str(target.parent)
        shortcut.save()
        return f"已把「{name}」（{target}）加入開機自動啟動"
    if action == "remove":
        if not name:
            raise ValueError("startup_program_op 的 remove 動作需要 name")
        lnk = folder / f"{name}.lnk"
        if not lnk.exists():
            raise ValueError(f"「啟動」資料夾裡沒有叫「{name}」的項目")
        lnk.unlink()
        return f"已把「{name}」從開機自動啟動移除"
    raise ValueError(f"startup_program_op 不支援的 action：{action}（只接受 list/add/remove）")


# ---- driver_op：驅動程式查詢（唯讀）----
# 只實作「查詢」，不實作「更新」——更新驅動程式風險高（可能造成硬體無法使用，且不像其他
# L3操作那樣容易復原），config/permissions.yaml把update動作單獨拉高到L3_DANGEROUS，
# 但目前連update本身都還沒實作，純粹是為未來預留、避免之後真的加上去時忘記標risk level。

# Windows的驅動程式裝置名稱一律是英文（跟系統語系無關），但使用者講中文問「查一下顯示卡
# 驅動」時，LLM填的keyword參數也會是中文（實測kpi_result_v2_new_tools.json抓到的真實案例：
# keyword="顯示卡"，逐字比對"Microsoft Basic Display Driver"當然對不上，回報「找不到」——
# 但顯示卡驅動明明就在清單裡，是關鍵字語言對不上，不是真的沒有）。這裡加一份常見硬體類別的
# 中英對照，比對時中文關鍵字會額外用對應的英文詞再試一次，不需要使用者自己講英文才查得到。
_DRIVER_KEYWORD_SYNONYMS = {
    "顯示卡": ["display", "graphics", "video"], "顯卡": ["display", "graphics", "video"],
    "網卡": ["network", "ethernet", "wifi", "wireless"], "網路卡": ["network", "ethernet", "wifi", "wireless"],
    "音效卡": ["audio", "sound"], "音效": ["audio", "sound"], "喇叭": ["audio", "sound"],
    "藍芽": ["bluetooth"], "藍牙": ["bluetooth"],
    "觸控": ["touch"], "觸控板": ["touch", "trackpad", "touchpad"],
    "滑鼠": ["mouse"], "鍵盤": ["keyboard"],
    "印表機": ["printer"], "掃描器": ["scanner"], "讀卡機": ["card reader"],
    "攝影機": ["camera", "webcam"], "相機": ["camera", "webcam"],
}


def driver_op(action: str = "list", keyword: str = None) -> str:
    if action != "list":
        raise ValueError(f"driver_op 目前只實作 action=list（查詢，唯讀）；不提供 update，更新驅動風險太高，這個專案不自動做")
    import win32com.client
    keywords = [keyword] if keyword else []
    if keyword:
        keywords += _DRIVER_KEYWORD_SYNONYMS.get(keyword.strip(), [])
    wmi = win32com.client.GetObject("winmgmts:")
    drivers = wmi.ExecQuery("SELECT DeviceName, DriverVersion, Manufacturer FROM Win32_PnPSignedDriver")
    rows = []
    for d in drivers:
        device_name = d.DeviceName or ""
        if not device_name:
            continue
        if keywords and not any(kw.lower() in device_name.lower() for kw in keywords):
            continue
        rows.append(f"{device_name}（{d.Manufacturer or '未知廠商'}，版本{d.DriverVersion or '未知'}）")
    if not rows:
        return f"找不到符合「{keyword}」的驅動程式" if keyword else "沒有查到任何驅動程式資訊"
    rows = sorted(set(rows))
    return "、".join(rows[:20]) + (f"（共{len(rows)}項，只列前20）" if len(rows) > 20 else "")


# ---- photo_edit：本機圖片基本編輯（旋轉/縮放/裁切/灰階/翻轉）----
# 用PIL（既有依賴，screenshot功能已經在用），只處理使用者家目錄底下的圖片檔（比照file_op的
# 路徑安全限制）。輸出一律存成新檔案（原檔名+_edited），不覆寫原圖——即使權限表把這個工具設成
# L1_ROUTINE（容易復原），"容易復原"的前提也是「原圖還在」，不是真的去復原一個已覆寫的檔案。

def photo_edit(path: str, action: str, **kwargs) -> str:
    from PIL import Image
    p = _require_safe_path(path, "photo_edit")
    if not p.exists():
        raise ValueError(f"找不到圖片：{p}")
    img = Image.open(p)
    if action == "rotate":
        degrees = kwargs.get("degrees")
        if degrees is None:
            raise ValueError("photo_edit 的 rotate 動作需要 degrees")
        img = img.rotate(-float(degrees), expand=True)
    elif action == "resize":
        width, height = kwargs.get("width"), kwargs.get("height")
        if not width or not height:
            raise ValueError("photo_edit 的 resize 動作需要 width 跟 height")
        img = img.resize((int(width), int(height)))
    elif action == "crop":
        box = kwargs.get("box")
        if not box or len(box) != 4:
            raise ValueError("photo_edit 的 crop 動作需要 box=[left, top, right, bottom]")
        img = img.crop(tuple(int(v) for v in box))
    elif action == "grayscale":
        img = img.convert("L")
    elif action == "flip_horizontal":
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    elif action == "flip_vertical":
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    else:
        raise ValueError(f"photo_edit 不支援的 action：{action}（只接受 rotate/resize/crop/grayscale/flip_horizontal/flip_vertical）")
    out_path = p.with_stem(p.stem + "_edited")
    img.save(out_path)
    return f"已完成編輯，另存為 {out_path}"


# ---- git_op：本機git版本控制操作（重新檢視docs/08原本排除的12個工具後，發現這個判斷是錯的）----
# 先前排除理由是「push/merge可能造成程式碼遺失」，但那只是git_op眾多動作裡風險最高的兩個，
# `config/permissions.yaml`裡其實早就把push/merge個別標成L3、其餘動作留在L2——這張表
# 在更早的階段就已經預留好分級，只是一直沒有真的把函式實作出來。status/log/diff是純查詢，
# add/commit只影響本機repo（本身可用git revert/reset復原），都不需要碰網路，完全符合離線原則。
# push/merge需要遠端連線+可能造成真正的程式碼遺失，這裡刻意不實作（保持風險最高的部分留白），
# 跟driver_op的update、record_screen以外的部分是同一種「先做安全的部分，危險的部分先不做」原則。

def _resolve_git_repo(repo_path: str):
    repo = _resolve_under_home(repo_path) if repo_path else None
    if repo is None or not repo.exists():
        raise ValueError(f"git_op 需要一個真實存在的repo_path：{repo_path}")
    if not (repo / ".git").exists():
        raise ValueError(f"{repo} 不是一個git repo（找不到.git目錄）")
    return repo


def git_op(action: str, repo_path: str = None, message: str = None, path: str = None) -> str:
    import subprocess
    repo = _resolve_git_repo(repo_path)
    handlers = {
        "status": lambda: ["git", "-C", str(repo), "status", "--short", "--branch"],
        "log": lambda: ["git", "-C", str(repo), "log", "--oneline", "-n", "10"],
        "diff": lambda: ["git", "-C", str(repo), "diff", "--stat"],
        "add": lambda: ["git", "-C", str(repo), "add", path or "."],
        "commit": lambda: (
            ["git", "-C", str(repo), "commit", "-m", message]
            if message else (_ for _ in ()).throw(ValueError("git_op 的 commit 動作需要 message"))
        ),
    }
    if action not in handlers:
        raise ValueError(f"git_op 不支援的 action：{action}（只接受 status/log/diff/add/commit；push/merge風險太高，這個專案不自動做）")
    result = subprocess.run(handlers[action](), capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if result.returncode != 0:
        raise RuntimeError(f"git {action} 失敗：{result.stderr.strip() or result.stdout.strip()}")
    output = result.stdout.strip()
    if action == "status":
        return output if output else "工作目錄是乾淨的，沒有未commit的變更"
    if action == "log":
        return output if output else "這個repo還沒有任何commit"
    if action == "diff":
        return output if output else "沒有偵測到差異（stat為空）"
    if action == "add":
        return f"已加入待commit清單：{path or '.'}"
    return f"已commit：{output}"


# ---- print_or_scan：本機列印（只實作print，不實作scan）----
# scan需要這台機器實際接掃描器硬體才能驗證，跟record_screen（Xbox Game Bar）同一類「沒有
# 硬體/背景服務可以驗證，不該空口宣稱做到」的情況，這裡不實作、誠實留白。print不需要——
# Windows標準的「列印」右鍵動作（ShellExecute的print verb）送到系統設定的預設印表機，
# 沒有印表機時系統本身就會用標準對話框告知「找不到印表機」，不需要我們自己額外處理這個狀況。

def print_or_scan(action: str, path: str = None) -> str:
    if action != "print":
        raise ValueError(f"print_or_scan 目前只實作 action=print；scan需要真實掃描器硬體才能驗證，這個環境沒有可測，暫不實作")
    import os
    p = _require_safe_path(path, "print_or_scan")
    if not p.exists():
        raise ValueError(f"找不到要列印的檔案：{p}")
    os.startfile(str(p), "print")
    return f"已送出列印：{p}（送到系統目前設定的預設印表機）"
