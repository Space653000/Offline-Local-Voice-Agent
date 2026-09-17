# AERIS — 100 位聲學工程師、本地 AI 架構與前端 Navigator 完整對話紀錄

- 文件日期：2026-09-14
- 文件性質：目前此對話中，關於 AERIS「100 位聲學工程師 / 前端 / 後端 / 本地 AI / Capability Contract」之完整整理紀錄
- 目的：作為 AERIS 後續設計、Claude Code 施工、Capability Manifest、測試與驗收的基準文件
- 原則：保留本次對話中已確認的架構與能力定義，不額外加入新的產品路線干涉
- 注意：本文件只整理使用者與 Assistant 可見對話內容，不包含系統提示、內部推理或隱藏指令

---

# 0. 本次對話的核心問題

本次對話聚焦於以下幾個問題：

1. AERIS 的「100 位聲學工程師」到底是真功能，還是只有角色名稱？
2. 每一位聲學工程師的能力是否能具體化、工程化、驗證？
3. AERIS 是否需要一個偏前端的 AI 頁面，幫助使用者收斂問題、發散問題並導入後端專家？
4. 前端應該使用什麼模型？
5. AERIS 是否一定需要雲端 AI？
6. 前端、後端、LLM、RAG、資料庫、工具調度、報告是否都能本地化？
7. 100 位聲學工程師要如何定義能力、技能、功能與使用方法？
8. 如何避免最後變成「100 個人格 Prompt」，而是真正可以工作的聲學工程 AI 系統？

---

# 1. 對話原始紀錄 — 第一階段

## User

> AESIR這種設計 就像後端和資料庫  
> 他那100聲學工程師 真的有功能嗎？  
> 你有條列出來嗎？  
> 或是每一個工程師的能力有辦法具體化嗎？  
> 那AERIS本地AI真的能做的嗎?不能理解？  
>
> 但這樣感覺就是還需要有一個偏前端的頁面來輔助使用者來收斂問題和發散問題去導入使用AERIS?  
> 而這個前端要用哪個模型？

---

## Assistant 回覆重點

### 1.1 AERIS 不應只有後端 100 位聲學專家

AERIS 本體比較像：

- 後端專家系統
- 工具鏈
- 知識庫
- 資料庫
- RAG
- 工程計算與量測工具

但前面仍需要一層真正面向人的：

> **AI 前台 / 問題導航層**

也就是：

> **AERIS Navigator**

---

### 1.2 100 位聲學工程師不是 100 個 LLM

100 位聲學工程師不能只是 100 個名字，也不是要在記憶體中同時執行 100 個模型。

正確概念是：

> **1 個或少數幾個強大的本地模型 + 100 套專業能力 + 不同工具 + 不同知識 + 不同驗收規則**

概念架構：

```text
                    ┌───────────────┐
                    │ Shared LLM    │
                    │ Qwen3 30B     │
                    └───────┬───────┘
                            │
             載入不同 Capability Contract
                            │
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
     SPK-012              MIC-007             QA-004
     Speaker              Mic Port            Failure
     Engineer             Engineer            Engineer
```

---

### 1.3 每一位工程師必須有 Capability Contract

一位真正可用的 AERIS Engineer 不能只有一句：

> 你是一位 Micro Speaker 專家。

必須至少具備：

| 模組 | 內容 |
|---|---|
| Role | 專家角色 |
| Knowledge | 專業知識範圍 |
| Measurements | 能處理的量測 |
| Tools | 可使用工具 |
| Inputs | 所需輸入 |
| SOP | 執行流程 |
| Outputs | 輸出格式 |
| Boundary | 不可越界的範圍 |
| Escalation | 無法確認時升級給誰 |
| Evaluation | Golden cases / regression tests |
| Evidence | 每個結論所依據的證據 |

---

### 1.4 Capability Contract 範例

**AERIS-SPK-012 — Micro Speaker Transducer Engineer**

| 模組 | SPK-012 實際內容 |
|---|---|
| Role | Micro Speaker Transducer Engineer |
| Knowledge | T/S、BL(x)、Cms(x)、Le(x)、thermal、excursion |
| Measurements | SPL、THD、Impedance、Rub & Buzz |
| Tools | Klippel、APx、Python、MATLAB、CSV parser |
| Inputs | FR、IMP、THD、voltage、distance、sample info |
| SOP | 資料檢查 → 異常判定 → Root Cause → 建議 |
| Outputs | Diagnosis + Evidence + Confidence |
| Boundary | 不擅自判斷未量測的 failure mechanism |
| Escalation | 無法確認 → 丟給 ME / Speaker Chief / Simulation |
| Evaluation | Golden cases、bad cases、regression tests |
| Evidence | 每個結論必須指出數據來源 |

使用範例：

> 「1 kHz 以下 SPL 掉 4 dB，THD 也變差，是什麼原因？」

SPK-012 不應該直接猜答案，而應執行：

1. 檢查資料完整度
2. 比較 impedance
3. 檢查 excursion
4. 檢查 vent / leakage
5. 檢查 BL / Cms / thermal
6. 建立 hypothesis
7. 指定下一個驗證實驗

---

# 2. AERIS Navigator — 前端 AI 問題導航層

普通使用者不會知道自己應該找哪一位 AERIS Engineer。

例如：

> 「我的 speaker 聽起來怪怪的。」

所以需要：

> **AERIS Navigator**

它不是聲學工程師本身，而是：

> **把人的模糊問題，轉換成 AERIS 可以處理的工程問題。**

---

## 2.1 AERIS Navigator 架構

```text
使用者
   ↓
┌──────────────────────────┐
│ AERIS Navigator          │
│ 問題導航 / 對話 / GUI     │
└────────────┬─────────────┘
             ↓
      Requirement Canvas
             ↓
┌──────────────────────────┐
│ AERIS Task Router        │
└────────────┬─────────────┘
             ↓
      自動建立 Engineer Pod
             ↓
 ┌────────┬────────┬────────┐
 SPK-012   ME-006   SIM-003   QA-004
 └────────┴────────┴────────┘
             ↓
      Python / APx / Klippel
      COMSOL / DB / RAG
             ↓
       Chief Reviewer
             ↓
          結論
```

---

## 2.2 Navigator 必須負責「收斂 + 發散」

輸入：

> Speaker 低頻不好。

Navigator 不應直接開始回答，而應引導：

```text
Speaker 低頻異常

可能方向：

□ SPL 不足
□ F0 異常
□ THD 太高
□ Buzz / Rattle
□ Bass extension 不足
□ 箱體 leakage
□ Port tuning
□ excursion 過大
□ 不確定 → 幫我診斷
```

例如選：

> SPL 不足

再繼續收斂：

```text
產品類型？
Notebook / Tablet / Phone / Smart Speaker / Other

是否有量測資料？
APx / SoundCheck / Klippel / CSV / 沒有

比較對象？
Golden Sample / Previous EVT / Spec / Competitor
```

最後轉成正式工程問題：

```text
Problem:
Low-frequency SPL degradation

Product:
Notebook

Frequency:
180–500 Hz

Delta:
-4.2 dB

Available data:
FR + Impedance + THD

Suggested specialists:
SPK-012
ENC-004
ME-008
QA-003
```

---

# 3. 前端模型與後端模型分工

在本次對話中，AERIS 正式運作的方向為：

> **100% 本機**

因此正式產品的前台不必依賴 Claude 或 GPT API。

---

## 3.1 建議模型分工

### AERIS Frontend / Navigator

```text
AERIS FRONTEND
─────────────────────────
Qwen3 30B Instruct
↓
理解中文
追問問題
問題收斂
問題發散
Requirement extraction
推薦專家
建立 Task
```

### AERIS Backend

```text
AERIS BACKEND
─────────────────────────
Qwen3 30B
+
100 Capability Contracts
+
RAG
+
Engineering Skills
+
Tools
```

### Coding / Automation

```text
CODING / AUTOMATION
─────────────────────────
Qwen3-Coder 30B
↓
Python
Parser
Automation
測試程式
資料處理
```

---

## 3.2 Claude Code 的角色

Claude Code / Sonnet 類雲端模型適合用於：

- 開發 AERIS
- 寫 Frontend
- 建立 Capability Framework
- 建立 100 Engineers
- 建立 Golden Tests
- 建立工程程式與自動化

但 AERIS 正式運作不必綁定 Claude API。

也就是：

```text
開發 AERIS
     ↓
Claude Code
     ↓
寫 AERIS Frontend
寫 Capability Framework
建立 100 Engineers
建立 Golden Tests
```

而不是：

```text
AERIS正式產品
     ↓
必須依賴 Claude API
```

---

# 4. 第一版四層 AERIS 定義

```text
┌──────────────────────────────────┐
│  L1  AERIS Navigator             │
│  Qwen3 30B                       │
│  使用者對話 / 收斂 / 發散         │
├──────────────────────────────────┤
│  L2  AERIS Orchestrator          │
│  Router / Planner / Engineer Pod │
├──────────────────────────────────┤
│  L3  100 Acoustic Engineers      │
│                                  │
│  Role + Knowledge + Skill        │
│  SOP + Tools + Tests + Evidence  │
├──────────────────────────────────┤
│  L4  Engineering Infrastructure │
│                                  │
│  RAG / DB / APx / Klippel       │
│  Python / MATLAB / COMSOL / Git │
└──────────────────────────────────┘
```

說明：

- L1：前台
- L2：工頭 / Orchestrator
- L3：真正的 100 位聲學工程師
- L4：實驗室 + 資料庫 + 工具箱

---

# 5. 對話原始紀錄 — 第二階段

## User

> 難道一定要雲端AI執行和前端和 後端嗎？  
> 可以本地化嗎？  
> 請條列這100聲學工程師各自每一個能力和技能和功能和使用手冊

