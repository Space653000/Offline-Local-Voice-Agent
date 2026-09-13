# 離線語音桌面代理人 — Claude Code 執行藍圖 v0.1
（目標硬體：Microsoft Surface Laptop Ultra, RTX Spark, 64GB 統一記憶體, Windows on ARM）

> 本藍圖是對照你上傳的 `Offline_Local_Voice_Desktop_Agent_Blueprint_v0.1.md` 與 ChatGPT 深度研究報告後，
> 針對「RTX Spark 是 ARM 架構」這個關鍵事實重新調整的執行順序。核心哲學不變（API first / UI Automation second / Vision last，離線優先，Tool化，權限分級），
> 但把「Phase 0 硬體與生態驗證」拉到最優先，因為 ARM Windows 上的 CUDA/PyTorch/llama.cpp 生態目前仍不成熟，這點比模型選擇更決定成敗。

---

## 0. 與 ChatGPT 報告的差異（為何要改）

1. ChatGPT 報告預設 x86 Windows + NVIDIA 獨顯（GTX/RTX 40系）。你的實際硬體是 **ARM CPU（20核）+ Blackwell GPU（6144 CUDA核）+ 64GB 統一記憶體**，架構完全不同：
   - 好處：統一記憶體不用在「系統RAM」與「顯存」之間切分，大模型與ASR可以同時常駐而不互搶記憶體。
   - 風險：許多 Python/CUDA 生態（PyTorch、faster-whisper 的 CTranslate2 後端、部分 llama.cpp CUDA build）在 Windows ARM64 上的成熟度尚待驗證，不能假設「x86能跑=ARM能跑」。
2. 因此本藍圖把「環境相容性驗證」列為 **Phase 0 的唯一任務**，且明確禁止在驗證前下載大型模型或寫功能程式碼——這點沿用你原始藍圖 P0 的精神，但加嚴。
3. 喚醒詞模型改推薦 openWakeWord（開源、免授權）取代 Porcupine（商用授權），符合你「完全掌控、可長期擁有」的一貫偏好（對照 PAFAS 精神：permanently-owned, model-agnostic）。

---

## 1. 整條運作路徑（最終建議版）

```
麥克風
 ↓
VAD (webrtcvad 或 silero-vad，純CPU，ARM相容性高)
 ↓
喚醒詞 openWakeWord（CPU常駐，低功耗）
 ↓
ASR faster-whisper (medium → 驗證穩定後升 large-v3)
 ↓
主腦 Qwen3-30B-A3B (llama.cpp / Ollama，MoE架構省記憶體)
 ↓ 輸出 Structured JSON（Tool call，禁止自然語言直接執行）
Policy Engine（L0~L3 權限分級，L2以上需二次確認）
 ↓
Tool Executor（Windows UIA / PowerShell / 檔案系統，禁止 execute_any_shell_command）
 ↓ 失敗才觸發
Vision Fallback：Qwen3-VL（lazy load，僅描述畫面＋定位UI，不直接控制滑鼠）
 ↓
驗證結果
 ↓
TTS（Windows 內建離線神經語音 或 Piper，二擇一，皆離線）
```

---

## 2. 各層模型與理由（附ARM風險註記）

| 層 | 選型 | 理由 | ARM風險 |
|---|---|---|---|
| VAD | silero-vad | 純CPU、輕量、PyTorch可用ONNX Runtime跑，繞開部分ARM CUDA問題 | 低 |
| 喚醒詞 | openWakeWord | 開源可自訓、無授權費，符合永久自有原則 | 低（純CPU） |
| ASR | faster-whisper (CTranslate2) | 中英混說、工程術語辨識強 | **中—CTranslate2 ARM64 build需現場驗證，備援方案見下** |
| ASR備援 | whisper.cpp | 純C++、GGML量化，ARM相容性歷史上優於Python生態 | 低（建議優先試這個） |
| 主腦 | Qwen3-30B-A3B (llama.cpp) | MoE只需活化~3B參數，統一記憶體架構下效率佳 | 中—需確認llama.cpp的CUDA/ARM64 build是否支援Blackwell |
| 主腦備援 | Ollama（若原生llama.cpp build不穩） | 封裝好、跨平台維護較積極 | 低—但需確認Ollama是否已支援RTX Spark |
| Vision | Qwen3-VL-30B-A3B | 同樣MoE，lazy load不常駐 | 同主腦 |
| TTS | Windows內建離線神經語音 | 系統原生、零額外依賴、100%離線 | 極低 |

