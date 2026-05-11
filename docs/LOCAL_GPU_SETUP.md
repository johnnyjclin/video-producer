# 客戶端本地 GPU 設定指南

video-producer 支援兩條本地 GPU 出片路徑——**ComfyUI 路徑**（彈性最大、模型生態最廣）與 **diffusers 路徑**（直接 import 模型，無需額外 server）。兩條可以共存，selector 工具自動依配置路由。

本文是給「**客戶端機器**」的一次性設定步驟。

> Plugin 本身的 Python/Node 依賴用 `bash install.sh` 裝；本文只談 GPU 模型怎麼啟用。

---

## 目錄

1. [硬體需求](#硬體需求)
2. [前置：驅動 + Python](#前置驅動--python)
3. [Path A：ComfyUI（推薦）](#path-acomfyui推薦)
4. [Path B：diffusers 本地工具](#path-bdiffusers-本地工具)
5. [模型 vs VRAM 決策矩陣](#模型-vs-vram-決策矩陣)
6. [驗證安裝](#驗證安裝)
7. [Troubleshooting](#troubleshooting)

---

## 硬體需求

| VRAM | 能跑什麼 | 推薦組合 |
|---|---|---|
| **6 GB** | SD 1.5 / SD 2.1、SDXL-Lightning 4-step、Wan 2.1 1.3B、CogVideoX 2B、SVD 14-frame（壓低解析度） | ComfyUI + SDXL Lightning 模板 |
| **8 GB** | 以上 + FLUX-schnell GGUF Q4、SVD 768×432、AnimateDiff | ComfyUI + FLUX/SVD 模板 (主力配置) |
| **10-12 GB** | 以上 + LTX-2、CogVideoX 5B、HunyuanVideo（offload）、SVD-XT | ComfyUI + diffusers 雙開 |
| **16 GB+** | 以上 + FLUX-dev FP16、HunyuanVideo 1.5 全速 | 任意組合 |
| **24 GB+** | 以上 + Wan 2.1 14B、Flux-pro 等大模型 | diffusers 為主 |

**主要目標**：RTX 4060 8GB。本文所有「預設配置」都是針對這張卡。

### 額外資源建議

- **系統 RAM**：≥ 16 GB（模型載入時瞬間佔用很大）
- **硬碟**：≥ 50 GB free space（模型權重總和）
- **連網**：第一次下載權重需要（FLUX 12GB、Wan 2.1 1.3B ~6GB、SVD ~9.5GB...）

---

## 前置：驅動 + Python

### 1. NVIDIA 驅動 + CUDA

確認 `nvidia-smi` 跑得起來：

```bash
nvidia-smi
# 應該看到你的卡型號 + Driver Version + CUDA Version
```

如果沒有：
- **Windows**：去 [NVIDIA 官網](https://www.nvidia.com/Download/index.aspx) 抓你的卡的最新驅動
- **Linux (Ubuntu)**：`sudo apt install nvidia-driver-550 nvidia-cuda-toolkit`
- **WSL2**：在 Windows 上裝驅動，WSL2 會自動共用

CUDA 版本目標：**≥ 12.1**（torch 2.0+ 需要）。

### 2. Python ≥ 3.10

```bash
python --version    # >= 3.10，建議 3.11
```

### 3. PyTorch with CUDA

video-producer 的 `requirements-gpu.txt` 列了 torch≥2.0，但你必須確保**是 CUDA 版**不是 CPU 版：

```bash
# 先檢查（這要在 video-producer 的 .venv 裡跑）
python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"
# 期望：True 12.x
```

如果 `False`：

```bash
# 解除安裝 CPU 版 torch（如果有的話）
pip uninstall -y torch torchvision torchaudio

# 裝 CUDA 版（CUDA 12.1 對應 cu121）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

---

## Path A：ComfyUI（推薦）

ComfyUI 是個獨立的 Python server，跑在你本機（loopback `127.0.0.1:8188`，不出網卡）。我們的 `comfyui_image` / `comfyui_video` 工具透過 HTTP 跟它溝通。

**為什麼推薦這條**：
- 模型生態最廣（FLUX GGUF 量化、SDXL Lightning、SVD、AnimateDiff、IPAdapter、LoRA、ControlNet...）
- 換模型 = 換 workflow JSON，不動 Python
- 8GB VRAM 甜蜜點：FLUX-schnell GGUF Q4 出圖 + SVD 14-frame i2v

### Step 1：clone + 裝依賴

```bash
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI
pip install -r requirements.txt
```

### Step 2：啟動 server

```bash
python main.py --listen 127.0.0.1 --port 8188
```

第一次啟動會初始化目錄結構：

```
ComfyUI/
├── models/
│   ├── checkpoints/     ← SDXL / SD1.5 / SVD 等大模型
│   ├── unet/            ← FLUX UNET (GGUF)
│   ├── clip/            ← FLUX text encoders
│   ├── vae/             ← VAE 解碼器
│   └── loras/           ← LoRA (選用)
└── custom_nodes/        ← 第三方擴充節點
```

留著 server 跑著（terminal 不能關），開新 terminal 繼續下一步。

### Step 3：裝必要的 custom nodes

```bash
cd ComfyUI/custom_nodes

# ComfyUI-Manager — 圖形化裝其他 custom nodes（強烈推薦）
git clone https://github.com/ltdrdata/ComfyUI-Manager

# ComfyUI-GGUF — 跑 FLUX GGUF 量化模型必裝
git clone https://github.com/city96/ComfyUI-GGUF

# ComfyUI-VideoHelperSuite — SVD 影片輸出 MP4 必裝
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite

cd ..
```

重啟 ComfyUI server（`Ctrl+C` 然後重新 `python main.py --listen 127.0.0.1 --port 8188`）。

### Step 4：下載模型權重

這是最佔時間 + 硬碟的一步。video-producer 預設的 3 個 workflow 需要這些檔案。

#### 先：HuggingFace CLI + 登入

```bash
# 一次性裝好（已裝可跳過）
pip install -U "huggingface_hub[cli]"
```

新版 `hf` CLI（`huggingface_hub ≥ 0.20`）取代了舊的 `huggingface-cli`，兩個都可用，**本指南用 `hf`**。重點變更：

- 舊 flag `--local-dir-use-symlinks False` 已移除——新版預設就是直接下載實檔，**不要再加這個 flag**（會報 "No such option" 然後死掉）
- 舊命令 `huggingface-cli download` 仍可用但不會收到新功能，建議用 `hf download`

**強烈建議登入**，理由有二：

1. **不登入會被 HF rate-limit** — 下載期間會跳 `Warning: You are sending unauthenticated requests`，IP 級限速容易斷
2. **有些 repo 是 gated**（如下表標註 🔒 的），不登入直接 `403 Access denied`

```bash
# Step 1：拿一個 read token
#   到 https://huggingface.co/settings/tokens 建一個 "read" type token

# Step 2：登入 CLI
hf auth login
# 貼 token，按 Enter

# Step 3：對 gated repo 點接受
#   到 model 的 HF 頁面，點頁面上方的 "Agree and access repository"
#   每個 gated repo 各做一次（看下方表標 🔒 的）
```

#### 工作流 1：`sdxl_lightning`（最低門檻、純核心 node）

| 檔案 | 放哪裡 | 大小 | 來源 |
|---|---|---|---|
| `sd_xl_lightning_4step.safetensors` | `ComfyUI/models/checkpoints/` | ~6.5 GB | `ByteDance/SDXL-Lightning`（或任何 merged SDXL-Lightning checkpoint） |

下載命令：

```bash
cd /path/to/ComfyUI
hf download ByteDance/SDXL-Lightning sdxl_lightning_4step.safetensors --local-dir models/checkpoints
# workflow 預設找 sd_xl_lightning_4step.safetensors（有底線）
cd models/checkpoints && mv sdxl_lightning_4step.safetensors sd_xl_lightning_4step.safetensors && cd ../..
```

#### 工作流 2：`flux_schnell_gguf`（最佳 8GB 圖質）

| 檔案 | 放哪裡 | 大小 | 來源 |
|---|---|---|---|
| `flux1-schnell-Q4_K_S.gguf` | `ComfyUI/models/unet/` | ~6.5 GB | `city96/FLUX.1-schnell-gguf` |
| `t5xxl_fp8_e4m3fn.safetensors` | `ComfyUI/models/clip/` | ~5 GB | `comfyanonymous/flux_text_encoders` |
| `clip_l.safetensors` | `ComfyUI/models/clip/` | ~250 MB | `comfyanonymous/flux_text_encoders` |
| `ae.safetensors` | `ComfyUI/models/vae/` | ~340 MB | 🔒 `black-forest-labs/FLUX.1-schnell`（gated — 要先點 Accept） |

下載命令：

```bash
cd /path/to/ComfyUI

hf download city96/FLUX.1-schnell-gguf flux1-schnell-Q4_K_S.gguf --local-dir models/unet
hf download comfyanonymous/flux_text_encoders t5xxl_fp8_e4m3fn.safetensors --local-dir models/clip
hf download comfyanonymous/flux_text_encoders clip_l.safetensors --local-dir models/clip

# 注意：直接抓 root 的 ae.safetensors（不是 vae/ 子資料夾的 diffusion_pytorch_model）
# 這需要先在 HF 網頁點 "Agree and access repository"
hf download black-forest-labs/FLUX.1-schnell ae.safetensors --local-dir models/vae
```

⚠️ FLUX-schnell 是 distilled，**`cfg=1.0`、`steps=4`、negative prompt 無效**。不要去調這些。

#### 工作流 3：`svd_image_to_video`（image-to-video，2 秒 motion clip）

| 檔案 | 放哪裡 | 大小 | 來源 |
|---|---|---|---|
| `svd.safetensors` | `ComfyUI/models/checkpoints/` | ~9.5 GB | 🔒 `stabilityai/stable-video-diffusion-img2vid`（gated — 要先點 Accept） |

下載命令：

```bash
cd /path/to/ComfyUI

# 同樣要先在 HF 網頁點 "Agree and access repository"
hf download stabilityai/stable-video-diffusion-img2vid svd.safetensors --local-dir models/checkpoints
```

⚠️ **絕對不要用 `svd_xt.safetensors`**——那是 25-frame 版，需要 ≥ 10 GB VRAM，4060 8GB 一定 OOM。

#### 驗證模型都齊了

```bash
cd /path/to/ComfyUI

# Option 1（如果只下了 sdxl_lightning）
ls -lh models/checkpoints/sd_xl_lightning_4step.safetensors   # ~6.5G

# Option 2（如果也下了 flux_schnell_gguf）— 共 4 個檔
ls -lh models/unet/flux1-schnell-Q4_K_S.gguf                  # ~6.5G
ls -lh models/clip/t5xxl_fp8_e4m3fn.safetensors               # ~4.9G
ls -lh models/clip/clip_l.safetensors                         # ~246M
ls -lh models/vae/ae.safetensors                              # ~340M

# Option 3（如果也下了 svd_image_to_video）
ls -lh models/checkpoints/svd.safetensors                     # ~9.5G
```

任一檔案大小明顯偏小（例如只有幾百 KB）= 下載中斷或被 HF 擋掉，重跑 `hf download` 會自動 resume。

### Step 5：驗證

```bash
curl -fsS http://127.0.0.1:8188/system_stats
# 應該回 JSON，列出你的 GPU 名稱 + VRAM
```

從 video-producer repo 跑：

```bash
python -c "
from tools.tool_registry import registry
registry.discover()
img = registry.get('comfyui_image')
vid = registry.get('comfyui_video')
print('comfyui_image:', img.get_status().value)
print('  templates:', list(img.provider_matrix.keys()))
print('comfyui_video:', vid.get_status().value)
print('  templates:', list(vid.provider_matrix.keys()))
"
```

期望：

```
comfyui_image: available
  templates: ['flux_schnell_gguf', 'sdxl_lightning']
comfyui_video: available
  templates: ['svd_image_to_video']
```

完整工作流詳細說明（含 slot 結構、如何加新模板）見 [tools/comfyui_workflows/README.md](../tools/comfyui_workflows/README.md)。

### Step 6（選用）：自訂 host / port

預設 `127.0.0.1:8188`。如果你把 ComfyUI 跑在另一台 GPU 機器上：

```bash
# 在跑 ComfyUI 的機器
python main.py --listen 0.0.0.0 --port 8188

# 在跑 video-producer 的機器，設環境變數
export COMFYUI_HOST=192.168.1.50
export COMFYUI_PORT=8188
```

### Step 7：ComfyUI 怎麼跟 Claude Code 連接？

簡答：**沒有特別的「連接」步驟**。ComfyUI 跑著、plugin 裝著，兩件事就會自動連上。

```
┌─────────────────────────────────────────────────────┐
│  Claude Code (terminal / IDE)                       │
│   ┌────────────────────────────────────────┐        │
│   │  video-producer plugin                  │        │
│   │  ├─ MCP server (mcp/server.py)         │        │
│   │  └─ tools registry                     │        │
│   │       ├─ comfyui_image                 │        │
│   │       └─ comfyui_video                 │        │
│   │            │ HTTP                       │        │
│   └────────────┼────────────────────────────┘        │
└────────────────┼─────────────────────────────────────┘
                 │
                 │  GET /system_stats  → 確認還活著
                 │  POST /prompt       → 送 workflow
                 │  GET /history/<id>  → 拉結果
                 │  GET /view?...      → 下載圖/影片
                 ▼
        ┌─────────────────────┐
        │  ComfyUI server     │ ← 你 `python main.py` 跑起來的那個
        │  127.0.0.1:8188     │
        └─────────────────────┘
```

**關鍵概念**：ComfyUI 是個**獨立的 Python process**，跟 plugin 完全脫鉤。Plugin 內的 `comfyui_image` / `comfyui_video` 工具只是個 HTTP client，呼叫 ComfyUI 的 REST API。

#### 三種典型部署情境

##### 情境 A：本機跑 ComfyUI（最常見、最簡單）

```
┌──────── 同一台機器 ────────┐
│  Claude Code               │
│  └─ plugin                 │
│      └─ HTTP → 127.0.0.1:8188
│                  ▲          │
│  ComfyUI server  │          │
│  └────────────────         │
└────────────────────────────┘
```

**設定步驟**：

```bash
# Terminal 1：啟動 ComfyUI server，留著別關
cd ComfyUI
python main.py --listen 127.0.0.1 --port 8188

# Terminal 2：開 Claude Code（plugin 已透過 marketplace 裝好）
claude

# Claude Code 裡的 agent 自動找到 ComfyUI
# 不需要任何手動「連接」指令
```

驗證：

```bash
# Claude Code 裡叫 agent 跑：
"run preflight and show me what's configured"

# 應該看到 comfyui_image / comfyui_video 都 status=available
```

##### 情境 B：ComfyUI 跑在另一台 GPU 機器（LAN 內）

例如：MacBook 上開發 + 開 Claude Code，旁邊一台 PC 有 RTX 4060 跑 ComfyUI。

```
┌─ MacBook ────────┐         ┌─ PC (Windows/Linux) ─┐
│ Claude Code      │         │ ComfyUI server       │
│ └─ plugin        │ ──HTTP──▶ 0.0.0.0:8188         │
│   COMFYUI_HOST=  │  LAN    │                     │
│   192.168.1.50   │         │ (有 GPU)            │
└──────────────────┘         └─────────────────────┘
```

**PC 端**：

```bash
# 必須用 --listen 0.0.0.0 才接受外部連線（不是 127.0.0.1）
python main.py --listen 0.0.0.0 --port 8188

# 確認 PC 的 LAN IP
ipconfig    # Windows
ip a        # Linux
# 例如：192.168.1.50
```

**MacBook 端**——在 plugin 根目錄（裝 video-producer 那個資料夾）的 `.env` 加：

```bash
COMFYUI_HOST=192.168.1.50
COMFYUI_PORT=8188
```

或暫時用 shell env：

```bash
export COMFYUI_HOST=192.168.1.50
export COMFYUI_PORT=8188
claude   # 重新開 Claude Code session
```

⚠️ **防火牆**：PC 端可能要開放 port 8188 的 inbound：

- Windows：`New-NetFirewallRule -DisplayName "ComfyUI" -Direction Inbound -Protocol TCP -LocalPort 8188 -Action Allow`
- Linux ufw：`sudo ufw allow 8188/tcp`

##### 情境 C：WSL2 / Docker / SSH tunnel

如果 ComfyUI 跑在 WSL2 裡、Docker container 裡、或遠端 SSH server 上：

**WSL2**：WSL2 跟 Windows 主機透過 `localhost` 可以互通，但要注意 WSL2 的 IP 會變動。建議從 Windows 主機 access WSL2 用 `localhost`（這是 Microsoft 預設的 port forwarding）：

```bash
# 在 WSL2 裡跑 ComfyUI
python main.py --listen 0.0.0.0 --port 8188

# 在 Windows 主機跑 Claude Code，plugin 用預設值（127.0.0.1）就能連上
# Microsoft 的 WSL2 自動把 127.0.0.1:8188 轉發進 WSL2
```

**SSH tunnel**（最隱密、跨 internet 也行）：

```bash
# 從你的開發機，把遠端 GPU server 的 8188 port forward 到本機
ssh -L 8188:127.0.0.1:8188 user@gpu-server.example.com

# 之後 plugin 用預設 127.0.0.1:8188 就會穿過 tunnel
# Claude Code 跟 ComfyUI 都以為對方在本機
```

**Docker**：把 container 的 8188 publish 到 host：

```bash
docker run -p 8188:8188 --gpus all your-comfyui-image
# plugin 用預設 127.0.0.1:8188 連上
```

#### 為什麼這樣設計？

| 設計選擇 | 原因 |
|---|---|
| HTTP 而非 IPC / shared memory | ComfyUI 可以跑在任何地方（本機、LAN、遠端、container） |
| 預設 loopback (`127.0.0.1`) | 安全 — 不會意外暴露 GPU server 到網路 |
| 用 env var 設 host/port | 不用改 plugin 程式碼，部署彈性大 |
| Plugin 是純 client，不啟動 server | 客戶可以自己用 ComfyUI 的 GUI 開發 workflow，然後 plugin 直接用 |

#### 連接斷掉時會發生什麼

ComfyUI server 沒開、port 不通、或 host 設錯 → plugin 的工具 `get_status()` 回 `UNAVAILABLE`。Agent 收到後會：

1. 在 preflight 顯示 `comfyui_image: unavailable`
2. 從 selector 候選名單裡剔除
3. 改去挑下一個可用的 provider（如本地 diffusers 工具、或雲端 API 如果有設 key）
4. **不會** silent crash，**不會** 偷打雲端 API（除非 selector 評分剛好讓雲端贏）

完整 fallback 邏輯見 [tools/graphics/image_selector.py:225-241](../tools/graphics/image_selector.py)。

---

## Path B：diffusers 本地工具

不想跑額外 server？這條走 HuggingFace diffusers 直接載模型進記憶體。每個工具呼叫時自己載入。

**通用安裝**：

```bash
cd /path/to/video-producer
pip install -r requirements-gpu.txt
pip install diffusers transformers accelerate pillow requests

# 開啟本地生成（這個 flag 是「我同意載入大模型」的明確訊號）
export VIDEO_GEN_LOCAL_ENABLED=true
```

第一次呼叫每個工具時，diffusers 會自動從 HuggingFace 下載 model 到 `~/.cache/huggingface/`。

### 工具清單

| Tool | 模型 | VRAM | T2V/I2V | 預設解析度 | License |
|---|---|---|---|---|---|
| `local_diffusion` | Stable Diffusion 2.1 (text→image) | ~4 GB | image only | 512×512 | CreativeML OpenRAIL |
| `wan_video` | Wan 2.1 (1.3B) | ~8 GB | T2V + I2V | 832×480 @ 16fps, 81 frames | Apache-2.0 |
| `wan_video` (14B) | Wan 2.1 (14B) | ~24 GB | T2V + I2V | 1280×720 @ 16fps | Apache-2.0 |
| `ltx_video_local` | LTX-2 | ~12 GB | T2V + I2V | 768×512 @ 24fps, 121 frames | LTX-2 Community |
| `hunyuan_video` | HunyuanVideo 1.5 | ~14 GB | T2V + I2V | 848×480 @ 24fps, 121 frames | Apache-2.0 |
| `cogvideo_video` (5B) | CogVideoX 1.5 | ~12 GB | T2V + I2V | 720×480 @ 8fps, 49 frames | Apache-2.0 |
| `cogvideo_video` (2B) | CogVideoX (2B) | ~6 GB | T2V only | 720×480 @ 8fps | Apache-2.0 |

### 用法（registry 路徑）

```python
from tools.tool_registry import registry
registry.discover()

# T2V via Wan 2.1 1.3B（最 8GB-friendly 的 text-to-video）
registry.get("wan_video").execute({
    "operation": "text_to_video",
    "model_variant": "wan2.1-1.3b",
    "prompt": "a steaming bowl of beef noodle soup on a wooden table",
    "num_frames": 81,
    "output_path": "out.mp4",
})

# I2V via LTX-2（更高動畫品質，需 12GB）
registry.get("ltx_video_local").execute({
    "operation": "image_to_video",
    "reference_image_path": "keyframe.png",
    "prompt": "slow camera push-in, soft window light",
    "num_frames": 121,
    "output_path": "clip.mp4",
})
```

### 用法（selector 路徑——讓 agent 自動挑）

```python
registry.get("video_selector").execute({
    "operation": "text_to_video",
    "prompt": "...",
    "output_path": "out.mp4",
})
# selector 自動依「使用者偏好 > 可用性 > 評分」挑工具
```

### 關掉自動下載（air-gapped 環境）

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
```

需要先手動下載 weights 到 `~/.cache/huggingface/hub/` 才能跑。

---

## 模型 vs VRAM 決策矩陣

「我的 GPU 有 X GB VRAM，該用哪個？」

### 8 GB VRAM (RTX 4060 / 3060 Ti / 3070)

**主力推薦**：

```
出圖   → ComfyUI + flux_schnell_gguf (Q4_K_S)
出影片 → ComfyUI + svd_image_to_video (svd.safetensors，14 frame)
備援   → wan_video (wan2.1-1.3b) 走 diffusers 路徑做 t2v
```

| 任務 | 推薦工具 | 備註 |
|---|---|---|
| 高品質單張圖 | `comfyui_image` (flux_schnell_gguf) | 自然語言 prompt |
| 大量批次圖 | `comfyui_image` (sdxl_lightning) | 4-step、~12s 一張 |
| Image → 2 秒 motion | `comfyui_video` (svd_image_to_video) | SVD，i2v 最強 |
| 純文字 → 5 秒影片 | `wan_video` (wan2.1-1.3b, t2v) | 80 frames @ 16fps |
| **不要做** | HunyuanVideo / LTX-2 / Wan 14B / svd_xt | OOM 必死 |

### 12 GB VRAM (RTX 3060 12GB / 4070 / A4000)

加入：

- `ltx_video_local`：121 frames @ 24fps，比 SVD 長很多
- `cogvideo_video` (5B)：text-to-video，49 frames
- HunyuanVideo（要開 `enable_model_offload`）

### 16-24 GB VRAM (RTX 4080 / 4090 / A5000)

幾乎所有 diffusers 工具都跑得開不用 offload。可以開：

- FLUX-dev FP16（無量化版，最高品質）
- Wan 2.1 14B
- HunyuanVideo 1.5 全速
- 同時跑 ComfyUI server + diffusers tools

### < 6 GB VRAM 怎麼辦

老實說很難。可行選項：

- ComfyUI + SD 1.5（不是 SDXL）+ 512×512
- `cogvideo_video` (2B) 做 text-to-video，48fps、低解析
- 走雲端 API 路徑（設 `FAL_KEY` / `RUNWAY_API_KEY` 等）

---

## 驗證安裝

### 完整 preflight（agent 入口會跑這個）

```bash
python -c "
from tools.tool_registry import registry
import json
registry.discover()
print(json.dumps(registry.provider_menu_summary(), indent=2))
"
```

期望輸出包含：

```json
{
  "capabilities": [
    {"name": "image_generation", "configured": 1, "total": 7, "providers": ["comfyui", "..."]},
    {"name": "video_generation", "configured": 2, "total": 13, "providers": ["comfyui", "wan", "..."]}
  ],
  "composition_runtimes": {"ffmpeg": true, "remotion": true, "hyperframes": false},
  "setup_offers": [...],
  "runtime_warnings": []
}
```

### 個別工具狀態

```bash
python -c "
from tools.tool_registry import registry
registry.discover()
for name in ['comfyui_image', 'comfyui_video', 'wan_video', 'ltx_video_local',
             'hunyuan_video', 'cogvideo_video', 'local_diffusion']:
    t = registry.get(name)
    if t:
        print(f'  {name:25s} {t.get_status().value}')
"
```

期望（8GB 主力配置）：

```
  comfyui_image             available
  comfyui_video             available
  wan_video                 available
  ltx_video_local           unavailable   # 12GB 起跳
  hunyuan_video             unavailable   # 14GB 起跳
  cogvideo_video            available     # 2B 變體可
  local_diffusion           available
```

---

## Troubleshooting

### ComfyUI

| 症狀 | 原因 | 解法 |
|---|---|---|
| `comfyui_image status=unavailable` 但 server 在跑 | `COMFYUI_HOST`/`COMFYUI_PORT` 沒對齊 | `curl http://127.0.0.1:8188/system_stats`，對照 env var |
| 跑 workflow 時 `prompt outputs failed validation` | Workflow 引用的 custom node 沒裝 | 看 workflow 的 `_meta.required_custom_nodes`，補裝 |
| 跑 workflow 時 `model not found` | model 檔案沒放對路徑 | 看 workflow 的 `_meta.required_models`，照路徑放 |
| ComfyUI 啟動就 OOM | 另一個進程吃了 VRAM | `nvidia-smi` 看誰佔，kill 掉 |
| 在 GUI 看到 workflow 跑得起來但 API 失敗 | GUI 跟 API 的 workflow 格式不一樣 | 在 GUI 用「Save (API Format)」匯出，不是用「Save」 |

### diffusers (wan / ltx / hunyuan / cog)

| 症狀 | 原因 | 解法 |
|---|---|---|
| `status=unavailable` | `VIDEO_GEN_LOCAL_ENABLED` 沒設、或缺 `diffusers` package | `export VIDEO_GEN_LOCAL_ENABLED=true` + 重裝依賴 |
| `CUDA out of memory` | 模型太大 | 開 `enable_model_offload=True`，或換更小變體（如 cog-2b、wan-1.3b） |
| 第一次跑很慢 | 從 HuggingFace 下載 weights | 後續會 cache 在 `~/.cache/huggingface/` |
| `torch.cuda.is_available() == False` | torch 是 CPU 版 | 重裝 CUDA 版：見 [前置](#前置驅動--python) |
| 跑出來 quality 很差 | `num_inference_steps` 太低 | Wan/LTX 建議 30-50 steps；CogVideoX 50 |

### 共通

| 症狀 | 原因 | 解法 |
|---|---|---|
| `nvidia-smi` not found | 驅動沒裝 | 見 [前置](#前置驅動--python) |
| 模型下載到一半中斷 | 連線不穩 | 重跑就好，HuggingFace 會 resume |
| 硬碟爆滿 | 模型重複下載 | ComfyUI 用 `models/` 路徑；diffusers 用 `~/.cache/huggingface/`。**可以同個 model 軟連結兩邊**避免重複 |
| HuggingFace `403 Access denied / This repository requires approval` | repo 是 gated，沒登入或沒接受 license | `hf auth login` + 在 HF 網頁點 "Agree and access repository"（見 Step 4 開頭） |
| HuggingFace `Warning: You are sending unauthenticated requests` | 沒登入，速度被 rate-limit | `hf auth login`；雖然抓得到但容易斷 |
| `hf download` 報 `No such option: --local-dir-use-symlinks` | 新版 CLI 移除了這個 flag | 刪掉 `--local-dir-use-symlinks False`，新版預設就是下載實檔 |

---

## 設定完之後

回去看 [PLUGIN_USAGE.md](../PLUGIN_USAGE.md) 了解 host agent 怎麼呼叫這些工具，或讀 [.claude/skills/comfyui/SKILL.md](../.claude/skills/comfyui/SKILL.md) 看 ComfyUI workflow 怎麼挑、怎麼下 prompt、多分鏡一致性怎麼做。

要在 host 小編 agent 端只跑本地（拒絕雲端工具）？目前沒有 hard switch——但客戶不設 `FAL_KEY` / `RUNWAY_API_KEY` / `ELEVENLABS_API_KEY` 等 env，selector 就會自動只挑到 status=available 的本地工具。完整路由邏輯見 [tools/graphics/image_selector.py:225-241](../tools/graphics/image_selector.py)。
