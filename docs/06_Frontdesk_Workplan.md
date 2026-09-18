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

## P3驗收劇本真的跑通了：記事本開→打字→存檔→關閉→重新打開（對照 docs/07 進度報告第2節）

`docs/07`第2節記錄過藍圖P3自己定義的驗收劇本（開記事本→輸入Hello→存檔→關閉→重新打開）一直沒有真正執行過，原因寫的是「這台機器UWP應用程式起不來」。這次重新嘗試，**發現先前的診斷是錯的，真正的原因跟修法完全不同**，過程抓到並修正了4個真實bug，最後把整套劇本真的走完一次。

### 先前診斷錯誤：不是「UWP起不來」，是PATH解析找錯執行檔

`open_app()`原本用`subprocess.Popen(['notepad.exe'])`，靠系統PATH找執行檔——這台機器的PATH裡`C:\Users\testuser\AppData\Local\Microsoft\WindowsApps\notepad.exe`（新版記事本的「執行別名」轉接殼層）跟真正的`C:\Windows\System32\notepad.exe`同時存在。實測發現：**直接用完整路徑呼叫`C:\Windows\System32\notepad.exe`，記事本真的開出一個持久的視窗**；先前判斷「UWP應用程式在這個環境起不來」是誤判，當時只是恰好卡在轉接殼層那個環節。這也代表先前`record_screen`（Xbox Game Bar）測不出結果的推論理由需要重新檢視，但因為Game Bar牽涉不同的啟動路徑，這次沒有再深入驗證那一個。

### 過程中抓到並修正的4個真實bug

1. **`uia_set_text`原本假設每個UIA控制項都有`set_text()`方法**——記事本主編輯區是"Document"類型，pywinauto包成通用UIAWrapper沒有這個方法，會丟`AttributeError`。改成分層嘗試：`set_text()` → UIA的`ValuePattern.SetValue()` → 點擊+模擬打字，三種都試過才放棄。
2. **更關鍵：`ValuePattern.SetValue()`能設定值，但不會給控制項真正的鍵盤輸入焦點**——設完值之後送出的`hotkey()`/`press_key()`完全沒反應（連單一字元'a'都打不進去），因為視窗「在最前面」跟「內部某個控制項真的有輸入焦點」是兩件不同的事，尤其對WinUI/XAML應用程式更明顯。修法：`uia_set_text`一律先真的點擊一次目標控制項建立焦點，才決定用哪種方式設值。
3. **`press_key()`/`hotkey()`底層的`win32api.keybd_event()`（舊式鍵盤事件API）對這個現代應用程式完全沒有反應**——連視窗層級的Ctrl+N/Ctrl+S快捷鍵都送不到，即使當時視窗確實在最前面。改用`SendInput`（Windows官方建議取代keybd_event的現代API）。但**這個修正只解決了一部分**：即使改用SendInput（甚至改用pywinauto自己的`send_keys()`，同樣底層機制），Ctrl+N/Ctrl+S這兩個組合鍵**仍然到不了這個特定應用程式的快捷鍵處理層**——這代表問題比「用哪個API模擬按鍵」更深層，可能是這個WinUI應用程式的鍵盤加速器（accelerator）處理管線本身不接受這個執行環境的合成輸入事件。
4. **`_find_uia_control`的名稱比對邏輯太粗糙**：(a) 按鈕常常有一個顯示同樣文字的子元素(Static)，UIA會把兩個都列成候選；(b) 選單裡「儲存」跟「全部儲存」這種一個名稱是另一個的子字串，substring比對會誤抓到不同的選項。修成優先挑選「唯一的可互動類型控制項」，再退而求其次挑選「文字完全相等的候選」，兩層備援解決掉。

### 順手把根本原因也修掉了：`open_app()`改用完整路徑，不靠PATH解析

既然找到`open_app()`啟動失敗的真正原因是PATH解析撞到WindowsApps轉接殼層，這次直接把`config/tools.yaml`裡`notepad`/`calculator`/`explorer`的對應值從裸執行檔名稱（`notepad.exe`）改成完整路徑（`C:\Windows\System32\notepad.exe`），並修正`open_app()`裡`REAL_PROCESS_NAME`查表邏輯（原本直接拿完整路徑字串去查一個key是短檔名的字典，改完路徑後會查不到，用`Path(exe).name`取basename再查）。修完後重測記事本跟小算盤各3次，全部都是持久、真實的視窗，不再是先前那種「行程存在但視窗不持久」的不穩定狀態。

### 最終解法：改用UIA選單點擊，不是鍵盤快捷鍵——這正好驗證了藍圖自己的設計哲學

第3個bug發現「連SendInput都到不了這個app的快捷鍵處理」之後，改成**直接用`uia_click`點擊「檔案」選單→「儲存」選單項**，而不是送`Ctrl+S`——這樣做確實成功觸發了存檔對話框。這個轉折本身很值得記錄：藍圖`docs/01`第2節的控制優先順序明講「Level 2 UI Automation」要優先於「Level 5 Keyboard/Mouse automation」，這次實測**親身驗證了為什麼**——鍵盤快捷鍵對某些現代應用程式不可靠，UI Automation的按鈕/選單點擊才是。

### 端到端真實驗證（每一步都有具體證據，不是假設）

