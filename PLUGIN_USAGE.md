# Using `video-producer` as a Claude Code plugin

This plugin gives a host agent access to a general-purpose video
production toolkit — 13 pipelines, 80+ tools, both local-GPU and
cloud-API paths. The host agent reads the customer's request, picks a
pipeline, and drives the production through it.

## What you get after install

| Surface | Name | Use it when… |
|---|---|---|
| **Pipelines** | `animated-explainer`, `talking-head`, `screen-demo`, `clip-factory`, `podcast-repurpose`, `cinematic`, `animation`, `hybrid`, `avatar-spokesperson`, `localization-dub`, `documentary-montage`, `social-short-15s` | The host agent picks one per the request shape — see [AGENT_GUIDE.md](AGENT_GUIDE.md) Rule Zero |
| **Local-GPU image** | `comfyui_image` | Local FLUX-schnell GGUF / SDXL-Lightning via ComfyUI server |
| **Local-GPU video** | `comfyui_video` | Local Stable Video Diffusion (image-to-video) via ComfyUI |
| **Local-GPU video (diffusers)** | `wan_video`, `ltx_video_local`, `hunyuan_video`, `cogvideo_video` | Direct diffusers pipelines (alternative to ComfyUI) |
| **Cloud image gen** | `flux_image`, `recraft_image`, `google_imagen`, `openai_image`, `grok_image` | Premium quality / no local GPU |
| **Cloud video gen** | `runway_video`, `kling_video`, `seedance_video`, `minimax_video`, `veo_video`, `higgsfield_video`, `heygen_video` | Top-tier motion, lip-sync, hero shots |
| **MCP cloud wrappers** | `runway_image_to_video`, `runway_text_to_video_gen45`, `elevenlabs_tts`, `elevenlabs_music`, `remotion_render`, `measure_audio_duration` | Direct cloud calls from host agent (no registry routing) |
| **Selectors** | `image_selector`, `video_selector`, `tts_selector` | Auto-route by preference + availability |

The host agent reads [AGENT_GUIDE.md](AGENT_GUIDE.md) Rule Zero, picks
the right pipeline, runs preflight, and only then executes. Pipelines
declare which tools they need; selectors handle multi-provider routing.

## Hardware target

- **CPU-only / API-only path**: any modern machine + API keys for FAL /
  Runway / ElevenLabs
- **Local-GPU path**: NVIDIA GPU recommended (RTX 4060 8GB+) — runs
  ComfyUI server locally, zero API cost
- **Hybrid**: install both. Selectors auto-route to local where
  available, fall back to cloud where not

## Install (one-time)

```bash
git clone <this-repo>
cd video-producer
bash install.sh        # Python + Node + .env scaffold
```

### Optional — bring up ComfyUI for the local-GPU path

Full instructions including the model download list live in
[tools/comfyui_workflows/README.md](tools/comfyui_workflows/README.md).
Quick version:

```bash
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI && pip install -r requirements.txt

# custom nodes for FLUX-GGUF + SVD (only needed for those workflows)
cd custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager
git clone https://github.com/city96/ComfyUI-GGUF
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
cd ..

# start the server (the bridge connects here)
python main.py --listen 127.0.0.1 --port 8188
```

Drop model weights per the workflow README's table, then verify:

```bash
curl -fsS http://127.0.0.1:8188/system_stats   # should return JSON
```

Override host/port via `COMFYUI_HOST` / `COMFYUI_PORT` env vars.

### Optional — fill .env for cloud providers

The plugin runs purely local with no .env. Add keys only for the cloud
providers you actually want to use:

```bash
FAL_KEY=                 # FLUX / Kling / Veo via fal.ai
RUNWAY_API_KEY=          # Runway Gen-4 / gen4.5
ELEVENLABS_API_KEY=      # TTS + music generation
GOOGLE_API_KEY=          # Imagen / VEO direct
OPENAI_API_KEY=          # DALL-E / OpenAI TTS
# … see .env.example for the full list
```

