# video-producer

**Claude Code 專用的影片製作工具集**。13 個 pipeline、80+ 個工具、本地 GPU 與雲端 API 都能跑——讓 agent 根據客戶需求自動挑路徑出片。

> Based on [OpenMontage](https://github.com/calesthio/OpenMontage) by calesthio（AGPLv3）。見 [NOTICE](NOTICE)。

[![License](https://img.shields.io/badge/license-AGPLv3-blue.svg)](LICENSE)

---

## 設計重點

- **Claude Code 專用**：移除 Cursor / Copilot / Codex / Windsurf 所有整合
- **Pipeline 驅動**：YAML manifest 定義流程，Markdown skill 定義每個 stage 的執行方式；沒有 Python orchestration logic
- **本地 GPU 路徑 + 雲端 API 路徑並存**：客戶可選離線、可選付費
- **執行入口 = Claude Code 自然語言**

### 三層知識架構

```
Layer 1: tools/ + pipeline_defs/   工具能力 + 流程編排
Layer 2: skills/                   每個 stage 的執行規範與品質標準
Layer 3: .claude/skills/           供應商 API 深度知識包
```

---

## 兩條出片路徑（不互斥）

### 🅰 本地 GPU 路徑（免 API key，適合離線/隱私）

需要一張 NVIDIA GPU（建議 RTX 4060 8GB +）跑 ComfyUI server。一次性裝好後，整條鏈完全離線。

```bash
# 啟動本地 ComfyUI（在 GPU 機器上）
git clone https://github.com/comfyanonymous/ComfyUI && cd ComfyUI
pip install -r requirements.txt
python main.py --listen 127.0.0.1 --port 8188
```

下載對應模型權重（FLUX-schnell GGUF / SDXL Lightning / Stable Video Diffusion）— 完整客戶端設定步驟見 **[docs/LOCAL_GPU_SETUP.md](docs/LOCAL_GPU_SETUP.md)**（含驅動、ComfyUI bring-up、diffusers 工具、VRAM 決策矩陣、troubleshooting）。

之後 agent 透過 `comfyui_image` / `comfyui_video` 工具直接打 `127.0.0.1:8188`，免 API key、免上傳、免計費。

### 🅱 雲端 API 路徑（追求品質上限）

至少設一組 image gen + 一組 TTS：

```bash
# .env（從 .env.example 複製）
FAL_KEY=              # FLUX 圖片 + Kling / Veo 影片
ELEVENLABS_API_KEY=   # TTS 旁白 + 背景音樂生成
RUNWAY_API_KEY=       # Runway Gen-4 影片生成（直接 API）
```

其他供應商見 `.env.example`，全部選填。

### 🅰 + 🅱 混合路徑

selector 工具（`image_selector` / `video_selector` / `tts_selector`）會自動依「使用者偏好 > 可用性 > 發現順序」路由。沒裝 ComfyUI 時自動走雲端；有裝且狀態 AVAILABLE 時優先本地。

---

## 合成引擎

| 引擎 | 適合場景 |
|------|----------|
| **Remotion** | 資料驅動動畫、圖片轉影片、文字卡、字幕 |
| **HyperFrames** | HTML/CSS/GSAP 動態排版、品牌啟動片、website-to-video |
| **FFmpeg** | 剪接、音訊混音、字幕燒錄（永遠可用） |

引擎在 proposal 階段鎖定，不允許靜默切換。

---

## 13 個 pipeline

| Pipeline | 用途 | 穩定性 |
|---|---|---|
| `animated-explainer` | 主題 → 完整 AI 生成解說影片 | production |
| `talking-head` | 真人說話素材剪輯 | beta |
| `screen-demo` | 螢幕錄影教學 / 產品 demo | production |
| `clip-factory` | 長片源 → 多條短片批次提取 | beta |
| `podcast-repurpose` | Podcast 精華片段 | beta |
| `cinematic` | 預告 / 氣氛剪輯 | production |
| `animation` | 動畫優先 / motion graphics | production |
| `hybrid` | 真人素材 + 補充視覺 | production |
| `avatar-spokesperson` | AI avatar 主播 / 對嘴 | production |
| `localization-dub` | 多語字幕與配音 | beta |
| `documentary-montage` | 紀錄片 montage | beta |
| `social-short-15s` | 15 秒社群短影音（IG / TikTok / Shorts），本地 GPU 優先 | beta |
| `framework-smoke` | 框架健康檢查 | test |

Agent 收到請求後讀 [AGENT_GUIDE.md](AGENT_GUIDE.md) → Rule Zero → 從上面挑 pipeline。

---

## 前置需求

```bash
node --version      # >= 18
python --version    # >= 3.10
ffmpeg -version     # 任意版本
claude --version    # Claude Code 已安裝

# 本地 GPU 路徑 (選用)
nvidia-smi          # >= 8GB VRAM 建議
```

---

## 安裝

```bash
git clone https://github.com/johnnyjclin/video-producer.git
cd video-producer
bash install.sh        # 裝 Python + Node 依賴，建立 .env scaffold
```

進 Claude Code 後：

1. **確認環境** — `"run preflight and show me what's configured"`
2. **填 .env**（雲端路徑）或 **啟動 ComfyUI**（本地路徑）
3. **下指令** — 例如：
   - `"Make a 30-second product showcase for our XYZ widget, 9:16 vertical"` → animated-explainer
   - `"Cut this 30-min webinar into 5 short clips"` → clip-factory  
   - `"產一支 15 秒 IG Reel 介紹我們的拿鐵"` → social-short-15s
   - `"Generate the same video with Japanese narration"` → localization-dub

---

## 把 video-producer 掛進別的 agent 專案

可以把這個 plugin 掛進任何 host agent 專案（不限定品牌），讓主 agent 委派影片生產任務。

**Step 1 — 在 video-producer 安裝依賴**

```bash
cd /path/to/video-producer
bash install.sh
```

**Step 2 — 在 host agent 專案的 Claude Code 註冊 marketplace 並裝 plugin**

```bash
claude plugin marketplace add /absolute/path/to/video-producer
claude plugin install video-producer@video-producer
```

**Step 3 — 確認 plugin 可用**

```
"show me available plugins"
```

應該看到 `video-producer` plugin 出現，MCP tools（`runway_image_to_video`、`elevenlabs_tts`、`remotion_render` 等）可被呼叫。

**Step 4 — 在 host agent 裡產影片**

```
"Make a 30-second product showcase for [產品名], 9:16"
```

成品輸出到 `video-producer/projects/<product-id>/renders/final.mp4`。

完整 plugin 整合說明見 [PLUGIN_USAGE.md](PLUGIN_USAGE.md)。

---

## 目錄結構

```
video-producer/
├── CLAUDE.md               # Claude Code 指令入口
├── AGENT_GUIDE.md          # Agent 完整操作合約
├── PROJECT_CONTEXT.md      # 架構與檔案地圖
├── PLUGIN_USAGE.md         # Plugin 安裝與整合
├── README.md
├── NOTICE                  # 上游 OpenMontage 歸屬聲明
│
├── pipeline_defs/          # YAML pipeline 定義 (13 支)
├── skills/                 # Markdown stage director skills + meta skills
├── tools/                  # Python 工具 (影像、音訊、字幕、分析、ComfyUI bridge)
│   └── comfyui_workflows/  # ComfyUI workflow templates (本地 GPU 路徑)
├── schemas/                # JSON Schema 驗證
├── styles/                 # 視覺風格 playbook
├── remotion-composer/      # React/Remotion 合成引擎
├── lib/                    # 核心基礎設施 (checkpoint、pipeline loader)
└── tests/                  # Contract tests + QA harness

# Gitignored，使用者本地存放
├── assets/brand/           # 品牌素材 (Logo、產品圖、視覺參考)
├── projects/<id>/          # 每次生產的輸出
└── music_library/          # 版權自由音樂 (可選)
```

---

## 客製化

- **換 pipeline** → 找 [pipeline_defs/](pipeline_defs/) 對應 YAML，或新增一個
- **換視覺風格** → 改 `styles/*.yaml` 色票、字體、轉場規則
- **換語言** → 指令加 `"with [語言] narration and subtitles"`
- **新增輸出格式** → 修改 `lib/media_profiles.py` 的 render profile

---

## 測試

```bash
make test-contracts    # Contract tests（不需 API Key）
make test              # 全部測試
```

---

## License & 歸屬

Licensed under [GNU AGPLv3](LICENSE).

This project is a fork of [OpenMontage](https://github.com/calesthio/OpenMontage) by calesthio, also licensed under AGPLv3. See [NOTICE](NOTICE) for full attribution.