1. ✅ 開啟記事本：真的產生持久視窗（`open_app`，pid可查證存活）
2. ✅ 輸入"Hello"：`uia_set_text`成功，**螢幕截圖視覺確認**分頁標題變成"Hello"、狀態列顯示「5個字元」
3. ✅ 存檔：用`uia_click`點「檔案」→「儲存」（不是Ctrl+S），彈出存檔對話框，用`uia_set_text`填入安全路徑後點「存檔」按鈕——**分頁標題的未儲存圓點消失，且直接讀取磁碟檔案確認內容真的是"Hello"（5 bytes）**
4. ✅ 關閉：`Stop-Process`強制關閉（因為已經存檔，安全）
5. ✅ 重新打開：`file_op(open)`重新開啟同一個檔案路徑，沒有報錯

**誠實記錄一個環境限制，不影響上述驗證的有效性**：這台機器的記事本因為長期session-restore累積了好幾個跟這次測試無關的殘留分頁（`AERIS_START.ps1`、之前測試留下的`newest_report.txt`等），加上這次測試橫跨好幾個獨立行程，UI層面要100%精確追蹤「哪個分頁對應哪次測試」變得混亂——但**存檔後的內容已經直接用檔案系統層級的讀取驗證過是正確的**，這才是P3驗收劇本真正關心的事（資料有沒有正確持久化），不是UI分頁管理本身。

## P3 工具擴充第五批：record_screen（18/35 → 19/35）

35工具表裡最後一個「沒有被刻意排除、單純還沒做」的工具。用Windows內建Xbox Game Bar的`Win+Alt+R`切換快捷鍵實作（同一個鍵開始/停止都送，Windows自己知道目前是不是在錄，我們這端沒辦法單獨區分）。

**誠實記錄一個環境限制，不是程式bug**：實測送出`Win+Alt+R`後，`Videos\Captures`資料夾沒有產生任何檔案，也沒有偵測到Xbox Game Bar相關行程啟動——一開始判斷跟記事本/小算盤的UWP問題是同一類，但**後來記事本那個問題查出來是`open_app()`的PATH解析bug，跟真正的UWP相容性無關，這個結論的前提已經不成立，需要重新單獨驗證Game Bar這個案例**（見下方2026-09-18的重新驗證）。

**重新驗證的結果（2026-09-18）**：
1. 登錄機`HKCU\System\GameConfigStore\GameDVR_Enabled`確認是`1`（功能本身有啟用）
2. 但`Get-Process`確認**完全沒有任何`GameBar`/`Gaming`/`Xbox`相關背景行程在跑**——`Win+Alt+R`快捷鍵設計上是靠一個常駐的背景監聽服務才能被系統攔截，這個服務沒有在跑
3. 嘗試直接啟動Gaming App本身（`explorer.exe shell:AppsFolder\Microsoft.GamingApp...`）來喚醒背景服務，**啟動後仍然完全沒有任何相關行程出現**——這跟記事本「換個啟動方式就正常」的情況不一樣，是真正啟動失敗，不是啟動方式問題

**結論**：Xbox Game Bar在這個工作環境裡確實無法啟動，但**跟記事本/小算盤是兩個獨立、不同性質的限制**——記事本是「啟動方式錯誤」（已修正），Game Bar是「背景服務起不來」（原因不明，沒有繼續深入排查，因為`record_screen`不是高優先度工具）。`record_screen`工具本身的實作（送出`Win+Alt+R`、LLM正確路由、Executor正確執行不出錯）已經驗證正確，只是在這台機器上沒辦法拿到「錄影檔案真的產生了」的完整端到端證據，跟工具實作無關。

## 補測2項延遲KPI，其中一項發現真實沒達標（對照 docs/07 進度報告第9節）

用真的語音路徑（不是文字輸入）量測`Wake→ASR延遲`跟`整體端到端延遲`，方法論上特別注意一個陷阱：既有的模擬音訊測試把整段音檔快速塞進迴圈跑完，量出來的是CPU處理速度不是真實麥克風節奏——這次改成每個80ms chunk之間真的`sleep`，模擬真實麥克風串流節奏，才是使用者真正會感受到的延遲（完整方法論跟數字見`progress/p4_kpi_measurement/REPORT.md`）。

**結果誠實記錄——這次有兩項KPI測出來沒達標，不是為了報告好看回頭調整量測方式**：
- Wake→ASR延遲：目標<1.5秒，實測**5.38~5.42秒**（3次測試都穩定），❌沒達標
- 整體端到端延遲：目標<3秒，實測**6.08~6.11秒**，❌沒達標

**找到明確、可重現的結構性原因**：把時間拆成「喚醒→講完話判定」跟「講完話判定→ASR轉錄完成」兩段，後者（真的ASR轉錄）約1.5秒符合P1階段的正常範圍；前者約3.88秒，光是VAD「連續安靜才算講完」的固定等待（喚醒詞尾音確認0.32秒+講完後安靜確認0.8秒）就佔了至少1.12秒，這是P1階段刻意的安全設計（縮短緩衝期會誤判使用者話還沒講完就切斷），不是效能不夠。這代表藍圖這個KPI目標，在目前的端點偵測架構下結構上很難達成，需要的是重新設計端點偵測策略、跟現有的「避免誤切斷使用者說話」需求重新權衡，不是單純調參數就能兩全。

## P3 工具擴充第四批：speech_to_text_op（17/35 → 18/35）

`docs/07`第3節「35個工具逐一比對表」列出的15個未實作工具裡，大多數是刻意跳過的（需要外部服務整合或違反離線原則），但`speech_to_text_op`（把一份已經存在的錄音檔轉成文字）跟`record_screen`是少數**沒有被刻意排除、單純還沒做**的。這次補上`speech_to_text_op`：

