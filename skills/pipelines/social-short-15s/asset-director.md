# Asset Director — social-short-15s

## When To Use

`scene_plan` approved. Generate 5 keyframes + 5 motion clips and
optionally narration audio + background music.

**Read `.agents/skills/comfyui/SKILL.md` first.** Workflow choice,
prompt formatting, and parameter ranges live there.

## Output

`asset_manifest`:

```yaml
project: <project_id>
images:
  - shot_id: 1
    path: projects/<project>/assets/images/shot_01.png
    workflow: flux_schnell_gguf
    seed: 42
    prompt_used: "<full prompt>"
video:
  - shot_id: 1
    path: projects/<project>/assets/video/shot_01.mp4
    keyframe: projects/<project>/assets/images/shot_01.png
    workflow: svd_image_to_video
    motion_bucket_id: 90
    seed: 42
audio:
  narration:
    - section: hook
      path: projects/<project>/assets/audio/hook.mp3
    ...
  music:
    path: projects/<project>/assets/music/bgm.mp3
    source: library | generated | none
```

## Process

### 1. Preflight check

Confirm before any generation:

- `comfyui_image.get_status() == AVAILABLE` (ComfyUI server reachable)
- `comfyui_video.get_status() == AVAILABLE`
- Required custom nodes installed for each workflow in the plan
- Required model files present in `ComfyUI/models/`

If any of these fail, **stop and surface the blocker** per AGENT_GUIDE.md
"Escalate Blockers Explicitly". Don't silently fall back to cloud
providers — the user picked this pipeline specifically for local. Ask
before substituting.

### 2. Generate keyframes (5 shots)

For each shot in `scene_plan.shots`:

```python
result = comfyui_image.execute({
    "workflow": shot.image_workflow,
    "prompt": shot.image_prompt,
    "negative_prompt": "blurry, lowres, watermark, bad anatomy" if shot.image_workflow == "sdxl_lightning" else None,
    "width": shot.image_size.width,
    "height": shot.image_size.height,
    "seed": <see consistency strategy below>,
    "output_path": f"projects/{project}/assets/images/shot_{shot.shot_id:02d}.png",
})
```

**Consistency strategy** (default — Option 1 from comfyui skill):

- Use the SAME `seed` for shots 1, 2, 3, 4, 5 if subject is a person/character
- Use VARIED `seed` if shots are environmental / abstract (variety helps)
- Subject prefix is already baked into every prompt by `scene-director`

If after generating shot 1 the subject visibly drifts in shot 2, **stop
the batch** and surface to the user. Don't burn 90s on shots 3-5 only to
discover the same drift. Options:
- Regenerate the offending shot with a different seed
- Tighten the subject_prefix and regenerate the batch
- Escalate to IPAdapter workflow (requires `sdxl_lightning_ipadapter.json`
  template that is not shipped — flag this as a follow-up)

### 3. Generate motion clips (per shot)

For each shot whose `video_workflow` is non-null:

```python
motion_map = {"subtle": 90, "balanced": 127, "dramatic": 175}
result = comfyui_video.execute({
    "operation": "image_to_video",
    "workflow": shot.video_workflow,
    "reference_image_path": image_path_for_shot,
    "video_frames": 14,                   # ALWAYS 14 — see "Why fixed" below
    "motion_bucket_id": motion_map[shot.video_motion],
    "fps": 7,                             # ALWAYS 7
    "augmentation_level": 0.0,
    "seed": shot_seed,
    "output_path": f"projects/{project}/assets/video/shot_{shot.shot_id:02d}_motion.mp4",
    "timeout_s": 600,
})
```

**Why `video_frames=14` is fixed (do NOT increase):**
- 14 frames is what `svd.safetensors` was trained on — going higher
  trades quality for runtime
