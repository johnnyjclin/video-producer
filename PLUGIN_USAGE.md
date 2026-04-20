# Using `noirsboxes-video-producer` as a Claude Code plugin

This project ships as a reusable Claude Code plugin so your **main agent
project** can delegate NoirsBoxes (Black Magic) MD-xxx showcase video
production to it without ever touching the underlying Python / Node / Runway
plumbing.

## What you get after install

| Surface | Name | Use it when… |
|---|---|---|
| **Sub-agent** | `video-production-agent` | Parent agent wants a hands-off "make me the video" delegation with a clean JSON return |
| **MCP tool (high-level)** | `mcp__noirsboxes-video-producer__produce_noirsboxes_short(sku, ...)` | One-shot full-pipeline call. 15–20 min, ~$2. |
| **MCP tools (low-level)** | `runway_image_to_video`, `runway_text_to_video_gen45`, `elevenlabs_tts`, `elevenlabs_music`, `remotion_render`, `measure_audio_duration` | Custom orchestration, retake a single clip, mix languages |
| **Skill** | `noirsboxes-shorts` | Reference knowledge for the whole pipeline; auto-loads when the parent mentions NoirsBoxes |

## Install (one-time)

```bash
# 1. Clone or download this repo to any location on your machine.
git clone https://github.com/<user>/video-producer.git
cd video-producer

# 2. One-shot dependency installer (Python + Node + .env scaffold).
bash install.sh

# 3. Fill in .env with your real API keys:
#      RUNWAY_API_KEY      (required)
#      ELEVENLABS_API_KEY  (required)
#      FAL_KEY             (optional — only needed if you want FAL-backed tools)

# 4. Drop product photos (if you haven't already) under:
#    assets/brand/norisboxes/product-image/MD-XXX/
#      MD-XXX-blank-holding.jpg              # hand holding, blank screen
#      MD-XXX-cable-inferior-89scores.jpg    # hand holding, "Inferior 89" screen
#      MD-XXX-cable-original-100scores.jpg   # hand holding, "Original 100" screen
#      MD-XXX-blank.jpg                      # studio shot (used in outro)
```

## Register with your main agent project

In a **different** folder (your main Claude Code project):

```bash
cd /path/to/my-main-agent-project
```

In the Claude Code session there, run:

```
/plugin add /absolute/path/to/video-producer
```

Claude Code reads `.claude-plugin/plugin.json`, auto-registers:
- the skill (`.agents/skills/noirsboxes-shorts`)
- the sub-agent (`agents/video-production-agent.md`)
- the MCP server (`mcp/server.py`)

All tools show up with the `mcp__noirsboxes-video-producer__` prefix.

## Invocation patterns

### Pattern 1 — hands-off sub-agent

```
You: please produce a NoirsBoxes MD-907 showcase short for our new SKU launch

Main agent (thinking) → this is a NoirsBoxes video request; delegate to
                        video-production-agent via Task tool

Task(subagent_type="video-production-agent",
     prompt="Produce a 30s 9:16 English showcase for MD-907.
             Tagline: 'The charger that sees through fakes.'
             Features: ['USB-C PD read', 'QC 2.0 detection', 'Offline scoring',
                        'C48 to C94 chips'].
             Output to ./renders/md907-launch.mp4")

video-production-agent (12-18 min later) →
    {"mp4_path": "./renders/md907-launch.mp4",
     "duration_s": 26.5,
     "resolution": "1080x1920",
     "cost_usd_estimated": 2.05,
     "scenes_rendered": 9,
     "notes": "all scenes rendered cleanly"}

Main agent → "done: ./renders/md907-launch.mp4 (26.5s, $2.05)"
```

### Pattern 2 — direct MCP tool call

When the main agent wants more control:

```python
mcp__noirsboxes-video-producer__produce_noirsboxes_short(
    sku="MD-907",
    tagline="The charger that sees through fakes.",
    features=["USB-C PD read", "QC 2.0 detection",
              "Offline scoring", "C48 to C94 chips"],
    language="en",
    output_dir="./renders/",
)
```

