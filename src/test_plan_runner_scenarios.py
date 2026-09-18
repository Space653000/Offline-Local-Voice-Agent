# -*- coding: utf-8 -*-
"""
docs/07/docs/08 誠實記錄過的缺口：P6多步驟規劃（PlanRunner）先前只驗證過一種場景
（找檔案→開啟→回報），且是用手動腳本測的，沒有留下可以重跑的迴歸測試檔案。
這裡補齊成正式、可重複執行的迴歸測試，覆蓋4種不同場景，全部走真實LLM(127.0.0.1:8811)
跟真實Executor（真的建/找/開檔案），不是mock。
"""
import sys, time, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from full_pipeline import PlanRunner
from executor.executor import Executor
from executor import audit_db

audit_db.sync_policy_rules()
ex = Executor()

test_root = Path.home() / "_va_test_plan_scenarios"
if test_root.exists():
    shutil.rmtree(test_root)
test_root.mkdir()

try:
    print("=== 場景1：找檔案→開啟→回報檔名（既有已驗證過的場景，補成正式迴歸測試）===")
    target = test_root / "latest_report.txt"
    target.write_text("hello from scenario 1", encoding="utf-8")
    runner = PlanRunner(f"找到{test_root}裡最新的txt檔案，打開它，然後告訴我檔名", ex)
    result = runner.run()
    print(result["status"], "| steps:", len(result.get("history", [])))
    assert result["status"] == "plan_done"
    assert any(h["tool"] == "file_op" and h["args"].get("action") == "find" for h in result["history"])
    assert any(h["tool"] == "file_op" and h["args"].get("action") == "open" for h in result["history"])
    print("通過\n")

    print("=== 場景2：步驟失敗的復原能力（叫它找一個根本不存在的檔案再開啟它）===")
    runner2 = PlanRunner(f"找到{test_root}裡叫做definitely_does_not_exist_xyz.txt的檔案，打開它，告訴我結果", ex)
    result2 = runner2.run()
    print(result2["status"], "| steps:", len(result2.get("history", [])))
    # 誠實驗證重點：find_file對「查詢本身成功執行、但零筆符合」回報executed=True+人類可讀的
    # 「找不到」訊息（這是設計上合理的行為——查詢動作本身沒有失敗，零結果是合法答案，不是例外）。
    # 真正該驗證的是：規劃者(LLM)看到這句「找不到」的訊息後，不能因為executed=True就誤判成
    # 「已經找到了」，硬著頭皮拿一個瞎猜的路徑去呼叫open——這才是P6文件裡強調的真實風險。
    first_step = result2["history"][0]
    assert first_step["tool"] == "file_op" and first_step["args"].get("action") == "find"
    assert "找不到" in str(first_step["result"].get("result", "")), "find的回應訊息沒有清楚表達零結果"
    open_calls = [h for h in result2["history"] if h["tool"] == "file_op" and h["args"].get("action") == "open"]
    assert len(open_calls) == 0, "find已經誠實回報找不到，規劃者卻還是硬著頭皮呼叫open，這是瞎猜參數的bug"
    print("通過（find回報找不到之後，規劃者正確停手，沒有硬猜路徑去open）\n")

    print("=== 場景3：單步驟指令不應該進入多輪迴圈（維持原本的低延遲）===")
    t0 = time.time()
    runner3 = PlanRunner("現在幾點", ex)
    result3 = runner3.run()
    elapsed = time.time() - t0
    print(result3["status"], "| steps:", len(result3["history"]), "| elapsed:", f"{elapsed:.2f}s")
    assert result3["status"] == "plan_done"
    assert len(result3["history"]) == 1, "單步驟指令被誤判成需要追問下一步，多跑了不必要的LLM呼叫"
    print("通過\n")

    print("=== 場景4：多步驟規劃中途撞到L2確認（建資料夾是敏感操作），確認後應該能正確接續===")
    folder_name = "va_plan_scenario_subfolder"
    runner4 = PlanRunner(f"在{test_root}底下建立一個叫{folder_name}的資料夾，然後打開它", ex)
    result4 = runner4.run()
    print("第一次呼叫狀態:", result4["status"])
    assert result4["status"] == "plan_needs_confirmation"
    assert result4["call"]["tool"] == "file_op" and result4["call"]["args"].get("action") == "create_folder"
    result4b = runner4.resume(approved=True)
    print("確認後狀態:", result4b["status"], "| steps:", len(result4b["history"]))
    assert result4b["status"] == "plan_done"
    created = test_root / folder_name
    assert created.is_dir(), "PlanRunner回報執行成功，但資料夾實際上沒有被建立出來"
    open_after_confirm = [h for h in result4b["history"] if h["tool"] == "file_op" and h["args"].get("action") == "open"]
    assert len(open_after_confirm) >= 1, "確認建資料夾之後，規劃者沒有接著執行「打開它」這個後續動作"
    print("通過（確認後正確接續執行後續步驟，資料夾真的存在磁碟上）\n")

    print("全部4種P6場景測試通過。")
finally:
    if test_root.exists():
        shutil.rmtree(test_root)
