# AERIS 整合拆分 — 兩條後續作法

> 依據 `AERIS_100_Acoustic_Engineers_Conversation_Record_v1.1_2026-09-15.md` 拆分。
> 兩個專案完全獨立施工、不共用程式碼，只透過 `ORDER.md` 檔案格式互通。

---

## 1. 使用者介面（本專案 `C:\0_JN1_Offline-Local-Voice-Agent`）

本專案原本的目標（P0–P6，見 `docs/03`）是通用的 Windows 桌面語音控制代理人，**這個定位不變**。
AERIS 對話紀錄裡描述的「Front Desk」，剛好跟本專案 P1（語音輸入）+ P2（意圖辨識）的技術完全對得上：

| AERIS Front Desk 需求 | 本專案現有基礎 |
|---|---|
| Voice → STT → Text | ✅ P1 whisper.cpp（GPU，medium模型，已驗證） |
| Text → Intent | ✅ P2 llama-server + JSON schema tool-calling（97.1%準確率） |
| Guided Conversation（收斂+發散） | 需新增：目前 P2 是「一句話→一個工具」，AERIS 需要的是多輪對話狀態機（文件42節 S0–S9） |
| 產出 `ORDER.md` | 需新增：目前 P2 的輸出是 Tool Call JSON，不是 ORDER.md 格式 |

### 後續要做的事（不影響既有 P0–P3 主線，是新增的一個「模式」）

1. **新增一個 Front Desk 對話狀態機**：`src/frontdesk/` — S0 CAPTURE → S1 INTENT → S2 DIVERGE → S3 CONVERGE → S4 EVIDENCE → S5 ROUTE → S6 PREVIEW → S7 CONFIRM → S8 ORDER_LOCKED，對照文件第42節。
2. **ORDER.md 產生器**：依文件29.2的格式（YAML front-matter + markdown 內容），把收斂完的結構化需求寫成檔案。
3. **交接資料夾**：定義一個雙方都認得的本機路徑（例如 `C:\0_JN1_AERIS_HANDOFF\orders\`），Voice-Agent 寫入、AERIS 監看讀取——這是唯一的整合點，不涉及程式碼共用。
4. **這是「模式」不是「取代」**：一般 Windows 控制指令（開瀏覽器、調音量…）繼續走原本 P2 的 35 個工具；只有辨識出「這是聲學工程問題」時才切換成 Front Desk 引導流程。判斷方式：先用現有 LLM 做一個粗分類（一般桌面操作 vs 工程問題）。

### 暫不做的事

- 不會去碰 100 位工程師的能力定義（那是 AERIS 的事）
- 不會直接呼叫 AERIS 的任何內部程式碼或 API（維持「完全獨立」）

---

## 2. 管理介面（`C:\0_JN1_AERIS`，本 session 不會動手）

以下是**依照文件內容整理出來、AERIS 那邊該做的事**，僅供參考／同步規劃使用，不在本 session 施工範圍：

1. **Order Validator**：收到交接資料夾裡的 `ORDER.md`，做 schema/completeness 檢查（文件第30節驗收標準）。
2. **100 個 Capability Contract YAML**：先做 Wave 1（文件第49節）：003, 018, 021, 022, 023, 057, 086, 091, 097, 100 這十位，打通第一條完整 Vertical Slice（文件第48節建議的 NB Speaker Golden vs NG 案例）。
3. **Orchestrator + Expert Pod 自動組隊**。
4. **Results.xlsx + Report.pptx 固定交付格式**（文件32節的 Sheet/Slide 結構）。
5. **G0–G10 驗收 Gate 機制**（文件34節），不可只憑文件宣稱完成度。

---

## 3. 兩邊怎麼確認「接得上」

因為不共用程式碼，唯一的整合驗證方式是：

1. 本專案先做出一個範例 `ORDER.md`（就算 Front Desk 狀態機還沒做完，也可以先手動照格式寫一份測試檔）
2. 丟到交接資料夾
3. 請 AERIS 那邊（或你自己）確認格式能被他們的 Order Validator 正確解析

這樣兩個專案可以平行施工，不用互相等待。