### Pattern 3 — custom orchestration (e.g. only retake scene 2)

```python
# Regenerate just the "phone dying" T2V clip with a tighter prompt
mcp__noirsboxes-video-producer__runway_text_to_video_gen45(
    prompt="Extreme close-up of a smartphone screen with pulsing red low-battery "
           "icon on a midnight-blue desk, shallow DOF, cinematic. Vertical 9:16.",
    output_path="./assets/video/tv_phone_dying.mp4",
    duration=5, ratio="9:16",
)

# Then re-render Remotion without re-running the whole pipeline
mcp__noirsboxes-video-producer__remotion_render(
    composition_id="MD905Shorts",
    output_path="./renders/md905-shorts-v4.mp4",
)
```

### Pattern 4 — language variant (German)

```python
# Translate narration lines externally, then call low-level TTS with German voice
for name, text in [("vo_01_hook", "Dieses Kabel sah echt aus."), ...]:
    mcp__noirsboxes-video-producer__elevenlabs_tts(
        text=text,
        output_path=f"./assets/audio-de/{name}.mp3",
        voice_id="pqHfZKP75CvOlQylNhV4",  # Bill (German)
    )

# Re-render with overridden voiceover paths
mcp__noirsboxes-video-producer__remotion_render(
    composition_id="MD905Shorts",
    output_path="./renders/md905-shorts-de.mp4",
    props={"vo1": "./assets/audio-de/vo_01_hook.mp3", ...},
)
```

## What counts as a "new SKU"?

Minimum needed to produce a video for MD-907, MD-910, etc.:

1. Three brand photos under `assets/brand/norisboxes/product-image/MD-XXX/`
   matching the MD-905 filename pattern.
2. That's it. If the SKU uses the same scoring system (inferior N / original 100)
   the default script works as-is with only the SKU number changed.

If the SKU has a different scoring display (e.g. voltage tester with
safe/unsafe instead of 0-100):
- Edit the `SCENE_SECONDS` in `remotion-composer/src/MD905Shorts.tsx`
- Replace the scene 4/6 captions with `Unsafe. 9.1V.` / `Safe. 5.2V.`
- Rerun — the MCP high-level tool also needs a schema patch

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `/plugin add` reports "plugin.json not found" | Plugin root mis-specified | Point to the repo's **root**, not the `.claude-plugin/` folder |
| MCP server fails to start | Python version / missing deps | Re-run `bash install.sh`; verify `python >=3.11` and `mcp` is installed |
| `produce_noirsboxes_short` returns `blocker: Brand folder not found` | Missing SKU photos | Drop the three required photos per "What counts as a new SKU?" above |
| Runway T2V returns 400/403 on all models | Account plan doesn't include gen4.5 | Ask Runway support to enable gen4.5 or seedance2 on the API key |
| ElevenLabs returns 429 on multiple TTS calls | Burst rate-limit | The high-level tool already retries sequentially; if still failing, reduce `max_workers` in `server.py` |
| Remotion render crashes with font errors | `remotion-composer/node_modules` corrupt | `cd remotion-composer && rm -rf node_modules && npm install` |

## Uninstall

```
/plugin remove noirsboxes-video-producer
```

The plugin code stays on disk — delete the folder manually if you want it gone.

## Cost reference

| Action | Typical cost |
|---|---|
| One new 30s MD-xxx short (all 7 clips + TTS + music + render) | ~$2.00 |
| One retake of a single Runway clip (I2V or T2V) | $0.25 |
| One new language variant (TTS-only) | $0.05 |
| One re-render of Remotion (no Runway/TTS changes) | $0.00 |

Keep an eye on the `cost_usd_estimated` field in the high-level tool's return
value. Anything over $4 on a single invocation means retries were out of
control — investigate before batching more.