Preflight (`provider_menu_summary()`) reports which providers are
configured, and the selectors silently skip the unconfigured ones.

## Register with Claude Code (local marketplace install)

Claude Code does **not** have `/plugin add <path>`. Local installs go
through a self-hosted **marketplace** — the plugin folder declares
itself as a marketplace, you register it once, then install the plugin
from that marketplace. Once installed it's available globally in every
Claude Code session.

### Step 1 — validate (optional, recommended)

```bash
claude plugin validate /absolute/path/to/video-producer
```

Expect `✔ Validation passed`.

### Step 2 — register the self-marketplace

```bash
claude plugin marketplace add /absolute/path/to/video-producer
```

Verify:

```bash
claude plugin marketplace list
# → video-producer   /abs/path/to/video-producer   (local)
```

### Step 3 — install the plugin

```bash
claude plugin install video-producer@video-producer
```

Verify:

```bash
claude plugin list
# → video-producer@video-producer    Version: 0.2.0    Scope: user    Status: ✔ enabled
```

### What gets registered

Claude Code reads `.claude-plugin/plugin.json` and auto-loads the **MCP
server** (`mcp/server.py`); its low-level tools appear with the
`mcp__video-producer__` prefix.

The 13 pipelines + their stage director skills + the tool registry are
all picked up on demand by Rule Zero — no separate registration.

### Plugin lifecycle commands

| Command | Action |
|---|---|
| `claude plugin list` | List installed plugins, versions, status |
| `claude plugin disable video-producer` | Disable without uninstalling |
| `claude plugin enable video-producer` | Re-enable |
| `claude plugin uninstall video-producer@video-producer` | Uninstall (leaves source on disk) |
| `claude plugin update video-producer` | Pull latest from marketplace |
| `claude plugin marketplace update video-producer` | Refresh marketplace after local edits |
| `claude plugin marketplace remove video-producer` | Remove the whole marketplace |

### Session-only install (no persistence)

```bash
claude --plugin-dir /absolute/path/to/video-producer
```

Useful for testing uncommitted changes.

## How a host agent invokes the plugin

### Pattern 1 — pipeline-driven (the standard path)

The host agent reads [AGENT_GUIDE.md](AGENT_GUIDE.md), classifies the
request, picks a pipeline from `pipeline_defs/`, reads its stage
director skills, runs preflight, and executes:

```
User: "Make me a 60-second explainer about how solar panels work"

Host agent → Rule Zero → animated-explainer pipeline
          → reads pipeline_defs/animated-explainer.yaml
          → research → proposal → script → scene_plan → assets → edit → compose → publish
          → returns projects/solar-panels-explainer/renders/final.mp4
```

Different request shapes route to different pipelines automatically —
see the pipeline table in [AGENT_GUIDE.md](AGENT_GUIDE.md). The host
agent never invents its own production order.

### Pattern 2 — direct tool calls (one-shot generation)

For ad-hoc image / clip generation without going through a pipeline:

```python
from tools.tool_registry import registry
registry.discover()

# Local-GPU keyframe via FLUX-schnell GGUF
registry.get("comfyui_image").execute({
    "prompt": "a cinematic close-up of a Taipei street vendor at night",
    "workflow": "flux_schnell_gguf",
    "width": 1024, "height": 1024,
    "output_path": "out.png",
})

# Cloud equivalent via FLUX on fal.ai
registry.get("flux_image").execute({
    "prompt": "a cinematic close-up of a Taipei street vendor at night",
    "width": 1024, "height": 1024,
    "output_path": "out.png",
})

# Let the selector pick whichever is configured + available
registry.get("image_selector").execute({
    "prompt": "...",
    "output_path": "out.png",
})
```

### Pattern 3 — MCP cloud wrappers for hero shots