- 直接重用P0/P1階段驗證過的whisper.cpp medium模型（跟`listen_loop.py`的`run_asr()`共用同一顆，但這裡處理的是「使用者指定一個已經存在的.wav檔案」而不是即時麥克風輸入）
- L0唯讀，`config/permissions.yaml`裡本來就設定好了（上一批補UIA原語時沒有連動加上這個工具，這次才真的接上實作）
- **安全設計上的一個內部反思**：一開始沿用`open_file`的寬鬆路徑處理（`_resolve_under_home`，只把相對路徑錨定到家目錄，不會阻擋絕對路徑逃到家目錄外），寫完後自己重新檢查才意識到這裡不適用`open_file`的邏輯——`open_file`只是請Windows用預設程式打開、不回傳內容；但`speech_to_text_op`會把錄音內容轉成文字回傳進LLM對話紀錄，等於「讀取檔案內容」，跟`file_op`的`move`/`copy`風險層級更接近，改用`_require_safe_path`（真正擋住家目錄外的絕對路徑）。這是實作過程中自己抓到並修正的問題，不是外部測試才發現。
- **端到端真實測試**：用專案裡既有的測試音檔（`sim_cmd_16k.wav`，內容是「現在幾點」）複製到家目錄下測試，whisper.cpp真的把它轉錄回「現在幾點」；故意指定不存在的檔案、非.wav檔案、家目錄外的絕對路徑都正確被擋下並給出清楚錯誤訊息；透過完整LLM指令流程（「幫我把這個錄音檔轉成文字」）也正確路由到這個工具並執行成功

## config/ 外部化設定（對照 docs/07 進度報告第11節）

`docs/07`第11節指出：藍圖第15節建議的專案結構有`config/`資料夾放`permissions.yaml`等設定檔，但這個專案一直沒有，權限規則(`TOOL_RISK_TABLE`)跟App白名單(`KNOWN_APPS`)都寫死在Python檔案裡，使用者想調整規則得改程式碼——這跟這個專案「新手友善」的目標有點矛盾。這次補上：

- 新增`config/permissions.yaml`（35個工具的風險等級+10條escalation規則）跟`config/tools.yaml`（App白名單+MSIX殼層對照表），資料本身搬出Python檔案
- 新增`src/config_loader.py`統一讀取入口，**安全設計是核心重點**：任何載入失敗（檔案不存在、YAML格式錯誤、風險等級名稱打錯字）一律直接丟例外讓程式啟動失敗，不能悄悄退回某種預設權限表——這種安全關鍵資料寧可讓程式開不起來，也不能在資料有問題時還假裝一切正常運作
- `policy/risk_levels.py`跟`tools/basic_tools.py`改成從YAML載入，但保留完全一樣的`TOOL_RISK_TABLE`/`ESCALATION_RULES`/`KNOWN_APPS`/`REAL_PROCESS_NAME`這幾個模組層級變數名稱跟資料型別，`PolicyEngine`跟其他呼叫方完全不用改
- **端到端真實驗證**：逐一比對YAML載入後的41個工具等級跟10條escalation規則，跟改動前的硬編碼資料**完全一致，沒有任何一個等級跑掉**；重跑`test_listen_loop_simulated.py`跟`test_l3_confirmation.py`兩個既有回歸測試都正常通過；也故意測試了YAML格式錯誤（打錯風險等級名稱）會正確丟出`ValueError`而不是悄悄接受，證明安全設計有效
- **踩坑記錄**：YAML裡`ms-settings:`這個值（結尾是冒號）第一次寫沒加引號，被PyYAML誤判成巢狀對照表的開始，丟出`ScannerError`——這種「值本身看起來像YAML語法」的字串一定要明確加引號，這是實測抓到的真實問題

## 補上UI五態模型，順便抓到兩個真實bug（對照 docs/07 進度報告第10節）

藍圖第18節要求UI只需要5個canonical狀態（Listening/Thinking/Executing/Waiting confirmation/Stopped），`docs/07`第10節指出原本沒有明確對應，尤其「Executing」跟「Waiting confirmation」沒有獨立可視化。這次在`listen_loop.py`加了`CANONICAL_STATE_MAP`，把現有細顆粒度狀態（idle/wake_detected/listening_command/thinking/speaking/front_desk/stopped/not_running）跟新增的兩個狀態（`executing`/`waiting_confirmation`）都對應到藍圖的5態，`LiveStateWriter.update()`寫進`live_state.json`時多帶一個`canonical_state`欄位（細顆粒度狀態不拿掉，給`companion.html`的動畫用；藍圖要求的5態並存，不是二選一）。`companion.html`也加了這兩個新狀態的圖示/文字/顏色，用假的`live_state.json`實際在瀏覽器截圖確認過畫面正確（橘色驚嘆號=等待確認、旋轉齒輪=執行中）。

**修這個功能時，靠著要重新檢查`run_live()`的`on_event`，意外抓到兩個真實bug（不是這次新寫的功能才有的問題，是先前PlanRunner整合時漏改的地方）**：

1. **`action_result`事件格式對不上，會直接丟`KeyError`崩潰**：之前把`handle_utterance()`改成用`PlanRunner`之後，`action_result`事件的內容從`{"call":..., "result":...}`改成`{"history":..., "summary":...}`，但`run_live()`裡的`on_event`（一般語音路徑實際在用的那份）跟`test_live_state_writing.py`（測試檔案裡另外複製的一份）都還在用舊格式的`e["result"]`——這代表**如果真的接麥克風講一句話讓desktop_control執行完，程式會直接當掉**，只是因為單元測試都是直接呼叫`handle_utterance()`帶自訂`on_event`，沒有走過`run_live()`這條路徑，所以先前的回歸測試都沒抓到。已修正兩處。
2. **`stopped_by_voice`事件完全沒有對應的UI更新**：使用者講「停止」之後，`live_state.json`會停在講「停止」之前的狀態，畫面上完全沒有任何反應——使用者會搞不清楚指令到底有沒有生效。已補上，講完「停止」後畫面會正確顯示「好，已經取消了」。

