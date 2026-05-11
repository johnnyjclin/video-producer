# Compose Director — social-short-15s

## When To Use

`asset_manifest` is complete (or partial — see degraded path). Stitch
the 5 clips, burn text overlays, mix audio, render the final 15s mp4.

This pipeline collapses the usual `edit` + `compose` stages — at 15
seconds with a fixed 5×3s structure, the edit decisions are largely
determined by the scene plan. Don't introduce a separate edit stage.

## Output

`render_report`:

```yaml
project: <project_id>
output_path: projects/<project>/renders/final.mp4
duration_seconds: 15.0
resolution: {width: 1080, height: 1920}
render_runtime: remotion | ffmpeg
encoding: h264, yuv420p, crf 19
verification:
  ffprobe_duration: 15.02
  ffprobe_resolution: "1080x1920"
  ffprobe_audio_present: true | false
decision_log:
  - category: render_runtime_selection
    chosen: remotion
    rationale: "Text overlays + word-level captions"
    rejected:
      - hyperframes: "not required for this short structure"
      - ffmpeg: "no native text-overlay engine for kinetic captions"
```

## Process

### 1. Lock the render runtime (HARD RULE)

Per AGENT_GUIDE.md "Present Both Composition Runtimes": if both Remotion
and HyperFrames are available, surface the choice before locking runtime.
For social-short-15s this should normally be done at brief approval; if
it was skipped, stop in this stage and ask before rendering. For this pipeline:

| Runtime | Best for | Why for this pipeline |
|---|---|---|
| **Remotion** (recommended) | Hook + CTA text overlays, word-level caption burn, spring animations on text | Text is the deliverable's whole personality on social shorts |
| **HyperFrames** | Kinetic typography, GSAP-driven motion, brand-heavy launch reels | Overkill for a 15s talking-head/product short |
| **FFmpeg** | Raw concat with no text | Acceptable only if the short has zero on-screen text |

Default recommendation: **Remotion**. Ensure approval exists, and log the
decision in `render_report.decision_log` with `render_runtime_selection`.

### 2. Build the timeline (motion sandwich pattern)

Each shot in `asset_manifest.video[]` carries four duration fields from
asset-director:

| Field | Meaning |
|---|---|
| `target_seconds` | Total display duration of this shot |
| `static_pad_intro_s` | Hold high-res keyframe before motion starts |
| `motion_seconds` | SVD motion clip plays (always 2.0s) |
| `static_pad_outro_s` | Hold last frame of motion after motion ends |

Build each shot as: **`[keyframe held for intro_s]` → `[2s SVD motion,
upscaled to keyframe resolution]` → `[final motion frame held for outro_s]`**.

For a 5×3.0s default layout:

```
shot 1 (0:00.0 - 0:03.0):
  0:00.0-00.3  static keyframe held       (intro_s=0.3)
  0:00.3-02.3  SVD motion plays           (motion_seconds=2.0)
  0:02.3-03.0  final motion frame held    (outro_s=0.7)
  overlay:     hook on-screen text — fade in by 0:00.4, hold to 0:02.8

shot 2 (0:03.0 - 0:06.0): same sandwich, mid_1 overlay
shot 3 (0:06.0 - 0:09.0): same sandwich, mid_2 overlay
shot 4 (0:09.0 - 0:12.0): same sandwich, mid_3 overlay
shot 5 (0:12.0 - 0:15.0):
  0:12.0-12.5  static keyframe held       (intro_s=0.5)
  0:12.5-14.5  SVD motion plays           (motion_seconds=2.0)
  0:14.5-15.0  final motion frame held    (outro_s=0.5)
  overlay:     CTA — visible 0:12.0 through 0:15.0 (full shot)
```

**Why the sandwich**: viewers read the brief static beats as deliberate
pacing — a moment to absorb the previous shot, a moment to land the
text overlay. Constant motion looks frantic and uncontrolled (it's also
what flags AI-generated shorts the moment a viewer is paying attention).
The sandwich is what well-edited human-shot social content does too.

