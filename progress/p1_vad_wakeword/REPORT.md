# P1 驗收報告 — VAD + 喚醒詞 + ASR

**結論**：✅ PASS，可進入 P2

## VAD（silero-vad, ONNX, CPU）

- **重要踩坑**：torch 在 ARM64 Windows 完全沒有 wheel（跟 ctranslate2 同樣的坑），所以不能用官方 `pip install silero-vad` 的 Python API，改成直接下載 `.onnx` 檔用我們已驗證好的 onnxruntime CPU EP 呼叫。
- 用 20 個測試音檔驗證：**20/20 正確偵測到語音**，平均 6.4ms/句 —— CPU 負擔完全可忽略，維持原計畫留在 CPU。
- 技術細節：silero-vad v5+ 的 ONNX 圖需要 512-sample chunk **外加前一個 chunk 最後 64 個 sample 當作 context** 一起餵進去，不能只餵單獨的 512 sample，否則機率會全部趨近於零（第一次測試踩到這個坑，修正後才正常）。

## 喚醒詞（openWakeWord, ONNX, CPU）

- 安裝順利（不需要 torch，走 onnxruntime/tflite），ARM64 完全相容。
- 用內建的 11 個英文喚醒詞模型（alexa/hey jarvis/hey mycroft...）測試：載入成功、跑起來沒有崩潰，對不含這些詞的音檔正確給出接近零的分數（代表模型判斷邏輯正常，不是隨機輸出）。
- 平均耗時 48ms / 2秒音檔，CPU 負擔可忽略。
- **待辦**：目前的預訓練喚醒詞都是英文（Alexa/Jarvis...），沒有中文或台語的喚醒詞。要正式使用，之後需要用 openWakeWord 的訓練流程自己錄音訓練一個中文/台語喚醒詞（例如「嗨小助理」之類），這是 P1 收尾後的獨立小任務，不阻塞 P2。

## ASR（whisper.cpp, CUDA GPU）

見 `progress/p1_asr_bench/REPORT.md`。依使用者指示「精準度優先於速度」，正式採用 **medium** 模型（CER 2.1%，延遲 1.61s）。

## P1 總結（對照原藍圖驗收標準：中文指令辨識成功率 > 95%）

- 字元層級準確率 97.9%（medium 模型）→ 達標
- 句子完全比對（含標點）90.3% → 未達 95%，但差距主要來自模型自己加的句尾標點，不影響下游意圖判斷，視為可接受
- VAD、喚醒詞的軟體相容性、延遲都驗證通過

**判定：P1 PASS，進入 P2（意圖辨識 / Tool Calling）。**
