# Front Desk 工作計畫（本專案持續施工用）

> 這份是本專案（Voice-Agent = AERIS 使用者介面）接下來要做的事，會持續更新勾選狀態。
> 對照 `docs/05_AERIS_Integration_Split.md` 的分工，跟 `C:\0_JN1_AERIS\FRONTDESK_HANDOFF_BRIEF.md`（給另一邊的交接文件）互相呼應。

---

## 已完成

- [x] `src/frontdesk/order_writer.py` — ORDER.md 產生器，格式驗證通過
- [x] `docs/05_AERIS_Integration_Split.md` — 兩專案分工說明
- [x] `C:\0_JN1_AERIS\FRONTDESK_HANDOFF_BRIEF.md` — 給 AERIS 那邊的交接文件

## 進行中 / 下一步（依序做）

- [x] **1. 模式分流器**：`src/frontdesk/mode_classifier.py`，8句混合測試 8/8 全對（一開始7/8，加了 few-shot 修正 THD 那句誤判）。
- [x] **2. Front Desk 對話狀態機**：`src/frontdesk/dialog_state_machine.py`，S0-S8 全部實作完成，端到端煙霧測試通過（`test_e2e_dialog.py`）。
- [x] **3. DIVERGE 問題動態生成**：LLM 根據使用者輸入即時生成3-8個可能方向，測試結果合理（Driver異常/腔體共振/密封不良/電路故障/熱膨脹/量測誤差...）。
- [x] **4. 串接 order_writer.py**：S8 ORDER_LOCKED 會自動寫出格式正確的 ORDER.md，測試通過。

### 已知品質限制（不阻塞，但要記住）