**核心判斷原則**：優先選「純C++/GGML/ONNX」路線的工具（whisper.cpp、llama.cpp、ONNX Runtime），避開重度依賴PyTorch CUDA wheel的路線（faster-whisper的CTranslate2），因為前者的ARM64移植歷史更久、社群支援更廣。這是本藍圖與ChatGPT報告最大的技術判斷差異。

---

## 3. 施工階段（Claude Code 版）

### P0 — 硬體與生態驗證（唯一任務：確認能不能跑，不寫功能）
Claude Code 執行：
1. 偵測 Windows版本、ARM64架構、RTX Spark驅動版本、CUDA on WoA是否可用
2. 分別測試安裝：`llama.cpp`（含CUDA backend）、`whisper.cpp`、`faster-whisper`、`onnxruntime-directml`
3. 每項工具跑一個最小可行的推論測試（載入一個小模型，跑一句話），記錄成功/失敗
4. 輸出 `hardware_compat_report.json`，明確列出「哪些工具鏈在這台機器上可用」
5. **驗收標準**：至少一條ASR路徑 + 一條LLM推論路徑成功跑通，才能進P1。若全部失敗，改用WSL2作為執行環境（沿用你在Maera專案裡對公司RTX Spark機器的既有結論），重新跑一次P0。

### P1 — 語音輸入（VAD + 喚醒詞 + ASR，不控制Windows）
- 沿用你原始藍圖的驗收標準：中文指令辨識成功率 > 95%
- 差異：ASR backend以P0驗證結果為準，不預設faster-whisper

### P2 — 意圖辨識 / Tool Calling（只驗證JSON，不執行）
- 100個指令測試集，Tool選擇成功率 ≥ 95%
- 這階段可直接用你 AGENTS.md 裡既有的「Claude規劃→Codex執行→互審」流程跑

### P3 — Windows Automation（開始真控制）
- 沿用原藍圖工具清單（open_application/find_file/uia_click等）
- 新增：ARM64版Windows UIA函式庫相容性需在此階段補驗證（許多C#/COM互操作套件在ARM上行為不同於x86）

### P4 — 安全 / 權限分級
- L0~L3沿用原設計，Emergency Stop熱鍵沿用
- 補一條：因為是筆電非桌機，加入「合蓋/待機時自動停止監聽」規則，避免背景誤觸發

### P5 — Vision Fallback
- Qwen3-VL僅在UIA找不到元素時lazy load，沿用原設計不變

### P6 — 完整語音代理人整合測試
- 沿用原KPI：喚醒→ASR < 1.5秒、指令路由 ≥ 95%、整體簡單指令 < 3秒感受延遲
- 因統一記憶體架構，理論上多模型同時常駐的延遲會比傳統獨顯+系統RAM架構更平滑，此為P6要實測驗證的假設，不是既定結論

---

## 4. 與你既有 PAFAS / AGENTS.md house rules 的整合建議

- 這個語音代理人專案可以掛在 PAFAS 九層架構下作為一個「邊緣互動層」模組，而非獨立系統
- 建議比照 `Claude_code_AGENTS` repo的既有模式：本專案也開一個 `plans/queue/done/reviews` 任務板，讓 Claude 規劃、Codex/本地LLM執行、互審的loop可以複用
- 由於這台是ARM機器，AGENTS_install腳本可能需要一個ARM64專用分支，這點在P0報告裡一併記錄

---

## 5. 一句話總結

**64GB Surface Laptop Ultra在記憶體與GPU算力上綽綽有餘，真正的變數是ARM生態成熟度——所以第一步不是選模型，是先花半天到一天做P0相容性驗證，這比選Whisper還是SenseVoice重要十倍。**
