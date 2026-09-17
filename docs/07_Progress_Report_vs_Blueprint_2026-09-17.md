# 進度報告：對照藍圖逐項盤點（2026-09-17）

> 本報告的比對基準：`docs/01_Original_Blueprint_v0.1.md`（原始藍圖，內容最完整，本報告逐節對照的主要對象）
> 與 `docs/03_ClaudeCode_Execution_Blueprint_v0.1.md`（正式採用的執行順序調整版）。
> 寫作原則：**只寫查證過的事實**——每一項「完成」都附上驗證方式跟數字／檔案位置；每一項「落差」都直接承認，不美化、不迴避。
> 資料來源：直接讀取當前 repo 程式碼、`progress/*/REPORT.md`、`progress/*/*.json` 實測結果，以及本次盤點時重新執行的驗證指令。

---

## 目錄

1. [總結（先講結論）](#1-總結先講結論)
2. [Phase 逐項比對（P0～P6）](#2-phase-逐項比對p0p6)
3. [35個工具逐一比對表](#3-35個工具逐一比對表)
4. [藍圖第7節「canonical工具清單」vs 目前35工具表：一個必須誠實面對的落差](#4-藍圖第7節canonical工具清單vs-目前35工具表一個必須誠實面對的落差)
5. [權限分級（L0~L3）比對](#5-權限分級l0l3比對)
6. [Emergency Stop / 語音安全 比對](#6-emergency-stop--語音安全-比對)
7. [Memory（第13節）比對](#7-memory第13節比對)
8. [Logging（第14節）比對](#8-logging第14節比對)
9. [Performance KPI（第17節）逐項比對](#9-performance-kpi第17節逐項比對)
10. [UI（第18節）比對](#10-ui第18節比對)
11. [Project Structure（第15節）比對](#11-project-structure第15節比對)
12. [第20節「第一版不做的事」遵守情況](#12-第20節第一版不做的事遵守情況)
13. [超出藍圖範圍的額外成果（Front Desk / AERIS整合）](#13-超出藍圖範圍的額外成果front-desk--aeris整合)
14. [已知落差總表（按嚴重度排序）](#14-已知落差總表按嚴重度排序)
15. [建議下一步優先順序](#15-建議下一步優先順序)

---

## 1. 總結（先講結論）

| 項目 | 狀態 |
|---|---|
| P0 硬體驗證 | ✅ **PASS**，有完整報告 `hardware_compat_report.json` |
| P1 語音輸入 | ✅ **PASS**，中文辨識率超標，但喚醒詞近似詞誤判率偏高 |
| P2 意圖辨識 | ✅ **PASS**，97.1%（超過95%門檻），但只驗證「單一工具呼叫」，不含多步驟規劃 |
| P3 電腦操作 | 🟡 **部分完成**——35工具表17/35，但藍圖原文第7節的「canonical工具清單」缺了近半（見第4節，這是本報告最重要的發現） |
| P4 安全機制 | 🟡 **核心閉環已通，但周邊未完整**——L0~L3判斷/語音文字雙確認/Emergency Stop都驗證過，但Memory跟Logging兩節的資料表設計跟藍圖要求有明確落差 |
| P5 視覺備援 | ❌ **完全未開始**，0% |
| P6 完整整合 | ❌ **未達成**——目前系統一句話只能對應一個工具呼叫，藍圖P6驗收測試要求的「連續多步驟」（找PDF→開啟→回報檔名）能力完全不存在 |
| 額外成果（藍圖沒要求但已完成） | ✅ Front Desk 聲學工程案例引導對話（語音+文字雙模態）、初學者陪伴介面、雙語系主控台儀表板 |

**一句話總結**：底層地基（P0-P2）扎實且有數據佐證；P3-P4 的「安全可控的單一動作執行」已經是一個能用的系統，並且在今天之前的盤點中修正了兩個真實的安全缺口（Emergency Stop熱鍵設錯、語音停止指令完全沒做）；但**距離藍圖定義的「完整語音代理人」還有兩個結構性缺口沒解決**：(a) 缺乏通用UI Automation原語（uia_click/uia_set_text/list_windows等），導致藍圖P3自己定義的驗收劇本（記事本開→打字→存檔→關閉→重開）從未真正跑過；(b) 完全沒有「一句話拆成多步驟執行」的規劃能力，這是藍圖P6驗收測試的核心要求。

---

## 2. Phase 逐項比對（P0～P6）

### P0 — 硬體與生態相容性驗證

**藍圖要求**（docs/01 第16節）：偵測 Windows/CPU/RAM/GPU/CUDA/Python/麥克風/喇叭，輸出 `hardware_report.json`，PASS/FAIL 驗收，禁止此階段下載大型模型。

**實際狀態**：✅ PASS，有完整報告 `hardware_compat_report.json`（97KB附近的JSON，並非空殼）。關鍵發現：

| 工具鏈 | 結果 | 備註 |
|---|---|---|
| whisper.cpp | ✅ PASS（CPU + CUDA兩條路徑都測過） | GPU路徑用CUDA0(RTX Spark)，總延遲339.96ms，比CPU路徑815.78ms快2.4倍 |
| llama.cpp | ✅ PASS（CUDA） | Qwen2.5-0.5B測試，prompt 1431 tok/s、生成275.7 tok/s，完全GPU常駐 |
| faster-whisper | ❌ FAIL | ctranslate2在win_arm64完全沒有wheel，連PyAV依賴都編譯失敗，**正式排除**，不是「暫緩」 |
| onnxruntime-directml | ❌ FAIL | 無win_arm64 wheel，降級用純CPU版onnxruntime（1.30.0）代替，用於VAD/喚醒詞 |
| NPU | ⚠️ 硬體存在但無法使用 | ACPI\NVDA200A\0 有偵測到，但沒有ARM64 Windows的NPU SDK或ONNX Runtime EP可以呼叫它 |

**與藍圖的差異**：藍圖原本假設x86+獨顯，執行藍圖(docs/03)在P0階段就把這個假設打破，這個判斷被P0報告完整驗證：**確實不能假設x86能跑=ARM能跑**（faster-whisper/onnxruntime-directml雙雙倒下就是證據），whisper.cpp+llama.cpp的「純C++/GGML路線」判斷被證實是對的。

**評級**：✅ PASS，符合藍圖驗收標準（至少一條ASR + 一條LLM路徑成功），且有紮實證據，沒有灌水。

---

### P1 — 語音輸入（VAD + 喚醒詞 + ASR）

**藍圖要求**：Microphone→VAD→Wake word→ASR，先不控制Windows，驗收標準「中文指令成功率 > 95%」。

**實際狀態**：✅ PASS，但細節上有一個誠實的弱項要記錄。

| 子系統 | 數字 | 來源 |
|---|---|---|
| VAD (silero-vad ONNX) | 6ms/次判斷 | 效能忽略不計 |
| 喚醒詞（自訓練「嗨小助理」） | **真實部署路徑88.5%**（23/26） | `progress/p1_wakeword_train/real_inference_result.txt` |
| ASR（whisper.cpp, medium模型） | CER 2.06%（script-normalized）／5.34%（raw） | `progress/p1_asr_bench/summary.json` |
| ASR 延遲（medium模型） | 1.61秒 / 句，real-time factor 0.597 | 同上 |

**藍圖驗收「>95%」怎麼算？** 這裡要誠實分兩件事拆開看：
- 如果指的是「ASR辨識成功率」：medium模型normalized CER只有2.06%（即字元層級97.94%正確），**達標**。
- 如果指的是「喚醒詞觸發成功率」：真實部署路徑88.5%，**未達95%**，而且細看子項：一般語句/持續環境噪音的「不誤觸發」表現接近100%（held-out測試集裡沒誤觸發），問題集中在「近似詞混淆」（例如「嗨小主理」）跟部分正樣本本身沒觸發（testpos_4.wav score僅0.302，低於閾值），這是**訓練資料量不足**造成的已知弱項，`progress/p1_wakeword_train/REPORT.md`裡有記錄，不是新發現。

**與藍圖的差異**：藍圖沒有把「喚醒詞成功率」和「ASR辨識率」分開寫驗收標準（原文只寫「中文指令成功率」），這次盤點刻意把兩者拆開報告，避免用ASR的高分掩蓋喚醒詞的弱項。

**評級**：✅ PASS（整體可用，且用「近似詞需要二次確認」的安全設計彌補喚醒詞弱項），但喚醒詞近似詞辨別力**未達成藍圖隱含的95%高標**，這是一個誠實的已知限制。

---

### P2 — 意圖辨識 / Tool Calling

**藍圖要求**：加入Local LLM，輸出Structured JSON（不執行），100個指令測試集，Tool選擇成功率≥95%。

**實際狀態**：✅ PASS，且超過測試集規模要求。

- 測試集：103句（超過藍圖要求的100句）
- 最終準確率：**97.09%**（`accuracy: 0.970873786407767`），排除歧義句後97.1%（clean 96.84%）——來源 `progress/p2_tool_calling/results_v2_7b.json`
- 過程記錄誠實：第一版只有78.6%，錯誤集中在工具說明混淆（例如「工作管理員」vs「工作排程器」），加強說明跟few-shot後才拉到97%+，`progress/p2_tool_calling/REPORT.md`有完整記錄

**與藍圖的差異（重要）**：藍圖第2節「Executor不接受自然語言Command」、「LLM必須輸出Structured JSON」——這點做到了（`full_pipeline.py`的`SCHEMA`用JSON Schema強制輸出格式）。**但藍圖P2的範圍只到「單一工具呼叫」的分類，沒有測試過「一句話需要拆成多個工具呼叫」的規劃能力**，因為藍圖P2本身的定義也只到這裡（P6才要求"Planner"串起多步驟）。這代表97.1%這個高分是「單步驟意圖分類」的分數，不能直接當成「整體任務規劃成功率」——這個區分在後面P6一節會再展開。

**評級**：✅ PASS，數字紮實可信，但**要注意這個97.1%衡量的範圍比藍圖P6最終要求的「規劃能力」窄很多**。

---

### P3 — Windows Automation（開始真控制）

**藍圖要求**（docs/01第16節）：先支援 `open_application/close_application/focus_window/find_file/open_file/create_folder/move_file/copy_file/uia_click/uia_set_text/hotkey` 這11個工具；驗收劇本：「開記事本→輸入Hello→存檔→關閉→重新打開，整條成功才PASS」。

**實際狀態**：🟡 **部分完成，且驗收劇本從未執行過**。

先看好消息——這11個工具裡，真正等價實作的有：

| 藍圖工具 | 對應目前實作 | 狀態 |
|---|---|---|
| `open_application` | `open_app`（白名單app_name→exe） | ✅ |
| `close_application` | `close_window`（需已知pid） | ✅ |
| `find_file` | `file_op(action=find)` | ✅（今天新增） |
| `open_file` | `file_op(action=open)` | ✅（今天新增） |
| `create_folder` | `file_op(action=create_folder)` | ✅（今天新增） |
| `move_file` | `file_op(action=move)` | ✅（今天新增） |
| `copy_file` | `file_op(action=copy)` | ✅（今天新增） |

再看壞消息——這11個裡剩下4個，**完全沒有實作**：

| 藍圖工具 | 目前狀態 | 說明 |
|---|---|---|
| `focus_window` | ❌ 不存在 | `window_op`只有`minimize/show_desktop/switch_next`三個動作，沒有「切到指定視窗」這個能力 |
| `uia_click` | ❌ 不存在 | 沒有任何一個工具透過UI Automation定位並點擊畫面元素 |
| `uia_set_text` | 🟡 有替代但不等價 | `text_input_op`用`SendKeys`打字到「目前作用中欄位」，這是「盲打」不是「用UIA找到特定欄位再打」——如果焦點不在正確欄位，會打錯地方 |
| `hotkey` | ❌ 不存在 | 沒有一個通用的「送出任意組合鍵」工具給LLM呼叫。註：Emergency Stop內部用`keyboard.add_hotkey`監聽`Ctrl+Shift+F12`，跟「LLM可以呼叫hotkey()送出Ctrl+S」是兩件不同的事，不能互相抵充 |

**驗收劇本核對**：藍圖明文要求「開記事本→輸入Hello→**存檔**→關閉→重新打開，整條成功才PASS」。「存檔」在記事本裡是`Ctrl+S`——這一步**沒有工具可以做**（沒有`hotkey()`或`press_key()`），這次盤點直接搜尋整個repo（`grep -r "存檔\|Ctrl.*S\|uia_click\|uia_set_text\|focus_window\|list_windows\|get_active_window"`），確認除了「Emergency Stop熱鍵」跟純文字說明外，**沒有任何程式碼實作或測試過這個劇本**。

**評級**：🟡 部分完成。目前34工具表上的「17/35」是一個**容易誤導的樂觀數字**——那17個工具大多是「桌面便利功能」（音量/剪貼簿/翻譯/小算盤），跟藍圖P3真正要驗收的「能不能可靠地操作任意App的UI」是兩個不同的能力集合，後者目前是0%。

---

### P4 — Safety / Policy

**藍圖要求**：L0~L3四級判斷，「刪掉Downloads全部檔案」不能直接執行必須要求確認，Emergency Stop必須驗證。

**實際狀態**：✅ 核心閉環已完整驗證，且今天的盤點修正了兩個真實安全缺口。

- L0~L3判斷邏輯：`policy/policy_engine.py`，**未知工具預設視為L3**（比藍圖原文更嚴格的安全設計，藍圖沒有明確要求這點，是額外加上的保守設計）
- 語音確認閉環：L2用自由回答+LLM判斷同意/拒絕，L3強制要求複誦「確認執行」關鍵字，兩者都用**真語音**（非文字模擬）測試過，包括「把Wi-Fi關掉→回答不要→事後查證Wi-Fi真的沒被動到」
- 文字確認閉環：`command_processor.py`+`companion.html`，今天新增並在真實瀏覽器裡測試過L2/L3流程
- Emergency Stop熱鍵：**今天盤點時發現原本設成`ctrl+alt+q`（不是藍圖規定的`Ctrl+Shift+F12`），已修正並用`keyboard.add_hotkey`實測註冊/移除成功**
- 語音停止指令：**藍圖要求的「停止/取消/不要執行」原本完全沒實作，今天盤點時發現並補上**，用真的SAPI合成語音跑真的whisper.cpp驗證：「停止」「不要」「算了」正確識別並中斷；「取消」「不要執行」被誤聽（見下方KPI一節的討論）
- 「刪掉Downloads全部檔案」情境：**目前的`file_op`刻意不支援刪除整個資料夾或批量刪除**（安全設計，見`docs/06`），如果使用者真的這樣說，系統會在L3確認關卡之後、實際執行時因為`delete_file`只接受單一檔案而報錯拒絕——這跟藍圖原文期望的「確認後可以執行批量刪除」不同，是**比藍圖更保守的設計決定**，效果上更安全但功能上更受限，這個取捨沒有明確跟使用者確認過是否可接受

**評級**：🟡 核心機制已通且經過真實測試，但兩個周邊缺口（Memory/Logging，見第7、8節）跟一個未明說的設計取捨（拒絕批量刪除）需要記錄清楚。

---

### P5 — Vision Fallback

**藍圖要求**：Screenshot→Qwen3-VL→GUI understanding，只有UI Automation找不到元素時才用。

**實際狀態**：❌ **完全未開始**。搜尋整個repo沒有任何vision/VLM相關程式碼（唯一符合關鍵字的是`llama.cpp`原始碼庫裡跟建置本身有關的multimodal檔案，跟本專案的功能實作無關）。

**評級**：❌ 0%。這是誠實的現況，不需要多做解釋——而且**因為P3的uia_click等原語都還沒做，P5的「UI Automation找不到元素才觸發」這個前提條件目前也不成立**（沒有UI Automation可以「找不到」，因為根本沒接上）。

---

### P6 — Full Voice Agent（完整整合）

**藍圖要求**：整合Wake Word→Voice→ASR→LLM→Planner→Policy→Tool→Verify→TTS，驗收測試：「找到Downloads裡最新的PDF，打開它，然後把檔名告訴我」——**這是一句話裡包含三個依序動作**（找檔案→開啟→回報）。

**實際狀態**：❌ **未達成，且是結構性缺口，不是「還沒測試」而是「能力本身不存在」**。

現有的`listen_loop.py`/`full_pipeline.py`架構是：

```
一句話 → LLM分類（desktop_control 或 acoustic_engineering） → 如果是desktop_control → LLM輸出「一個」{tool, args} → Executor執行「這一個」動作
```

**沒有Planner這一層**。`full_pipeline.understand()`的Schema明確定義只回傳單一`tool`+`args`（`full_pipeline.py`第33-44行），不是一個動作序列。如果使用者真的說「找到Downloads裡最新的PDF，打開它，然後把檔名告訴我」，目前系統只會嘗試把整句話塞進**一個**工具呼叫，最可能的結果是LLM隨便選一個看起來最相關的工具（例如`file_op(action=find)`），然後就結束了——不會接著自動開啟找到的檔案，也不會執行「打開它」「告訴我檔名」這兩個後續步驟。

**這個缺口沒有被05/06號文件記錄過**，是這次盤點第一次明確指出：**藍圖P6驗收測試需要的「多步驟規劃」能力，在目前的架構設計裡完全不存在**，不是效能不夠或準確率不夠的問題，是這一層（Planner）根本沒有被設計進去。P2階段測的97.1%工具選擇準確率，衡量的是「單一句子對應單一工具」這個窄得多的任務，跟P6要求的複合任務規劃是兩件事。

**評級**：❌ 0%，且是本次盤點裡**優先度最高的架構缺口**（詳見第15節建議）。

---

## 3. 35個工具逐一比對表

> 這35個工具的清單來源是`progress/p2_tool_calling/tools_and_labels_v2.py`（P2階段設計的分類任務標籤），**不是**藍圖docs/01第7節的canonical清單——兩份清單本身就不是同一份，差異在第4節專門討論。這裡先把這35個工具的實作狀態盤點清楚。

| # | 工具 | 風險等級 | 實作狀態 | 備註 |
|---|---|---|---|---|
| 1 | `open_app` | L1 | ✅ 已實作 | 白名單4個app（notepad/calculator/explorer/settings） |
| 2 | `close_window` | L2 | ✅ 已實作 | 今天盤點時從L1修正為L2（對照docs/01第9節） |
| 3 | `get_datetime` | L0 | ✅ 已實作 | |
| 4 | `take_screenshot` | L1 | ✅ 已實作 | |
| 5 | `set_volume` | L1 | ✅ 已實作 | pycaw，已修正靜音旗標bug |
| 6 | `clipboard_op` | L1 | ✅ 已實作 | pyperclip |
| 7 | `window_op` | L1 | ✅ 已實作 | 只支援minimize/show_desktop/switch_next |
| 8 | `media_control` | L1 | ✅ 已實作 | 標準媒體鍵 |
| 9 | `adjust_brightness` | L1 | ⚠️ 已實作但硬體不支援 | WMI介面在這台機器上沒有實例（ARM64+Blackwell混合架構限制），程式碼保留給支援的機器 |
| 10 | `network_toggle` | L2 | ✅ 已實作 | netsh控制Wi-Fi，只支援wifi不支援藍牙 |
| 11 | `calculator` | L0 | ✅ 已實作 | AST白名單運算，非eval |
| 12 | `text_to_speech_op` | L0 | ✅ 已實作 | SAPI |
| 13 | `translate` | L0 | ✅ 已實作 | 借用常駐llama-server |
| 14 | `summarize_doc` | L0 | ✅ 已實作 | 借用常駐llama-server |
| 15 | `text_input_op` | L1 | ⚠️ 已實作但是盲打 | SendKeys打到「目前作用中欄位」，非UIA定位 |
| 16 | `file_op` | L2（delete會升L3） | ✅ 已實作（今天新增） | find/open/move/copy/rename/create_folder/delete七合一，限使用者家目錄，delete進資源回收桶 |
| 17 | `power_op` | L3 | ✅ 已實作（今天新增） | shutdown/restart/sleep/cancel，shutdown/restart實測用排程+取消驗證，sleep只驗證API存在未實際呼叫 |
| 18 | `speech_to_text_op` | L0 | ❌ 未實作 | 概念上跟整條ASR管線重疊，需要重新定義用途（見第15節） |
| 19 | `record_screen` | L1 | ❌ 未實作 | 可考慮用Win+Alt+R（Xbox Game Bar）模擬按鍵實作 |
| 20 | `calendar_op` | L1 | ❌ 未實作 | 刻意跳過：需整合Outlook/其他行事曆軟體 |
| 21 | `reminder_op` | L1 | ❌ 未實作 | 刻意跳過：同上 |
| 22 | `alarm_op` | L1 | ❌ 未實作 | 刻意跳過：同上 |
| 23 | `print_or_scan` | L1 | ❌ 未實作 | 刻意跳過：需印表機/掃描器驅動整合 |
| 24 | `photo_edit` | L1 | ❌ 未實作 | 刻意跳過：需影像編輯軟體整合 |
| 25 | `email_op` | L2（delete/send會升L3） | ❌ 未實作 | 刻意跳過：需信箱服務整合 |
| 26 | `video_call_op` | L1 | ❌ 未實作 | 刻意跳過：需視訊軟體整合 |
| 27 | `cloud_file_op` | L2（delete會升L3） | ❌ 未實作 | 刻意跳過：與「100%離線」原則本質衝突，需要例外決策 |
| 28 | `system_maintenance` | L3 | ❌ 未實作 | 刻意跳過：風險高，Policy已設L3，先不急著補 |
| 29 | `task_scheduler_op` | L2 | ❌ 未實作 | 刻意跳過：同上 |
| 30 | `startup_program_op` | L2 | ❌ 未實作 | 刻意跳過：同上 |
| 31 | `driver_op` | L3 | ❌ 未實作 | 刻意跳過：風險高 |
| 32 | `dev_tool_op` | L2 | ❌ **明確禁止實作** | 等同CLAUDE.md禁止的`execute_any_shell_command()`模式，不會做 |
| 33 | `git_op` | L2（push/merge會升L3） | ❌ 未實作 | 刻意跳過：風險較高 |
| 34 | `get_weather` | L0 | ❌ **明確禁止實作** | 需連網查即時資料，跟「100%離線」核心原則衝突 |
| 35 | `get_exchange_rate` | L0 | ❌ **明確禁止實作** | 同上 |

**統計**：17/35 已實作（48.6%），其中2個有已知限制（`adjust_brightness`硬體不支援、`text_input_op`是盲打非UIA）；3個明確不會做（`dev_tool_op`架構禁止、`get_weather`/`get_exchange_rate`違反離線原則）；剩下15個是「還沒做但可以做」，多數是低優先度的外部服務整合。

---

## 4. 藍圖第7節「canonical工具清單」vs 目前35工具表：一個必須誠實面對的落差

這是本次盤點**最重要的發現**，值得單獨一節說明。

docs/01第7節明文列出的工具清單（原文逐字）：

```
open_application()  close_application()
find_file()  open_file()  move_file()  copy_file()  rename_file()
create_folder()
get_active_window()  list_windows()  focus_window()
uia_click()  uia_set_text()  uia_select()
press_key()  hotkey()
take_screenshot()
read_clipboard()  write_clipboard()
```

總共**19個**工具。這份清單的重點是「Windows UI Automation原語」——目的是讓LLM能夠**安全地操作任意應用程式的畫面元素**，是整個藍圖「Level 1 API優先→Level 2 UIA→...→Level 6 Vision」控制優先順序（docs/01第2節）裡Level 2的具體實作。

但專案實際追蹤進度用的「35工具表」（來自`progress/p2_tool_calling/tools_and_labels_v2.py`），是P2階段為了做「意圖分類」測試而設計的一份**更貼近一般消費型語音助理**的功能清單（音量/鬧鐘/行事曆/翻譯/視訊通話...），跟第7節的UIA原語清單**幾乎沒有重疊**。比對結果：

| 藍圖第7節19個工具 | 在35工具表裡對應誰 | 是否已實作 |
|---|---|---|
| `open_application` | `open_app` | ✅ |
| `close_application` | `close_window` | ✅ |
| `find_file` | `file_op(find)` | ✅ |
| `open_file` | `file_op(open)` | ✅ |
| `move_file` | `file_op(move)` | ✅ |
| `copy_file` | `file_op(copy)` | ✅ |
| `rename_file` | `file_op(rename)` | ✅ |
| `create_folder` | `file_op(create_folder)` | ✅ |
| `get_active_window` | 無對應 | ❌ |
| `list_windows` | 無對應 | ❌ |
| `focus_window` | `window_op`裡沒有這個動作 | ❌ |
| `uia_click` | 無對應 | ❌ |
| `uia_set_text` | `text_input_op`（但是盲打，非UIA） | ⚠️ 不等價 |
| `uia_select` | 無對應 | ❌ |
| `press_key` | 無對應（通用版） | ❌ |
| `hotkey` | 無對應（通用版，Emergency Stop的熱鍵監聽不算） | ❌ |
| `take_screenshot` | `take_screenshot` | ✅ |
| `read_clipboard` | `clipboard_op(paste)` | ✅ |
| `write_clipboard` | `clipboard_op(copy)` | ✅ |

**19個裡實作了12個（63%），完全空白的7個全部集中在「UI Automation操控任意應用程式」這個能力群組**（get_active_window / list_windows / focus_window / uia_click / uia_select / press_key / hotkey）。

**為什麼這件事重要**：目前系統能做的操作，全部侵限於「開發者事先寫死支援的4個app + 系統層級功能（音量/剪貼簿/電源）」，**還沒有辦法對使用者電腦上任意打開的視窗做操作**——例如藍圖範例句「開啟PowerPoint，把這張圖片放進去」，目前完全沒有工具鏈能做到（`open_app`的白名單裡甚至沒有PowerPoint）。這代表P3現在的「17/35」或「12/19」進度數字，衡量的是**便利功能的覆蓋率**，而不是藍圖真正想要的**「通用桌面操作能力」**，兩者不能混為一談。

---

## 5. 權限分級（L0~L3）比對

| 藍圖分類（docs/01第9節） | 藍圖範例 | 目前對應 |
|---|---|---|
| L0 完全安全 | 讀取時間/取得目前程式/搜尋檔案/查看資料夾/查看視窗 | `get_datetime`✅、搜尋檔案(`file_op find`)✅，但「取得目前程式」「查看視窗」（即`get_active_window`/`list_windows`）**沒有對應工具**，這兩個L0動作目前連「能不能自動執行」都無法討論，因為根本不存在 |
| L1 低風險 | 打開程式/切換視窗/播放音樂/開啟檔案 | `open_app`✅、`media_control`✅、`file_op open`✅；「切換視窗」如果指的是`focus_window`（切到指定視窗）**不存在**，如果指的是`window_switch_next`（Alt+Tab下一個）算是部分符合但不精確 |
| L2 可能修改資料 | 移動檔案/修改文件/重新命名/關閉程式 | `file_op move/rename`✅、`close_window`✅（今天修正risk level）；「修改文件」沒有專門工具，只能透過`text_input_op`盲打近似做到 |
| L3 高風險 | 刪除/格式化/安裝軟體/Registry/系統設定/Administrator/付款/密碼/Credential | `file_op delete`✅（單檔+資源回收桶）、`power_op`✅（今天新增）；格式化/Registry/系統設定/安裝軟體/付款/密碼**全部沒有工具**，但因為`system_maintenance`/`driver_op`等工具本身未實作，這些「危險操作」目前實質上是「做不到」而不是「能做但被擋下」——某種意義上更安全，但也代表L3這個等級目前主要驗證過的只有`power_op`跟`file_op delete`兩種 |

**確認事項**：PolicyEngine對「不在權限表裡的未知工具」預設判定為L3（`policy_engine.py`第22-28行），這是比藍圖原文更嚴格的保守設計。

---

## 6. Emergency Stop / 語音安全 比對

| 藍圖要求（第10、12節） | 現況 | 驗證方式 |
|---|---|---|
| `Ctrl+Shift+F12`立即停止 | ✅ 已修正並驗證 | 今天盤點發現原本誤設成`ctrl+alt+q`，修正後用`keyboard.add_hotkey`/`remove_hotkey`實測註冊與移除都成功 |
| 語音「停止」「取消」「不要執行」 | 🟡 已實作，效果因詞彙而異 | 用SAPI合成語音→真的跑whisper.cpp→餵進真實流程測試：「停止」「不要」「算了」三詞ASR正確識別並觸發停止；「取消」被誤聽成「屈臣」、「不要執行」被誤聽成「不要知心」——這是**單字/短詞在沒有前後文脈絡時的ASR辨識限制**（用TTS機器人語音合成，也比真人說話更難辨識），不是`is_stop_command()`邏輯錯誤 |
| Hotkey優先於語音 | ✅ 符合設計原則 | 程式碼註解明確標註「熱鍵才是最高優先級」，語音是次要防線 |
| 避免電視/YouTube/其他人語音誤觸發 | ⚠️ 未做長時間驗證 | 喚醒詞的「一般語句不誤觸發」在held-out測試集裡是100%，但沒有做過藍圖第17節要求的「8小時連續環境噪音」測試 |
| Voice Security流程（Wake→command→ASR→Confidence→validation） | 🟡 部分符合 | Wake→ASR→command流程都有，但「Confidence」這一關（喚醒詞分數本身有，但ASR輸出沒有信心分數判斷）沒有獨立實作，目前的confidence概念只用在喚醒詞閾值上 |

---

## 7. Memory（第13節）比對

**藍圖要求**：只建立5類——Session Context、User Preferences、Known Apps、Known Folders、Command History——存在SQLite，禁止永久保存完整錄音。

**實際狀態**：`src/executor/audit_db.py`目前只有3張表：

```sql
conversation_log   -- 對話紀錄（heard_text/reply_text/asr_model/asr_latency_ms）
action_audit       -- 操作稽核（tool/args/risk_level/user_confirmed/executed/result）
policy_rules       -- 權限規則對照表
```

比對結果：

| 藍圖要求的5類 | 對應現況 |
|---|---|
| Session Context | ❌ 不存在（沒有task/session邊界的概念，每次對話都是獨立事件） |
| User Preferences | ❌ 不存在 |
| Known Apps | ⚠️ 用`KNOWN_APPS`寫死在`basic_tools.py`的Python dict裡，不是資料庫表，不能動態學習新App |
| Known Folders | ❌ 不存在 |
| Command History | ⚠️ `conversation_log`+`action_audit`合起來勉強算是Command History，但缺乏跨表關聯（見第8節） |

**錄音保存原則核對**：✅ 確認`run_asr()`用`tmp_path.unlink(missing_ok=True)`即用即刪，符合「Audio→ASR→dispose」原則，**這條硬性規則有被遵守**。

**評級**：🟡 錄音處理原則正確，但5類記憶模型裡有3類完全缒付、1類是簡陋替代——這部分明顯落後於其他Phase的完成度。

---

## 8. Logging（第14節）比對

**藍圖要求每筆操作記錄**：Timestamp、Voice transcription、Intent、Plan、Tool、Arguments、Permission level、Execution result、Duration、Error。

**實際`action_audit`表欄位**：`ts, tool, args_json, risk_level, required_confirmation, user_confirmed, executed, result_summary`

| 藍圖要求欄位 | 對應現況 |
|---|---|
| Timestamp | ✅ `ts` |
| Voice transcription | ❌ 在`action_audit`裡沒有，要去`conversation_log`另一張表查，兩表**沒有共用ID**串連 |
| Intent | ❌ 不存在（`mode_classifier`的分類結果目前只用在流程分支，沒有落地存到資料庫） |
| Plan | ❌ 不存在（因為第2節已述，目前也沒有Plan這個概念） |
| Tool | ✅ `tool` |
| Arguments | ✅ `args_json` |
| Permission level | ✅ `risk_level` |
| Execution result | ✅ `executed`+`result_summary` |
| Duration | ❌ **完全沒有欄位**，`conversation_log`裡有`asr_latency_ms`但那只是ASR這一段的耗時，不是整個操作（決策+執行）的總耗時 |
| Error | ⚠️ 跟成功訊息混在同一個`result_summary`文字欄位裡，沒有獨立的錯誤欄位或錯誤分類，無法單純查「有哪些失敗」而不用字串比對 |

**評級**：🟡 10個要求欄位裡完整符合5個，2個有實作但混在一起、3個完全沒有。這是這次盤點裡繼「UIA原語缺失」之後第二個明確、具體、可以直接照著修的落差。

---

## 9. Performance KPI（第17節）逐項比對

| KPI | 藍圖目標 | 實測數字 | 達標？ |
|---|---|---|---|
| 喚醒詞誤觸發率 | < 1次/8小時 | **未測過** —— 只有一次12秒的真實麥克風煙霧測試，沒有做過8小時連續監聽測試 | ❓ 無法判斷 |
| 中文ASR CER | < 5%（安靜環境） | medium模型：2.06%（normalized）／5.34%（raw） | ✅ normalized算法下達標，raw算法下**沒達標**（差距0.34%），這個差異取決於「怎麼算CER」，報告誠實列出兩個數字 |
| 指令路由準確率 | ≥ 95% | 97.09%（103句測試集） | ✅ 達標 |
| 工具執行成功率 | ≥ 98% | **未測過** —— 沒有做過「連續N次真實工具呼叫，統計成功/失敗比例」這種獨立量測，過去的測試都是「單次驗證這個工具能不能動」，不是「這個工具穩定跑100次有幾次成功」 | ❓ 無法判斷 |
| Wake→ASR延遲 | < 1.5秒 | 沒有做過這兩點之間的獨立計時（喚醒詞判斷本身是ms級，加上錄音等待安靜的時間會依講話長度變動，沒有統一量測方法論） | ❓ 無法判斷 |
| ASR→Tool決策延遲 | < 2秒 | ASR本身0.34~1.6秒（依模型大小）+ LLM tool-calling約0.2~0.6秒（P2測試數字），**加總約0.5~2.2秒**，medium模型+複雜句子時可能超標，但沒有做過端到端的合併量測 | ⚠️ 估算值邊緣達標，缺乏正式量測 |
| Tool啟動延遲 | < 1秒 | 各工具的實際執行時間差異很大（`get_datetime`幾乎瞬間，`file_op`牽涉磁碟I/O），沒有統一量測 | ❓ 無法判斷 |
| 整體簡單指令感受延遲 | < 3秒 | 沒有做過使用者視角的「說完話到聽到回覆」端到端計時 | ❓ 無法判斷 |

**評級**：8項KPI裡，只有2項（ASR CER、指令路由）有明確數字可以對照，1項（ASR→Tool延遲）只能用零散數字粗估，剩下5項**完全沒有測過**。這跟`docs/06_Frontdesk_Workplan.md`裡標記的🟢「KPI量測不完整」是一致的，但這次盤點把「不完整」具體量化成「8項裡5項是0」，比之前的描述更精確。

---

## 10. UI（第18節）比對

**藍圖要求**：初期不要做漂亮介面，只做簡單Dashboard，5個狀態（Listening/Thinking/Executing/Waiting confirmation/Stopped），顯示ASR text/Current plan/Current tool/Result/GPU-RAM，**P6 PASS後才美化**。

**實際狀態**：這是一個**明確的、已經跟使用者溝通過的刻意偏離**，不是疏漏：
- 使用者在P6遠遠沒PASS的情況下，明確要求要有「給不懂技術的新手用的友善介面」，因此開發了`console/companion.html`（雙語、有onboarding流程、圓圈狀態動畫），這已經超出藍圖第18節「初期只做簡單Dashboard」的範圍
- 目前的狀態模型（`live_state.json`裡的`status`欄位）用的是`idle/wake_detected/listening_command/thinking/speaking/front_desk/not_running`，跟藍圖要求的5態（Listening/Thinking/Executing/Waiting confirmation/Stopped）**不是一一對應**——特別是「Executing」跟「Waiting confirmation」這兩個藍圖明確要求的獨立狀態，目前的實作沒有把它們當成獨立可視化的狀態呈現給使用者（confirmation目前在語音路徑裡是同步等待、沒有寫回`live_state.json`讓UI顯示「正在等你確認」這個畫面）

**評級**：這件事的性質跟其他落差不同——**不是「還沒做」，是「刻意選擇了不同的方向」**，且是使用者本人要求的。但底層藍圖定義的5態模型確實還沒有被完整實作出來，如果之後要補，優先度可以放低（畢竟目前的替代方案已經在用且使用者滿意）。

---

## 11. Project Structure（第15節）比對

藍圖建議的目錄結構包含`config/`（system.yaml/models.yaml/permissions.yaml/tools.yaml）、`tests/`（分unit/integration/voice/tools/security五個子目錄）、`models/`、`scripts/`、頂層`run_agent.py`。

**實際狀態**：目前專案結構是`src/`（含`frontdesk/`、`executor/`、`policy/`、`tools/`子模組）+ `console/` + `progress/`（依Phase分資料夾）+ `docs/`，**沒有**`config/`（所有設定寫死在Python檔案裡，例如`risk_levels.py`的`TOOL_RISK_TABLE`、`basic_tools.py`的`KNOWN_APPS`）、**沒有**獨立`tests/`目錄（測試檔案`test_*.py`直接散落在`src/`跟`src/frontdesk/`底下）、**沒有**`models/`（模型放在`progress/p1_wakeword_train/`跟whisper.cpp/llama.cpp各自的目錄裡）、**沒有**單一入口`run_agent.py`（`listen_loop.py`扮演這個角色但命名不同）。

**評級**：這是**結構性的偏離**，不影響功能，但如果專案繼續變大，缺乏`config/`會讓「使用者想調整權限規則卻要改Python原始碼」這件事變得不友善（跟這個專案「新手友善」的目標其實有點矛盾）。優先度中等，可以考慮之後把`TOOL_RISK_TABLE`跟`KNOWN_APPS`這類「使用者可能想自己調整」的設定移到YAML檔案。

---

## 12. 第20節「第一版不做的事」遵守情況

藍圖明確列出v0.1不該做的事：Cloud / Remote control / Web service / Mobile App / Long-term autonomous agent / Multi-agent / 100個AI Agent / Avatar / Fancy UI / Full RAG / Internet search / Self-modifying code。

逐項核對：

| 禁止項目 | 是否違反 |
|---|---|
| Cloud | ✅ 沒違反，`get_weather`/`get_exchange_rate`因為需要連網被明確禁止實作，正是為了守住這條線 |
| Remote control | ✅ 沒違反，`console/serve.py`只綁定`127.0.0.1` |
| Web service | ⚠️ 灰色地帶——`console/serve.py`技術上是一個本機HTTP伺服器，但只服務本機瀏覽器，精神上不算對外Web service |
| Mobile App | ✅ 沒有 |
| Long-term autonomous agent | ✅ 沒有，每次都是單次對話 |
| Multi-agent | ✅ 沒有 |
| Avatar | ✅ 沒有 |
| Fancy UI | ⚠️ 見第10節討論，`companion.html`比藍圖原本設想的「簡單Dashboard」漂亮不少，但是使用者明確要求的 |
| Full RAG | ✅ 沒有 |
| Internet search | ✅ 沒有 |
| Self-modifying code | ✅ 沒有 |

**評級**：整體遵守良好，兩個灰色地帶（本機web service、UI比預期漂亮）都是有意識的、可解釋的決定，不是失控的scope creep。

---

## 13. 超出藍圖範圍的額外成果（Front Desk / AERIS整合）

這部分**不在**docs/01原始藍圖的討論範圍內（藍圖是純粹的桌面代理人設計），是這個專案在執行過程中，因為要跟旁邊的AERIS聲學工程專案互動，額外長出來的能力，值得在報告裡完整記錄，因為它的完成度其實比藍圖本身的P3-P6都高：

- `dialog_state_machine.py`：S0(CAPTURE)→S8(ORDER_LOCKED)完整9狀態機，端到端測試通過
- `voice_dialog.py`：把上面的文字版問答邏輯接上真的語音輸入輸出（SAPI TTS + whisper.cpp ASR），用3句預先合成的語音模擬完整走完三輪問答，真的產生`ORDER.md`並寫進交接資料夾
- `command_processor.py`：今天新增的文字版對應實作，讓不方便講話的使用者也能用打字完成整個引導流程
- 這條路徑**已經做到了藍圖P6想要的「多步驟」效果**——只是範圍限定在「聲學工程問題引導」這個單一場景，不是通用的桌面操作多步驟規劃。某種意義上，這是一個「規劃能力」的局部原型，如果要補P6的Planner，這裡的狀態機設計經驗可以直接參考。

---

## 14. 已知落差總表（按嚴重度排序）

| 嚴重度 | 落差 | 影響範圍 | 是否今天新發現 |
|---|---|---|---|
| 🔴 極高 | P6要求的「多步驟規劃」能力完全不存在（第2節P6、第3節97.1%的範圍限制） | 藍圖最終驗收測試無法執行 | ✅ 本次盤點首次明確指出 |
| 🔴 高 | 藍圖第7節UIA原語（uia_click/uia_set_text/focus_window/list_windows/get_active_window/press_key/hotkey）7個裡6個完全空白 | P3自己定義的驗收劇本（記事本開→打字→存檔→關閉→重開）無法執行；「開啟PowerPoint放圖片」這類藍圖範例句完全做不到 | ✅ 本次盤點首次明確指出 |
| 🟡 中 | Memory（第13節）5類裡3類不存在 | 無法做到「記住使用者偏好」「認識常用資料夾」這類藍圖期望的基礎記憶功能 | 部分已知（`docs/06`提過logging缺共同ID，但沒明確拆到Memory章節這麼細） |
| 🟡 中 | Logging（第14節）10欄位裡3欄位完全缺失、2欄位混雜不分 | 出問題時無法單純從資料庫查出「Intent/Plan是什麼、花了多久、錯誤訊息是什麼」 | 部分已知 |
| 🟡 中 | KPI（第17節）8項裡5項完全沒測過 | 不知道系統是否真的達到藍圖定義的「可用」標準（尤其8小時誤觸發率跟98%工具執行成功率這兩項是安全/可靠性關鍵指標） | 部分已知（`docs/06`提過但沒拆這麼細） |
| 🟢 低 | Project Structure（第15節）沒有`config/`外部化設定 | 使用者無法不改程式碼就調整權限規則/白名單App清單 | ✅ 本次盤點首次指出 |
| 🟢 低 | 語音停止指令對單字詞彙（取消/不要執行）辨識不穩定 | 使用者講這兩個詞可能沒被正確中斷（但講「停止」「不要」「算了」沒問題，且Hotkey仍是最高優先保底） | 上次session已發現並記錄 |
| 🟢 低 | UI 5態模型（第18節）跟藍圖定義不完全一致 | 主要是「Waiting confirmation」沒有獨立可視化狀態 | 上次session已發現並記錄 |
| 🟢 低 | `file_op`刻意不支援批量刪除，跟藍圖範例「刪掉Downloads全部檔案」的期望行為不同 | 使用者若真的這樣講，會被系統拒絕而不是要求確認後批量執行——更安全但功能更受限，這個取捨沒明確跟使用者確認過 | ✅ 本次盤點首次指出 |

---

## 15. 建議下一步優先順序

1. **補UIA原語**（對應第4節、第14節🔴🔴兩項）——`get_active_window`/`list_windows`/`focus_window`/`uia_click`/`uia_set_text`（真UIA版）/`uia_select`/`press_key`/`hotkey`。這是解開P3驗收劇本跟P5前提條件的關鍵，Python生態裡`pywinauto`（已經在專案裡用於`close_app_by_pid`）跟`uiautomation`套件都能做到，技術上不是新問題。
2. **設計一個最小可行的Planner**（對應P6缺口）——不需要一次做到藍圖範例句的完整泛化能力，可以先讓LLM輸出一個「工具呼叫陣列」而不是單一`{tool,args}`，Executor依序執行並在每一步之間檢查Policy，這是從現有架構最小改動就能邁向P6的路徑。Front Desk的狀態機設計經驗可以參考。
3. **補Memory的3個缺失表**跟**Logging的3個缺失欄位**——這兩項改動範圍小、風險低、能直接提升「出問題時能不能查清楚」的能力，適合當作補完P4周邊的維護性工作。
4. **做一次完整的KPI量測**——尤其8小時喚醒詞誤觸發率跟98%工具執行成功率這兩項，是安全性/可靠性的關鍵訊號，目前完全是空白。
5. 其餘（`config/`外部化、剩下15個未實作的35工具表項目）優先度較低，可以視需求排入。

---

*報告產出時間：2026-09-17。方法論：重新完整讀取`docs/01`全文、對照目前程式碼實際內容（非憑印象），逐節列表比對，所有數字均來自`progress/`底下的實測結果檔案或本次盤點時重新執行的驗證指令，沒有引用未經查證的估計值當作事實陳述。*

---

## 後續更新（2026-09-17，同一天）

第4節指出的「7個UIA原語空白」缺口，已經動工補上其中8個工具（`get_active_window`/`list_windows`/`focus_window`/`uia_click`/`uia_set_text`/`uia_select`/`press_key`/`hotkey`），詳細實作跟真實測試記錄見`docs/06_Frontdesk_Workplan.md`「補齊藍圖第7節UIA原語」一節。簡短更新：

- ✅ 已實測驗證：`get_active_window`、`list_windows`、`focus_window`（過程中抓到並修正`SetForegroundWindow`焦點竊取保護的真實限制）、`uia_click`、`press_key`、`hotkey`
- ⚠️ 已實作但未獨立實測：`uia_set_text`、`uia_select`——跟已驗證的`uia_click`共用同一套連線/定位邏輯，但這次沒找到安全的可編輯欄位測試對象（UWP記事本在這個環境起不來，File Explorer裡的可編輯欄位牽涉真實專案檔案，風險太高沒有嘗試）
- 第3節、第4節的比對表仍保留原始盤點時的數字（12/19），**不回頭改動歷史記錄**，這裡只做狀態更新——目前藍圖第7節19個工具的真實完成度已經是**18/19**（只剩`rename_file`以外的部分都補齊，實際上`rename_file`早就有了，19個裡現在只缺0個核心工具存在性問題，但`uia_set_text`/`uia_select`仍缺獨立實測證據，嚴謹起見不升級成完全的✅）
- P3自己定義的驗收劇本（記事本開→打字→存檔→關閉→重開）**仍然沒有執行過**——不是工具不存在了，是這次的環境限制（UWP記事本起不來）擋住了這個特定劇本，需要換一台能正常啟動UWP應用程式的機器，或用別的文字編輯器重新設計這個驗收劇本

### 2026-09-17 第二次更新：P6「多步驟規劃」缺口也補上了最小可行版本

第2節指出的「完全沒有Planner，一句話只能對應一個工具呼叫」缺口，已經在`full_pipeline.py`加了`PlanRunner`（詳細設計跟真實測試記錄見`docs/06`「補上最小可行的多步驟規劃能力」一節）。簡短更新：

- ✅ **端到端真實驗證通過**：用藍圖P6範例句的同一種結構（「找到X資料夾裡最新的Y檔案，打開它，然後把檔名告訴我」）連續測試4次，每次都正確：先找到真正最新的檔案（不是瞎猜路徑）、用真實找到的路徑打開它、正確回報檔名——這證明「依賴前一步真實結果決定下一步參數」這個P6的核心能力現在是真的做到了，不是紙上設計。
- ⚠️ **範圍仍然有限**：只驗證過一種具體的三步驟場景，還沒測過更複雜的分支（步驟失敗如何恢復、規劃中途需要使用者補充資訊等）；小型本機LLM對「該拆成幾步」的判斷穩定性是靠三輪提示詞調整才收斂，換一種問法的複合指令有可能需要重新調校，不能假設任意複合指令都能一次成功。
- 第2節的原始評級「❌ 0%，且是結構性缺口」**已經過時**，目前正確的狀態是「🟡 最小可行版本已驗證，但覆蓋範圍跟穩定性都還有限」。
- 過程中額外抓到並修正兩個真實bug：(1) llama.cpp的JSON Schema轉GBNF語法有個限制——開放式object欄位(`"args":{"type":"object"}`)後面不能接其他必填欄位，否則LLM會產生格式錯誤的輸出後接亂碼，這是實測抓到的真實限制不是猜的；(2) `file_op`原本整個工具都設L2確認等級，導致純唯讀的「find」步驟也要求確認，修正成依動作分級（find/open是L1、move/copy/rename/create_folder是L2、delete是L3），更貼近藍圖第9節原意。

### 2026-09-17 第三次更新：Memory（第7節）跟 Logging（第8節）的資料表缺口也補上了

第7節指出的「Memory 5類裡3類不存在」、第8節指出的「Logging 10欄位裡3個缺、2個混雜」，已經在`executor/audit_db.py`補上（詳細設計跟真實測試記錄見`docs/06`「補齊 Memory 跟 Logging 的資料表缺口」一節）。簡短更新：

- ✅ **Logging**：`action_audit`新增`session_id`/`intent`/`duration_ms`/`error`四個原本缺的欄位，`conversation_log`新增`session_id`跟它join。第8節原文評級「🟡 10個要求欄位裡完整符合5個」**已過時**，目前是完整符合9個（只缺「Plan」——多步驟任務的完整規劃紀錄目前只存在`PlanRunner`的執行過程裡，沒有落地存進資料庫，這點還沒做，見下方限制）。
- ✅ **Memory**：新增`known_apps`/`known_folders`/`session_context`/`user_preferences`四張表，對應原本評級「🟡 5類裡3類不存在」提到的缺口。`user_preferences`表已建好但還沒有任何功能真的讀寫它，屬於基礎建設先準備好。
- ⚠️ **意外抓到的真實bug**：查資料庫實測才發現`conversation_log`表存在但**一直是0筆資料**——`log_conversation()`函式定義了卻從來沒有任何地方呼叫過，藍圖要求的「對話紀錄」這個記憶類別形同沒做。已修正並接到語音跟文字兩條路徑。這代表第7節原本寫「Command History勉強算是Command History」這句話**過譽了**——當時沒有實際查詢資料庫驗證表裡有沒有真的資料，只看了schema定義就判斷「有做」，這是本次盤點自己抓到自己先前的判斷疏漏，一併誠實記錄。
- ⚠️ **另外抓到並修正一個真實bug**：修這個功能時發現`PlanRunner.resume()`原本會錯誤地讓語音路徑已經驗證過的L3確認被打回拒絕（詳見`docs/06`）。
- 第14節KPI相關的「Duration」量測現在有資料庫記錄可查了，但**還沒有做成統計報表**（例如「工具執行成功率98%」這種聚合指標），第9節KPI評級的「5項完全沒測過」目前**沒有變化**，只是多了原始資料可以之後拿來算。

### 2026-09-17 第四次更新：KPI量測補上2項（工具執行成功率、ASR→Tool決策延遲）

利用上一次更新剛補上的`duration_ms`資料，寫了`progress/p4_kpi_measurement/run_kpi_test.py`
真的跑了20句涵蓋17個已實作工具的指令（完整方法論跟原始資料見該資料夾`REPORT.md`）。結果：

- ✅ **工具執行成功率**：100%（20/20），達標（目標≥98%）
- ✅ **ASR→Tool決策延遲**：p95 1.13秒，平均0.64秒，達標（目標<2秒）——量測時刻意把「工具
  本身執行要花多久」（例如唸一句話的時間跟句子長度成正比，不是延遲問題）跟「LLM決策要花
  多久」分開算，避免把兩種不同性質的時間混為一談
- 第9節「8項裡只有2項有數字、5項完全沒測過」**已過時**，目前是4項有正式數字（ASR CER、
  指令路由準確率、工具執行成功率、ASR→Tool決策延遲），4項仍待測（喚醒詞8小時誤觸發率、
  Wake→ASR延遲、Tool啟動延遲、整體感受延遲）——**喚醒詞誤觸發率需要真的連續監聽8小時，
  這次沒有跑，是唯一需要長時間背景執行才能測的一項，留到有更長的施工時間窗口再處理**。

### 2026-09-17 第五次更新：UI五態模型補上了，順便抓到兩個先前遺漏的真實bug

第10節指出的「Executing/Waiting confirmation沒有獨立可視化狀態」已經在`listen_loop.py`加了`CANONICAL_STATE_MAP`補上（詳細設計見`docs/06`「補上UI五態模型」一節），`companion.html`也視覺化驗證過。

- ✅ 第10節評級**已過時**，目前`live_state.json`每筆狀態都會帶`canonical_state`欄位，正確對應藍圖第18節要求的5態，包含原本缺的Executing跟Waiting confirmation。
- 🔴 **意外抓到一個嚴重bug，需要特別記錄**：修這個功能時發現`run_live()`（真的接麥克風時在用的那份事件處理邏輯）的`action_result`事件處理還在用第2次更新（PlanRunner整合）之前的舊格式，會在真實使用時直接丟`KeyError`崩潰——**這代表從PlanRunner整合完成到這次修復之間，如果真的對著麥克風講一句話讓desktop_control執行完，語音助理會當掉**。這個bug之所以沒被先前的回歸測試抓到，是因為所有單元測試都直接呼叫`handle_utterance()`帶自訂的`on_event`，沒有一個測試真的走過`run_live()`這條路徑——這是本次盤點方法論上的一個教訓：**改動事件格式時，要檢查所有消費那個事件的地方，不能只靠「單元測試通過」就假設沒事**，因為單元測試自己重新定義了一份簡化的`on_event`，繞過了正式程式碼路徑。
- ⚠️ 另外也發現`stopped_by_voice`事件在`run_live()`裡完全沒被處理，使用者講「停止」後畫面不會更新——已一併修正。

### 2026-09-17 第六次更新：config/ 外部化設定補上了

第11節指出的「沒有`config/`資料夾，權限規則寫死在Python檔案裡」已經補上（詳細設計跟安全驗證記錄見`docs/06`「config/ 外部化設定」一節）。簡短更新：

- ✅ 新增`config/permissions.yaml`（35個工具風險等級）跟`config/tools.yaml`（App白名單），`src/config_loader.py`統一讀取，載入失敗一律直接丟例外（安全關鍵資料不能悄悄退回預設值）
- ✅ 逐一比對YAML載入後的資料跟改動前的硬編碼資料**完全一致**，沒有任何風險等級意外跑掉；既有回歸測試正常通過
- 第11節評級「🟢低優先度」的這項缺口**已解決**，第15節Project Structure比對表裡「沒有`config/`」這一條**已過時**——不過`config/`目前只有`permissions.yaml`跟`tools.yaml`兩個檔案，藍圖第15節原本建議的`system.yaml`/`models.yaml`還沒有對應需求（目前沒有需要外部化的系統層級或模型層級設定），不是遺漏，是還沒有東西需要放進去
- 這是這次盤點連續第三輪修完手上功能又意外抓到真實bug之後，第一輪**沒有踩到新bug**的施工——過程單純的YAML語法問題（`ms-settings:`結尾冒號需要加引號）算是最輕微的一種踩坑

### 2026-09-17 第七次更新：補上`speech_to_text_op`（35工具表 17/35 → 18/35）

第3節工具比對表裡`speech_to_text_op`從❌改成✅（詳細設計跟安全反思見`docs/06`「P3工具擴充第四批」一節）。簡短更新：

- ✅ 重用P0/P1已驗證的whisper.cpp medium模型，端到端測試用真的錄音檔驗證轉錄正確
- ⚠️ **實作過程中自己抓到並修正一個安全設計問題**：一開始套用`open_file`的寬鬆路徑處理邏輯，寫完後重新檢查才意識到不適用——`speech_to_text_op`會把檔案內容（轉錄文字）回傳到對話紀錄裡，風險層級應該比照`file_op`的`move`/`copy`用嚴格的家目錄邊界，不是`open_file`那種只是「請作業系統打開」的寬鬆處理。這次是自己在寫完之後複查發現的，不是外部測試才抓到，記錄下來作為「新工具要對照類似風險層級的既有工具，不能只挑最順手的那個複製」的教訓。

**關於8小時喚醒詞誤觸發率測試（第9節仍缺的KPI）**：這次盤點評估後**刻意選擇不自主啟動**——這項測試需要真的無人值守跑8小時連續麥克風監聽，而且L0/L1指令（例如誤聽成「現在幾點」）會自動執行不需確認，8小時內累積下來有機率讓系統在使用者不知情的情況下對電腦做出非預期的真實操作（即使都是低風險動作）。這超出了「持續施工」這個授權的合理範圍，需要使用者明確知情並同意才啟動，不屬於這次自主迴圈施工的範圍。

### 2026-09-17 第八次更新：補測2項延遲KPI，其中兩項都測出真實沒達標

用真的語音路徑（喚醒詞+VAD+ASR+PlanRunner，不是文字輸入）量測第9節剩下的`Wake→ASR延遲`跟`整體端到端延遲`（完整方法論跟數字見`docs/06`「補測2項延遲KPI」一節、`progress/p4_kpi_measurement/REPORT.md`）。**這是這次盤點裡第一次出現「測出來不達標」的KPI，誠實記錄，沒有為了報告好看調整量測方法論**：

- ❌ **Wake→ASR延遲**：目標<1.5秒，實測**5.38~5.42秒**（3次測試都穩定，不是單次異常值）
- ❌ **整體端到端延遲**：目標<3秒，實測**6.08~6.11秒**

**找到明確、可重現的結構性原因，不是效能問題**：拆解後發現光是VAD端點偵測（判斷「使用者講完話了」）的固定安靜等待時間，就佔了整段延遲裡結構性的1秒以上，這是P1階段刻意的安全設計（縮短緩衝期會誤判使用者話還沒講完就提早切斷），真正的ASR轉錄時間（約1.5秒）符合P1階段量測的正常範圍，問題不在ASR。

**這代表**：第9節KPI比對表的評級**已過時**——目前8項KPI裡有**6項有正式數字**（ASR CER、指令路由準確率、工具執行成功率、ASR→Tool決策延遲、Wake→ASR延遲、整體端到端延遲），但**新增的2項都不達標**，且是可重現的架構性限制，不是測量誤差或還沒優化。要讓這兩項達標，需要重新設計端點偵測策略（例如縮短VAD安靜確認的等待時間），但這會直接跟P1階段已經記錄過的踩坑（縮短緩衝期會誤切斷使用者說話）衝突，是需要重新權衡的架構決策，不是單純調參數。剩下2項未測：喚醒詞8小時誤觸發率（需要使用者授權）、Tool啟動延遲（這個架構沒有獨立的派工環節可以測，說明見`docs/06`）。

### 2026-09-18 第九次更新：補上`record_screen`（35工具表 18/35 → 19/35），意外抓到環境限制的另一個例子

第3節工具比對表裡`record_screen`從❌改成✅（用Windows內建Xbox Game Bar的`Win+Alt+R`快捷鍵實作，詳見`docs/06`「P3工具擴充第五批」一節）。這是35工具表裡最後一個「沒有被刻意排除、單純還沒做」的工具，補完之後，剩下未實作的15個工具全部都是有明確理由跳過的（需要外部服務整合、違反離線原則、或明確禁止的萬用執行模式）。

- ✅ 工具實作、LLM路由、Executor執行三層都驗證正確（熱鍵正確送出、`hotkey()`機制本身已經在補UIA原語時用小畫家驗證過）
- ⚠️ **在這台機器上沒辦法拿到「錄影檔案真的產生了」的完整端到端證據**——Xbox Game Bar本身也是MSIX封裝的應用程式，跟本報告第2節記錄過的「這個工作環境UWP應用程式起不來」是同一類環境限制，不是新發現的問題，是既有環境限制的又一次驗證。這進一步支持第2節的結論：**這個特定執行環境（而不是程式碼本身）對UWP/MSIX應用程式有系統性的相容性問題**，換一台能正常執行UWP應用程式的機器，這個工具、以及P3驗收劇本（記事本開→打字→存檔→關閉→重開）都應該能真正跑通。
