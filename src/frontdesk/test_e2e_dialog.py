# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from dialog_state_machine import FrontDeskDialog

out = []

dlg = FrontDeskDialog()

r1 = dlg.capture("我的筆電喇叭低頻突然變差，聲音悶悶的", input_mode="voice")
out.append(("S1->S2 DIVERGE", r1))

r2 = dlg.converge(chosen_directions=[r1["options"][0]], known_symptoms=["180-500Hz SPL明顯下降"])
out.append(("S3->S4 EVIDENCE", r2))

r3 = dlg.evidence(available=["FR", "THD", "Impedance"], missing=["Klippel"], constraints=["不修改driver"])
out.append(("S4->S5/S6 PREVIEW", r3))

r4 = dlg.confirm(approved=True, handoff_dir=Path(__file__).parent / "test_output")
out.append(("S7->S8 ORDER_LOCKED", r4))

with open(Path(__file__).parent / "e2e_dialog_result.txt", "w", encoding="utf-8") as f:
    for label, r in out:
        f.write(f"=== {label} ===\n{json.dumps(r, ensure_ascii=False, indent=2)}\n\n")

print("done")