---

# 6. 是否一定需要雲端 AI？

答案：

> **不需要。AERIS 的前端、後端、模型、資料庫、RAG、工具調度、報告產生都可以本地化。**

真正要避免的是：

> 把 100 位工程師誤做成 100 個模型。

最佳做法：

> **1～3 個本地模型 + 100 份能力合約 + 工具 / RAG / 驗收規則**

---

# 7. 100% Local AERIS 完整架構

```text
使用者瀏覽器
http://localhost:xxxx
        │
        ▼
┌────────────────────────────┐
│ AERIS Frontend             │
│ 問題導航 / 上傳 / 圖表 / 報告 │
│ 深色 / 淺色 / 中英切換       │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│ AERIS Navigator            │
│ 本地 General LLM           │
│                            │
│ 模糊問題→工程問題            │
│ 收斂 + 發散 + 追問           │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│ AERIS Orchestrator         │
│ 任務拆解 / 專家選擇 / Review │
└─────────────┬──────────────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 Engineer   Engineer   Engineer
   #12        #23        #86
    │          │          │
    └──────────┼──────────┘
               ▼
┌────────────────────────────┐
│ Local Engineering Tools    │
│ Python / MATLAB / COMSOL   │
│ APx / Klippel / SoundCheck │
│ CAD / CSV / Excel          │
└─────────────┬──────────────┘
              ▼
┌────────────────────────────┐
│ Local Knowledge + Database │
│ Specs / SOP / DOE / Report │
│ Vector DB + SQL + Files    │
└────────────────────────────┘
```

---

# 8. 本地模型分工原則

| 工作 | 本地模型 |
|---|---|
| AERIS Navigator | General / Instruct 30B 級 |
| 100 位工程師推理 | 同一顆 General 30B 為主 |
| Python、Automation、API | `qwen3-coder:30b` |
| 快速分類 / Router | 小型 3B～8B，甚至可以不用 LLM |

概念：

```text
同一顆腦
+
100 個不同職務說明
+
100 套知識範圍
+
100 套工具權限
+
100 套 SOP
+
100 套驗收題庫
```

---

# 9. 真正可工作的 AERIS Engineer 最低規格

每一席至少需要：

```yaml
engineer_id:
role:
scope:
knowledge:
skills:
tools:
required_inputs:
optional_inputs:
workflow:
output_schema:
boundaries:
escalation:
golden_tests:
evidence_policy:
```

若只有：

> 「你是一位 Speaker Engineer。」

那只是 Prompt Persona，不是工程能力模組。

---

# 10. AERIS 100 位聲學工程師 Capability Map v1.0

---

## A. Chief / Engineering Governance：001–010

| ID | 工程師 | 核心能力 | 技能 / 工具 | 使用方式 |
|---|---|---|---|---|
| 001 | Chief Acoustic Architect | 全系統聲學架構 | System decomposition、trade-off | 給產品需求 → 建立聲學架構、風險與技術路線 |
| 002 | Acoustic Requirement Engineer | 規格定義 | KPI、spec flow-down | 給產品需求 → 轉 SPL、THD、SNR、NR 等可驗證規格 |
| 003 | Acoustic Design Reviewer | Design Review | Checklist、evidence review | 上傳設計與數據 → 找缺口、風險、待驗證項 |
| 004 | Acoustic Failure Review Chief | 跨領域故障判讀 | RCA、FTA、5 Why | 給 failure → 組建 RCA 專家小組 |
| 005 | Acoustic Experiment Chief | 實驗策略 | DOE、A/B、control variables | 給問題 → 產生最低成本驗證計畫 |
| 006 | Acoustic Risk Engineer | 技術風險管理 | FMEA、risk matrix | 給 architecture → 輸出風險排序與 mitigation |
| 007 | Acoustic Statistics Engineer | 統計判讀 | Cp/Cpk、ANOVA、CI | 給大量測試資料 → 判斷變異是否顯著 |
| 008 | Acoustic Evidence Engineer | 證據鏈 | Traceability、source control | 檢查每個結論是否有數據、文件來源 |
| 009 | Acoustic Standards Lead | 標準管理 | IEC / ISO / IEEE / 3GPP 等 | 給產品 / 測試目的 → 找適用規範與條件 |
| 010 | Principal Acoustic Reviewer | 最終技術簽核 | Cross-domain review | 收到其他 AI 結果 → 找矛盾、確認可信度 |

---

## B. Loudspeaker / Receiver Transducer：011–020

| ID | 工程師 | 能力 | 技能 / 工具 | 使用手冊 |
|---|---|---|---|---|
| 011 | Loudspeaker Physics Engineer | 揚聲器電機聲模型 | T/S、electro-mechanical model | 給 driver data → 建立行為模型 |
| 012 | T/S Parameter Engineer | T/S 分析 | Fs、Qts、Vas、Re、Le | 給 impedance / Klippel → 判定 driver 差異 |
| 013 | Nonlinear Speaker Engineer | 非線性失真 | BL(x)、Cms(x)、Le(x) | 給 Klippel → 分析大振幅 distortion |
| 014 | Suspension Engineer | Spider / surround | stiffness、aging | 低頻異常 → 判 suspension 可能性 |
| 015 | Magnetic Motor Engineer | Voice coil / magnet | BL、flux、gap | 靈敏度異常 → 分析 motor root cause |
| 016 | Speaker Thermal Engineer | 熱壓縮 | power compression、VC temp | 高功率 SPL 掉落 → 判熱效應 |
| 017 | Diaphragm Engineer | 振膜結構 | breakup、modal behavior | 中高頻峰谷 → 分析 diaphragm mode |
| 018 | Micro Speaker Engineer | 手機 / NB 小型單體 | excursion、back volume | 小型 speaker 設計與 failure 分析 |
| 019 | Receiver Engineer | Receiver / earpiece | leakage、ear coupling | 聽筒 FR / SPL / THD 問題 |
| 020 | Transducer Reliability Engineer | Driver 壽命 | aging、fatigue、power test | Before / after reliability 比較 |

---

## C. Speaker Acoustic System：021–030

| ID | 工程師 | 能力 | 技能 / 工具 | 使用手冊 |
|---|---|---|---|---|
| 021 | Enclosure Engineer | Speaker box | compliance、volume | 給腔體尺寸 → 分析低頻 / F0 |
| 022 | Port/Vent Engineer | Bass reflex / port | Helmholtz、port loss | 給 vent geometry → 估 tuning |
| 023 | Leakage Engineer | 漏氣 | sealing、leak path | 低頻 SPL 掉落 → 找漏氣路徑 |
| 024 | Passive Radiator Engineer | PR 系統 | mass、tuning | 給 PR 參數 → 建立 tuning 建議 |
| 025 | Grille/Mesh Engineer | 網布 / 孔洞聲阻 | acoustic impedance | 比較 mesh → 估 SPL / FR 損失 |
| 026 | Acoustic Path Engineer | 出音路徑 | duct / cavity resonance | CAD + FR → 找 cavity resonance |
| 027 | Speaker Array Engineer | 多 speaker 系統 | phase、interference | 多單體 → 分析 comb filtering |
| 028 | Amplifier Matching Engineer | Amp / driver 配對 | voltage、current、headroom | Amp + driver → 安全功率範圍 |
| 029 | Speaker Tuning Engineer | 聽感調校 | target curve、EQ | FR + 目標 → 產生 tuning direction |
| 030 | Speaker Protection Engineer | 保護策略 | excursion / thermal limiter | 建立 excursion、thermal protection |

---

## D. Microphone：031–040

| ID | 工程師 | 能力 | 技能 / 工具 | 使用手冊 |
|---|---|---|---|---|
| 031 | MEMS Microphone Engineer | MEMS 選型 | SNR、AOP、sensitivity | 給使用情境 → 推薦 mic KPI |
| 032 | Mic Port Engineer | Port 幾何 | resonance、tube model | CAD / 尺寸 → 分析 port resonance |
| 033 | Mic Mesh Engineer | 防塵防水膜 | acoustic resistance | mesh 前後 FR / SNR 比較 |
| 034 | Microphone Array Engineer | Array geometry | spacing、phase | 給 mic 座標 → 評估 array |
| 035 | Voice Pickup Engineer | 語音收音 | directivity、distance | 給場景 → 優化 pickup |
| 036 | Microphone Noise Engineer | Self noise | noise floor、SNR | 給 noise data → 拆解噪聲來源 |
| 037 | Microphone Distortion Engineer | AOP / THD | clipping / nonlinearity | 大聲壓問題 → 判 mic saturation |
| 038 | Wind Noise Engineer | 風噪 | turbulence、port | outdoor recording → 降低風噪 |
| 039 | Structure-Borne Mic Engineer | 結構傳振 | vibration coupling | 觸控 / 馬達噪音 → 分析 mechanical path |
| 040 | Mic Reliability Engineer | Mic aging | moisture、drop、aging | Reliability 前後性能比較 |

---

## E. Product Acoustic Specialists：041–050

| ID | 工程師 | 核心產品 | 主要用途 |
|---|---|---|---|
| 041 | Notebook Acoustic Engineer | Notebook | Speaker、mic、fan、機構整合 |
| 042 | Smartphone Acoustic Engineer | Phone | Receiver、speaker、mic、waterproof |
| 043 | Tablet Acoustic Engineer | Tablet | 多 speaker、cavity、array |
| 044 | Headphone/TWS Engineer | Headset / TWS | Ear coupling、ANC、driver |
| 045 | Smart Speaker Engineer | Smart speaker | Far-field voice + speaker |
| 046 | Conference Device Engineer | Conference | Beamforming、AEC、speakerphone |
| 047 | TV/Monitor Acoustic Engineer | TV / Monitor | Speaker cavity、radiation |
| 048 | Automotive Acoustic Engineer | Vehicle | Cabin acoustics、NVH / audio |
| 049 | AR/VR/Wearable Engineer | Wearable | Near-ear audio、miniature acoustics |
| 050 | Robot Acoustic Engineer | Robot | Voice pickup、speaker、motor noise |