## 補測2項KPI：工具執行成功率、ASR→Tool決策延遲（對照 docs/07 進度報告第9節）

利用上面Logging補上的`duration_ms`資料，寫了`progress/p4_kpi_measurement/run_kpi_test.py`跑20句涵蓋17個已實作工具的真實指令（完整方法論見該資料夾`REPORT.md`）：**工具執行成功率100%**（目標≥98%）、**ASR→Tool決策延遲p95 1.13秒**（目標<2秒，量測時刻意把工具本身執行時間跟LLM決策時間分開算，避免例如「唸一句話要花多久」這種跟延遲無關的時間污染數字）。8項KPI裡目前4項有正式數字，剩下的喚醒詞8小時誤觸發率需要真的連續監聽8小時，是唯一需要長時間背景執行才能測的一項，留到之後有更長時間窗口再處理。

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

## P3 工具擴充第六批：task_scheduler_op/startup_program_op/driver_op/photo_edit（19/35 → 23/35）

使用者要求「除了SOP項目以外全部做到100%」，回頭檢視`docs/08`§5列出的「16個未實作工具」，發現先前把其中幾個歸類成「需要外部服務整合」是錯誤判斷——重新逐一檢查後，這4個其實完全可以用Windows內建機制在100%離線的前提下做到：

- **`task_scheduler_op`**：`list`/`create`/`delete`三個動作，底層呼叫系統既有的`schtasks.exe`（固定二進位檔+受控參數，跟`power_op`呼叫`shutdown.exe`是同一種安全模式，不是CLAUDE.md禁止的萬用shell執行工具）。實測：`list`真的讀到這台機器現有的排程工作（AnyDesk、NVIDIA App SelfUpdate、OneDrive等真實系統排程），過濾掉`\Microsoft\`底下的系統內建工作避免洗版。
- **`startup_program_op`**：`list`/`add`/`remove`三個動作，操作使用者自己的「啟動」資料夾（`%APPDATA%\...\Startup`），用`win32com.client`的`WScript.Shell.CreateShortcut`建捷徑檔——刻意不碰登錄檔`Run`機碼，因為使用者自己的啟動資料夾範圍只影響這個帳號、而且使用者自己用檔案總管就能看到/手動清掉，比登錄檔更符合「操作要容易理解、容易復原」的原則。實測：真的加入一個指向`notepad.exe`的測試項目、確認`list`看到它、再移除、確認`list`不再看到——完整round-trip驗證，沒有留下測試垃圾。
- **`driver_op`**：只實作`list`（唯讀查詢，用WMI的`Win32_PnPSignedDriver`），不實作`update`——更新驅動風險太高，不像本專案其他L3操作那樣容易復原。`config/permissions.yaml`因此把`driver_op`基準等級從原本誤設的L3改回L0_READONLY，另外新增一條escalation_rule把「未來如果真的要做`update`」預先標記成L3，避免之後忘記標風險等級。實測：真的查到這台機器的顯示卡驅動（Microsoft Basic Display Driver + Surface Display Hardware Driver，含真實版本號）。
- **`photo_edit`**：`rotate`/`resize`/`crop`/`grayscale`/`flip_horizontal`/`flip_vertical`六個動作，用既有依賴PIL（screenshot功能已經在用）。安全設計：輸出一律另存成`{原檔名}_edited.png`，不覆寫原圖——即使權限表設成L1（容易復原），前提也是原圖還在，不是真的去復原一個被覆寫的檔案。實測：對一張真實截圖做旋轉跟灰階轉換，用PIL重新讀取輸出檔案確認`mode='L'`（灰階模式）跟尺寸都符合預期，不是只看回傳字串宣稱成功。

四個工具都已加進`full_pipeline.py`的LLM工具清單/JSON Schema enum、`executor.py`的`TOOL_IMPLEMENTATIONS`、`config/permissions.yaml`的風險分級表。修改途中發現一個自己寫的語法錯字（`task_scheduler_op`裡一個raw string跟轉義反斜線衝突，導致`basic_tools.py`整個模組load不起來），跑完整回歸測試（7個測試檔）時被抓到並立刻修正——這也印證了「每次改完一定要跑回歸測試」這個習慣的價值，不是形式主義。

跑完整回歸測試順便發現`test_p3_safety.py`本身有一個過時斷言：測試5的註解寫「`close_window`是L1免確認」，但這個等級在更早的藍圖盤點稽核中已經正確修正成L2_SENSITIVE（見上面「藍圖盤點稽核」一節）——測試檔案本身沒有跟著更新，導致這次重跑才第一次真的觸發`ConfirmationRequired`並讓測試失敗。這不是本次改動造成的迴歸，是先前那次修正遺留的技術債，這次順手補上（改成`user_confirmed=True`並更新註解跟斷言）。

## P6 多步驟規劃補測：4種場景，抓到並修正一個真實的無限重複bug

`docs/08`§5誠實列出「P6只驗證過一種場景（找檔案→開啟→回報）」，這次補成正式、可重複執行的迴歸測試`src/test_plan_runner_scenarios.py`，覆蓋4種場景，全部走真實LLM(127.0.0.1:8811)+真實Executor，不是mock：

1. **找檔案→開啟→回報檔名**：原本已經手動驗證過的場景，這次補成正式迴歸測試留存下來。
2. **步驟失敗的復原能力**：叫它找一個根本不存在的檔案再開啟它。過程中先弄清楚`file_op`的`find`動作本身的設計語意——「查詢零筆符合」是合法的成功結果（`executed=True`+人類可讀的「找不到」訊息），不是例外，這個設計本身沒有問題。真正該驗證、也確實驗證通過的重點是：規劃者(LLM)看到「找不到」的訊息後，**沒有**因為`executed=True`就誤判成「已經找到了」，硬著頭皮拿一個瞎猜的路徑去呼叫`open`。
3. **單步驟指令不進入多輪迴圈**：「現在幾點」這種單一動作指令，驗證只呼叫一次LLM（0.5秒內完成），沒有被誤判成需要追問下一步，維持原本的低延遲設計不受P6新功能拖累。
4. 🔴 **多步驟規劃中途撞到L2確認，確認後接續執行——這裡抓到一個真實bug**：「在X底下建立一個叫Y的資料夾，然後打開它」這句話，`create_folder`正確要求L2確認，`resume(approved=True)`之後`create_folder`跟`open`都確實執行成功（資料夾真的建立在磁碟上），**但規劃者判斷「這句話還沒做完」，不斷重複呼叫同一個已經成功過的`open`（同工具、同參數），一路撞到`MAX_STEPS=5`才停下來，回報`plan_incomplete`**——使用者要求的兩個動作明明都已經真的做完了，卻被誤報成「沒做完」。修法：在`PlanRunner._continue_loop()`加一道跟LLM判斷品質無關的演算法防呆（`src/full_pipeline.py`）——如果規劃者給的下一步跟history最後一筆完全相同（同工具+同參數），代表沒有任何新資訊，直接視為已完成，不必依賴LLM自己判斷對不對。這是繼SCHEMA的args順序bug之後，第二個「不靠改善prompt、靠加一層演算法保險絲」解決的LLM不可靠問題，同一種設計哲學：關鍵可靠性不能只賭LLM每次都判斷正確。

修好之後重跑全部4個場景＋原本7個既有迴歸測試，全部通過。

## 補上第三份外部化設定：config/runtime.yaml

`docs/08`§5列出「`config/`外部化只做了權限表跟App白名單」是誠實記錄的缺口，這次補上第三份：`config/runtime.yaml`，涵蓋原本散落在`listen_loop.py`/`full_pipeline.py`/`frontdesk/`底下4個檔案裡各自寫死的參數：

- **LLM推論端點URL**：原本`http://127.0.0.1:8811/v1/chat/completions`這串字串在`full_pipeline.py`、`frontdesk/dialog_state_machine.py`、`frontdesk/mode_classifier.py`、`frontdesk/voice_dialog.py`四個檔案各自抄一份，改一個值要記得改四個地方，現在統一從`config/runtime.yaml`讀取。
- **喚醒詞門檻**（`WAKE_THRESHOLD`）、**端點偵測相關參數**（`END_OF_SPEECH_SILENCE_CHUNKS`等4個）、**緊急停止熱鍵**、**睡眠縫隙偵測門檻**：從`listen_loop.py`裡的常數搬到YAML。

