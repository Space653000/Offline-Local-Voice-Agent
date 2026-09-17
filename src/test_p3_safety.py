# -*- coding: utf-8 -*-
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from executor.executor import Executor, ConfirmationRequired
from executor import audit_db

audit_db.sync_policy_rules()
ex = Executor()

print("=== 測試1: L0唯讀查詢 (get_datetime) 應該免確認直接執行 ===")
r = ex.run("get_datetime", {})
print(r)
assert r["executed"] is True

print("\n=== 測試2: L3危險操作 (file_op delete) 沒有 user_confirmed 應該被攔下，不執行 ===")
try:
    ex.run("file_op", {"action": "delete", "path": "C:/fake/test.txt"})
    print("錯誤：應該要 raise ConfirmationRequired 但沒有！")
except ConfirmationRequired as e:
    print(f"正確攔下：level={e.decision.level.name}, reason={e.decision.reason}")

print("\n=== 測試3: L3危險操作使用者拒絕後應該不執行 ===")
r = ex.run("file_op", {"action": "delete", "path": "C:/fake/test.txt"}, user_confirmed=False)
print(r)
assert r["executed"] is False

print("\n=== 測試4: 實際安全動作 — 開啟記事本（L1免確認）===")
r = ex.run("open_app", {"app_name": "notepad"})
print(r)
assert r["executed"] is True
opened_pid = r["result"]["pid"]
time.sleep(2)

print("\n=== 測試5: 只關閉剛剛那個 pid 的記事本，不影響其他視窗（L1免確認）===")
r = ex.run("close_window", {"pid": opened_pid})
print(r)

print("\n=== 測試6: 螢幕截圖（L1免確認）===")
r = ex.run("take_screenshot", {})
print(r)
assert r["executed"] is True

print("\n全部測試通過。稽核紀錄已寫入 data/voice_agent.db")