### 使用方式

選產品 → 輸入：

- 現象
- 結構
- 測試數據
- 使用情境
- 問題階段

Product Engineer 再自動找 011–040 的專家組成 Engineer Pod。

---

## F. Measurement / Laboratory：051–060

| ID | 工程師 | 能力 | 使用手冊 |
|---|---|---|---|
| 051 | APx Engineer | Audio Precision | 給 test target → 產生 APx sequence / 判讀 |
| 052 | SoundCheck Engineer | Listen SoundCheck | 建測試流程、limit 與資料分析 |
| 053 | Klippel Engineer | Loudspeaker characterization | 分析 LSI / LPM / nonlinear data |
| 054 | Anechoic Chamber Engineer | 無響室量測 | 距離、角度、校正、far field |
| 055 | HATS Engineer | Head / torso measurement | Headset / receiver / telephony |
| 056 | Calibration Engineer | Mic / SPL calibration | 建立 calibration 與 traceability |
| 057 | Impedance Measurement Engineer | Electrical impedance | 找 F0、leak、driver anomaly |
| 058 | Rub & Buzz Engineer | 異音偵測 | Buzz / rattle / spectral signatures |
| 059 | Production Acoustic Test Engineer | EOL | 快速測試、limit、false reject |
| 060 | Measurement Uncertainty Engineer | 誤差分析 | Gauge、環境、fixture、repeatability |

---

## G. CAE / Simulation：061–070

| ID | 工程師 | 能力 | 使用手冊 |
|---|---|---|---|
| 061 | COMSOL Acoustic FEM Engineer | FEM 聲場 | CAD → mesh → BC → solver → 結果 |
| 062 | BEM Acoustic Engineer | 外部聲場 | Radiation / scattering 問題 |
| 063 | Lumped Acoustic Model Engineer | 等效電路 | 快速建立 cavity / vent model |
| 064 | Vibro-Acoustic Engineer | 結構聲耦合 | FEA + acoustics |
| 065 | Structural Modal Engineer | 結構模態 | Housing / diaphragm resonance |
| 066 | CFD Acoustic Engineer | Flow acoustics | Port / wind / turbulence noise |
| 067 | Parametric Simulation Engineer | 參數掃描 | DOE、geometry sweep |
| 068 | Acoustic Optimization Engineer | 自動最佳化 | Objective / constraints → 最佳尺寸 |
| 069 | CAD Acoustic Preparation Engineer | CAD 清理 | CREO / STEP → CAE geometry |
| 070 | Simulation Correlation Engineer | CAE / 實測關聯 | Simulation vs measurement calibration |

這一組是 AERIS 中負責：

> CREO → COMSOL → AI 自動聲學模擬

的重要核心團隊。

---

## H. DSP / Algorithms：071–080

| ID | 工程師 | 能力 | 使用手冊 |
|---|---|---|---|
| 071 | EQ Engineer | PEQ / FIR / IIR | FR + target → EQ proposal |
| 072 | Crossover Engineer | 分頻 | Driver FR / phase → crossover |
| 073 | DRC Engineer | Dynamic range control | SPL / THD → compressor strategy |
| 074 | Spatial Audio Engineer | Spatial rendering | Speaker / headphone spatial |
| 075 | Beamforming Engineer | Beamforming | Mic array + DOA → algorithm |
| 076 | Noise Suppression Engineer | NS | Noise sample → suppression design |
| 077 | AEC Engineer | Echo cancellation | Speaker / mic loop → AEC analysis |
| 078 | ANC Engineer | Active noise cancellation | Ref / error mic → ANC architecture |
| 079 | Automatic Tuning Engineer | 自動調音 | Objective → algorithmic optimization |
| 080 | Acoustic ML Engineer | ML classification | 音訊 → 異常分類 / feature model |

---

## I. Manufacturing / Quality / NPI：081–090

| ID | 工程師 | 能力 | 使用手冊 |
|---|---|---|---|
| 081 | Acoustic NPI Engineer | EVT / DVT / PVT | 建立各 phase acoustic plan |
| 082 | Acoustic Process Engineer | 製程 | 膠量、裝配、壓合對 acoustic 影響 |
| 083 | Acoustic Fixture Engineer | Fixture | 設計 EOL fixture、密封 |
| 084 | Acoustic GR&R Engineer | GR&R | 測站 repeatability / reproducibility |
| 085 | Acoustic SPC Engineer | SPC | Production data → control chart |
| 086 | Acoustic Failure Analysis Engineer | FA | Failure sample → root cause tree |
| 087 | Supplier Acoustic Quality Engineer | SQE | Supplier data、limit、FA review |
| 088 | Acoustic Reliability Engineer | Reliability | Drop / temp / humidity / life |
| 089 | EOL Limit Engineer | Limit optimization | Golden / NG dataset → limit |
| 090 | Acoustic Cost Engineer | Cost / performance | BOM change → 聲學風險與成本 tradeoff |

---

## J. Data / AI / Knowledge / Documentation：091–100

| ID | 工程師 | 能力 | 使用手冊 |
|---|---|---|---|
| 091 | Acoustic Data Engineer | 資料清理 / ETL | APx / CSV / Excel → 統一 schema |
| 092 | Acoustic Knowledge Engineer | RAG | Spec / report / SOP → 可搜尋知識 |
| 093 | Acoustic Data Scientist | 大數據分析 | 大量 test data → trend / outlier |
| 094 | Acoustic RCA Intelligence Engineer | AI RCA | 多來源 evidence → RCA ranking |
| 095 | Acoustic DOE Copilot | DOE 自動化 | Variable / goal → experiment matrix |
| 096 | Acoustic Automation Engineer | Python / automation | 重複工程工作 → Script / tool |
| 097 | Acoustic Technical Writer | 報告 | Data + 結論 → 工程報告 |
| 098 | Acoustic Standards Librarian | 標準知識庫 | 找標準、版本、條文與 traceability |
| 099 | Acoustic Decision Intelligence Engineer | 決策 | 多方案 → performance / cost / risk matrix |
| 100 | Principal Acoustic Integration Engineer | 最終整合 | 整合 001–099 → 最終 engineering answer |

---

# 11. 所有 Engineer 的統一使用手冊框架

不應該各自寫成完全不同格式。

AERIS 應統一為：

```text
1. 何時使用
2. 可以處理什麼
3. 不可以處理什麼

4. Required Input
   - 測試資料
   - 產品資料
   - 規格
   - CAD
   - 測試條件

5. Optional Input

6. 自動檢查資料品質

7. 執行 SOP

8. 必要時呼叫 Tool

9. Evidence check

10. Confidence
    High / Medium / Low

11. 建議下一步實驗

12. Output
    Finding
    Evidence
    Root Cause
    Recommendation
    Risk
```

---

# 12. Engineer #023 — Leakage Engineer 使用手冊範例

```text
INPUT
FR
Impedance
Golden sample
Box volume
Seal structure

↓

檢查
低頻 SPL 是否下降？
Fs 是否位移？
Q 是否改變？
左右 sample 是否一致？

↓

Hypothesis
H1 seal leak
H2 driver variation
H3 cavity change
H4 vent blockage

↓

推薦實驗
Tape sealing A/B
Impedance A/B
Pressure/leak test

↓

OUTPUT
Most likely root cause
Supporting evidence
Confidence
Next verification
```

---

# 13. AERIS 本地 AI 可以真正執行的事情

## 13.1 讀取

可處理：

- PDF
- PPT
- Excel
- CSV
- APx 資料
- Klippel 資料
- SoundCheck 資料
- Spec
- SOP
- 歷史 FA
- CAD metadata

---

## 13.2 計算

可由本地工具完成：

- Python
- FFT
- FR
- THD
- 統計
- DOE
- curve comparison
- optimization

---

## 13.3 分析

AERIS 可以處理：

- Golden vs NG
- Root Cause ranking
- 異常頻段判斷
- correlation
- trend
- 多來源 evidence 整合

---

## 13.4 工具操作

只要建立 Adapter，可連接：

```text
Python
MATLAB
COMSOL
APx
SoundCheck
Klippel export
Git
CAD preprocessing
```

---

## 13.5 輸出

AERIS 可以產生：

- Engineering Report
- DOE
- FA Report
- Test Plan
- Design Review
- Engineering Recommendation
- Risk Matrix
- Root Cause ranking
- Evidence chain

---

# 14. AERIS 不能假裝知道的事情

如果使用者只輸入：

> 「幫我判斷這顆 Speaker 漏氣。」

但沒有：

- FR
- Impedance
- 結構
- Measurement
- Golden sample
- 測試條件

那 AERIS 最多只能提出：

- 可能原因
- 所需證據
- 下一步實驗

不能假裝已經量測或確認。

因此本次對話確立的重要原則：

> **AI 負責推理；工具負責計算；儀器負責量測；資料庫負責證據。**

---

# 15. 前端 UI 不應直接顯示 100 個 Avatar

AERIS 首頁更適合：

```text
AERIS
What are you working on today?

[分析異常]
[設計產品]
[規劃測試]
[分析資料]
[建立 Simulation]
[工廠問題]
[查規範]
[不知道，讓 AERIS 引導我]
```

---

## 15.1 Navigator Example

使用者輸入：

> NB Speaker 低頻變差。

Navigator 問：

```text
是：
○ EVT / DVT / PVT
○ Golden vs NG
○ Reliability before/after
○ Factory failure

有：
□ FR
□ THD
□ Impedance
□ CAD
□ Klippel
```

