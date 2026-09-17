# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from executor.executor import Executor
from executor import audit_db
from tools import basic_tools

audit_db.sync_policy_rules()
ex = Executor()

out = []

# 先讀現狀，測完要還原
original_volume = basic_tools.get_volume()
out.append(f"目前音量: {original_volume}%")

try:
    import pyperclip
    original_clipboard = pyperclip.paste()
except Exception as e:
    original_clipboard = None
out.append(f"目前剪貼簿(前30字): {(original_clipboard or '')[:30]!r}")

# 測試：調小音量 5%
r1 = ex.run("set_volume", {"delta": -5})
out.append(f"set_volume delta=-5 -> {r1}")

# 還原音量
r2 = ex.run("set_volume", {"level": original_volume})
out.append(f"還原音量 -> {r2}")
after_restore = basic_tools.get_volume()
out.append(f"還原後實際音量: {after_restore}% (應該等於原本的 {original_volume}%)")

# 測試剪貼簿複製/貼上
r3 = ex.run("clipboard_op", {"action": "copy", "text": "P3測試字串-不影響原本內容"})
out.append(f"clipboard copy -> {r3}")
r4 = ex.run("clipboard_op", {"action": "paste"})
out.append(f"clipboard paste -> {r4}")

# 還原剪貼簿
if original_clipboard is not None:
    ex.run("clipboard_op", {"action": "copy", "text": original_clipboard})
    out.append("已還原原本的剪貼簿內容")

with open(Path(__file__).parent / "test_p3_v2_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("done")