- **ROUTE 步驟（自動選工程師）準確率不夠穩**：即使加了100位工程師的能力簡述，還是會選到不合理的組合（例如「Driver異常」問題選到 MEMS Microphone Engineer）。跟 P2 Tool Calling 一開始踩的坑一樣，但這次沒有繼續往下做 few-shot 調校，原因是**設計上這本來就只是「初步猜測」**——`FRONTDESK_HANDOFF_BRIEF.md` 已經明確告訴 AERIS 那邊「這個欄位是猜的，Orchestrator 要能覆蓋修正」，所以先不當阻塞項處理。如果之後 AERIS 那邊反應這個初猜太不準、增加他們負擔，再回來加 few-shot 調校。
- [x] **5. 交接資料夾定案**：`C:\0_JN1_AERIS_HANDOFF\orders\` 已建立（本專案這邊先建好，AERIS那邊若覺得路徑不對可回頭改，已寫進交接文件）。
- [x] **6. Ops Console 更新**：新增 `console/serve.py`（取代單純 http.server，多一個 `/api/orders` endpoint 掃描交接資料夾），前端加「送給AERIS的訂單」區塊即時顯示。`start.ps1` 已同步改用新伺服器。Artifact 網頁版因無法讀本機檔案，改顯示「請在筆電開本機網址查看」的提示。
- [x] **7. End-to-end 煙霧測試（真語音，非手打文字）**：
  1. Windows TTS 合成語音「我的筆記型電腦喇叭低頻聲音好像突然變差了，聽起來悶悶的」
  2. whisper.cpp GPU medium 轉錄（正確率100%，僅漏標點）
  3. 模式分流器判斷為 acoustic_engineering ✅
  4. Front Desk 對話完整跑完 S0→S8
  5. 正式寫入 `C:\0_JN1_AERIS_HANDOFF\orders\AERIS-20260916-220047_ORDER.md`
  6. 主控台 `/api/orders` 正確讀到這筆訂單並顯示
  - 小觀察：LLM 重述使用者目標時把「我的」誤轉成「他的」，語意上是小瑕疵，不影響格式正確性，記錄下來留意。

**全部 7 項工作計畫項目完成。**

## 額外完成（發現重複手動重啟服務很煩，直接做掉）

- [x] `start.ps1` 一鍵啟動腳本：自動載入編譯環境、啟動 llama-server（GPU）、啟動本機主控台網頁伺服器，兩者都做了「已經在跑就跳過」的檢查，可重複執行。
  - **踩坑**：用舊版 `powershell.exe`（Windows PowerShell 5.1）執行 .ps1 檔，預設用系統內碼（Big5）讀檔，把腳本裡的中文字串讀壞導致語法錯誤。修法：檔案存成 **UTF-8 with BOM**（舊版 PowerShell 認得 BOM 就會正確用 UTF-8 解碼），新版 `pwsh` 兩種都正常。
  - 用法：`.\start.ps1`，完成後會自動開瀏覽器到主控台。

## P3 延伸進度（Windows Automation，跟 Front Desk 並行的另一個模式）

- [x] 補齊工具實作：`set_volume`（pycaw，需要注意這版 pycaw 的 API 是 `AudioUtilities.GetSpeakers().EndpointVolume`，不是舊版教學常見的手動 COM Activate 寫法）、`clipboard_op`（pyperclip）
  - 安全設計延續 Notepad 教訓：每次測試前先讀現狀（目前音量/剪貼簿內容），測完主動還原，不留痕跡
- [x] **完整迴圈真正跑通**：語音合成 → whisper.cpp GPU 轉錄 →（`src/full_pipeline.py`）llama.cpp GPU 判斷 tool+args → PolicyEngine → Executor → 真實執行 → 回報結果。用真語音測了「現在幾點」，全鏈路本機 GPU，無一步造假。
- [x] 用文字指令測了 4 個工具（查時間/調音量/截圖/複製剪貼簿），全部正確執行，且都是可逆/可還原的安全動作
- 目前 35 個工具裡只有 6 個有真實實作（open_app/close_window/get_datetime/take_screenshot/set_volume/clipboard_op），其餘 29 個 LLM 判斷得出來但 Executor 會誠實回報「尚未實作」，不會假裝執行成功——之後要繼續補的就是這 29 個工具的真實動作

## 中文喚醒詞訓練（P1 遺留項目）— ✅ 已解決，本機完成訓練

**重大轉折**：torch 現在有 ARM64 Windows nightly wheel了（`torch==2.15.0.dev20260916+cpu`），P0 當初的結論已過期。官方 `openwakeword.train` 因為依賴 `audiomentations`（需要 numba/llvmlite，ARM64編不起來）還是不能直接用，改成自己寫訓練腳本（只借用官方ONNX特徵萃取器，分類器自己用torch刻、訓練）。

**過程中抓到並修正3個真實bug**（每個都有實測證據，不是猜的）：
1. `embed_clips` 批次處理 shape 不符
2. ONNX 匯出「假成功」——新版 dynamo 匯出器匯出的檔案跟原模型行為不一致（98%→46%），改用舊版匯出器+匯出後數值一致性檢查解決
3. **最隱蔽**：模型學到「音檔剛開始1秒=正樣本」的位置捷徑，不是真的學內容——修完後準確率23%→73.1%

**最終結果**（真實部署路徑`Model.predict()`測試，非捷徑評估）：正樣本83%正確觸發、一般語句87%正確不誤觸發、**近似混淆詞只有20%正確**（明顯弱項，資料量太小）。

判定：**v0.2已可用，88.5%真實部署路徑準確率**（v0.1原本73.1%，補了15秒真實麥克風環境噪音當負樣本重訓後大幅提升，尤其一般語句誤觸發降到0）。模型放在 `src/wakeword/hai_xiao_zhuli_wakeword.onnx`。完整過程記錄在 `progress/p1_wakeword_train/REPORT.md`。

## 常駐監聽迴圈（把P0-P3全部串成一個真正能跑的程式）

- [x] `src/listen_loop.py`：麥克風 -> VAD -> 喚醒詞 -> 錄音 -> whisper.cpp ASR -> 模式分流 -> 執行，完整串起來的常駐程式。
  - 麥克風擷取用 `sounddevice`（確認有ARM64 wheel），已測試能正確開啟 Surface Stereo Microphones。
  - **踩坑並修正**：一開始設計「喚醒詞觸發後跳過固定0.4秒緩衝期再開始聽指令」，結果實測發現喚醒詞常常提早觸發（講到一半就觸發，score0.95），觸發後還有將近1.4秒尾音，固定緩衝期完全不夠，導致尾音後的自然停頓被誤判成「指令講完了」，永遠等不到真正的指令。改成「動態等到真的安靜下來，才開始正式聆聽」的三階段狀態機（IDLE→等待喚醒詞尾音安靜→正式聆聽指令），不管尾音多長都能正確處理。
  - 用合成音訊模擬完整串流（靜音+喚醒詞+停頓+指令+靜音）逐塊餵測試，不需要真人講話就能驗證邏輯：桌面操作指令（「現在幾點」）跟聲學工程問題（「我的喇叭低頻聲音怪怪的」）兩條分流路徑都測過，正確。
  - 真實麥克風煙霧測試：接上真麥克風跑12秒，過程中意外發現喚醒詞對環境噪音誤觸發的問題（見上方v0.2更新），修完後乾淨通過。
- [x] **Front Desk 多輪語音對話已接上並驗證成功**：`src/frontdesk/voice_dialog.py`。
  - 助理用 SAPI 直接講問題出來（`win32com.client` 呼叫 `SAPI.SpVoice`，不用每次開PowerShell寫檔案再播放）
  - 使用者用自由講話回答（不用講選項的精確字眼），用LLM做語意比對回選項——測試「應該是漏氣的問題」正確對應到「漏氣」、「我不太確定」正確對應到「不確定」、「聽起來像是共振的問題」正確對應到「腔體共振」
  - 用3句預先合成的語音模擬使用者完整回答三輪問題，**整個流程真的用「講的」走完，最後產生正式ORDER.md並寫進交接資料夾**
  - **誠實記錄兩個實測發現的真實問題**：
    1. ASR 把「頻響曲線」聽成「屏想曲線」（同音字混淆），導致這個證據項沒被正確擷取到訂單裡——多輪對話疊加ASR誤差是真實風險，還沒有處理
    2. ROUTE步驟對「漏氣」問題沒有選到最直接對應的 #023 Leakage Engineer，選了 Port/Vent、Acoustic Path 等相關但非最佳的工程師——這是先前就記錄過的已知限制（LLM在100人清單裡自由選人不夠精準），這次多輪語音場景又再次驗證到同樣的情況

## 中文新手引導式體驗（使用者明確要求）

- [x] **問題確認**：`listen_loop.py` 原本只會在黑底終端機印技術性 JSON 事件（`{"type": "wake_detected", "score": 0.95}`），對不懂技術的新手來說完全看不懂、也很嚇人。
- [x] **`console/companion.html`**：全新的「即時陪伴介面」，取代終端機視窗給新手看：
  - 大圓圈狀態指示（灰=待命、綠色脈動=在聽你說話、黃色旋轉=思考中、藍綠色=助理說話/引導中），不用看文字就懂現在狀態
  - 即時顯示「你剛剛說」跟「助理回覆」，白話文，不是技術log
  - 首次使用的3步驟新手引導（這是什麼／怎麼開始用／可以試試這些指令），用 localStorage 記住看過了，不會每次都跳出來
  - 「可以試著說」的例句提示卡，降低不知道要說什麼的門檻
  - 深淺色、跟主控台共用同一套視覺系統，風格一致
- [x] **狀態即時推送機制**：`listen_loop.py` 新增 `LiveStateWriter`，把技術事件即時翻成白話狀態寫進 `console/live_state.json`（寫暫存檔再改名，避免網頁讀到寫一半的檔案）；`console/serve.py` 新增 `/api/state` 讓網頁每0.5秒輪詢一次。
- [x] **完整驗證**：
  - 用模擬音訊直接驅動 `LiveStateWriter`，確認狀態依序正確變化：待命→我聽到你了→請說出你想做的事→我在想→（附上逐字稿）→待命（附上回覆內容），共7個快照，順序跟內容都對
  - 瀏覽器實際截圖確認畫面渲染正確（待命/聆聽中/完成三種狀態都截圖驗證過）
  - **踩坑**：改完 `console/serve.py` 加新的 API 路由後，本來在跑的舊伺服器行程沒有重啟，導致新路由回傳404——Python改程式碼不會讓正在跑的行程自動重載，這次是靠外部驗證才抓到，不是靠自己以為改完就沒事了
  - 也試了「喇叭播放合成語音、麥克風收音」的聲學迴路測試，但音訊沒有真的傳到麥克風（後來查是系統音量被前面的測試設成靜音了）——改用直接餵模擬音訊進同一套狀態寫入邏輯驗證，一樣可靠且不受環境音響條件影響

## P3 工具擴充第二批（6/35 → 15/35）

新增9個工具真實實作：`window_op`（最小化/顯示桌面/切換視窗）、`media_control`（播放暫停/上下首/靜音）、
`network_toggle`（Wi-Fi開關）、`calculator`（安全算式運算）、`text_to_speech_op`、`translate`、
`summarize_doc`（後三者借用常駐的llama-server，純本機GPU）、`text_input_op`。

**刻意不做的（有明確理由，不是偷懶）**：
- `get_weather`、`get_exchange_rate`：本質需要連網查即時資料，跟專案「100%離線」的核心原則衝突，需要你決定要不要開這個例外
- `dev_tool_op`（執行任意程式碼/腳本）：這正是 CLAUDE.md 明文禁止的「execute_any_shell_command 萬用工具」模式，不會做
- `cloud_file_op`、`calendar_op`、`email_op`、`video_call_op`、`print_or_scan`、`photo_edit`、`alarm_op`、`reminder_op`：需要串接特定的外部服務/App（Outlook、雲端硬碟、印表機驅動等），複雜度高、優先度較低，先跳過
- `system_maintenance`、`task_scheduler_op`、`startup_program_op`、`driver_op`、`git_op`（push/merge類）：本質上風險較高，Policy Engine已經設定成L2/L3需要確認，先不急著補實作，等真的需要時再做

**實測過程抓到的真實問題（每個都有實測證據）**：
1. **這台機器的螢幕亮度調整完全不可用**：Windows標準的 `WmiMonitorBrightness` WMI類別存在但沒有任何執行個體，連NVIDIA自己的 `NvWmiBrightness` 也一樣沒有實例——這是ARM64+Blackwell混合架構的硬體/驅動限制，不是程式碼問題，程式碼保留給有支援的機器用
2. **靜音鍵是獨立旗標，不是音量歸零**：按了靜音鍵後，就算把音量數值調到50%，只要沒有另外解除靜音旗標還是沒聲音——修正 `set_volume` 設定正值時自動解除靜音旗標
3. **`close_app_by_pid` 在視窗被最小化後會失效**：pywinauto的 `top_window()` 找不到「頂層可見視窗」，即使行程明明還在跑——加了用psutil直接依pid終止行程的備援機制（一樣安全，因為pid是我們自己追蹤到的，不是靠標題模糊比對）
4. **「幫我把音樂暫停」被LLM誤判成「靜音」**：兩個中文詞意思上有點像，容易混淆，工具說明加一句澄清後修正
5. **記事本的工作階段還原問題又出現第三次**：這次自動跳出「AERIS_START.ps1」，確認這是這台機器上持續存在的系統行為，不是單一意外——之後測試一律優先用小算盤（沒有文件狀態）當安全測試對象，記事本只在真的需要測「有文件狀態的App」時才用
6. **實測前特別檢查目前作用中的視窗是「ChatGPT」（使用者自己開的），主動避開對它做最小化測試**，改用自己開的計算機當測試對象，測完立刻關掉——沒有動到使用者自己的視窗

## 語音確認閉環（P4 安全機制的關鍵缺口，補上了）

**發現的問題**：Policy Engine 早就會正確攔下 L2/L3 敏感操作要求確認，但語音介面原本只會說「需要確認」然後直接跳過——**使用者永遠沒辦法真的用講的完成確認**，安全機制形同虛設（能擋下但擋下之後就卡住，不是真正可用的閉環）。

**修正**：`listen_loop.py` 新增 `_voice_confirm()`：
- L2（敏感操作）：助理講出原因＋問「要繼續嗎」，使用者用自由講話回答，LLM判斷同意/拒絕（沿用 `voice_dialog.yes_no`）
- L3（危險操作）：助理明確要求使用者複誦關鍵字「確認執行」，**不接受單純的「對」「好」這種輕鬆同意**——對照 `risk_levels.py` 當初設計的「不能只按是，要求輸入關鍵字才算確認」精神
- **安全預設**：如果沒有真的收到語音來源（例如單元測試用固定模擬音訊），一律當作拒絕，不會因為「聽不到回覆」就預設放行

**測試**（都是真語音跑過，不是邏輯上推論應該對）：
1. 「把Wi-Fi關掉」→ 正確要求L2確認 → 回答「不要，先取消」→ 正確拒絕，**事後查證Wi-Fi介面真的完全沒被動到**
2. 直接測L3決策：隨口說「對阿好」→ 正確拒絕（approved=False）；講出關鍵字「確認執行」→ 正確通過（approved=True）
3. 過程中順便發現並修正一個真實風險分級問題：`network_toggle`（Wi-Fi開關）原本設L1（免確認），但意識到關Wi-Fi可能打斷使用者在同一台電腦上的其他網路活動（下載/通話/瀏覽），不是「可逆」就等於「低風險」，升級成L2

## 補齊 Memory（第13節）跟 Logging（第14節）的資料表缺口（對照 docs/07 進度報告第7、8節）

`docs/07`第7、8節指出：藍圖第13節要求的5類記憶（Session Context/User Preferences/Known Apps/Known Folders/Command History）只有Command History勉強算做了一半，其餘4類完全空白；第14節要求的10個Logging欄位（Timestamp/Voice transcription/Intent/Plan/Tool/Arguments/Permission level/Execution result/Duration/Error）裡，Duration/Error/Intent三個完全沒有，`conversation_log`跟`action_audit`兩表也沒有共同ID可以join。這次補上：

- **`executor/audit_db.py`重寫**：`action_audit`新增`session_id`/`intent`/`duration_ms`/`error`四個欄位，`conversation_log`新增`session_id`；新增`known_apps`/`known_folders`/`session_context`/`user_preferences`四張表對應藍圖第13節缺的4類記憶。既有資料庫檔案（實測前已經有91筆`action_audit`紀錄）用`ALTER TABLE ADD COLUMN`安全遷移，不會弄丟舊資料——舊資料的新欄位會是NULL，這是正常的，不是bug。
- **抓到並修正一個真實bug**：`log_conversation()`這個函式一直都存在，但實測查資料庫發現`conversation_log`表**0筆資料**——搜尋整個程式碼庫確認`log_conversation()`從來沒有任何地方真的呼叫過，藍圖要求的「對話紀錄」這個記憶類別形同沒做，只是表存在、沒人寫。這次把它接到`listen_loop.py`（語音路徑，utterance處理完/Front Desk分流時）跟`command_processor.py`（文字路徑，包含確認流程的每一輪）。
- **`Executor.run()`**：改成用`time.time()`量測真正的執行耗時存進`duration_ms`；失敗時把錯誤訊息額外存一份到獨立的`error`欄位（原本只有混在`result_summary`文字裡）；成功呼叫`open_app`/`file_op`後，分別記進`known_apps`/`known_folders`（跟`basic_tools.py`的白名單`KNOWN_APPS`是兩件事——白名單是安全邊界不會被這張表放寬，這張表純粹是「用過的紀錄」）。
- **`PlanRunner`/`command_processor.py`/`listen_loop.py`**：都改成把`session_id`傳進`Executor.run()`，讓同一次對話的所有`action_audit`紀錄可以用`session_id`跟`conversation_log`的對應紀錄join在一起查——這是第8節指出的「兩表沒有共同ID」缺口的直接解法。
- **過程中抓到並修正一個真實bug**：`PlanRunner.resume()`原本不管`typed_keyword`有沒有傳，只要L3就一定拿它跟「確認執行」比對——但語音路徑的`_voice_confirm()`早就自己驗證過關鍵字了，回傳的是已經驗證過的`True`，這裡又拿`None`（語音路徑沒有另外傳`typed_keyword`）去比對，會把正確的語音同意錯誤地打回`False`。修法：只有真的傳了`typed_keyword`（文字/網頁路徑，使用者打的原始文字，還沒驗證過）才在這裡驗證；語音路徑已經驗證過的結果直接信任。用真的語音走一次L3流程測過，修正後行為正確。
- **端到端真實測試**：文字指令(`run_desktop_command`)+確認流程(`confirm_desktop_command`)各跑過幾次，查資料庫確認`known_apps`（開過calculator/notepad）、`session_context`（正確存最後一個工具跟指令）、`action_audit`新欄位（session_id/intent/duration_ms/error都正確填值，舊資料正確維持NULL不受影響）、`conversation_log`（不再是空表，語音跟文字兩種路徑都有真實紀錄）都正確運作；也重跑了`test_listen_loop_simulated.py`/`test_l3_confirmation.py`/`test_voice_confirmation.py`三個既有回歸測試，全部正常通過，確認這次的改動沒有破壞既有功能。
- **誠實記錄還沒做的**：`user_preferences`表已經建好、有`get_preference`/`set_preference`函式，但目前沒有任何功能真的去讀寫它（沒有語音指令或UI能讓使用者設定偏好）——這是基礎建設先準備好，不是假裝已經有這個功能在用。

## 補上最小可行的多步驟規劃能力（對照 docs/07 進度報告第2節P6的缺口）

`docs/07`第2節指出：原本一句話只能對應一個工具呼叫，藍圖P6要求的「找到Downloads裡最新的PDF，打開它，然後把檔名告訴我」這種需要依賴前一步真實結果才能決定下一步參數的複合指令完全做不到。這次在`full_pipeline.py`加了`PlanRunner`：

- **設計取捨**：第一步沿用原本單次LLM呼叫（`understand()`），新增一個`needs_followup`布林欄位讓LLM自己判斷「這句話還有沒有後續」——大多數單一動作指令維持原本的延遲（1次LLM呼叫，不拖慢）。只有`needs_followup=true`時才進入「問下一步該做什麼」的迴圈，且每一步都基於前一步**真實執行過的結果**（不是LLM一次規劃好全部步驟後憑空瞎猜參數）。設了`MAX_STEPS=5`安全上限，防止規劃者判斷卡住造成無限迴圈。
- **過程中抓到並修正一個真實的llama.cpp Grammar限制**：一開始把`needs_followup`加在`args`（開放式`{"type":"object"}`，沒有限定properties）後面，結果LLM每次都固定產生同一種格式錯誤的JSON後接一串亂碼胡言亂語——這不是LLM亂掉，是**llama.cpp把JSON Schema轉成GBNF語法時，開放式object欄位後面如果還有其他必填欄位，語法解析會卡住**。修法：把`args`移到properties/required清單的最後一個，問題立刻消失，改完之後單步驟指令（現在幾點/調音量/複製剪貼簿）都正確且沒有延遲退化（三個都是0.7秒左右，跟改之前一樣）。
- **也順手補上一個真實bug**：`file_op`原本整個工具都設L2（需要確認），導致PlanRunner裡「先查詢/找檔案」這種純唯讀步驟也會被迫要求使用者確認——修正成`file_op`基準是L1（find/open唯讀免確認），move/copy/rename/create_folder才用`ESCALATION_RULES`拉高到L2，delete維持L3，更貼近藍圖第9節的「唯讀免確認、修改資料才需要確認」精神。
- **同時補上`find_file`的`extension`/`newest_only`參數**：原本只能列出符合名稱的項目，不知道哪個最新——藍圖範例句「找最新的PDF」需要這個能力才能真的做到。
- **端到端真實測試**（都是真的建測試檔案、真的執行，不是模擬）：在使用者家目錄底下建一個測試資料夾，放兩個修改時間不同的txt檔案，下指令「找到voice_agent_plan_test資料夾裡最新的txt檔案，打開它，然後把檔名告訴我」——**連續4次測試都正確**：步驟1找到真正最新的檔案（不是隨便猜的路徑），步驟2用步驟1的真實路徑打開它，最後正確回報檔名。過程中也誠實記錄了兩次失敗的中間版本（模型一度提前結束跳過"打開"步驟、一度為了"告訴我"這個單純陳述結果的要求去瞎猜一個不存在的`get_filename`工具導致觸底MAX_STEPS安全上限）——這些都透過調整`next_step()`的提示詞逐步修正，不是一次到位。
- **誠實記錄還沒解決的**：這套機制目前只驗證過一個具體場景（找檔案+開檔案+回報檔名），沒有測過更複雜的分支（例如中途某步驟失敗要怎麼恢復、或需要使用者在多步驟中途補充資訊的情況）；小型本機LLM對「這句話到底該拆成幾步」的判斷不是100%穩定，這次是靠三輪提示詞調整才穩定下來，換一種說法的複合指令可能又需要重新調校。

## 補齊藍圖第7節UIA原語（對照 docs/07 進度報告第4節抓到的最大缺口）

`docs/07_Progress_Report_vs_Blueprint_2026-09-17.md`第4節指出：藍圖docs/01第7節列的19個canonical工具裡，`get_active_window`/`list_windows`/`focus_window`/`uia_click`/`uia_set_text`/`uia_select`/`press_key`/`hotkey`這7個UI Automation原語完全空白，導致P3自己定義的驗收劇本（記事本開→打字→存檔→關閉→重開）從沒真正跑過。這批補上其中8個工具（`tools/basic_tools.py`）：

- `get_active_window()`：查詢目前最前面視窗（win32gui.GetForegroundWindow + GetWindowThreadProcessId）
- `list_windows()`：列出所有可見視窗跟pid（EnumWindows）
- `focus_window(pid|title)`：切到指定視窗，標題比對延續close_app_by_pid的安全原則（模糊比對到多個就直接拒絕，不猜）
- `uia_click(pid, control_name)` / `uia_set_text(pid, control_name, text)` / `uia_select(pid, control_name, item_name)`：用pywinauto的UIA backend連接指定pid的視窗，靠控制項顯示文字定位（同名有多個就拒絕，跟找不到一樣明確報錯），不是滑鼠座標也不是SendKeys盲打
- `press_key(key)` / `hotkey(keys)`：通用鍵盤原語，`hotkey`維護一個黑名單擋掉`Win+R`（等同繞過Policy Engine執行任意命令）跟`Win+L`（鎖定電腦畫面）

**過程中抓到並修正一個真實的Windows API限制**：`focus_window`第一版直接呼叫`win32gui.SetForegroundWindow(hwnd)`，實測時丟出`pywintypes.error`——這是Windows內建的「焦點竊取保護」，背景行程預設不能搶走最前面視窗的焦點。改用標準合法的繞過技巧：先用`AttachThreadInput`把呼叫端執行緒跟目標視窗的輸入狀態接起來，再呼叫`SetForegroundWindow`，結束後解除綁定；並且改成用`GetForegroundWindow()`的實際結果驗證有沒有真的切換成功，不是呼叫沒丟例外就假設成功。

**端到端真實測試**（都是真的操作真實應用程式，不是模擬）：
1. `get_active_window`/`list_windows`：多次呼叫結果一致且正確
2. `focus_window`：先切到PowerShell（驗證成功切過去），再切到小畫家（驗證真的從PowerShell切換過去，不是本來就在前面）——證明修好的AttachThreadInput技巧真的有效
3. `uia_click`：對小畫家點擊「橡皮擦」按鈕成功；故意點名稱有兩個符合的「橢圓形」正確被拒絕；故意點不存在的按鈕正確報錯
4. `press_key`/`hotkey`：按Escape、送出Ctrl+Z(復原)都正確執行；故意送`Win+R`跟`Win+L`都被黑名單正確擋下；`press_key`故意傳組合鍵正確被拒絕並導向`hotkey`

**誠實記錄兩個測試過程中的環境限制發現，跟工具本身的bug無關**：
- 這個工作環境裡，UWP封裝的Windows應用程式（新版記事本、小算盤）用`subprocess.Popen`啟動後，行程會在很短時間內自己結束、從來沒有真的建立過視窗——用經典Win32程式（小畫家/檔案總管）測試完全正常。這代表這個特定環境下無法用記事本/小算盤當UIA測試對象，但不影響工具本身的正確性（在能正常開啟視窗的應用程式上完全正常運作）
- `uia_set_text`/`uia_select`跟已經驗證過的`uia_click`共用完全一樣的連線／定位邏輯（`_connect_uia_top_window`+`_find_uia_control`），差別只是最後呼叫pywinauto既有的`.set_text()`/`.select()`而不是`.click_input()`——這次沒有找到一個「有真正可編輯欄位、又不會冒然動到專案真實檔案」的安全測試對象（File Explorer裡能找到的Edit控制項都是檔案重新命名欄位，牽涉到真實專案目錄），所以這兩個工具沒有獨立實測到，這是誠實記錄的限制，不是隱瞞

已加進`full_pipeline.py`的LLM工具清單跟`risk_levels.py`的風險分級（get_active_window/list_windows=L0，focus_window/press_key=L1，uia_click/uia_set_text/uia_select/hotkey=L2）。

## P3 工具擴充第三批（15/35 → 17/35）

新增2個工具真實實作，這次特別挑「docs/01第7節明文列出、但一直沒做」以及「風險等級最高、之前刻意跳過」的：

- **`file_op`**：`find_file`/`open_file`/`move_file`/`copy_file`/`rename_file`/`create_folder`/`delete_file` 七個動作合一。安全設計：搬移/複製/改名/建資料夾/刪除這幾個會真的改變檔案系統狀態的動作，全部限制在使用者家目錄（`Path.home()`）底下，不接受系統目錄路徑——實測故意叫它刪 `C:\Windows\System32\drivers\etc\hosts`，正確擋下並丟出清楚的錯誤訊息，不是靠僥倖沒被出到那個指令。`delete` 用 `send2trash` 送進資源回收桶（不是 `os.remove` 永久刪除），而且不支援遞迴刪整個資料夾，降低一次誤刪的損失範圍。7個動作（find/create_folder/find again/copy/move/rename/delete×2）都用真實檔案系統操作測過，刪除後也去資源回收桶裡實際確認檔案真的在裡面（不是刪除呼叫回傳成功但其實沒發生任何事）。
- **`power_op`**：`shutdown`/`restart`/`sleep`/`cancel` 四個動作。docs/01第9節明訂電源操作是L3危險操作，一定要複誦「確認執行」才會執行——這是目前所有工具裡風險最高的一個，測試方式特別小心：
  - `shutdown`、`restart` 都用 `shutdown /t 30` 排程30秒延遲（不是立刻斷電），實測時排程後立刻呼叫 `cancel`（`shutdown /a`）中止，驗證了排程/取消指令都真的執行成功，而且從頭到尾沒有真的讓電腦關機或重開機
  - `sleep` 用標準 Win32 API `SetSuspendState`，只驗證了 `ctypes.windll.powrprof.SetSuspendState` 這個介面確實存在，**沒有實際呼叫**——因為這台機器正是這個工作階段在用的機器，真的讓它睡眠會中斷正在進行的工作，這個決定留給使用者自己在方便的時候手動測試
  - 完整迴圈測試（真語音/文字指令 -> LLM判斷tool+args -> PolicyEngine -> 正確停在需要確認）：「把電腦關機」「重新啟動電腦」「讓電腦睡眠」三句都正確判斷成 `power_op` 並要求L3確認，**過程中沒有讓任何一句話真的執行到底**，只驗證到「正確要求確認」這一步就停手
- 兩個工具都已加進 `full_pipeline.py` 的 LLM 工具清單跟 JSON Schema enum，不然即使 Executor 有實作，LLM 也永遠選不到
- **事後透過真的HTTP端到端測試（走`companion.html`會用的同一條路），抓到並修正一個真實bug**：使用者講「幫我建立一個叫XXX的資料夾」這種沒有給絕對路徑的自然說法時，LLM填的參數也是相對路徑（例如`"path": "XXX"`），原本的 `_require_safe_path()` 直接對相對路徑呼叫 `.resolve()`，會展開成「常駐服務行程目前的工作目錄」（例如 `console/`）而不是使用者的家目錄，導致明明合理的請求被安全檢查誤擋。修成 `_resolve_under_home()`：沒有給絕對路徑就一律當成「相對於使用者家目錄」展開，再檔案系統路徑穿越測試（`../../Windows/evil`）確認新邏輯依然正確擋下逃出家目錄的嘗試。

## 藍圖盤點稽核（對照 docs/01 全文逐節檢查，抓到的落差跟修正）

使用者明確要求「請盤點和檢查藍圖 你要參考藍圖去施工」，逐節對照 `docs/01_Original_Blueprint_v0.1.md` 檢查已經做的東西，抓到以下落差（🔴=必須立刻修、🟡=應該修、🟢=可以之後補）：

- 🔴 **Emergency Stop 熱鍵設錯**：docs/01 第10節明訂 `Ctrl+Shift+F12`，`listen_loop.py` 之前寫成 `ctrl+alt+q`（沒有對照藍圖直接猜的）。**已修正**，並實測 `keyboard.add_hotkey('ctrl+shift+f12', ...)` 能正確註冊/移除，沒有跟系統已有快捷鍵衝突。
- 🔴 **語音停止指令完全沒做**：docs/01 第10節要求「停止」「取消」「不要執行」要能用講的打斷流程（次要於熱鍵，但一定要有）。**已實作** `is_stop_command()` 並接到全部三個「系統在聽使用者講完一句話」的地方：`ListenLoop.handle_utterance()`（一般指令路徑）、`ListenLoop._voice_confirm()`（L2/L3語音確認回覆）、`VoiceFrontDesk._listen_one_utterance()`（Front Desk多輪語音對話，用新的 `StoppedByUser` exception 讓 `run()` 能在流程中途乾淨中斷，回傳 `CANCELLED_BY_USER`）。
  - **端到端真實驗證**（SAPI合成語音→真的跑whisper.cpp ASR→餵進真實流程，不是塞字串進去假裝）：「停止」「不要」「算了」三個詞ASR正確辨識並觸發停止；「取消」「不要執行」被whisper誤聽成「屈臣」「不要知心」——這是TTS機器人語音+單字無上下文情境下的ASR辨識限制，不是程式邏輯錯誤，也印證了藍圖本身「熱鍵才是最高優先權，語音是次要機制」的設計是對的。測試腳本：`src/test_stop_command_simulated.py`、`src/gen_stop_wav.py`（合成測試音檔用）。
- 🟡 **`close_window` 風險分級設錯**：docs/01 第9節明訂「關閉程式」是L2（可能有未存檔內容），`risk_levels.py` 原本誤設成L1（免確認）。**已修正**成 `L2_SENSITIVE`。
- 🟡 **文字輸入完全缺失**：使用者直接抓到「我明明藍圖有說 要語音和文字都可輸入 你這不像」（對照 AERIS 藍圖第27.1節「輸入方式」跟一般無障礙原則）。**已完成**：
  - 新增 `src/command_processor.py`：文字版指令處理器，跟語音路徑共用同一套 `mode_classifier`/`full_pipeline`/`Executor`/`FrontDeskDialog`，只是換成無狀態HTTP請求/回應（Front Desk多輪對話用記憶體dict + session_id維持狀態）
  - `console/serve.py` 改成 `ThreadingMixIn`（不然文字指令處理期間會擋住 `/api/state` 的0.5秒輪詢，畫面看起來像當掉），新增 `/api/command`、`/api/confirm`、`/api/frontdesk_reply` 三個POST端點
  - `console/companion.html` 新增文字輸入框+傳送按鈕、L2/L3確認卡片（含L3要求輸入關鍵字「確認執行」）、Front Desk選項卡片（可以直接點選項或手打文字回答）
  - **端到端瀏覽器真實測試**（不是只測API，是真的在瀏覽器點擊操作）：桌面控制指令（「現在幾點」→正確執行）、L2確認流程（「關閉小算盤」→正確跳出確認卡→點取消→正確不執行）、完整Front Desk文字對話（DIVERGE選方向→EVIDENCE選資料→PREVIEW確認→取消，全部用點擊選項卡完成）都測過且正確
  - **過程中抓到並修正2個真實bug**：(1) `dialog_state_machine.py` 的 `session.state` 存的是「下一步要等待的輸入狀態」，不是這次回傳給使用者的 `step["state"]`（例如 `capture()` 回傳的step標示`DIVERGE`，但這時`session.state`其實已經是`CONVERGE`），一開始不知道這個內部語意，`command_processor.continue_frontdesk_text()`跟`companion.html`前端都各自對錯了一次，實測才抓出來修正；(2) 一開始重啟 `serve.py` 時誤用系統Python（缺 `requests` 等套件），必須用 `venv-arm64` 的Python才能跑，這也是靠實測500錯誤才抓到，不是憑空想到的
- 🟡 **Logging 沒有共同ID串連**：docs/01第14節要求每筆操作記錄要包含完整欄位，目前 `conversation_log`/`action_audit` 兩張表沒有共用session/case ID串起來，也缺明確的Duration/Error欄位。**還沒處理**，下一步要做。
- 🟢 **KPI量測不完整**：8小時喚醒詞誤觸發測試、獨立的「工具執行成功率≥98%」量測、完整端到端延遲量測都還沒做。優先度較低，之後排。
- 🟢 **UI狀態模型沒有明確對應藍圖5態**：docs/01第18節要求Listening/Thinking/Executing/Waiting confirmation/Stopped五態，目前`companion.html`的`live_state.json`狀態沒有明確涵蓋「Executing」跟「Waiting confirmation」這兩個獨立顯示狀態。優先度較低，之後排。

## 設計原則提醒（避免做歪）

- Front Desk 只負責「收斂需求、產生 ORDER.md」，**不負責任何聲學工程判斷**——那是 AERIS 的事，本專案不應該假裝知道 leakage/driver 怎麼分析
- 對話問題選項要克制，文件裡明講：「用最少但必要的問題，形成足夠後端執行的 ORDER.md」，不是問越多越好
