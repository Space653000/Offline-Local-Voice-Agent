# -*- coding: utf-8 -*-
"""
真正的端到端測試：ASR 轉錄出來的文字（不是手打）-> 模式分流 -> Front Desk 對話 -> ORDER.md
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from mode_classifier import classify
from dialog_state_machine import FrontDeskDialog

# 這句就是剛才 whisper.cpp GPU medium 模型真實轉錄出來的文字
asr_text = "我的筆記型電腦喇叭低頻聲音好像突然變差了聽起來悶悶的"

out = []

mode_result = classify(asr_text)
out.append(("MODE_CLASSIFY", mode_result))
assert mode_result["mode"] == "acoustic_engineering", f"分流錯誤：{mode_result}"

dlg = FrontDeskDialog()
r1 = dlg.capture(asr_text, input_mode="voice")
out.append(("S1->S2 DIVERGE", r1))

r2 = dlg.converge(chosen_directions=[r1["options"][0]], known_symptoms=["使用者描述為突然低頻變差、聲音悶"])
out.append(("S3->S4 EVIDENCE", r2))

r3 = dlg.evidence(available=["FR", "Impedance"], missing=["THD", "Klippel"], constraints=[])
out.append(("S4->S5/S6 PREVIEW", r3))

r4 = dlg.confirm(approved=True, handoff_dir=Path("C:/0_JN1_AERIS_HANDOFF/orders"))
out.append(("S7->S8 ORDER_LOCKED (寫進正式交接資料夾)", r4))

with open(Path(__file__).parent / "e2e_voice_result.txt", "w", encoding="utf-8") as f:
    f.write(f"ASR輸入文字: {asr_text}\n\n")
    for label, r in out:
        f.write(f"=== {label} ===\n{json.dumps(r, ensure_ascii=False, indent=2)}\n\n")

print("done:", r4["path"])
