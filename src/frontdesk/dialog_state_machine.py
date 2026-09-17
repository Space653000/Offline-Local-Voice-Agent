# -*- coding: utf-8 -*-
"""
Front Desk 對話狀態機（對照 AERIS 文件第42節 S0-S9）。
S0 CAPTURE -> S1 INTENT -> S2 DIVERGE -> S3 CONVERGE -> S4 EVIDENCE ->
S5 ROUTE -> S6 PREVIEW -> S7 CONFIRM -> S8 ORDER_LOCKED

設計原則：問題要精簡（文件原話：「用最少但必要的問題」），LLM 只負責生成問題選項，
不負責下工程結論——結論永遠是 AERIS 後台的事。
"""
import sys, json, requests
from enum import Enum, auto
from pathlib import Path
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent))
from order_writer import OrderDraft, new_case_id, write_order
from engineers_directory import ENGINEERS, ENGINEER_CAPABILITY

URL = "http://127.0.0.1:8811/v1/chat/completions"


class State(Enum):
    CAPTURE = auto()
    INTENT = auto()
    DIVERGE = auto()
    CONVERGE = auto()
    EVIDENCE = auto()
    ROUTE = auto()
    PREVIEW = auto()
    CONFIRM = auto()
    ORDER_LOCKED = auto()


def _llm_json(system_prompt: str, user_content: str, schema: dict, max_tokens=300) -> dict:
    body = {
        "model": "local",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "resp", "schema": schema}},
        "max_tokens": max_tokens, "temperature": 0.2,
    }
    r = requests.post(URL, json=body, timeout=30)
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


@dataclass
class Session:
    raw_input: str = ""
    input_mode: str = "voice"
    product: str = ""
    problem_type: str = ""
    user_goal: str = ""
    diverge_options: list = field(default_factory=list)
    chosen_direction: str = ""
    known_symptoms: list = field(default_factory=list)
    available_evidence: list = field(default_factory=list)
    missing_evidence: list = field(default_factory=list)
    constraints: list = field(default_factory=list)
    selected_pod: list = field(default_factory=list)
    state: State = State.CAPTURE


class FrontDeskDialog:
    def __init__(self):
        self.session = Session()

    # ---- S0/S1: CAPTURE + INTENT ----
    def capture(self, text: str, input_mode: str = "voice"):
        self.session.raw_input = text
        self.session.input_mode = input_mode
        self.session.state = State.INTENT
        return self._do_intent()

    def _do_intent(self):
        schema = {
            "type": "object",
            "properties": {
                "product": {"type": "string", "enum": ["notebook", "smartphone", "tablet", "headphone_tws",
                                                          "smart_speaker", "conference_device", "tv_monitor",
                                                          "automotive", "wearable", "robot", "unspecified"]},
                "problem_summary": {"type": "string"},
            },
            "required": ["product", "problem_summary"],
        }
        result = _llm_json(
            "從使用者這句話萃取：(1) 產品類型 (2) 用一句話重述問題（不要下結論，只重述症狀）。",
            self.session.raw_input, schema,
        )
        self.session.product = result["product"]
        self.session.user_goal = result["problem_summary"]
        self.session.state = State.DIVERGE
        return self._do_diverge()

    # ---- S2: DIVERGE ----
    def _do_diverge(self):
        schema = {
            "type": "object",
            "properties": {"directions": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 8}},
            "required": ["directions"],
        }
        result = _llm_json(
            "根據這個聲學問題描述，列出3~8個「可能的異常方向」關鍵字（例如：漏氣、Driver異常、腔體共振、"
            "熱壓縮、量測誤差...），給使用者勾選用，不要下結論、不要解釋，只列方向名稱。",
            self.session.user_goal, schema,
        )
        self.session.diverge_options = result["directions"]
        self.session.state = State.CONVERGE
        return {"state": "DIVERGE", "question": "這個問題比較接近哪個方向？（可複選，或選不確定讓AERIS判斷）",
                "options": self.session.diverge_options + ["不確定，讓AERIS自動判斷"]}

    # ---- S3: CONVERGE ----
    def converge(self, chosen_directions: list, known_symptoms: list = None):
        self.session.chosen_direction = "、".join(chosen_directions)
        self.session.known_symptoms = known_symptoms or []
        self.session.state = State.EVIDENCE
        return {"state": "EVIDENCE", "question": "你目前有哪些量測資料？",
                "options": ["FR", "THD", "Impedance", "Klippel", "CAD", "Golden sample", "不確定"]}

    # ---- S4: EVIDENCE ----
    def evidence(self, available: list, missing: list = None, constraints: list = None):
        self.session.available_evidence = available
        self.session.missing_evidence = missing or []
        self.session.constraints = constraints or []
        self.session.state = State.ROUTE
        return self._do_route()

    # ---- S5: ROUTE ----
    def _do_route(self):
        engineer_list_text = "\n".join(f"#{eid} {name}：{ENGINEER_CAPABILITY[eid]}" for eid, name in ENGINEERS.items())
        schema = {
            "type": "object",
            "properties": {
                "engineer_ids": {"type": "array", "items": {"type": "string", "enum": list(ENGINEERS.keys())},
                                  "minItems": 2, "maxItems": 8},
            },
            "required": ["engineer_ids"],
        }
        context = (f"產品:{self.session.product} 問題:{self.session.user_goal} "
                   f"方向:{self.session.chosen_direction} 資料:{','.join(self.session.available_evidence)}")
        result = _llm_json(
            "從以下工程師清單（含核心能力說明）中，根據案例的產品類型、問題方向挑選2~8位最相關的工程師"
            f"（回傳ID，優先選能力說明跟「方向」關鍵字直接對應的人）：\n{engineer_list_text}",
            context, schema, max_tokens=100,
        )
        self.session.selected_pod = [(eid, ENGINEERS[eid]) for eid in result["engineer_ids"]]
        self.session.state = State.PREVIEW
        return self._do_preview()

    # ---- S6: PREVIEW ----
    def _do_preview(self):
        self.session.state = State.CONFIRM
        return {
            "state": "PREVIEW",
            "summary": {
                "product": self.session.product,
                "user_goal": self.session.user_goal,
                "direction": self.session.chosen_direction,
                "evidence": self.session.available_evidence,
                "pod": self.session.selected_pod,
            },
            "question": "這樣送給AERIS處理可以嗎？",
        }

    # ---- S7/S8: CONFIRM -> ORDER_LOCKED ----
    def confirm(self, approved: bool, handoff_dir=None):
        if not approved:
            return {"state": "CANCELLED"}
        order = OrderDraft(
            case_id=new_case_id(),
            input_mode=self.session.input_mode,
            product=self.session.product,
            user_goal=self.session.user_goal,
            problem_type=self.session.chosen_direction,
            known_symptoms=self.session.known_symptoms,
            available_evidence=self.session.available_evidence,
            missing_evidence=self.session.missing_evidence,
            constraints=self.session.constraints,
            selected_pod=self.session.selected_pod,
            required_work=[f"分析並排序 {self.session.chosen_direction} 等可能根因"],
        )
        path = write_order(order, handoff_dir=handoff_dir)
        self.session.state = State.ORDER_LOCKED
        return {"state": "ORDER_LOCKED", "path": str(path)}
