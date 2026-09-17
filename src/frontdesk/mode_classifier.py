# -*- coding: utf-8 -*-
"""
模式分流器：判斷使用者這句話是「一般桌面操作」還是「聲學工程問題」。
一般操作 -> 走既有 P2 的 35 個 Windows 工具（src/executor）
工程問題 -> 走 Front Desk 引導流程，最後產出 ORDER.md 給 AERIS

用同一個常駐的 llama-server，只是換一個很簡單的 system prompt，不需要另外訓練或換模型。
"""
import requests, json

URL = "http://127.0.0.1:8811/v1/chat/completions"

SYSTEM_PROMPT = (
    "你只做一件事：判斷使用者說的這句話，是「一般電腦操作」還是「聲學/揚聲器/麥克風工程問題」。"
    "聲學工程問題的特徵：提到喇叭、speaker、麥克風、mic、聲音異常、SPL、頻響、失真、THD、漏氣、"
    "產品聲學設計、量測、Klippel、APx 等。其餘一律算一般電腦操作。"
    "範例：\n"
    '「打開瀏覽器」→ {"mode": "desktop_control"}\n'
    '「這個THD失真是不是driver的問題」→ {"mode": "acoustic_engineering"}\n'
    '「喇叭THD太高怎麼辦」→ {"mode": "acoustic_engineering"}\n'
    "只輸出符合 schema 的 JSON，不要解釋。"
)

SCHEMA = {
    "type": "object",
    "properties": {
        "mode": {"type": "string", "enum": ["desktop_control", "acoustic_engineering"]},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["mode"],
}


def classify(text: str) -> dict:
    body = {
        "model": "local",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "mode", "schema": SCHEMA}},
        "max_tokens": 30,
        "temperature": 0.0,
    }
    r = requests.post(URL, json=body, timeout=15)
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])
