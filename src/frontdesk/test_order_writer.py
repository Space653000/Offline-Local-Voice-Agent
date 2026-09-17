# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from order_writer import OrderDraft, new_case_id, write_order

order = OrderDraft(
    case_id=new_case_id(),
    input_mode="voice",
    product="notebook",
    project_phase="DVT",
    user_goal="找出 NB Speaker 180–500 Hz SPL 比 Golden 低 4 dB 的主要原因",
    problem_type="Golden vs NG / Low-frequency SPL degradation",
    known_symptoms=["180–500 Hz: -4 dB", "THD 增加", "左右聲道皆有"],
    available_evidence=["FR.csv", "THD.csv", "IMP.csv", "enclosure.step", "Golden sample data"],
    missing_evidence=["Klippel nonlinear data", "Air leak pressure test"],
    constraints=["不修改 driver", "優先機構解法", "DVT 時程 3 天內"],
    selected_pod=[
        ("041", "Lead"), ("018", "Micro Speaker Engineer"), ("021", "Enclosure Engineer"),
        ("023", "Leakage Engineer"), ("057", "Impedance Measurement Engineer"),
        ("086", "Acoustic Failure Analysis Engineer"), ("003", "Reviewer"), ("100", "Final"),
    ],
    required_work=[
        "Golden/NG FR 比較", "IMP 特徵分析", "Leakage / enclosure / driver root-cause ranking",
        "提出最少實驗數的驗證方案", "產生量化結果與風險",
    ],
)

test_out_dir = Path(__file__).parent / "test_output"
path = write_order(order, handoff_dir=test_out_dir)
print(f"Wrote: {path}")
print("---content---")
print(path.read_text(encoding="utf-8"))
