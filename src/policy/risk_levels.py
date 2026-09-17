# -*- coding: utf-8 -*-
"""
權限分級表（對照 docs/03 藍圖第2節、CLAUDE.md 施工鐵則）。

L0 唯讀查詢：不改變系統任何狀態，免確認
L1 一般可逆操作：會改變狀態，但容易復原（開程式、調音量），免確認
L2 敏感操作：不容易復原或牽涉外部資源（刪檔、寄信、雲端上傳），需要二次確認
L3 危險操作：破壞性或難以復原（關機、清理垃圾檔、解決合併衝突），一定要明確確認，且每次都要問，不可記住「這次都同意」
"""
from enum import IntEnum


class RiskLevel(IntEnum):
    L0_READONLY = 0
    L1_ROUTINE = 1
    L2_SENSITIVE = 2
    L3_DANGEROUS = 3


# 對照 progress/p2_tool_calling/tools_and_labels_v2.py 的 35 個工具
TOOL_RISK_TABLE = {
    "open_app": RiskLevel.L1_ROUTINE,
    "close_window": RiskLevel.L2_SENSITIVE,  # docs/01第9節原始藍圖明確把「關閉程式」列在L2（可能有未存檔內容），原本誤設成L1
    "window_op": RiskLevel.L1_ROUTINE,
    "set_volume": RiskLevel.L1_ROUTINE,
    "media_control": RiskLevel.L1_ROUTINE,
    "get_datetime": RiskLevel.L0_READONLY,
    "get_weather": RiskLevel.L0_READONLY,
    "get_exchange_rate": RiskLevel.L0_READONLY,
    "adjust_brightness": RiskLevel.L1_ROUTINE,
    "take_screenshot": RiskLevel.L1_ROUTINE,
    "clipboard_op": RiskLevel.L1_ROUTINE,
    "file_op": RiskLevel.L1_ROUTINE,           # 基準是L1（find/open是唯讀，風險低）；move/copy/rename/create_folder/delete
                                                # 這些真的會改變檔案系統狀態的動作，由下面ESCALATION_RULES個別拉高，
                                                # 不能整個工具都當作L2——不然像PlanRunner裡「先找檔案」這種純查詢步驟
                                                # 也會被迫要求使用者確認，多此一舉（docs/07進度報告驗證PlanRunner時發現）
    "cloud_file_op": RiskLevel.L2_SENSITIVE,  # 牽涉外部雲端服務
    "power_op": RiskLevel.L3_DANGEROUS,       # 關機/重開/休眠，會中斷使用者正在做的事
    "network_toggle": RiskLevel.L2_SENSITIVE,  # 原本設L1，P3實測時意識到：關掉Wi-Fi可能打斷使用者在同一台電腦上的其他活動（下載/通話/瀏覽），不是單純「可逆」就等於「低風險」，升級成L2
    "calendar_op": RiskLevel.L1_ROUTINE,
    "reminder_op": RiskLevel.L1_ROUTINE,
    "alarm_op": RiskLevel.L1_ROUTINE,
    "print_or_scan": RiskLevel.L1_ROUTINE,
    "photo_edit": RiskLevel.L1_ROUTINE,
    "text_input_op": RiskLevel.L1_ROUTINE,
    "text_to_speech_op": RiskLevel.L0_READONLY,
    "speech_to_text_op": RiskLevel.L0_READONLY,
    "translate": RiskLevel.L0_READONLY,
    "calculator": RiskLevel.L0_READONLY,
    "email_op": RiskLevel.L2_SENSITIVE,       # 寄信/刪信是對外或不可逆動作
    "video_call_op": RiskLevel.L1_ROUTINE,
    "record_screen": RiskLevel.L1_ROUTINE,
    "system_maintenance": RiskLevel.L3_DANGEROUS,  # 清理垃圾檔/安裝更新可能不可逆
    "task_scheduler_op": RiskLevel.L2_SENSITIVE,
    "startup_program_op": RiskLevel.L2_SENSITIVE,
    "driver_op": RiskLevel.L3_DANGEROUS,      # 更新驅動程式風險較高
    "dev_tool_op": RiskLevel.L2_SENSITIVE,    # 執行程式碼本身有風險
    "git_op": RiskLevel.L2_SENSITIVE,         # push/merge 可能造成程式碼遺失
    "summarize_doc": RiskLevel.L0_READONLY,

    # 對照 docs/01 藍圖第7節的 UIA 原語（docs/07 進度報告抓到的缺口，這批補上）
    "get_active_window": RiskLevel.L0_READONLY,
    "list_windows": RiskLevel.L0_READONLY,
    "focus_window": RiskLevel.L1_ROUTINE,
    "uia_click": RiskLevel.L2_SENSITIVE,      # 點到什麼按鈕效果不可預期，比照file_op的謹慎程度
    "uia_set_text": RiskLevel.L2_SENSITIVE,
    "uia_select": RiskLevel.L2_SENSITIVE,
    "press_key": RiskLevel.L1_ROUTINE,        # 多是導覽用的單鍵（Enter/Esc/方向鍵），風險低
    "hotkey": RiskLevel.L2_SENSITIVE,         # 組合鍵威力較大（例如Alt+F4關視窗），黑名單擋掉最危險的幾個
}

# 特定工具 + 特定參數組合可以再往上升級（例如 file_op 若 action=delete 就算 L3）
ESCALATION_RULES = {
    ("file_op", "delete"): RiskLevel.L3_DANGEROUS,
    ("file_op", "move"): RiskLevel.L2_SENSITIVE,
    ("file_op", "copy"): RiskLevel.L2_SENSITIVE,
    ("file_op", "rename"): RiskLevel.L2_SENSITIVE,
    ("file_op", "create_folder"): RiskLevel.L2_SENSITIVE,
    ("git_op", "push"): RiskLevel.L3_DANGEROUS,
    ("git_op", "merge"): RiskLevel.L3_DANGEROUS,
    ("cloud_file_op", "delete"): RiskLevel.L3_DANGEROUS,
    ("email_op", "delete"): RiskLevel.L3_DANGEROUS,
    ("email_op", "send"): RiskLevel.L3_DANGEROUS,
}