**Implementation in Remotion**:
- `<Img>` for the keyframe held intro/outro
- `<Video>` for the SVD motion clip in the middle
- `<Sequence from=..., durationInFrames=...>` to schedule each segment

**Implementation in FFmpeg fallback** (no text overlay):
- Use `tpad` filter for static padding: `tpad=start_duration=0.3:start_mode=clone`
- Concat motion + padded segments with `concat` filter
- Note: text overlays are awkward in FFmpeg. If overlays are required,
  insist on Remotion runtime.

**Static-only shots** (when scene_plan sets `video_workflow: null`):
- Just hold the keyframe for the full `target_seconds`
- No SVD generation happened for this shot — `motion_path` is null
- Useful for: text-heavy CTA, brand frames, transitions

### 3. Audio mix (only if narration was generated)

Layer order, top to bottom (loudest to quietest):

| Track | Level | Notes |
|---|---|---|
| Narration | -1 dB | Drives intelligibility |
| Sound effects | -8 dB | Optional — none ship by default |
| Music | -16 dB while narration plays, -8 dB during gaps | Sidechain duck if `audio_mixer` supports it |

If no narration: music can sit at -3 dB (it's the only audio).

If no music either: silent video. That's fine for some platforms, but
flag it in `render_report.verification.ffprobe_audio_present: false` so
the host agent knows to disclaim.

### 4. Caption burn (Remotion only)

If narration exists, generate word-level captions via `subtitle_gen` and
burn them on the bottom-third of the frame. For 9:16 social shorts:

- Caption Y position: 70% from top (above the typical UI overlay zone)
- Font: bold, sans-serif, white with black stroke, 6% of frame height
- Word-level highlight: pop the active word in brand color (or yellow)

If no narration: skip caption burn entirely. The on-screen-text overlays
already do the talking.

### 5. Aspect ratio guard

Every shot's keyframe was generated for the brief's aspect ratio, but
double-check at compose time:

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
  projects/<project>/assets/video/shot_01.mp4
```

If any shot's rendered width:height ratio differs from `brief.aspect_ratio`
(for example `1080x1920` => `9:16`), that's a bug upstream — surface it,
don't crop silently. Compare aspect ratios, not literal pixel strings.

### 6. Render

```python
result = video_compose.execute({
    "render_runtime": render_runtime,        # locked above
    "edit_decisions": <built timeline>,
    "output_path": f"projects/{project}/renders/final.mp4",
    "encoding": {"codec": "h264", "pix_fmt": "yuv420p", "crf": 19},
})
```

`video_compose` routes to the matching engine. If the locked runtime
becomes unavailable at compose time (e.g. Node not in PATH), surface a
blocker — do not silently swap to FFmpeg per AGENT_GUIDE.md
"Critical Rule: Motion-Required Requests".

### 7. Verify the render

After successful render:

```bash
ffprobe -v error -show_entries format=duration:stream=width,height,codec_name \
  projects/<project>/renders/final.mp4
```

Sanity checks:

- duration: 14.7 ≤ d ≤ 15.3 (allow ±0.3s drift from concat)
- rendered aspect ratio matches brief.aspect_ratio
- video codec is h264, audio codec is aac (or absent)

If any check fails, mark `render_report.success: false` and report.

## Review

`human_approval_default: true` — present the render summary and wait for
approval before treating compose as complete. Present a
single-block summary at the end of the pipeline:

```
✓ social-short-15s render complete
  Output: projects/<project>/renders/final.mp4
  Duration: 15.02s • 1080×1920 • h264 (~3.4 MB)
  Runtime: Remotion (text overlays + captions)
  Audio:   narration + library music

  Total wall-time: 8m 42s on RTX 4060 8GB
  All assets local — no API calls made.

Ready to upload via the host 小編 agent.
```

## Anti-patterns

- Don't re-edit shots at this stage — if a shot is wrong, send back to
  asset-director, don't paper over with crops/cuts here
- Don't add transitions between shots unless the playbook calls for them
  — hard cuts are correct for 3-second pacing
- Don't change render_runtime mid-render — surface a blocker if locked
  runtime becomes unavailable
- Don't upload — that's the host 小編 agent's job, not this pipeline's
