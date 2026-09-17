# -*- coding: utf-8 -*-
"""
ORDER.md 產生器：把 Front Desk 對話收斂完的結構化需求，寫成 AERIS 看得懂的格式。
格式對照 AERIS_100_Acoustic_Engineers_Conversation_Record...md 第29.2節。

這個模組只負責「寫檔案」，不負責對話邏輯（對話狀態機在 frontdesk_dialog.py，之後補）。
跟 AERIS 之間唯一的整合點就是這個檔案格式 + 交接資料夾，沒有任何程式碼共用。
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

HANDOFF_DIR = Path("C:/0_JN1_AERIS_HANDOFF/orders")


@dataclass
class OrderDraft:
    case_id: str
    input_mode: str  # "voice" | "text"
    language: str = "zh-TW"
    product: str = ""
    project_phase: str = ""
    priority: str = "normal"
    user_goal: str = ""
    problem_type: str = ""
    known_symptoms: list = field(default_factory=list)
    available_evidence: list = field(default_factory=list)
    missing_evidence: list = field(default_factory=list)
    constraints: list = field(default_factory=list)
    selected_pod: list = field(default_factory=list)  # [(id, role), ...]
    required_work: list = field(default_factory=list)
    acceptance_criteria: list = field(default_factory=list)


def new_case_id() -> str:
    return f"AERIS-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"


def _bullets(items: list) -> str:
    if not items:
        return "- （無）"
    return "\n".join(f"- {i}" for i in items)


def render_order_md(order: OrderDraft) -> str:
    pod_lines = "\n".join(f"- {role}: #{oid}" if role else f"- #{oid}" for oid, role in order.selected_pod) or "- （尚未指派）"
    return f"""---
case_id: {order.case_id}
created_at: {datetime.now(timezone.utc).isoformat()}
input_mode: {order.input_mode}
language: {order.language}
product: {order.product or 'unspecified'}
project_phase: {order.project_phase or 'unspecified'}
priority: {order.priority}
status: draft
---

# User Goal
{order.user_goal or '(待補)'}

# Problem Type
{order.problem_type or '(待補)'}

# Known Symptoms
{_bullets(order.known_symptoms)}

# Available Evidence
{_bullets(order.available_evidence)}

# Missing Evidence
{_bullets(order.missing_evidence)}

# Constraints
{_bullets(order.constraints)}

# Selected Capability Pod
{pod_lines}

# Required Work
{_bullets(order.required_work)}

# Backend Required Deliverables
- Results.xlsx
- Report.pptx

# Acceptance Criteria
{_bullets(order.acceptance_criteria) if order.acceptance_criteria else "- 所有結論需有 evidence\n- 不得把 hypothesis 當 confirmed fact\n- 每個 root cause 需提供 confidence\n- 至少提供一個可執行驗證實驗"}
"""


def write_order(order: OrderDraft, handoff_dir: Path = None) -> Path:
    """寫入交接資料夾。這是本專案跟 AERIS 唯一的接觸點。"""
    target_dir = handoff_dir or HANDOFF_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^A-Za-z0-9\-]", "_", order.case_id)
    path = target_dir / f"{safe_id}_ORDER.md"
    path.write_text(render_order_md(order), encoding="utf-8")
    return path