最後後台自動建立：

```text
AERIS CASE #20260914-001

Lead:
#041 Notebook Acoustic Engineer

Specialists:
#018 Micro Speaker
#021 Enclosure
#023 Leakage
#057 Impedance
#086 Failure Analysis

Reviewer:
#003 Design Reviewer

Final approval:
#100 Integration Engineer
```

使用者不需要自己知道該找哪五位工程師。

---

# 16. 最終六層 AERIS 定義

本次對話最後收斂為：

```text
L1  User Experience
    AERIS Navigator

L2  Problem Engineering
    問題收斂 / 發散 / Requirement

L3  Orchestration
    自動選擇 Expert Pod

L4  100 Acoustic Capability Modules
    001～100

L5  Engineering Tools
    Python / MATLAB / COMSOL
    APx / Klippel / SoundCheck

L6  Engineering Memory
    RAG / SQL / Vector DB / Files
```

---

# 17. 100% 本地化結論

以下都可以 Local：

- Frontend
- Navigator
- LLM
- Orchestrator
- 100 Acoustic Capability Modules
- RAG
- Vector DB
- SQL
- File repository
- Python
- MATLAB
- COMSOL automation
- APx integration
- SoundCheck integration
- Klippel data integration
- CAD preprocessing
- Report generation
- Testing
- Golden Cases
- Regression Tests

因此：

> **AERIS 不需要依賴雲端 AI 才能成立。**

雲端 AI 可以作為：

- 開發助手
- 外部 benchmark
- 可選 fallback
- 非正式研發輔助

但不應成為 AERIS 正式工作的必要依賴。

---

# 18. AERIS Capability Contract v1.0 建議基準

每一位工程師正式落地時，應至少具備以下 manifest：

```yaml
engineer_id: "023"
name: "Leakage Engineer"
domain: "Speaker Acoustic System"

role:
  summary: "分析 speaker enclosure、seal、vent 相關漏氣造成的聲學異常"

scope:
  in_scope:
    - low_frequency_spl_loss
    - impedance_shift
    - enclosure_leak
    - seal_failure
    - vent_abnormality
  out_of_scope:
    - unsupported_physical_claim_without_evidence

knowledge:
  - enclosure_acoustics
  - acoustic_compliance
  - impedance
  - resonance
  - leak_path
  - sealing

skills:
  - compare_fr
  - compare_impedance
  - identify_low_frequency_loss
  - build_hypothesis
  - rank_root_causes
  - propose_validation_experiments

tools:
  - python
  - csv_parser
  - apx_data_parser
  - soundcheck_export_parser
  - plotting
  - statistics

required_inputs:
  - fr_or_spl_data
  - sample_identity
  - test_condition

optional_inputs:
  - impedance
  - golden_sample
  - enclosure_volume
  - seal_structure
  - cad
  - reliability_condition

workflow:
  - validate_inputs
  - compare_golden_ng
  - locate_abnormal_frequency_band
  - inspect_impedance_shift
  - generate_hypotheses
  - rank_hypotheses
  - propose_ab_tests
  - generate_evidence_based_output

output_schema:
  - finding
  - evidence
  - hypotheses
  - root_cause_ranking
  - confidence
  - next_verification
  - recommendation
  - risk

boundaries:
  - "不得在缺乏證據時宣稱已確認 leak"
  - "不得把推測寫成量測事實"

escalation:
  - "021 Enclosure Engineer"
  - "057 Impedance Measurement Engineer"
  - "086 Acoustic Failure Analysis Engineer"
  - "003 Acoustic Design Reviewer"

golden_tests:
  - known_leak_case
  - blocked_vent_case
  - driver_variation_case
  - cavity_change_case

evidence_policy:
  requirement: "所有 root cause 結論必須引用對應資料、量測或文件"
```

---

# 19. AERIS Engineer 的完成度標準

一位 Engineer 不應因為「有名字」就被 UI 顯示成 Ready。

最低應分為：

| 狀態 | 定義 |
|---|---|
| Draft | 只有角色 / scope |
| Defined | Capability Contract 完成 |
| Tool-Connected | 工具 adapter 可運作 |
| Tested | Golden test 通過 |
| Validated | 實際工程案例驗證 |
| Production Ready | 可正式使用 |

---

# 20. AERIS UI 顯示規則

本次對話確立的重要規則：

> **沒有 Skill、Tool、Input/Output Contract、Golden Test、Evidence 的角色，不得被 AERIS UI 顯示成「已具備能力的工程師」。**

因此 100 位工程師不能只是：

- 名稱
- Avatar
- Prompt
- 人格設定

必須是：

- Capability Contract
- Tool
- Knowledge
- Workflow
- Evidence
- Test
- Boundary
- Escalation
- Output schema

---

# 21. 最終產品概念

AERIS 不是：

> 100 個 Chatbot

而應該是：

> **一套本地 Acoustic Engineering Operating System / AI Engineering Team**

其本質為：

```text
Human
↓
Navigator
↓
Problem Engineering
↓
Task Orchestrator
↓
Expert Pod
↓
Engineering Tools
↓
Engineering Data / Evidence
↓
Review
↓
Decision / Report
```

---

# 22. 本次對話的最終共識

1. AERIS 可以 100% Local。
2. 不需要讓前端與後端必須依賴雲端 AI。
3. 100 位 Engineer 不等於 100 個模型。
4. 100 位 Engineer 應該是 100 個 Capability Modules。
5. 每一席必須有：
   - Role
   - Scope
   - Knowledge
   - Skills
   - Tools
   - Inputs
   - Workflow
   - Output
   - Boundary
   - Escalation
   - Golden Tests
   - Evidence
6. AERIS Navigator 是必要的前端問題導航層。
7. Navigator 的目的是幫使用者：
   - 收斂問題
   - 發散可能原因
   - 補齊必要資料
   - 建立正式 Engineering Case
8. Orchestrator 負責自動組成 Expert Pod。
9. 工程師不能憑空宣稱已驗證。
10. AI 負責推理。
11. 工具負責計算。
12. 儀器負責量測。
13. Database / RAG 負責證據。
14. 最終 Reviewer / Integration Engineer 負責整合與品質把關。
15. AERIS 的目標不是「100 個角色」，而是「100 個可調用、可測試、可驗收、可升級的工程能力模組」。

---

# 23. 建議作為 Claude Code 施工輸入的下一個實作單位

本文件本身已可作為 AERIS Blueprint 的需求來源。

後續實作時，應優先把本文件轉成：

```text
/aeris
  /capabilities
    001_chief_acoustic_architect.yaml
    002_acoustic_requirement_engineer.yaml
    ...
    100_principal_acoustic_integration_engineer.yaml

  /schemas
    capability_contract.schema.json
    engineering_case.schema.json
    evidence.schema.json
    output.schema.json

  /tests
    /golden_cases
    /regression

  /navigator
  /orchestrator
  /tools
  /knowledge
  /reports
```

其中最優先的工程成果不是 UI 動畫或 100 個 Avatar，而是：

1. `Capability Contract Schema`
2. 100 個 capability manifest
3. Engineer Router
4. Engineering Case Schema
5. Evidence policy
6. Golden tests
7. Tool adapter
8. Navigator

---

# 24. 文件結論

本次對話把 AERIS 從：

> 「有 100 位聲學工程師的本地 AI」

進一步定義成：

> **一套 100% 可本地化、以 Navigator + Orchestrator + 100 個 Capability Modules + Engineering Tools + Evidence Memory 組成的聲學工程 AI 系統。**

真正的價值不是工程師名稱，而是：

> **每一席都有真實能力、固定輸入、可調用工具、SOP、證據規則、輸出格式、能力邊界與 Golden Tests。**

這是後續 AERIS 從「概念」走向「工程產品」的正式基準。

---

# 25. 2026-09-15 新增設計：AERIS「前台點餐 → 後台工程 → 交付」閉環

## 25.1 使用者的新思路

本次新增需求：

> 前端讓使用者可以直接用語音產生文字。  
> 不管語音或打字，最後都必須進入引導式流程。  
> 前端像餐廳服務員點餐，一步一步幫使用者把模糊需求收斂，最後點到後端 100 位聲學工程師的能力。  
> 前端最後應產生一份「點菜單 `.md`」交給 AERIS。  
> 後端 AERIS 收到點菜單後執行工程工作。  
> 數據型結果用 Excel；說明、判斷、結論用 PowerPoint。  
> 前端與後端都必須各自有明確產出。  
> 並且 100 位工程師全部必須可以從前端一路跑到後端做 End-to-End 驗收。

本文件將這個概念正式命名為：

> **AERIS Order-to-Engineering Pipeline**

核心不是「聊天」，而是：

> **把自然語言需求轉成可執行、可追溯、可驗收的工程訂單。**

---

# 26. AERIS 新版總架構

```text
┌─────────────────────────────────────────────┐
│  USER                                       │
│  Voice / Text / File / Measurement Data     │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│ L1  AERIS FRONT DESK                        │
│                                             │
│ Voice → STT → Text                          │
│ Text → Intent                               │
│ Guided Conversation                         │
│ 問題收斂 + 問題發散 + 缺資料提醒              │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
          FRONTEND CANONICAL OUTPUT
          CASE-xxxx_ORDER.md
                    │
                    ▼
┌─────────────────────────────────────────────┐
│ L2  ORDER VALIDATOR                         │
│ Schema / completeness / safety / evidence   │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│ L3  AERIS ORCHESTRATOR                      │
│ Router / Planner / Expert Pod               │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│ L4  100 ACOUSTIC CAPABILITY MODULES         │
│ #001 ... #100                               │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│ L5  ENGINEERING TOOLS                       │
│ Python / MATLAB / COMSOL / APx / Klippel    │
│ SoundCheck / CAD / Statistics / RAG         │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│ L6  REVIEW / EVIDENCE / TRACEABILITY        │
│ Evidence / Confidence / Reviewer / Logs     │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
           BACKEND CANONICAL DELIVERY
      CASE-xxxx_DELIVERY/
      ├─ Results.xlsx
      ├─ Report.pptx
      └─ Evidence/
```

