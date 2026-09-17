# P0 驗收報告 — 硬體與生態相容性驗證

**日期**: 2026-09-13
**結論**: ✅ **PASS** — 可進入 P1

## 驗收標準對照

> 至少一條 ASR 路徑 + 一條 LLM 推論路徑成功跑通

- ASR：**whisper.cpp（CUDA GPU，Blackwell）** ✅
- LLM：**llama.cpp（CUDA GPU，Blackwell）** ✅

兩條都通過，且應使用者「盡量榨乾 GPU、CPU 留給 AERIS」的要求，**ASR 跟 LLM 都已改成完整跑在 GPU 上**（whisper.cpp 原本先驗證 CPU 版可行，後續重編 CUDA 版確認 GPU 加速有效）。

## 逐項結果

| 工具鏈 | 狀態 | 備註 |
|---|---|---|
| whisper.cpp | ✅ PASS | **CUDA GPU**，using CUDA0 backend，encode 604ms→77.9ms（CPU→GPU），JFK 樣本轉錄正確 |
| llama.cpp（CUDA backend） | ✅ PASS | Qwen2.5-0.5B 完整跑在 GPU（sm_121a Blackwell），275.7 tok/s |
| faster-whisper | ❌ FAIL | 依賴的 ctranslate2 在 win_arm64 完全沒有 wheel，此路線排除 |
| onnxruntime-directml | ❌ FAIL | win_arm64 無 wheel；退回測試純 onnxruntime CPU EP，成功 |
| onnxruntime-gpu (CUDA EP) | ❌ FAIL | 同上，win_arm64 也無 wheel |
| NPU (`ACPI\NVDA200A\0`) | ⚠️ 存在但無法用 | Windows 認得到，但沒有獨立 NPU SDK，也沒有任何 ONNX EP 能連到它。待 NVIDIA 出對應軟體再回頭處理，非阻塞項 |

### GPU / NPU 使用原則（使用者指示）
- ASR + LLM（最耗算力的兩塊）：**GPU（CUDA）**，已完整驗證
- VAD / 喚醒詞：建議留 CPU——模型極小、CPU 佔用率可忽略，硬塞 GPU 反而因搬資料開銷可能更慢，且省下的 CPU 對 AERIS 沒有實質意義
- NPU：目前無可用軟體介面，暫緩

完整數據見同目錄 `hardware_compat_report.json`。

## 關鍵工程發現（P1 之後會用到）

1. **ggml CPU backend 必須用 clang-cl**，MSVC(cl.exe) 會直接被 ggml 的 CMake 擋掉（ARM NEON intrinsics 不支援）。
2. **CUDA (.cu) 編譯的 host compiler 必須用 cl.exe**，clang-cl 會被 nvcc 拒絕（"Host compiler targets unsupported OS"）。這跟第1點剛好相反，所以 llama.cpp 的 build 是混合 toolchain：C/CXX 用 clang-cl，`CMAKE_CUDA_HOST_COMPILER` 用 cl.exe。
3. **GGML_OPENMP 目前關閉**：這台機器只裝了 debug 版的 `libomp140d.aarch64.dll`，沒有 release 版，開 OpenMP 會導致 exe 啟動時 DLL not found (0xC0000135)。之後若要開 OpenMP 需另外處理 VC redist ARM64 元件。
4. **faster-whisper / ctranslate2 路線正式排除**，不用再嘗試，全部語音辨識走 whisper.cpp。
5. **onnxruntime-directml 在 ARM64 不存在**，若之後真的需要 ONNX GPU 推論，要評估 QNN Execution Provider（NPU）或乾脆放棄 ONNX GPU 路線。

## 建置產物位置（未納入 git，僅本機）

- `progress/p0/build/whisper.cpp/` — whisper.cpp 原始碼 + build 產物 + tiny.en 模型
- `progress/p0/build/llama.cpp/` — llama.cpp 原始碼 + build 產物 + Qwen2.5-0.5B 測試模型
- `progress/p0/venv-arm64/` — Python ARM64 venv（faster-whisper 測試失敗殘留 + onnxruntime CPU 測試成功）
- 各項 build/inference log：`progress/p0/*.log`

> 這些是驗證用的暫存產物，不是正式產品程式碼，之後 P1 開工時會用正式的專案結構重新組織（例如搬到 `src/asr/`、`src/llm/`），不會直接繼續用這堆測試資料夾。

## 已知待處理事項（非 P0 阻塞項，但要記住）

- **[README.md](../../README.md) 裡有沒解決的 git merge conflict 標記**（`<<<<<<< HEAD` / `>>>>>>>`），內容被直接 commit 進去了，需要清理。
- P0 的驗證產物（venv、下載的模型、build 目錄）目前都在 `progress/p0/`，尚未加 `.gitignore`，正式 commit 前建議排除這些大檔案。

## 下一步

可以開始 P1（VAD + 喚醒詞 + ASR，不控制 Windows），ASR backend 固定用 whisper.cpp，不用 faster-whisper。