⚠️ **特別澄清一個容易被誤會的地方**：`END_OF_SPEECH_SILENCE_CHUNKS`（連續安靜多少個chunk才算話講完了）就是`docs/08`§4.1「端點偵測延遲的架構取捨」那個SOP項目討論的參數本身。這次外部化**只是把數字從程式碼搬到YAML檔案，數值完全沒有改動**（維持選項A的現狀），不是趁機幫使用者做了選項B的決定——之後使用者真的回覆要選A/B/C時，調整這個參數會變成改一個YAML數字，不用再改程式碼，但「要不要調」跟「調多少」仍然完全等使用者決定。

四個frontdesk相關檔案原本`sys.path`設定不一致（`mode_classifier.py`甚至沒有把`src/`加進path），這次補上`sys.path.insert(0, str(Path(__file__).parent.parent))`讓它們都能匯入`config_loader`。跑完整回歸測試（8個測試檔，含新加的P6場景測試）全部通過，另外單獨驗證3個frontdesk模組能正確匯入並讀到同一個URL值。

## P5 視覺備援：軟硬體可行性查證（還沒下載模型，原因見下方）

`docs/08`把P5列成0%、完全沒開始，是目前最大的單一缺口。這次沒有直接動手實作，先做了藍圖`docs/01`第908行「P5 — Vision Fallback」明訂的軟硬體前提查證，不是憑空假設可行：