- 14 × 1/7 = 2.0s of motion — matches scene-director's `motion_seconds`
- 21+ frames at 432×768 may OOM on 8GB
- For longer total shots, scene-director uses static padding, not more
  frames (see scene-director's "motion sandwich" pattern)

If the shot has `video_workflow: null` (static-only shot):
- Skip SVD entirely
- Output is just the keyframe duplicated for `target_seconds` — done by
  compose-director using FFmpeg, not here

### 4. Resize keyframe for SVD if needed

`scene_plan` lists keyframe size (e.g., 768×1344) and SVD size
(432×768). Before calling SVD, resize the keyframe down using PIL:

```python
from PIL import Image
img = Image.open(keyframe_path)
img.thumbnail((shot.svd_input_size.width, shot.svd_input_size.height), Image.LANCZOS)
svd_input_path = keyframe_path.replace(".png", "_svd_input.png")
img.save(svd_input_path)
```

Pass `svd_input_path` to `comfyui_video.execute()` as
`reference_image_path`. Keep the original high-res keyframe — it's still
needed for static padding at compose stage.

Record both paths in the asset_manifest:

```yaml
images:
  - shot_id: 1
    keyframe_path: projects/<project>/assets/images/shot_01.png       # high-res
    svd_input_path: projects/<project>/assets/images/shot_01_svd.png  # downsized
video:
  - shot_id: 1
    motion_path: projects/<project>/assets/video/shot_01_motion.mp4   # 2s @ 432x768
    keyframe_ref: projects/<project>/assets/images/shot_01.png        # for static padding
    motion_seconds: 2.0
    static_pad_intro_s: 0.3
    static_pad_outro_s: 0.7
    target_seconds: 3.0
```

compose-director needs all four fields per shot to build the sandwich.

### 4. Generate narration (only if TTS configured)

Check preflight: is any `tts_*` provider AVAILABLE? If yes, route via
`tts_selector` per script section. One audio file per section.

If no TTS available, set `audio.narration: null` and proceed. The short
will run silent — `compose-director` will rely on on-screen text.

Don't ask the user to set up TTS mid-pipeline. The choice was already
made at preflight; honor it.

### 5. Pick / generate background music

Per AGENT_GUIDE.md "Music Plan (Mandatory)":

1. Check `music_library/` for existing tracks. If non-empty, surface to
   user as the default.
2. If `music_gen` is AVAILABLE, offer it as alternative.
3. If neither, accept "no music" — set `audio.music: null`.

This decision was already locked in `brief` if the idea-director did
their job. Just execute.

### 6. Wall-time budget

Target on RTX 4060 8GB:

| Asset | Per-shot time | 5-shot total |
|---|---|---|
| FLUX-schnell keyframe | ~30s | up to 2.5 min |
| SDXL-Lightning keyframe | ~12s | up to 1 min |
| SVD 14-frame clip | ~90s | 7.5 min |
| TTS (3s segment) | ~3s | 15s |
| Music (15s gen) | ~30s | 30s |

Total budget: **~10 minutes wall-time**. If you exceed 15 minutes, stop
and report — likely a model is offloading badly or a generation hung.

### 7. Sequential vs parallel

ComfyUI server runs ONE job at a time. Submitting 5 keyframe jobs in
parallel is fine — they queue. But don't try to run keyframes and SVD
concurrently if the SVD reference depends on the keyframe — that's a
data dependency.

Recommended order:

```
keyframes 1-5 (parallel queue)
   ↓
SVD clips 1-5 (sequential — each needs its keyframe)
   ↓
narration (parallel via TTS provider)
   ↓
music (single job)
```

## Review

`human_approval_default: false` — auto-proceed unless something failed.

Surface to the user only when:
- A keyframe regeneration loop hit max revisions (3)
- Subject consistency drift detected
- A required tool went UNAVAILABLE mid-stage
- Wall-time exceeded budget

## Anti-patterns

- Don't generate all 10 jobs (5 image + 5 video) before reviewing
  shot 1's keyframe — fail fast
- Don't override `subject_prefix` per shot — that's by design
- Don't switch workflows mid-batch — if FLUX fails on shot 3, regenerate
  shot 3, don't drop the rest of the batch to SDXL
- Don't write to ad-hoc paths — strictly under `projects/<project>/assets/`