---

# 27. 前端不是一般 Chatbot：它是「AERIS Front Desk」

## 27.1 輸入方式

前端至少支援四種輸入：

1. **語音**
   - 使用者直接說明問題
   - Local STT 將語音轉成文字
   - 使用者可確認 / 修改轉寫結果

2. **文字**
   - 自由輸入
   - 可一句話，也可以貼整段問題

3. **檔案**
   - CSV / Excel / PDF / PPT / image / CAD metadata / instrument export
   - 檔案本身不等於完成下單，仍必須經過引導流程

4. **結構化選項**
   - Product
   - Project phase
   - Failure type
   - Available measurements
   - Desired output
   - Urgency / risk / constraints

---

## 27.2 語音與文字最後必須匯流

```text
Voice
  ↓
Local STT
  ↓
Normalized Text
  ┐
  ├──→ Guided Intake
  │
Text
  ┘
```

因此語音只是一種輸入方式。

**AERIS 不可因為使用者使用語音，就跳過需求澄清。**

---

# 28. 「餐廳服務員點餐」模型

AERIS Front Desk 的責任不是回答所有問題，而是像一位懂聲學的服務員：

1. 先理解使用者今天要做什麼。
2. 不要求使用者知道 100 位工程師的名字。
3. 用少量問題逐步縮小範圍。
4. 同時提供可能遺漏的方向，協助發散。
5. 確認有哪些數據。
6. 確認期待交付物。
7. 確認限制與風險。
8. 自動挑選後端專家。
9. 產出正式工程點菜單。

例：

```text
USER:
我的 NB speaker 低頻突然變差。

AERIS:
這個問題比較接近哪一種？

[Golden vs NG]
[Reliability 前後]
[EVT / DVT / PVT]
[量產異常]
[不知道]

USER:
Golden vs NG

AERIS:
你目前有哪些資料？

[x] FR
[x] THD
[x] Impedance
[ ] Klippel
[x] CAD
[ ] 不確定

AERIS:
低頻大約從哪個頻帶開始異常？

[<150 Hz]
[150–300 Hz]
[300–500 Hz]
[不確定，請自動判斷]

AERIS:
是否希望 AERIS 自動檢查 Leakage / Driver / Enclosure / Vent？

[是]
[只分析 Leakage]
[讓 AERIS 決定]
```

最後不是繼續聊天，而是生成正式訂單。

---

# 29. 前端唯一正式交付：`CASE-xxxx_ORDER.md`

## 29.1 定義

`ORDER.md` 是：

> **Human-readable + Machine-parseable 的工程任務契約。**

它同時是：

- 使用者需求確認書
- AERIS 後端工作指令
- Expert Router 的輸入
- 驗收的基準
- 後續 Results.xlsx / Report.pptx 的 traceability root

---

## 29.2 `ORDER.md` 建議格式

```markdown
---
case_id: AERIS-20260915-0001
created_at: 2026-09-15T00:00:00+08:00
input_mode: voice
language: zh-TW
product: notebook
project_phase: DVT
priority: normal
status: confirmed
---

# User Goal
找出 NB Speaker 180–500 Hz SPL 比 Golden 低 4 dB 的主要原因。

# Problem Type
Golden vs NG / Low-frequency SPL degradation

# Known Symptoms
- 180–500 Hz: -4 dB
- THD 增加
- 左右聲道皆有

# Available Evidence
- FR.csv
- THD.csv
- IMP.csv
- enclosure.step
- Golden sample data

# Missing Evidence
- Klippel nonlinear data
- Air leak pressure test

# Constraints
- 不修改 driver
- 優先機構解法
- DVT 時程 3 天內

# Selected Capability Pod
- Lead: #041 Notebook Acoustic Engineer
- #018 Micro Speaker Engineer
- #021 Enclosure Engineer
- #023 Leakage Engineer
- #057 Impedance Measurement Engineer
- #086 Acoustic Failure Analysis Engineer
- Reviewer: #003 Acoustic Design Reviewer
- Final: #100 Principal Acoustic Integration Engineer

# Required Work
1. Golden/NG FR 比較
2. IMP 特徵分析
3. Leakage / enclosure / driver root-cause ranking
4. 提出最少實驗數的驗證方案
5. 產生量化結果與風險

# Backend Required Deliverables
- Results.xlsx
- Report.pptx

# Acceptance Criteria
- 所有結論需有 evidence
- 不得把 hypothesis 當 confirmed fact
- 每個 root cause 需提供 confidence
- 至少提供一個可執行驗證實驗
```

---

# 30. 前端驗收標準

AERIS Front Desk 驗收時，不以「回答得像不像人」作為主要標準。

必須驗收：

| 項目 | Pass 條件 |
|---|---|
| Voice STT | 語音可轉成可編輯文字 |
| Text Input | 文字可直接進入相同流程 |
| Intent | 能辨識產品 / 問題 / 目的 |
| Guided Intake | 能問出必要缺口 |
| Divergence | 能提出合理候選方向 |
| Convergence | 能收斂成明確工程問題 |
| File Binding | 上傳資料能綁定 Case |
| Expert Routing | 能選到合理 Expert Pod |
| Order Completeness | Required fields 齊全 |
| Confirmation | 使用者確認後才鎖定訂單 |
| Traceability | Case ID 一路帶到後端 |
| Output | 成功生成 `ORDER.md` |

前端的 **Definition of Done**：

> 使用者不需要懂 100 位工程師，也能完成一份後端可以直接執行的 `ORDER.md`。

---

# 31. 後端不是 Chatbot：它是「Engineering Execution Engine」

AERIS Backend 收到 `ORDER.md` 後：

```text
ORDER.md
   ↓
Schema Validator
   ↓
Capability Router
   ↓
Expert Pod
   ↓
Task Graph
   ↓
Tool Execution
   ↓
Evidence Collection
   ↓
Cross Review
   ↓
Result Assembly
   ↓
Results.xlsx + Report.pptx
```

---

# 32. 後端固定交付規格

## 32.1 `Results.xlsx` — 數據主檔

所有可量化內容優先寫進 Excel。

建議 Sheet：

| Sheet | 內容 |
|---|---|
| 00_CASE | Case ID / Order summary / model version |
| 01_INPUT | 原始輸入與檔案清單 |
| 02_DATA_QC | 資料完整性與品質檢查 |
| 03_METRICS | KPI / 數值 / limit / delta |
| 04_ANALYSIS | 計算與統計結果 |
| 05_HYPOTHESES | Root Cause ranking + confidence |
| 06_EXPERIMENT | 建議驗證實驗 / DOE |
| 07_RESULT | 最終數值結論 |
| 08_EVIDENCE | 結論 ↔ evidence mapping |
| 09_TRACE | 使用工程師 / Tool / Model / timestamp |
| 10_ACCEPTANCE | Gate 結果 / Pass-Fail |

原則：

> **可以用數字表示的，不只寫在 PPT。**

---

## 32.2 `Report.pptx` — 工程說明主檔

PPT 負責：

- 問題是什麼
- 為什麼這樣分析
- 找到什麼
- 證據是什麼
- 根因排序
- 風險
- 下一步
- 決策建議

建議固定結構：

```text
01 Executive Summary
02 Problem Definition
03 Input / Evidence
04 Data Quality
05 Analysis
06 Key Findings
07 Root Cause Ranking
08 Validation Experiment
09 Recommendation
10 Risk / Limitation
11 Traceability
12 Acceptance
```

原則：

> **PPT 不應成為原始數據資料庫；Excel 才是數據 source of truth。**

---

# 33. 後端「一個產出」的定義

雖然後端實際包含 Excel + PowerPoint，但對系統層級視為一個正式 Delivery：

```text
CASE-xxxx_DELIVERY/
├── Results.xlsx
├── Report.pptx
└── Evidence/
```

因此：

- 前端正式產出：`CASE-xxxx_ORDER.md`
- 後端正式產出：`CASE-xxxx_DELIVERY/`

這樣前後端責任清楚。

---

# 34. Frontend → Backend End-to-End 驗收 Gate

每一位 001–100 Engineer 都必須走相同 E2E Gate。

## 34.1 Gate 定義

| Gate | 權重 | 驗收內容 |
|---|---:|---|
| G0 Capability Contract | 5% | Role / Scope / Boundary / Input / Output 已定義 |
| G1 Frontend Discoverability | 5% | 使用者用自然語言能被引導到此能力 |
| G2 Voice/Text Intake | 10% | Voice 與 Text 都能正確建立需求 |
| G3 Guided Questions | 10% | 能問出此 Engineer 必要 input |
| G4 ORDER.md | 10% | 能生成完整、可解析、可確認的訂單 |
| G5 Routing | 10% | Orchestrator 能正確調用此 Engineer |
| G6 Engineering Execution | 15% | Engineer SOP 真正執行，非只產生文字 |
| G7 Tool + Evidence | 15% | 正確呼叫工具，結論可追溯 evidence |
| G8 Results.xlsx | 8% | 定量結果正確落地到 Excel |
| G9 Report.pptx | 7% | 解釋、風險、結論正確落地到 PPT |
| G10 Golden E2E Test | 5% | 固定 Golden Case 可重跑且 Pass |
| **總分** | **100%** | |

---

## 34.2 驗收狀態

每一 Gate 只能有：

```text
NOT_STARTED
IN_PROGRESS
BLOCKED
PASS
FAIL
```

