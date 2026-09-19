# Offline-Local-Voice-Agent

100% 離線、斷網可用的 Windows 語音桌面代理人。
使用者說話（或打字）→ 本機 AI 理解 → 安全控制 Windows（開程式、找檔案、UI 操作）→ 語音（或文字）回覆。

目標硬體：**Microsoft Surface Laptop Ultra（NVIDIA RTX Spark, 64GB 統一記憶體, Windows on ARM）**

本地建置路徑：`C:\0_JN1_Offline-Local-Voice-Agent`

---

## 目錄結構

```
Offline-Local-Voice-Agent/
├── README.md                  ← 本檔案
├── CLAUDE.md                  ← Claude Code 進場規則（開工前必讀）
├── src/                       ← 常駐服務原始碼（listen_loop.py、Executor、Front Desk、35個工具）
├── console/                   ← 主控台網頁（index.html 進度儀表板、companion.html 即時陪伴介面）
├── config/                    ← 外部化設定（permissions.yaml 權限分級、tools.yaml、runtime.yaml）
├── progress/                  ← 各Phase的驗證/量測/評估報告與原始資料
└── docs/
    ├── 01_Original_Blueprint_v0.1.md               ← 最初版本設計藍圖（AERIS概念版，背景參考）
    ├── 02_ChatGPT_Deep_Research_Report.md          ← 模型/硬體/SOP 深度研究（ChatGPT，背景參考）
    ├── 03_ClaudeCode_Execution_Blueprint_v0.1.md   ← 正式採用的執行藍圖，一切施工以此為準
    ├── 06_Frontdesk_Workplan.md                    ← 逐次施工紀錄（技術細節、bug、修法）
    ├── 07_Progress_Report_vs_Blueprint_2026-09-17.md ← 逐節對照藍圖的詳細稽核報告（持續更新）
    └── 08_Executive_Summary_and_User_SOP.md        ← 一頁式總覽：目前進度、待你決定的事
```

## 現況（持續更新，以`docs/08`為準）

- **目前整體工程進度：約84%**（P0～P6共7大階段，詳見`docs/08_Executive_Summary_and_User_SOP.md`第2節的逐階段拆解）
- P0（硬體驗證）、P1（語音輸入）、P2（意圖辨識）已100%完成並驗收
- P3（電腦操作）：34個真實工具實作（35工具表25/35＋8個UI Automation原語＋額外的`memory_op`記憶功能）
- P4（安全機制）：L0~L3風險分級、語音/文字雙確認、Emergency Stop、喚醒詞開關（預設關閉）都已完成並測試
- P5（視覺備援）：已下載Qwen3-VL模型並真實測過畫面理解跟精確定位能力，還沒接進Executor自動化流程
- P6（完整整合）：多步驟規劃已驗證多種場景，喚醒詞到完整回覆的延遲仍未達藍圖目標（已知限制，原因跟取捨記錄在`docs/08`）
- 正式採用版本以`docs/03_ClaudeCode_Execution_Blueprint_v0.1.md`為準；`01`與`02`為前期研究素材，保留作為對照與追溯依據，不作為執行標準

**想看目前實際進度，從這三份文件開始**：
1. `docs/08_Executive_Summary_and_User_SOP.md` — 一頁式總覽，適合快速了解現況
2. `docs/07_Progress_Report_vs_Blueprint_2026-09-17.md` — 逐次更新的完整技術稽核紀錄
3. `console/index.html`（或對應的線上主控台）— 視覺化的進度儀表板

## 核心原則（不可違反）

1. 完全離線 — 正式運作階段禁止任何雲端 API
2. LLM 不直接執行任意 Shell/PowerShell — 一律走 Structured Tool Call → Policy Engine → Executor
3. API first / UI Automation second / Vision last
4. 每個 Phase 獨立驗收，PASS 才能進下一階段，不重做已 PASS 功能
5. **Phase 0 專門驗證 ARM64 生態相容性，禁止在驗證前下載大型模型或寫功能程式碼**（此為本專案相對於原版藍圖的關鍵修正）
6. 介面/UX/功能可以參考現有雲端AI助理的做法（例如統一對話記錄、記憶功能、檔案問答），但運算本身必須留在本機完成——「100%離線」限定的是運算，不是設計靈感的來源

## 下一步

見 `CLAUDE.md`，這是給 Claude Code 開工時讀的第一份文件。目前待你決定的事、以及AI會自主繼續做的事，見`docs/08`第4、5節。
