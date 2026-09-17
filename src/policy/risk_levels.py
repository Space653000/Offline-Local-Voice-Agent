# -*- coding: utf-8 -*-
"""
權限分級表（對照 docs/01 藍圖第9節、docs/03 藍圖第2節、CLAUDE.md 施工鐵則）。

L0 唯讀查詢：不改變系統任何狀態，免確認
L1 一般可逆操作：會改變狀態，但容易復原（開程式、調音量），免確認
L2 敏感操作：不容易復原或牽涉外部資源（刪檔、寄信、雲端上傳），需要二次確認
L3 危險操作：破壞性或難以復原（關機、清理垃圾檔、解決合併衝突），一定要明確確認，且每次都要問，不可記住「這次都同意」

對照 docs/07 進度報告第11節指出的落差：資料本身（哪個工具是哪個等級）已經外部化到
config/permissions.yaml，這個檔案只留判斷邏輯跟等級定義——使用者現在可以直接改YAML
調整權限規則，不需要碰Python原始碼。
"""
import sys
from pathlib import Path
from enum import IntEnum

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config_loader import load_permissions


class RiskLevel(IntEnum):
    L0_READONLY = 0
    L1_ROUTINE = 1
    L2_SENSITIVE = 2
    L3_DANGEROUS = 3


def _build_tables():
    data = load_permissions()

    tools_cfg = data.get("tools")
    if not tools_cfg:
        raise ValueError("config/permissions.yaml 缺少 'tools' 區塊，權限表不能是空的")

    risk_table = {}
    for tool, cfg in tools_cfg.items():
        if not isinstance(cfg, dict) or "level" not in cfg:
            raise ValueError(f"config/permissions.yaml 裡工具 '{tool}' 沒有指定 level")
        level_name = cfg["level"]
        if level_name not in RiskLevel.__members__:
            raise ValueError(
                f"config/permissions.yaml 裡工具 '{tool}' 的 level '{level_name}' 不是合法的風險等級"
                f"（只接受 {list(RiskLevel.__members__)}）"
            )
        risk_table[tool] = RiskLevel[level_name]

    escalation = {}
    for rule in data.get("escalation_rules", []) or []:
        for key in ("tool", "action", "level"):
            if key not in rule:
                raise ValueError(f"config/permissions.yaml 的 escalation_rules 有一條規則缺少 '{key}'：{rule}")
        level_name = rule["level"]
        if level_name not in RiskLevel.__members__:
            raise ValueError(f"config/permissions.yaml 的 escalation_rules 裡有不合法的風險等級：{level_name}")
        escalation[(rule["tool"], rule["action"])] = RiskLevel[level_name]

    return risk_table, escalation


TOOL_RISK_TABLE, ESCALATION_RULES = _build_tables()
