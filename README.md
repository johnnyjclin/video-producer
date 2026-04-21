# video-producer

輸入產品型號，10 分鐘內自動產出一支 30 秒商品展示影片。**Claude Code 專用。**

> Based on [OpenMontage](https://github.com/calesthio/OpenMontage) by calesthio（AGPLv3）。見 [NOTICE](NOTICE)。

[![License](https://img.shields.io/badge/license-AGPLv3-blue.svg)](LICENSE)

---

## 驗收標準

| # | 項目 |
|---|---|
| **#1** | 輸入產品型號後，10 分鐘內產出完整 30 秒展示影片 |
| **#2** | 影片含品牌 Logo、開場動畫、產品特點文字、背景音樂、結尾 CTA |
| **#3** | 支援至少 3 種語言旁白與字幕 |
| **#4** | 輸出格式適配 YouTube（16:9）與 TikTok / Reels（9:16）兩種比例 |

---

## 設計

- **Claude Code 專用**：移除 Cursor / Copilot / Codex / Windsurf 所有整合
- **Pipeline 驅動**：YAML manifest 定義流程，Markdown skill 定義每個 stage 的執行方式；沒有 Python orchestration logic
- **本地儲存**（2026-04-21 起）：
  - 品牌素材 = `media/assets/brand/`
  - 成品 = `projects/<product-id>/renders/final.mp4`
  - 決策日誌 = `projects/<product-id>/artifacts/decision_log.json`
- **執行入口 = Claude Code 自然語言**

### 三層知識架構

```
Layer 1: tools/ + pipeline_defs/   工具能力 + 流程編排
Layer 2: skills/                   每個 stage 的執行規範與品質標準
Layer 3: .agents/skills/           供應商 API 深度知識包
```

### 合成引擎

| 引擎 | 適合場景 |
|------|----------|
| **Remotion** | 資料驅動動畫、圖片轉影片、文字卡、字幕 |
| **FFmpeg** | 剪接、音訊混音、字幕燒錄（永遠可用） |

引擎在 proposal 階段鎖定，不允許靜默切換。

---

## 前置需求

```bash
node --version      # >= 18
python --version    # >= 3.10
ffmpeg -version     # 任意版本
claude --version    # Claude Code 已安裝
```

必要 API Key（至少一組影像生成 + 一組 TTS）：

```bash
# .env（從 .env.example 複製）
FAL_KEY=              # FLUX 圖片 + Kling / Veo 影片（推薦入門）
ELEVENLABS_API_KEY=   # TTS 旁白 + 背景音樂生成
RUNWAY_API_KEY=       # Runway Gen-4 影片生成（直接 API）
```

其他供應商見 `.env.example`，全部選填。

---

## 驗收流程

```bash
git clone https://github.com/johnnyjclin/video-producer.git
cd video-producer
make setup
```

進 Claude Code 後依序執行：

1. **確認環境** — 告訴 Claude `"run preflight and show me what's configured"`
2. **填 `.env`** — 加入至少一組影像生成 Key（`FAL_KEY` 推薦）和一組 TTS Key
3. **放品牌素材** — Logo 和產品圖放入 `media/assets/brand/`
4. **驗收 #1 #2** — `"Make a 30-second product showcase for [型號], 9:16 vertical"`
5. **驗收 #3** — `"Generate the same video with Japanese narration and subtitles"`
6. **驗收 #4** — `"Also export a 16:9 version for YouTube"`

---

### 加入 noirsboxes-agent 專案作為 Plugin

如果你的主要工作環境是 noirsboxes-agent，可以把 video-producer 掛進去，讓兩個專案的能力合併使用。

**Step 1 — 先在 video-producer 安裝依賴**

```bash
cd /path/to/video-producer
bash install.sh        # 安裝 Python + Node 依賴，產生 .env
# 填好 .env 的 API Key
```

**Step 2 — 在 noirsboxes-agent 的 Claude Code 裡加載 plugin**

```
/plugin add /path/to/video-producer
```

加載成功後，Claude Code 會顯示 `video-producer` plugin 已啟用，MCP server 自動掛載。

**Step 3 — 確認 plugin 可用**

```
"show me available plugins"
```

應該看到 `video-producer` 出現在清單，且 MCP tools（`runway_image_to_video`、`elevenlabs_tts`、`remotion_render` 等）可以被呼叫。

**Step 4 — 在 noirsboxes-agent 裡產影片**

```
"Make a 30-second product showcase for MD-905, 9:16"
```

Claude 會透過 video-producer plugin 的工具完成整個生產流程，成品輸出到 `video-producer/projects/<product-id>/renders/final.mp4`。

> **Plugin 路徑提示：** `/plugin add` 接受絕對路徑或相對路徑（相對於 noirsboxes-agent 專案根目錄）。建議用絕對路徑避免混淆。

---

## 目錄結構

```
video-producer/
├── CLAUDE.md               # Claude Code 指令入口
├── AGENT_GUIDE.md          # Agent 完整操作合約
├── README.md
├── NOTICE                  # 上游 OpenMontage 歸屬聲明
│
├── pipeline_defs/          # YAML pipeline 定義
├── skills/                 # Markdown stage director skills
├── tools/                  # Python 工具（影像、音訊、字幕、分析）
├── schemas/                # JSON Schema 驗證
├── styles/                 # 視覺風格 playbook
├── remotion-composer/      # React/Remotion 合成引擎
├── lib/                    # 核心基礎設施（checkpoint、pipeline loader）
└── tests/                  # Contract tests + QA harness
│
├── media/
│   └── assets/             # 🟡 gitignored；品牌素材（Logo、產品圖）
│       └── brand/
│
├── projects/               # 🟢 gitignored；每次生產的輸出
│   └── <product-id>/
│       ├── artifacts/      # 各 stage JSON artifact
│       ├── assets/         # 生成素材（圖、影、音）
│       └── renders/        # final.mp4
│
└── music_library/          # 🟡 gitignored；版權自由音樂（可選）
```

---

## 換產品 / 換品牌

- **換品牌** → 替換 `media/assets/brand/` 素材 + 調整 `styles/*.yaml` 色票與字體
- **換語言** → 同一指令加 `"with [語言] narration and subtitles"`
- **新增輸出格式** → 修改 `lib/media_profiles.py` 的 render profile

---

## 測試

```bash
# Contract tests（不需要 API Key）
make test-contracts

# 全部測試
make test
```

---

## License & 歸屬

Licensed under [GNU AGPLv3](LICENSE).

This project is a fork of [OpenMontage](https://github.com/calesthio/OpenMontage) by calesthio, also licensed under AGPLv3. See [NOTICE](NOTICE) for full attribution.
