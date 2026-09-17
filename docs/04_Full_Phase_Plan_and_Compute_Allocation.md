# P0 → P6 完整建置計畫與 CPU/GPU/NPU 分配

> 依據 `docs/03_ClaudeCode_Execution_Blueprint_v0.1.md` 展開，補上每個環節的運算裝置分配、驗證方式。
> 原則：**GPU 優先**（ASR、LLM 這類重運算全上 CUDA），**CPU 盡量少用**（留給 AERIS），**NPU 目前無法用**（P0 已確認缺 SDK，暫列觀察）。

---

## P0 — 硬體與生態相容性驗證 ✅ 已完成（PASS）

| 項目 | 結果 |
|---|---|
| ASR 引擎 | whisper.cpp，**CUDA GPU** |
| LLM 引擎 | llama.cpp，**CUDA GPU** |
| faster-whisper | FAIL（ctranslate2 無 ARM64 wheel），排除 |
| onnxruntime-directml/-gpu | FAIL（無 ARM64 wheel），VAD 類小模型留 CPU |
| NPU | 硬體存在，無 SDK，暫緩 |

詳細數據見 `hardware_compat_report.json`、`progress/p0/REPORT.md`。

---

## P1 — 語音輸入（VAD + 喚醒詞 + ASR，不控制 Windows）

| 環節 | 運算裝置 | 理由 |
|---|---|---|
| VAD（silero-vad） | **CPU** | 模型 <2MB，單次推論 <5ms，GPU 搬資料開銷比運算本身還貴，不值得佔 GPU/VRAM |
| 喚醒詞（openWakeWord） | **CPU** | 同上，常駐監聽但負載極輕 |
| ASR（whisper.cpp） | **GPU（CUDA）** | P0 已驗證：GPU 版比 CPU 版快 2.4 倍（340ms vs 815ms），且 ASR 是這條路徑裡最重的運算 |

**驗證方式（本次已執行，見下方 P1 實測章節）**：
- 100+ 句中文語音指令，量測：辨識準確率（字元錯誤率 CER）、單句處理延遲、即時率（RTF）
- 驗收標準（沿用原藍圖）：**中文指令辨識成功率 > 95%**
- 額外量測：「反應快不快」= 端到端延遲；「字幕出來快不快」= RTF（處理時間 / 音檔長度，< 1 代表比即時說話還快）

---

## P2 — 意圖辨識 / Tool Calling（只驗證 JSON，不執行）

| 環節 | 運算裝置 | 理由 |
|---|---|---|
| LLM 推論（結構化輸出/Tool Call 選擇） | **GPU（CUDA）** | 沿用 P0 驗證的 llama.cpp CUDA 路徑，Qwen 系列本身支援 function-calling 格式 |
| JSON Schema 驗證 / 格式檢查 | **CPU** | 純邏輯運算，毫秒級，用 GPU 沒有意義 |

**驗證方式**：100 個指令測試集，Tool 選擇成功率 ≥ 95%（沿用原藍圖），可搭配「Claude 規劃 → Codex 執行 → 互審」流程跑。

---

## P3 — Windows Automation（開始真控制）

| 環節 | 運算裝置 | 理由 |
|---|---|---|
| UIA 操作 / PowerShell Executor | **CPU** | Windows API 呼叫本質上是 CPU/IO 工作，GPU 無關 |
| （若需要）畫面元素辨識輔助 | **GPU（CUDA，若走 CV 模型）** | 只在 UIA 找不到元素時才會用到（屬於 P5 Vision Fallback 範疇，這裡先不做） |

**驗證方式**：ARM64 版 Windows UIA 函式庫相容性測試（C#/COM interop 在 ARM64 上常有行為差異，需額外補測）。

---

## P4 — 安全 / 權限分級

| 環節 | 運算裝置 | 理由 |
|---|---|---|
| Policy Engine（L0~L3 判斷） | **CPU** | 規則引擎，純邏輯 |
| 稽核紀錄寫入（SQLite） | **CPU/IO** | 資料庫寫入不需要 GPU |
| Emergency Stop 熱鍵監聽 | **CPU** | 系統層級鉤子 |

**驗證方式**：模擬 100 次不同權限等級的動作請求，確認 L2 以上都正確跳出二次確認；合蓋/待機時自動停止監聽測試。

---

## P5 — Vision Fallback

| 環節 | 運算裝置 | 理由 |
|---|---|---|
| Qwen3-VL 視覺推論 | **GPU（CUDA），lazy load** | 影像模型運算量大，且此階段才需要，不常駐省 VRAM |

**驗證方式**：UIA 找不到元素的案例集，量測 Vision Fallback 觸發後的定位成功率與延遲。

---

## P6 — 完整語音代理人整合測試

| 環節 | 運算裝置 | 理由 |
|---|---|---|
| 全流程（VAD→喚醒詞→ASR→LLM→Policy→Executor） | CPU（VAD/喚醒詞/Policy/Executor）+ **GPU（ASR/LLM 常駐）** | 統一記憶體架構下，GPU 常駐兩個模型不會擠爆記憶體（46GB VRAM 目前只用 <1GB） |

**驗證方式**：沿用原 KPI —— 喚醒→ASR < 1.5 秒、指令路由 ≥ 95%、簡單指令整體延遲 < 3 秒感受延遲。

---

## 總覽表：每個環節的運算裝置

| 環節 | CPU | GPU | NPU |
|---|---|---|---|
| VAD | ✅ | | |
| 喚醒詞 | ✅ | | |
| ASR | | ✅ | （待 NVIDIA 出 SDK 後可評估） |
| LLM 推論 | | ✅ | |
| Tool Call JSON 驗證 | ✅ | | |
| UIA/PowerShell 操作 | ✅ | | |
| Policy Engine | ✅ | | |
| 稽核 DB 寫入 | ✅ | | |
| Vision Fallback | | ✅ | |
| TTS | ✅（系統原生） | | |
