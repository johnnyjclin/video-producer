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

## Register with Claude Code (local install)

Claude Code does **not** have a `/plugin add <path>` command. Local installs
go through a self-hosted **marketplace** — the plugin directory declares
itself as a marketplace, you register it once, then install the plugin from
that marketplace. After install the plugin is available globally (user
scope) so every Claude Code session in every project sees it.

### Step 1 — validate the manifest (optional, recommended)

```bash
claude plugin validate /absolute/path/to/video-producer
```

Expect `✔ Validation passed` for both the plugin manifest and the
marketplace manifest.

### Step 2 — register the self-marketplace

```bash
claude plugin marketplace add /absolute/path/to/video-producer
```

This reads `.claude-plugin/marketplace.json` from the folder and registers
the marketplace **under the name declared inside that file** (currently
`video-producer`). Claude Code adds it to user settings; no re-run needed
per project.

Verify:
```bash
claude plugin marketplace list
# → video-producer   /abs/path/to/video-producer   (local)
```

### Step 3 — install the plugin from the marketplace

```bash
claude plugin install noirsboxes-video-producer@video-producer
```

The `@video-producer` suffix names the marketplace added in Step 2.
Output:
```
Installing plugin "noirsboxes-video-producer@video-producer"...
✔ Successfully installed plugin: noirsboxes-video-producer@video-producer (scope: user)
```

Verify:
```bash
claude plugin list
# → noirsboxes-video-producer@video-producer    Version: 0.1.0    Scope: user    Status: ✔ enabled
```

### What just got registered

Claude Code reads `.claude-plugin/plugin.json` and auto-loads:
- the **skill** (`.agents/skills/noirsboxes-shorts`) — visible via `/noirsboxes-shorts`
- the **sub-agent** (`agents/video-production-agent.md`) — invokable via the `Task` tool as `subagent_type="video-production-agent"`
- the **MCP server** (`mcp/server.py`) — its 7 tools appear with the `mcp__noirsboxes-video-producer__` prefix

### Plugin lifecycle commands

| Command | What it does |
|---|---|
| `claude plugin list` | Show all installed plugins, versions, scope, enabled state |
| `claude plugin disable noirsboxes-video-producer` | Temporarily disable without uninstalling (keeps settings) |
| `claude plugin enable noirsboxes-video-producer` | Re-enable a disabled plugin |
| `claude plugin uninstall noirsboxes-video-producer@video-producer` | Uninstall (leaves the files on disk) |
| `claude plugin update noirsboxes-video-producer` | Pull newest version from the marketplace — run after editing files in the plugin folder |
| `claude plugin marketplace list` | See all registered marketplaces |
| `claude plugin marketplace update video-producer` | Refresh the local marketplace after editing `marketplace.json` |
| `claude plugin marketplace remove video-producer` | Remove the whole marketplace (uninstalls every plugin from it) |

### Session-only install (no persistence)

If you want to try the plugin in a single session without registering it
globally, launch Claude Code with `--plugin-dir`:

```bash
claude --plugin-dir /absolute/path/to/video-producer
```

The plugin is loaded for that session only and disappears when you exit.
Useful for testing a plugin you haven't committed yet.

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
| `claude plugin validate` reports unrecognized keys | `plugin.json` has non-spec fields (`$schema`, `requirements`, `install`) | Remove those keys — only `name`, `version`, `description`, `author`, `license`, `keywords`, `skills`, `agents`, `mcpServers` are recognized |
| `claude plugin marketplace add <path>` errors "manifest not found" | Folder has no `.claude-plugin/marketplace.json` | Add the marketplace file (see `.claude-plugin/marketplace.json` for the schema) |
| `claude plugin install <name>@<marketplace>` says "plugin not found" | The `<name>` in the install command must match `plugins[].name` in marketplace.json, and `<marketplace>` must match the marketplace's top-level `name` | Check both files: `cat .claude-plugin/plugin.json .claude-plugin/marketplace.json \| grep '"name"'` |
| `/plugin add <path>` is rejected as unknown command | No such command exists in Claude Code | Use the `marketplace add` → `plugin install` flow described above |
| Plugin size exceeds 100 MB | Folder contains `node_modules/`, `projects/`, `.git/`, or similar bulk | Add them to `.claudeignore` (already done in this repo — see `.claudeignore`) |
| MCP server fails to start | Python version / missing deps | Re-run `bash install.sh`; verify `python >=3.11` and `pip install mcp` |
| `produce_noirsboxes_short` returns `blocker: Brand folder not found` | Missing SKU photos | Drop the three required photos per "What counts as a new SKU?" above |
| Runway T2V returns 400/403 on all models | Account plan doesn't include gen4.5 | Ask Runway support to enable gen4.5 or seedance2 on the API key |
| ElevenLabs returns 429 on multiple TTS calls | Burst rate-limit | The high-level tool already retries sequentially; if still failing, reduce `max_workers` in `server.py` |
| Remotion render crashes with font errors | `remotion-composer/node_modules` corrupt | `cd remotion-composer && rm -rf node_modules && npm install` |
| MCP tools don't appear in a new session | Plugin is `disabled`, MCP server crashed on boot, or cache stale | `claude plugin list` (check status) → `claude plugin update noirsboxes-video-producer` → restart the session |

## Uninstall

```bash
claude plugin uninstall noirsboxes-video-producer@video-producer
# or remove the marketplace entirely (uninstalls all plugins in it):
claude plugin marketplace remove video-producer
```

The plugin source code stays on disk — delete the folder manually if you want it gone.

## Updating the plugin after local edits

When you edit files inside this folder (e.g. tweak the subagent prompt, add
a new MCP tool, update the skill), Claude Code **caches** the previous
version. To pick up your changes:

```bash
# 1. Refresh the marketplace's view of the plugin folder
claude plugin marketplace update video-producer

# 2. Pull the new plugin version into each install
claude plugin update noirsboxes-video-producer
```

Restart the Claude Code session (exit and re-open) so the MCP server
re-launches with the new `mcp/server.py`.

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