When the host agent wants a single high-quality cloud generation
without going through the registry:

```python
mcp__video-producer__runway_image_to_video(
    image_path="./hero.png",
    prompt="slow push-in, golden-hour, shallow depth of field",
    output_path="./hero-clip.mp4",
    duration=5,
    ratio="9:16",
)
```

Requires `RUNWAY_API_KEY` in `.env`.

## Picking a pipeline (cheat sheet)

| Customer request shape | Pipeline | Why |
|---|---|---|
| "Make a video about X" (topic-driven) | `animated-explainer` | Research → script → AI assets → render |
| "Edit this 30-min talk into highlights" | `clip-factory` | Long source → many short outputs |
| "Cut this footage into a teaser" | `cinematic` | Mood-led edit on existing footage |
| "Make a screen recording demo for our app" | `screen-demo` | Capture or synthetic screen recording |
| "Animate this concept" / motion-graphics-heavy | `animation` | Remotion/HyperFrames-first assets |
| "Talking head video from this raw footage" | `talking-head` | Cuts + captions + auto-reframe |
| "Avatar presenter version" | `avatar-spokesperson` | HeyGen / lip-sync routes |
| "Translate this video into Japanese" | `localization-dub` | Subtitle + dub pipeline |
| "Repurpose this podcast" | `podcast-repurpose` | Audio-led → visual derivatives |
| "Mix footage with B-roll generation" | `hybrid` | Real footage + generated visuals |
| "Documentary cut from this 2-hour interview" | `documentary-montage` | Theme-driven montage |
| "Quick 15s Reel / TikTok for our brand" | `social-short-15s` | Lean 5-stage path, local-GPU friendly |

If the host agent can't classify, AGENT_GUIDE.md says to ask the user
rather than guess.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `comfyui_image` reports `status=unavailable` | ComfyUI server not running, or `COMFYUI_HOST/PORT` mismatch | `curl http://127.0.0.1:8188/system_stats`; check env vars |
| `prompt outputs failed validation` (ComfyUI) | Workflow references a custom node not installed | Read the workflow's `_meta.required_custom_nodes`; install via ComfyUI-Manager |
| Cloud tool reports `status=unavailable` | API key not set | `cat .env`; add the relevant key per its `install_instructions` |
| Agent picks the "wrong" pipeline | Request was ambiguous | AGENT_GUIDE.md instructs agent to ask the user when unclear; if it didn't, file an issue and tighten the brief |
| `CUDA out of memory` on local video gen | Model too large for VRAM | For SVD: use `svd.safetensors` (14-frame), NOT `svd_xt`; lower resolution to 432×768 |
| `claude plugin install` says "plugin not found" | Marketplace name vs plugin name mismatch | `cat .claude-plugin/{plugin,marketplace}.json \| grep name` |
| MCP tools don't appear in a new session | Plugin disabled / MCP server crashed | `claude plugin list` (check status); `claude plugin update video-producer`; restart session |
| Remotion render crashes with font errors | `remotion-composer/node_modules` corrupt | `cd remotion-composer && rm -rf node_modules && npm install` |

## Uninstall

```bash
claude plugin uninstall video-producer@video-producer
# or remove the whole marketplace:
claude plugin marketplace remove video-producer
```

## Updating after local edits

```bash
claude plugin marketplace update video-producer
claude plugin update video-producer
```

Restart the Claude Code session so the MCP server re-launches with the
new code.

## Cost reference

| Path | Per-video cost |
|---|---|
| Local-GPU only (ComfyUI) | **$0.00** — just wall-time on your hardware |
| Cloud premium (Runway + ElevenLabs + music gen) | $0.50-$3.00 depending on length + clip count |
| Hybrid (local keyframes + cloud hero shots) | $0.10-$0.50 |

Track actual costs via `tools/cost_tracker.py` — each pipeline records
itemized spend in `projects/<id>/artifacts/cost_log.json`.