禁止只寫：

```text
差不多
應該可以
看起來正常
```

---

## 34.3 Production Ready 條件

一位 Engineer 只有在以下條件全部成立時才可顯示：

> **Production Ready**

條件：

1. G0–G10 全部 PASS
2. 總分 = 100%
3. Golden Case 至少連續重跑 3 次 PASS
4. 不可有 High severity open issue
5. Evidence trace 完整
6. Excel / PPT 均可產出
7. Reviewer PASS

---

# 35. 目前進度如何表示

本文件新增的是：

> **驗收規格與驗收案例設計。**

不得把「文件已寫好」宣稱成「軟體已通過驗收」。

因此目前所有 100 位 Engineer 應分開記錄：

```text
Specification Status: DEFINED
Implementation Status: NOT VERIFIED
E2E Acceptance: NOT RUN
Production Ready: NO
```

這樣避免虛假進度。

---

# 36. 100 位 Engineer 的 End-to-End Golden Acceptance Cases

下表不是聲稱目前已通過，而是每一位 Engineer 後續必須實跑的驗收案例。

| ID | Engineer | 前端使用者自然語言 / 點餐入口 | 後端必須真正執行 | Golden Case 最低交付 |
|---|---|---|---|---|
| 001 | Chief Acoustic Architect | 我要規劃一台新產品的整體聲學架構 | 需求→系統分解→trade-off→風險 | 架構KPI/風險矩陣/技術路線 |
| 002 | Acoustic Requirement Engineer | 幫我把產品需求轉成可驗收聲學規格 | 需求解析→KPI flow-down→測試條件 | Spec表/Pass-Fail條件 |
| 003 | Acoustic Design Reviewer | 幫我審查這版聲學設計是否有缺口 | 設計文件+數據→checklist→evidence review | Review finding/缺口/待驗證清單 |
| 004 | Acoustic Failure Review Chief | 這個聲學失敗要怎麼跨領域找根因 | Failure intake→FTA/5Why→組Expert Pod | RCA tree/專家分工/優先驗證 |
| 005 | Acoustic Experiment Chief | 請用最低成本驗證這個假設 | 假設→DOE/A-B→控制變因 | 實驗矩陣/樣本數/判定準則 |
| 006 | Acoustic Risk Engineer | 這個設計的聲學風險在哪裡 | 架構→FMEA→risk scoring | 風險排序/mitigation/owner |
| 007 | Acoustic Statistics Engineer | 兩批量測差異是否真的顯著 | 資料→清理→CI/ANOVA/CpCpk | 統計表/顯著性/結論 |
| 008 | Acoustic Evidence Engineer | 這份結論有沒有足夠證據 | 結論→來源追溯→證據完整性檢查 | Evidence matrix/缺證項 |
| 009 | Acoustic Standards Lead | 這個產品要符合哪些聲學標準 | 產品/市場/測試目的→標準映射 | 標準清單/條款/測試條件 |
| 010 | Principal Acoustic Reviewer | 幫我做最終技術簽核 | 多專家結果→矛盾檢查→整合判定 | Final review/風險/簽核意見 |
| 011 | Loudspeaker Physics Engineer | 這顆 speaker 的電機聲行為是否合理 | Driver data→等效模型→參數敏感度 | 模型參數/FR-IMP預測/異常 |
| 012 | T/S Parameter Engineer | Golden 和 NG 的 T/S 差在哪 | IMP/Klippel→Fs/Qts/Vas/Re/Le比較 | T/S差異表/影響排序 |
| 013 | Nonlinear Speaker Engineer | 大音量失真原因是什麼 | Klippel→BL(x)/Cms(x)/Le(x)→非線性判讀 | 非線性指標/根因排序 |
| 014 | Suspension Engineer | 低頻異常是否與 surround/spider 有關 | FR/IMP/位移→stiffness/aging分析 | 懸吊異常證據/驗證方案 |
| 015 | Magnetic Motor Engineer | 靈敏度下降是否是 motor 問題 | BL/flux/gap/coil資料→motor分析 | 磁路風險/可能製程因子 |
| 016 | Speaker Thermal Engineer | 連續播放後 SPL 為何掉下來 | 功率/時間/溫度/FR→thermal compression | 熱壓縮曲線/安全功率 |
| 017 | Diaphragm Engineer | 中高頻峰谷是否是振膜 breakup | FR/modal/CAE→breakup辨識 | 模態頻點/結構修改建議 |
| 018 | Micro Speaker Engineer | NB/Phone 小喇叭低頻與失真怎麼改善 | FR/THD/IMP/腔體→小型單體整合分析 | 改善項/風險/驗證 |
| 019 | Receiver Engineer | Receiver SPL/THD/漏氣問題怎麼判 | HATS/FR/IMP/leak→ear coupling分析 | Receiver診斷/密封建議 |
| 020 | Transducer Reliability Engineer | Reliability 前後 driver 是否退化 | Before/After資料→漂移/疲勞分析 | 退化量/失效模式/可信度 |
| 021 | Enclosure Engineer | Speaker box 容積改變會怎麼影響 | Volume/FR/IMP→compliance/resonance | 容積敏感度/F0預測 |
| 022 | Port/Vent Engineer | Vent 尺寸怎麼調整 | Geometry→Helmholtz/損失→tuning | 目標tuning/尺寸建議 |
| 023 | Leakage Engineer | 低頻掉 4 dB 是否漏氣 | FR/IMP/結構→leak hypothesis→A/B | 漏氣根因排序/封膠A-B |
| 024 | Passive Radiator Engineer | PR 質量與調諧如何設定 | PR/box/driver參數→tuning | PR mass/tuning建議 |
| 025 | Grille/Mesh Engineer | 換 mesh 後 FR 掉多少是正常的 | Mesh前後資料→聲阻/損失分析 | Insertion loss/選型建議 |
| 026 | Acoustic Path Engineer | 出音 duct 是否造成 resonance | CAD/FR→cavity/duct resonance | 共振頻點/幾何修改 |
| 027 | Speaker Array Engineer | 多顆 speaker 是否互相干涉 | 位置/phase/FR→interference分析 | Comb filtering/相位建議 |
| 028 | Amplifier Matching Engineer | Amp 和 driver 搭配是否安全 | Amp/driver/負載→headroom/current分析 | 安全工作區/限制條件 |
| 029 | Speaker Tuning Engineer | 請把 FR 調到 target curve | FR/target→EQ方向→限制檢查 | EQ建議/預期改善/風險 |
| 030 | Speaker Protection Engineer | 怎麼避免 excursion/thermal 過載 | 位移/溫度/功率→limiter策略 | Protection threshold/曲線 |
| 031 | MEMS Microphone Engineer | 這個使用情境該選什麼 Mic KPI | 場景→SNR/AOP/sensitivity需求 | Mic規格表/選型條件 |
| 032 | Mic Port Engineer | Mic port 長度是否造成共振 | Geometry/FR→tube resonance | 共振頻率/port修改 |
| 033 | Mic Mesh Engineer | 防水膜造成多少收音損失 | Mesh前後FR/SNR→聲阻分析 | 損失表/材料建議 |
| 034 | Microphone Array Engineer | 這個 mic 座標適合 array 嗎 | 座標/頻段→spacing/aliasing分析 | Array可用頻段/配置建議 |
| 035 | Voice Pickup Engineer | 遠場人聲收不到要改善哪裡 | 距離/方向/FR/noise→pickup分析 | 收音路徑/靈敏度建議 |
| 036 | Microphone Noise Engineer | 底噪是 Mic 還是系統造成 | Noise sample/電路/環境→noise decomposition | Noise budget/來源排序 |
| 037 | Microphone Distortion Engineer | 大聲壓時 Mic 為什麼失真 | AOP/THD/waveform→clipping分析 | 飽和點/安全SPL |
| 038 | Wind Noise Engineer | 戶外錄音風噪怎麼降低 | Audio/port/mesh→turbulence分析 | 風噪頻帶/結構與算法建議 |
| 039 | Structure-Borne Mic Engineer | 馬達/觸控震動為何進 Mic | 振動+audio→coupling path分析 | 傳遞路徑/隔振建議 |
| 040 | Mic Reliability Engineer | 高溫高濕後 Mic 是否退化 | Before/After FR/SNR/AOP→漂移 | 退化量/失效風險 |
| 041 | Notebook Acoustic Engineer | NB 的 speaker/mic/fan 聲學問題怎麼整合處理 | NB需求/結構/量測→跨模組Pod | NB聲學問題清單/優先序 |
| 042 | Smartphone Acoustic Engineer | Phone 的 receiver/speaker/mic 問題 | Phone case→跨模組Pod | 手機聲學整合報告 |
| 043 | Tablet Acoustic Engineer | Tablet 多 speaker 與 array 怎麼整合 | Tablet資料→speaker+mic整合 | 多單體/陣列風險 |
| 044 | Headphone/TWS Engineer | TWS 頻響/ANC/密封怎麼改善 | HATS/FR/leak/ANC→整合分析 | 佩戴/密封/調音建議 |
| 045 | Smart Speaker Engineer | Smart speaker 遠場收音與播放互相干擾 | Speaker+array+room→整合分析 | Far-field方案/AEC風險 |
| 046 | Conference Device Engineer | 會議機 speakerphone 為何回音/收音差 | AEC/array/speaker資料→系統分析 | 會議語音改善項 |
| 047 | TV/Monitor Acoustic Engineer | 薄型 TV/Monitor speaker 如何改善 | 結構/box/FR→輻射與腔體分析 | 薄型聲學方案 |
| 048 | Automotive Acoustic Engineer | 車艙中的聲學/NVH 問題怎麼判 | Cabin/audio/NVH→系統分析 | 車艙頻帶/路徑/改善 |
| 049 | AR/VR/Wearable Engineer | 近耳穿戴裝置聲學怎麼設計 | Near-ear geometry/HATS→整合 | 佩戴敏感度/目標FR |
| 050 | Robot Acoustic Engineer | Robot 馬達噪音影響語音與播放 | Motor/audio/array→跨域Pod | Robot聲學隔離/收音方案 |
| 051 | APx Engineer | 我要建立 APx 測試流程 | Target/spec→APx sequence/limit | 測試序列/limit/結果表 |
| 052 | SoundCheck Engineer | 我要建立 SoundCheck EOL 測試 | Spec/fixture→sequence/limit | SoundCheck流程/判定 |
| 053 | Klippel Engineer | 這份 Klippel 數據代表什麼 | Klippel export→LSI/LPM/nonlinear解析 | Klippel指標/異常判讀 |
| 054 | Anechoic Chamber Engineer | 無響室量測條件是否正確 | 距離/角度/環境→setup review | Setup checklist/不確定度 |
| 055 | HATS Engineer | HATS 量測 headset/receiver 怎麼做 | 產品/標準→HATS setup | Fixture/定位/測試方法 |
| 056 | Calibration Engineer | 量測鏈該怎麼校正 | Mic/calibrator/instrument→traceability | 校正紀錄/有效期/誤差 |
| 057 | Impedance Measurement Engineer | Impedance 能看出什麼異常 | IMP曲線→Fs/Q/leak/driver分析 | IMP特徵/異常分類 |
| 058 | Rub & Buzz Engineer | 這個異音是 buzz/rattle 嗎 | Audio/spectrum/level sweep→異音分類 | R&B特徵/門檻/根因方向 |
| 059 | Production Acoustic Test Engineer | 工廠怎麼快速測聲學品質 | CT/GRR/defect→EOL設計 | 測項/節拍/coverage |
| 060 | Measurement Uncertainty Engineer | 這個差異會不會只是量測誤差 | Setup/repeat data→uncertainty budget | 誤差預算/可信區間 |
| 061 | COMSOL Acoustic FEM Engineer | 用 CAD 做聲學 FEM 模擬 | Geometry/material/BC→mesh/solver | 場分布/FR/報告 |
| 062 | BEM Acoustic Engineer | 我要模擬外部輻射/散射 | Surface/BC/frequency→BEM | Directivity/field結果 |
| 063 | Lumped Acoustic Model Engineer | 先用等效模型快速估 cavity/vent | 參數→lumped network | 快速預測/敏感度 |
| 064 | Vibro-Acoustic Engineer | 結構振動如何耦合成聲音 | FEA/modal/acoustic→coupled analysis | 振聲路徑/貢獻度 |
| 065 | Structural Modal Engineer | Housing 哪些模態造成峰值 | CAD/modal/FR→mode correlation | 模態頻率/結構修改 |
| 066 | CFD Acoustic Engineer | 風道/port 流動噪音怎麼分析 | Flow geometry/condition→CFD acoustics | 流速/渦流/噪音熱點 |
| 067 | Parametric Simulation Engineer | 幫我掃尺寸找到趨勢 | Variables/range/objective→sweep | DOE表/response surface |
| 068 | Acoustic Optimization Engineer | 在限制條件下自動找最佳尺寸 | Objective/constraints/model→optimization | Pareto/最佳方案 |
| 069 | CAD Acoustic Preparation Engineer | CREO/STEP 怎麼整理成聲學模型 | CAD→defeature/封閉體/region | 可模擬geometry/修復清單 |
| 070 | Simulation Correlation Engineer | COMSOL 與實測差很多怎麼校正 | Sim+measurement→correlation/tuning | 誤差來源/校正參數 |
| 071 | EQ Engineer | 幫我算 PEQ/FIR/IIR 調音方向 | FR/target/constraints→filter design | Filter表/預估FR |
| 072 | Crossover Engineer | 兩顆 driver 怎麼分頻 | FR/phase/limits→crossover | Fc/slope/phase margin |
| 073 | DRC Engineer | 怎麼做壓縮又不傷聲音 | Level/THD/headroom→DRC | Threshold/ratio/attack/release |
| 074 | Spatial Audio Engineer | 空間音訊系統如何設計/驗收 | HRTF/geometry/content→spatial analysis | 定位/寬度/驗收指標 |
| 075 | Beamforming Engineer | Mic array 如何形成目標指向 | Geometry/audio/DOA→beamformer | Beampattern/頻帶/權重 |
| 076 | Noise Suppression Engineer | 背景噪音如何抑制 | Speech/noise samples→NS analysis | SNR提升/語音損傷指標 |
| 077 | AEC Engineer | 回音為何消不乾淨 | Far/near-end/loop→AEC diagnostics | ERLE/殘回音/改善 |
| 078 | ANC Engineer | ANC 架構與效果怎麼驗收 | Ref/error mic/path→ANC analysis | Attenuation/穩定性/頻帶 |
| 079 | Automatic Tuning Engineer | 請自動找最佳 EQ/參數 | Objective/limits/data→auto tuning | 最佳參數/收斂紀錄 |
| 080 | Acoustic ML Engineer | 用音訊自動分類異常 | Labeled audio→feature/model/eval | Confusion matrix/F1/模型輸出 |
| 081 | Acoustic NPI Engineer | EVT/DVT/PVT 聲學要做什麼 | Project phase/risk→test plan | Phase gate/樣本/exit criteria |
| 082 | Acoustic Process Engineer | 膠量/壓合/裝配如何影響聲學 | Process params+audio→correlation | 製程敏感因子/窗口 |
| 083 | Acoustic Fixture Engineer | EOL fixture 是否造成測試偏差 | Fixture/CAD/data→seal/repeatability | Fixture風險/修改項 |
| 084 | Acoustic GR&R Engineer | 這個測站 GR&R 過不過 | Operator/station/repeat data→GRR | %GRR/判定/改善 |
| 085 | Acoustic SPC Engineer | 產線聲學數據有沒有漂移 | Time-series→control chart/SPC | Cp/Cpk/異常點/趨勢 |
| 086 | Acoustic Failure Analysis Engineer | NG sample 根因是什麼 | Golden/NG/結構/製程→RCA | Root cause tree/驗證順序 |
| 087 | Supplier Acoustic Quality Engineer | 供應商聲學品質是否穩定 | Supplier lot/data/spec→SQE review | 供應商風險/改善要求 |
| 088 | Acoustic Reliability Engineer | Drop/Temp/Humidity 後聲學變化 | Before/After + condition→reliability | 漂移/失效模式/風險 |
| 089 | EOL Limit Engineer | 量產 limit 怎麼設才不誤殺 | Golden/NG/distribution→limit optimize | Limit/FRR/FAR |
| 090 | Acoustic Cost Engineer | 降 BOM 成本會犧牲多少聲學 | BOM方案+performance→trade-off | 成本/性能/風險矩陣 |
| 091 | Acoustic Data Engineer | 把不同儀器資料整理成統一格式 | APx/CSV/Excel/SC→ETL/schema | Clean dataset/data dictionary |
| 092 | Acoustic Knowledge Engineer | 把 SOP/Spec/Report 變成可查知識庫 | Documents→chunk/meta/index | RAG index/來源追溯 |
| 093 | Acoustic Data Scientist | 大量量測資料找趨勢與異常 | Dataset→EDA/outlier/correlation | Trend/outlier/correlation |
| 094 | Acoustic RCA Intelligence Engineer | 多份證據自動排序根因 | Evidence graph→RCA ranking | Hypothesis score/evidence map |
| 095 | Acoustic DOE Copilot | 幫我建立 DOE | Factors/levels/goal→DOE | Experiment matrix/analysis plan |
| 096 | Acoustic Automation Engineer | 把重複分析自動化 | Manual workflow→script/tool/test | Python tool/log/regression |
| 097 | Acoustic Technical Writer | 把結果整理成正式工程報告 | Data/findings/evidence→narrative | PPT/報告文字/圖表說明 |
| 098 | Acoustic Standards Librarian | 找到正確版本標準與條文 | Product/region/topic→standard retrieval | 版本/條款/來源 |
| 099 | Acoustic Decision Intelligence Engineer | 多個方案怎麼選 | Performance/cost/risk→decision matrix | 加權決策/Pareto/建議 |
| 100 | Principal Acoustic Integration Engineer | 把多位專家的結果整合成最終答案 | All pod outputs→conflict/evidence integration | Final conclusion/decision/risk |