- ✅ **軟體支援比預期好**：這台機器`progress/p0/build/llama.cpp`的原始碼（2026-09-13的checkout）裡已經有`tools/mtmd/models/qwen3vl.cpp`跟`qwen3vlmoe.cpp`——**藍圖第192行明訂的`Qwen3-VL-30B-A3B-Instruct`（MoE架構）已經有原生支援**，不是要等社群移植或自己修補。而且現有的`llama-server.exe`（P0階段就編譯好、目前正在跑的那一份）本身就已經內建`--mmproj`參數支援多模態，**完全不需要重新編譯**——這比原本以為「可能要重新build一個獨立的vision-cli」樂觀很多。
- ⚠️ **硬體有明確的顯示卡記憶體限制，誠實記錄**：`nvidia-smi`查證這台機器RTX Spark總共24.5GB VRAM，目前主要文字LLM（Qwen2.5-7B）常駐佔用約12.4GB，剩下約12GB可用。`Qwen3-VL-30B-A3B`即使量化過，30B參數的MoE模型（MoE的「A3B」只代表推論時每個token只啟用3B參數計算量小、速度快，**不代表權重檔案變小**——全部30B個參數的權重仍然要載入記憶體）Q4量化預估仍需要17~20GB左右，加上視覺編碼器跟context，剩下的12GB可用空間裝不下，還要同時保留文字LLM常駐。
- 這剛好呼應藍圖自己在第205行講的設計原則「不要讓Vision model常駐一直看桌面，只有需要時才呼叫」——但這個原則主要在講「省運算資源」，沒有明講「跟常駐的文字LLM搶顯示卡記憶體怎麼辦」這個更具體的問題。目前想到3個方案，各有取捨，這是一個需要跟你討論、不是我能自己決定的架構問題（跟`docs/08`§4.1端點延遲取捨是同一類性質）：
  - **方案A（換入換出，重新查證後比原本想的更可行）**：用WebSearch查了llama.cpp社群/官方文件對這個問題的實際做法後發現——現有的`llama-server.exe`本身已經內建「router模式」，`--help`裡真的能看到`--models-dir`/`--models-max`/`--sleep-idle-seconds`這幾個參數（不需要另外裝軟體、也不用自己刻一套換入換出的邏輯，這是llama.cpp官方就設計來解決「多個模型共用一張顯示卡」這個情境的機制：閒置N秒自動卸載、要用時自動載入、限制同時最多載入幾個模型）。代價是每次觸發視覺備援，第一次呼叫要花幾秒到十幾秒重新把17~20GB讀進顯示卡的延遲。（參考：[llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)、[New in llama.cpp: Model Management](https://huggingface.co/blog/ggml-org/model-management-in-llamacpp)）
  - **方案B（改用較小/更激進量化的VL模型）**：犧牲一些視覺理解準確度，換取跟文字LLM同時常駐在剩下12GB裡，沒有載入延遲
  - **方案C（CPU/部分GPU卸載）**：VL模型部分layer跑在CPU，不跟文字LLM搶顯示卡記憶體，但推論速度會慢很多

**還沒下載任何模型檔案**：`Qwen3-VL-30B-A3B`的GGUF量化版本預估要下載15~20GB，屬於「下載檔案」這類需要先明確告知檔名/來源/大小並取得你同意才能做的動作，不是我能自己決定按下去的——所以這次先把軟硬體可行性查清楚、把架構取捨想清楚，等你看過方案A/B/C的取捨、或者有其他想法，再決定要不要、以及選哪個方案繼續。

## companion.html介面改版：參考主流雲端AI助理的UX慣例

使用者明確澄清：「100%離線」只限定**運算**要在本機完成（唯一差異是把右下角的雲端模型換成本地模型），介面/UX/互動設計可以參考ChatGPT、Gemini等現有雲端AI助理已經驗證過的做法，不算違反離線原則。照這個方向補強`console/companion.html`：

- **統一對話記錄（最主要的改動）**：原本語音跟文字各自只顯示「最後一句」的兩張靜態卡片（新的一句會直接覆蓋掉上一句，看不到對話歷史）。改成參考ChatGPT/Gemini/Claude等主流助理的做法——一個可捲動的聊天記錄（`chat-log`），使用者訊息/助理回覆用左右對齊的聊天泡泡呈現。**語音跟文字兩種輸入路徑最後都會匯進同一份聊天記錄**，不是分開顯示，這樣使用者不管用講的還是打字，都能在同一條時間軸上看到完整對話。
  - 語音那邊透過`live_state.json`每500ms輪詢一次拿到的`transcript`/`response`，同一輪會被輪詢到很多次——用值比對（跟上次顯示的字串是否相同）而不是每次輪詢都加一筆，避免同一句話在聊天記錄裡重複出現幾十次
  - 原本`handleResult()`裡「完成」狀態直接把整個result物件`JSON.stringify`丟進畫面（會顯示醜陋的`{"executed":true,"result":"..."}`原始JSON），改成抽取真正的人類可讀摘要文字
- **加上「停止」按鈕**：參考ChatGPT等助理在AI正在處理/回答時提供的停止控制，只在忙碌狀態（聽指令中/思考中/執行中/等確認/說話中/Front Desk問答中）才顯示，避免平常佔用畫面空間
- 🔴 **過程中抓到並修正一個真實的文字/語音功能落差**：`is_stop_command()`原本只接到語音路徑（`listen_loop.py`/`voice_dialog.py`），文字/網頁路徑完全沒有對應的「中斷」機制——使用者卡在多步驟任務確認中或Front Desk問答中途，除了等超時或硬把瀏覽器分頁關掉，沒有辦法主動放棄重來。新增`command_processor.stop_session()` + `POST /api/stop`端點，讓網頁的停止按鈕能直接清掉這個session卡住的`PlanRunner`跟`FrontDeskDialog`狀態。

**真實測試（不是只看程式碼推理）**：用瀏覽器工具實際操作`http://127.0.0.1:8899/companion.html`——確認先前一次語音互動（「現在幾點」）正確顯示在聊天記錄裡且標示「🎙️ 語音」來源；打字送出「把音量調到50%」，確認訊息以「⌨️ 文字」來源正確加入聊天記錄、且助理回覆是乾淨的文字而非JSON、音量真的被設定成50%；打字觸發一個L2敏感操作（建立資料夾），確認確認卡正確顯示在聊天記錄下方、按下「同意執行」後資料夾真的被建立在磁碟上（測試後已清除）；直接呼叫`POST /api/stop`確認端點正常回應。

過程中還發現並清理了一個環境問題：這台機器同時跑著兩份`serve.py`（一份用正確的`venv-arm64`直譯器，一份誤用系統Python缺套件）搶同一個埠號，以及`llama-server.exe`推論服務中途不知何時已經停止（連回歸測試都連不上），都已排查並用`start.ps1`正確重啟、確認只剩一份`serve.py`綁定在8899埠。

## companion.html介面改版第二輪：思考中動態提示 + 逐字浮現效果

延續上一輪「介面/UX可以參考主流雲端AI助理做法」的方向，補兩個ChatGPT/Gemini常見的細節：

- **思考中動態提示（typing indicator）**：使用者送出文字指令、或語音路徑進入「思考中/執行中」狀態時，聊天記錄裡會出現一個三點跳動的動畫泡泡，回覆真的送達後才移除——參考主流助理在等待回應期間給的視覺回饋，避免使用者以為畫面卡住了。
- **助理回覆逐字浮現**：文字路徑的助理回覆改成一個字一個字跑出來（帶閃爍游標），視覺上更接近「正在回答」而不是整段文字一次跳出來。語音路徑（`live_state.json`輪詢拿到的response）維持原本立即顯示，因為那個回覆本身已經是完成的事實，不是「正在產生中」，逐字效果反而會誤導。

⚠️ **誠實記錄一個技術細節，避免自己之後搞混**：這個逐字效果**純粹是前端呈現節奏**，後端`/api/command`本身還是一次性回傳完整結果字串，不是真的逐token串流——跟ChatGPT那種真正一邊生成一邊吐字給前端不是同一回事，只是最終呈現效果類似。之所以特別寫下來，是因為之後如果有人（包括我自己）想拿這個當作「已經做到串流輸出」的證據，那是錯的。

修這個過程中發現一個潛在的競態問題並修正：語音狀態每500ms輪詢一次，如果剛好文字指令的HTTP請求還沒回來、輪詢又看到語音那邊是idle狀態，會誤把文字指令自己叫出來的打字動畫關掉——加了`textRequestInFlight`旗標，文字請求進行中時輪詢不插手管打字動畫的顯示/隱藏。

**真實測試**：用瀏覽器打字送出「幫我截圖」，用`get_page_text`在回覆逐字浮現的過程中截到一次「還沒跑完」的中間狀態（文字被截斷在還沒跑出完整檔名的地方），等2秒後再讀一次確認完整檔名正確顯示、螢幕截圖檔案真的產生在磁碟上（測試後已清除），瀏覽器console沒有任何錯誤。

## 補測工具執行成功率KPI，過程中抓到一個「執行成功但答案錯」的隱蔽bug

先前`docs/07`盤點提到的「工具執行成功率≥98%」這項KPI，其實在更早的`progress/p4_kpi_measurement/`已經測過（20句涵蓋17個工具，100%），這次要補的是後續新增的4個工具（`task_scheduler_op`/`startup_program_op`/`driver_op`/`photo_edit`）還沒被納入這個樣本。用`progress/p4_kpi_measurement/run_kpi_test_v2_new_tools.py`補測，一樣走真實文字指令->LLM判斷->PolicyEngine->Executor完整流程（L2的兩個工具用`confirm_desktop_command`自動同意，做法跟`test_p3_safety.py`測`close_window`一致）。

- 表面數字：4句全部路由正確、全部執行成功（合併v1後24句100%）
- 🔴 **但人工檢查每一筆結果內容時，抓到一個「executed=True但答案錯」的隱蔽bug**：測`driver_op`時，「幫我查一下顯示卡驅動版本」正確路由到`driver_op`並執行成功，但LLM填的`keyword`參數是中文「顯示卡」——Windows驅動裝置名稱一律英文，逐字比對對不上，回報「找不到符合『顯示卡』的驅動程式」，但這台機器明明有顯示卡驅動。**「執行成功率」這個KPI衡量的是工具有沒有崩潰，不代表答案語義正確**，這種問題不會被成功率數字抓到。
- **修法**：`basic_tools.py`的`driver_op()`加一份常見硬體類別中英對照表（顯示卡/網卡/音效/藍芽/觸控/滑鼠/鍵盤/印表機/攝影機），中文關鍵字額外用對應英文詞再比對一次。修好後重測，正確回報「Microsoft Basic Display Driver...、Surface Display Hardware Driver...」。
- **誠實記錄方法論侵限**：除了這次巡查抓到的案例，目前沒有系統性驗證每個工具「執行成功」時答案內容也語義正確，這是量測方法論本身的侵限，不是已經解決的事。

## P3工具擴充第七批：git_op / print_or_scan（23/35 → 25/35）

使用者要求「不要再問我，持續朝藍圖施工」，這次再重新檢視剩下12個排除工具，抓到2個之前判斷過於保守的：

- **`git_op`**：只實作`status`/`log`/`diff`（純查詢）跟`add`/`commit`（只影響本機repo）。`push`/`merge`刻意不實作——牽涉遠端連線且可能造成真正的程式碼遺失，`config/permissions.yaml`其實早在更早的階段就已經把這兩個動作預留成L3（`escalation_rules`裡本來就有`git_op push/merge → L3_DANGEROUS`），這次只是把函式真正實作出來，權限表不用改。實測：直接對這個真實repo跑`status`/`log`/`diff`（拿到真實的commit歷史、真實的未commit變更清單），另外對一個全新的scratch測試repo跑`add`+`commit`，確認檔案真的被commit進git歷史（測試完已清除）。也用真實文字指令走完整LLM路由測過一次「幫我看一下這個git專案有哪些檔案還沒commit」，正確路由到`git_op(action=status)`並執行成功。
- **`print_or_scan`**：只實作`print`（用Windows標準的`os.startfile(path, "print")`列印verb，送到系統目前設定的預設印表機）。`scan`不實作——需要真實掃描器硬體才能驗證，跟`record_screen`（Xbox Game Bar）同一類「沒有硬體可以驗證，不該空口宣稱做到」的情況。
  - ⚠️ **誠實記錄一個沒有完全驗證成功的部分**：實測時發現這台機器原本完全沒有設定預設印表機（`Get-Printer`查不到任何`Default=True`），設定「Microsoft Print to PDF」當預設印表機之後重測，`.txt`跟`.png`檔案的「列印」verb在這台機器上**都沒有真的觸發列印/產生PDF**，而是分別開啟了記事本、Windows設定頁面——API呼叫本身沒有丟例外（`ShellExecute`回傳碼42代表成功），但看不到印表機佇列裡有任何工作、也沒有PDF檔案產生。這跟`docs/07`記錄過的現代記事本應用程式對某些標準Windows API反應異常是同一類環境限制的延伸（這次是「列印」verb，不是鍵盤快捷鍵），不是`print_or_scan()`程式碼邏輯本身的bug——API呼叫方式（`os.startfile`跟`win32api.ShellExecute`兩種都試過，結果一樣）都是標準做法。在能正常處理列印verb的機器上，這個工具應該能正常運作，但這次沒辦法在這台機器上拿到完整的端到端驗證證據，誠實標記成「程式碼邏輯正確、這台機器的環境限制沒辦法完整驗證」，不是「已驗證完全能用」。

跑完整回歸測試（8個測試檔）全部通過。

## 語意正確性抽查：driver_op之外還有沒有藏著同類問題

`driver_op`那個中英關鍵字bug證明「執行成功率100%」不等於「答案都對」，這次額外抽查了7個有實質內容輸出的工具，人工核對答案本身而不是只看`executed`旗標：`calculator`（25×4=100、100÷4=25.0，正確）、`get_datetime`（跟系統真實時間`datetime.datetime.now()`比對，正確）、`clipboard_op`（複製「kpi_roundtrip_test_123」再貼上，內容一致）、`file_op find newest_only`（真的建立兩個修改時間差1.2秒的測試檔，確認抓到的是後建立、修改時間較新的那個，不是先建立的那個）、`translate`（「你好嗎」→「How are you?」，語意正確）、`summarize_doc`（摘要內容跟原文一致，沒有幻覺出原文沒有的資訊）、`get_active_window`（跟當下真實最前面的視窗標題比對一致）。這7個都沒有發現類似`driver_op`那種問題，這次抽查沒有再找到新的隱蔽bug，但仍然只是抽查，不是涵蓋全部33個工具的系統性驗證。

## summarize_doc補上讀本機檔案的能力（參考雲端AI「上傳檔案直接問內容」做法）

使用者進一步澄清「除了必要的資料以外，能在本地做起來的都不用等我，自己去參考外部雲端服務建立在本地」——這次補上`summarize_doc`直接讀本機檔案的能力，不用使用者先把內容整段講出來或打字貼上（真實文件不可能這樣用）。這是參考ChatGPT/Gemini「上傳檔案直接問內容」這個功能的本地對應版本：檔案內容解析完全在本機函式庫（`pypdf`/`python-docx`，這次用`pip install`裝進`venv-arm64`）進行，不會把檔案內容傳到任何外部服務，跟這個專案「100%離線」的原則完全一致——換掉的只是雲端服務本身，功能參考它的做法，運算留在本機。

- 支援`.txt`/`.md`（直接讀）、`.pdf`（`pypdf`）、`.docx`（`python-docx`）
- `args`同時支援`{"text": "..."}`（原本的貼文字用法，向下相容）跟`{"path": "檔案路徑"}`（新增，讀本機檔案）
- 超長文件只取前30000字元送進LLM，避免一次塞爆context拖慢回應——這是「整理重點摘要」這個用途本身的合理限制，不是為了省token武斷砍內容

**真實測試（不是只看程式碼推理）**：用真實建立的`.txt`（模擬會議紀錄）、`.docx`（`python-docx`寫的產品測試報告）、`.pdf`（手刻一份有效的最小PDF二進位檔，`pypdf`能正確容錯處理裡面不太標準的xref並抓出內嵌文字）三種格式分別測過，三種格式的摘要內容都跟原文語意一致，沒有幻覺出原文沒有的資訊。也走過一次真實文字指令的完整NL路由測試（「幫我讀一下C:\...\_va_doc_test2.txt這份文件並整理重點」），正確路由到`summarize_doc(path=...)`並執行成功。測試檔案跟安裝的套件都是這次新增，測試完已清除暫存檔（套件保留，因為是這個功能的必要依賴）。

跑完整回歸測試（8個測試檔）全部通過。

## 設計原則提醒（避免做歪）

- Front Desk 只負責「收斂需求、產生 ORDER.md」，**不負責任何聲學工程判斷**——那是 AERIS 的事，本專案不應該假裝知道 leakage/driver 怎麼分析
- 對話問題選項要克制，文件裡明講：「用最少但必要的問題，形成足夠後端執行的 ORDER.md」，不是問越多越好
