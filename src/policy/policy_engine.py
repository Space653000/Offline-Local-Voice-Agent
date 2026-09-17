# -*- coding: utf-8 -*-
"""
Policy Engine：所有 Tool Call 執行前一定要先過這一關。
只做「這個動作允不允許直接跑」的判斷，不負責真正執行（那是 executor 的工作）。
"""
from dataclasses import dataclass
from .risk_levels import RiskLevel, TOOL_RISK_TABLE, ESCALATION_RULES


@dataclass
class PolicyDecision:
    tool: str
    args: dict
    level: RiskLevel
    requires_confirmation: bool
    requires_typed_confirmation: bool  # L3：不能只按「是」，要求輸入這個動作的關鍵字才算確認
    reason: str


class PolicyEngine:
    def evaluate(self, tool: str, args: dict) -> PolicyDecision:
        if tool not in TOOL_RISK_TABLE:
            # 未知工具一律當作最高風險，寧可多問也不要漏放
            return PolicyDecision(
                tool=tool, args=args, level=RiskLevel.L3_DANGEROUS,
                requires_confirmation=True, requires_typed_confirmation=True,
                reason=f"未知工具 '{tool}' 不在權限表內，預設視為最高風險",
            )

        level = TOOL_RISK_TABLE[tool]

        action = (args or {}).get("action")
        if action and (tool, action) in ESCALATION_RULES:
            escalated = ESCALATION_RULES[(tool, action)]
            if escalated > level:
                level = escalated

        requires_confirmation = level >= RiskLevel.L2_SENSITIVE
        requires_typed_confirmation = level >= RiskLevel.L3_DANGEROUS

        reason = {
            RiskLevel.L0_READONLY: "唯讀查詢，不影響任何東西",
            RiskLevel.L1_ROUTINE: "一般可逆操作",
            RiskLevel.L2_SENSITIVE: "敏感操作，需要你確認一次",
            RiskLevel.L3_DANGEROUS: "危險/不可逆操作，一定要你明確確認，不會記住這次同意就跳過下次",
        }[level]

        return PolicyDecision(
            tool=tool, args=args, level=level,
            requires_confirmation=requires_confirmation,
            requires_typed_confirmation=requires_typed_confirmation,
            reason=reason,
        )