---

# 37. 每一位 Engineer 的驗收紀錄格式

每次驗收不可只在 UI 打一個勾。

應產生：

```yaml
case_id: AERIS-VAL-023-0001
engineer_id: "023"
engineer_name: Leakage Engineer
golden_case: known_enclosure_leak

gates:
  G0: PASS
  G1: PASS
  G2: PASS
  G3: PASS
  G4: PASS
  G5: PASS
  G6: PASS
  G7: PASS
  G8: PASS
  G9: PASS
  G10: PASS

score: 100
repeat_pass: 3
high_severity_open_issue: 0

artifacts:
  order_md: "AERIS-VAL-023-0001_ORDER.md"
  results_xlsx: "AERIS-VAL-023-0001_Results.xlsx"
  report_pptx: "AERIS-VAL-023-0001_Report.pptx"

evidence:
  - fr_golden.csv
  - fr_ng.csv
  - impedance_golden.csv
  - impedance_ng.csv

reviewer: "003 Acoustic Design Reviewer"
final_reviewer: "100 Principal Acoustic Integration Engineer"

status: PRODUCTION_READY
```

---

# 38. Engineer 驗收 Dashboard 建議

AERIS 開發期間應有內部頁面：

```text
AERIS Capability Validation

001 Chief Acoustic Architect        70%  IN_PROGRESS
002 Requirement Engineer            40%  IN_PROGRESS
...
023 Leakage Engineer               100%  PRODUCTION READY
...
100 Principal Integration            0%  NOT STARTED

Production Ready: 1 / 100
E2E Passed:       1 / 100
Blocked:          3 / 100
Average Score:    xx.x%
```

