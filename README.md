# Offline-Local-Voice-Agent

100% 離線、斷網可用的 Windows 語音桌面代理人。
使用者說話 → 本機 AI 理解 → 安全控制 Windows（開程式、找檔案、UI 操作）→ 語音回覆。

目標硬體：**Microsoft Surface Laptop Ultra（NVIDIA RTX Spark, 64GB 統一記憶體, Windows on ARM）**

本地建置路徑：`C:\0_JN1_Offline-Local-Voice-Agent`

---

## 目錄結構

```
Offline-Local-Voice-Agent/
├── README.md                  ← 本檔案
├── CLAUDE.md                  ← Claude Code 進場規則（開工前必讀）
└── docs/
    ├── 01_Original_Blueprint_v0.1.md              ← 最初版本設計藍圖（AERIS概念版）
    ├── 02_ChatGPT_Deep_Research_Report.md          ← 模型/硬體/SOP 深度研究（ChatGPT）
    └── 03_ClaudeCode_Execution_Blueprint_v0.1.md   ← 針對 RTX Spark ARM 硬體修正後的正式執行藍圖（本專案採用版本）
```

## 現況

- 目前狀態：**規劃完成，尚未開工（P0 未開始）**
- 正式採用版本以 `docs/03_ClaudeCode_Execution_Blueprint_v0.1.md` 為準
- `01` 與 `02` 為前期研究素材，保留作為對照與追溯依據，不作為執行標準

## 核心原則（不可違反）

1. 完全離線 — 正式運作階段禁止任何雲端 API
2. LLM 不直接執行任意 Shell/PowerShell — 一律走 Structured Tool Call → Policy Engine → Executor
3. API first / UI Automation second / Vision last
4. 每個 Phase 獨立驗收，PASS 才能進下一階段，不重做已 PASS 功能
5. **Phase 0 專門驗證 ARM64 生態相容性，禁止在驗證前下載大型模型或寫功能程式碼**（此為本專案相對於原版藍圖的關鍵修正）

## 下一步

見 `CLAUDE.md`，這是給 Claude Code 開工時讀的第一份文件。