注意：

> 上述數字只是 UI 格式範例，不代表目前真實施工進度。

真正數字只能由自動測試結果計算。

---

# 39. 每位 Engineer 的驗收資料夾

建議：

```text
/tests/e2e/
  /001_chief_acoustic_architect/
    /golden_case_01/
      input/
      expected/
      order_expected.md
      validation.yaml

  /002_acoustic_requirement_engineer/
  ...
  /023_leakage_engineer/
    /known_leak/
    /blocked_vent/
    /driver_variation/
    /cavity_change/

  ...
  /100_principal_acoustic_integration/
```

每位 Engineer 至少：

- 1 個 Positive Golden Case
- 1 個 Confuser Case
- 1 個 Missing-data Case
- 1 個 Boundary Case

成熟後再增加：

- Regression Case
- Adversarial Case
- Noisy-data Case
- Multi-engineer Case

---

# 40. 驗收不只測「答對」，還要測「不亂答」

每位 Engineer 至少需測四種情境。

## Case A — 正常案例

資料充分，應得到正確結論。

## Case B — 類似但不同根因

例如 Leakage Engineer：

- 真正 leak
- blocked vent
- driver variation
- cavity volume change

必須能區分。

## Case C — 資料不足

AERIS 必須回答：

> Evidence insufficient

並要求下一個必要實驗。

不可硬猜。

## Case D — 超出能力邊界

Engineer 應 escalation，不可冒充其他專家。

---

# 41. 前端的「發散 → 收斂」驗收

前端應有兩種思考動作。

## 發散

例如：

> Speaker 低頻掉了。

AERIS 可提出：

- Leakage
- Enclosure
- Driver T/S
- Vent
- Thermal
- Amplifier
- Measurement setup

## 收斂

透過：

- Product
- Phase
- Symptom
- Frequency
- Golden / NG
- Available evidence
- Constraints

逐步把候選縮小。

因此 Front Desk 的品質指標不是「問越多越好」。

而是：

> **用最少但必要的問題，形成足夠後端執行的 ORDER.md。**

---

# 42. 建議的 Front Desk 狀態機

```text
S0 START
 ↓
S1 CAPTURE
   Voice / Text
 ↓
S2 INTENT
   使用者想做什麼？
 ↓
S3 DIVERGE
   合理可能方向
 ↓
S4 CONVERGE
   必要澄清
 ↓
S5 EVIDENCE
   有什麼資料 / 缺什麼資料
 ↓
S6 ROUTE
   預選 Expert Pod
 ↓
S7 PREVIEW
   顯示點菜單摘要
 ↓
S8 CONFIRM
   使用者確認
 ↓
S9 ORDER_LOCKED
   生成 ORDER.md
```

---

# 43. `ORDER.md` 必須可以「重新播放」

AERIS 必須能做到：

```text
同一份 ORDER.md
      ↓
重新送進 Backend
      ↓
得到可比較的 Delivery
```

這很重要，因為：

- 模型升級後要做 regression
- Tool 更新後要比較
- 演算法更新後要驗證
- 同一問題不同版本要做 A/B

因此 `ORDER.md` 是正式工程 input，不只是聊天摘要。

---

# 44. Backend 必須避免的錯誤

禁止以下行為：

1. 收到 Order 後又無限制自由聊天。
2. 沒有 evidence 就直接宣布 root cause。
3. 只產生漂亮 PPT，沒有計算檔。
4. Excel 數字與 PPT 不一致。
5. Expert Pod 不記錄版本。
6. Tool execution 沒有 log。
7. 找不到答案時虛構數據。
8. 不知道就跳過 Acceptance Criteria。
9. 100 位 Engineer 只有 prompt，沒有 Golden Case。
10. UI 顯示 Production Ready，但沒有 G0–G10 PASS 記錄。

---

# 45. Frontend / Backend 責任界線

| 層 | 應該做 | 不應該做 |
|---|---|---|
| Frontend | 理解、引導、收斂、發散、確認 | 假裝已完成工程分析 |
| ORDER.md | 定義任務、輸入、限制、交付 | 填入尚未計算的結論 |
| Orchestrator | 拆任務、選專家、控流程 | 自己冒充所有專家 |
| Engineer | 在自己 scope 執行 SOP | 超出 scope 仍強行作答 |
| Tool | 計算、模擬、資料處理 | 生成沒有來源的結論 |
| Reviewer | 找錯誤、矛盾、證據缺口 | 只做文字潤飾 |
| Excel | 數據 source of truth | 只放漂亮摘要 |
| PPT | 解釋、決策、風險 | 成為唯一數據來源 |

---

# 46. AERIS 的完整「點餐」對應

| 餐廳概念 | AERIS 對應 |
|---|---|
| 顧客 | 使用者 |
| 語音告訴服務員 | Voice input |
| 服務員 | AERIS Front Desk / Navigator |
| 菜單 | 100 Capability Modules |
| 詢問口味 / 人數 / 禁忌 | Guided Questions / Constraints |
| 點菜 | Selected Expert Pod / Tasks |
| 點菜單 | `ORDER.md` |
| 廚房派單 | Orchestrator |
| 廚師 | 100 Acoustic Engineers |
| 廚具 | Python / COMSOL / APx / Klippel / MATLAB |
| 食材 | Data / Spec / CAD / Measurement |
| 出菜檢查 | Reviewer / Evidence Gate |
| 數據成品 | `Results.xlsx` |
| 說明成品 | `Report.pptx` |
| 整桌出餐 | `CASE-xxxx_DELIVERY/` |

這個比喻可以保留作為產品概念，但程式內部仍應使用：

- Order
- Case
- Capability
- Task
- Evidence
- Delivery
- Acceptance

等工程化命名。

---

# 47. 最終 End-to-End Definition of Done

AERIS 的一個 Case 完整完成，必須同時滿足：

```text
[PASS] Voice 或 Text 成功輸入
[PASS] Guided Intake 完成
[PASS] ORDER.md 產生
[PASS] 使用者確認
[PASS] Router 正確
[PASS] Expert Pod 執行
[PASS] Required Tool 執行
[PASS] Evidence 完整
[PASS] Results.xlsx 產生
[PASS] Report.pptx 產生
[PASS] Excel / PPT 數字一致
[PASS] Reviewer PASS
[PASS] Acceptance Criteria PASS
[PASS] Case 全程可追溯
```

任何一項失敗：

> Case 不得標示 Completed。

---

# 48. 建議開發順序

不要一開始同時施工 100 位 Engineer。

建議先打通一條 Vertical Slice：

```text
Voice/Text
  ↓
Front Desk
  ↓
ORDER.md
  ↓
#041 Notebook Acoustic Engineer
  ↓
#023 Leakage Engineer
  ↓
#057 Impedance Measurement Engineer
  ↓
#086 Failure Analysis Engineer
  ↓
Python analysis
  ↓
Results.xlsx
  ↓
Report.pptx
  ↓
#003 Reviewer
  ↓
#100 Integration
```

這條完整 PASS 後，再複製框架到其餘 Engineer。

第一個推薦驗收案例：

> **NB Speaker Golden vs NG，180–500 Hz SPL -4 dB，判斷 Leakage / Enclosure / Driver。**

理由：

- 容易準備 Golden data
- 有定量 FR / THD / IMP
- 可以驗證發散與收斂
- 可以測多 Engineer orchestration
- Excel / PPT 都有明確內容
- 很符合 AERIS 核心聲學工程價值

---

# 49. 100 Engineer 擴展波次

建議不要依 ID 依序硬做，而是依「可形成完整工作流」分批。

## Wave 1 — Speaker Failure Analysis

- 003
- 018
- 021
- 022
- 023
- 057
- 086
- 091
- 097
- 100

目標：

> 打通第一條完整 Order → Excel → PPT。

## Wave 2 — Measurement / Factory

- 051–060
- 081–090

目標：

> 儀器 / 生產 / 品質流程落地。

## Wave 3 — Microphone / Algorithm

- 031–040
- 071–080

目標：

> Mic / DSP / audio algorithm。

## Wave 4 — CAE / Optimization

- 061–070

目標：

> CAD / simulation / correlation。

## Wave 5 — Product Integration / Governance

- 001–010
- 041–050
- 092–099

目標：

> 完整跨域 orchestration 與決策層。

---

# 50. 這個新設計的核心結論

AERIS 的產品流程正式由：

> 「使用者直接找 AI 工程師聊天」

升級為：

> **「自然語言下單 → 工程訂單 → AI 專家團隊執行 → 工程交付 → 自動驗收」**

最重要的三個 artifact：

```text
INPUT CONTRACT
CASE-xxxx_ORDER.md

DATA TRUTH
CASE-xxxx_Results.xlsx

ENGINEERING EXPLANATION
CASE-xxxx_Report.pptx
```

其中：

- `ORDER.md` 代表前端完成。
- `Results.xlsx + Report.pptx` 代表後端完成。
- G0–G10 全 PASS 才代表該 Engineer 真正具備可驗收能力。

---

# 51. 修訂紀錄

| 日期 | Revision | 內容 |
|---|---|---|
| 2026-09-14 | v1.0 | 建立 100 位 Acoustic Engineer、Local AI、Navigator、Capability Contract 基準 |
| 2026-09-15 | v1.1 | 加入 Voice/Text Front Desk、餐廳點餐模型、ORDER.md、Excel/PPT Delivery、100 Engineer E2E 驗收架構 |

