---
name: comfyui
description: How to drive the local ComfyUI bridge (comfyui_image, comfyui_video) — workflow selection, model-specific prompting, 8GB VRAM parameter ranges, and multi-shot consistency for social shorts.
metadata:
  version: "1.0.0"
  tags: comfyui, local-gpu, flux, sdxl, svd, image-generation, video-generation
---

# ComfyUI Bridge

Use this skill before calling `comfyui_image` or `comfyui_video`. Those
tools route to a local ComfyUI server — they don't make creative
decisions. This skill is where the creative decisions live.

## When this skill applies

- Any call to `comfyui_image` or `comfyui_video`
- Any time the user wants offline / no-API-key / privacy-sensitive generation
- Any time cost matters (cloud video at scale is expensive; ComfyUI is free per call)

If the user has cloud providers (fal, runway) configured AND quality is
the top priority, prefer those — they outrun any 8GB-class local model on
absolute fidelity. ComfyUI wins on cost, latency-once-warm, and privacy.

### Cross-pipeline applicability

The ComfyUI bridge isn't tied to one pipeline. It's available wherever
`image_selector` / `video_selector` route — which is every pipeline that
generates visuals:

| Pipeline | Where ComfyUI fits |
|---|---|
| `social-short-15s` | **Default path.** All 5 shots local; cloud only as fallback. |
| `animated-explainer` | Scene `assets` stage — substitute FLUX schnell GGUF for FLUX-pro cloud calls; substitute SVD for cloud video gen on short reveal shots. |
| `animation` | Pair `comfyui_image` with the Remotion/HyperFrames runtime — generate stills locally, animate via composition engine. |
| `clip-factory`, `podcast-repurpose` | Use `comfyui_image` for thumbnail / cover frame generation between extracted clips. |
| `hybrid` | Generate B-roll keyframes locally; layer over real footage in compose. |
| `cinematic` | ComfyUI can produce keyframes for atmosphere shots; cloud video providers still better for hero motion. |
| `talking-head`, `avatar-spokesperson`, `localization-dub` | Mostly footage-led — ComfyUI rarely needed except for opening/closing card visuals. |
| `screen-demo`, `documentary-montage` | Footage-led; skip ComfyUI unless adding generated B-roll. |

Pipelines that route via the selectors get ComfyUI "for free" — no
pipeline-specific wiring. Just make sure the ComfyUI server is reachable
at preflight; the selectors will pick it up.

## Workflow selection (THE most consequential decision)

The bridge ships three templates. Pick by use case:

| Workflow | When | Speed | Quality | VRAM |
|---|---|---|---|---|
| `sdxl_lightning` | Bulk keyframes, fast iteration, batch of 5 shots | 8-15s | Good | ~6GB |
| `flux_schnell_gguf` | Hero shot, brand cover, anything where the image *is* the deliverable | 25-40s | Best at 8GB | ~7GB |
| `svd_image_to_video` | Animate a keyframe into a 2-3s clip | 60-120s | Subtle motion only | ~8GB |

**Heuristic for the social-short-15s pipeline:**
- Hook frame + CTA frame → `flux_schnell_gguf` (these are the "first impression" frames)
- Middle 3 shots → `sdxl_lightning` (volume + iteration)
- All 5 keyframes → `svd_image_to_video` to animate

Don't mix FLUX and SDXL outputs in the same short unless the brief explicitly
calls for stylistic variation — they have visibly different looks.

## Prompting per model

These models read prompts very differently. Using the wrong style is the
single biggest cause of bad output.

### FLUX (schnell, dev)

**Natural language. Full sentences. No tag soup.**

Good:
```
A weary night-market vendor in Taipei, mid-50s, looking up from
his steaming cart of beef noodle soup. Soft tungsten light from
the stall, neon reflections on wet pavement, shallow depth of
field, 35mm cinematic.
```

Bad (this is SDXL-style, FLUX will partially ignore it):
```
night market vendor, taipei, 50yo man, beef noodle, neon, bokeh,
cinematic, 35mm, masterpiece, best quality, 8k, ultrarealistic
```

FLUX-schnell quirks:
- Distilled for `cfg=1.0` and 4 steps. Don't raise either — the slot
  patcher will let you, but quality degrades.
- **Negative prompt is a no-op on schnell.** Don't waste tokens on it.
- Renders text well. If the brief includes signage/captions inside the
  image, FLUX is the right pick (SDXL mangles text).

### SDXL Lightning

**Tag-style prompts. Comma-separated. Quality terms help.**

Good:
```
night market food vendor, asian man 50s, beef noodle stall, steam
rising, neon signs reflected on wet street, tungsten warm light,
shallow depth of field, 35mm, cinematic, photorealistic, sharp
focus, professional photography
```

Negative prompt does work — use it to fight common SDXL failure modes:
```
blurry, lowres, watermark, text, signature, bad anatomy, extra
fingers, deformed face, plastic skin, oversaturated
```

Steps=4, cfg=1.5, sampler=dpmpp_sde, scheduler=karras. The slots default
to these. Don't change unless you know why.

### SVD (image-to-video)

**SVD ignores text prompts.** It's purely image-conditioned. The
`prompt` slot exists for record-keeping; the model never sees it.

The two parameters that actually matter:
- `motion_bucket_id` (1-255): camera/subject motion intensity
  - 60-100: subtle hair/cloth movement, slow drift — best for portraits, food shots
  - 110-140: balanced — default for most shots, light camera push
  - 150-200: dramatic — action, environments, time-of-day shifts
  - >200: rarely good. Often produces warping artifacts.
- `augmentation_level` (0.0-1.0): how much SVD allowed to deviate from input
  - 0.0 (default): faithful to input frame — what you usually want
  - 0.1-0.2: more motion freedom, slight loss of subject fidelity
  - >0.3: subject morphing, often unusable

`fps=7` + `video_frames=14` = 2-second clip. That's the 8GB sweet spot.
Stretching to 25 frames (svd_xt territory) needs ≥10GB.

## 8GB VRAM parameter envelope (safe defaults)

| Workflow | Resolution sweet spot | Don't exceed |
|---|---|---|
| `sdxl_lightning` | 1024×1024 or 768×1280 | 1280×1280 |
| `flux_schnell_gguf` | 1024×1024 or 768×1024 | 1280×1024 |
| `svd_image_to_video` | 768×432 (16:9) or 576×1024 (9:16) | 1024×576 |

Going beyond these on a 4060 8GB → OOM or 30s+ per step. The bridge
won't catch this; the symptom shows up as a `comfyui execution failed`
error in the ToolResult.

## Multi-shot consistency (the social-short-15s killer feature)

Five separate generations of "a young woman holding a coffee" will give
you five different women. For a coherent 15-second short, three options:

### Option 1: Same seed + locked subject prompt prefix (cheapest)

Pin a `subject_prefix` in your scene_plan and reuse it verbatim across
shots. Keep `seed` constant for the keyframes, vary it only for clips.

```
subject_prefix: "a 28-year-old Taiwanese barista, short black bob,
white linen apron, warm brown eyes"
```

Then per shot: `<subject_prefix>, <shot-specific action and setting>`.

Works ~70% of the time on FLUX, ~50% on SDXL. Cheapest possible solution.

### Option 2: IPAdapter from shot-1 keyframe (recommended)

Generate shot-1 keyframe normally. Use it as IPAdapter style+face reference
for shots 2-5. Requires:
- `ComfyUI_IPAdapter_plus` custom node installed
- A new workflow template (e.g. `sdxl_lightning_ipadapter.json`) — not shipped by default

This is the standard ComfyUI consistency play. If the user is doing
multiple shorts of the same brand/character, build this template once.

### Option 3: Train a LoRA (premium)

For sustained brand/character work — train a 1-shot LoRA with ~10
reference images. Reuse forever. Outside this skill's scope but worth
knowing exists.

**Default**: start with Option 1. Only escalate to Option 2 when shot-1
quality is high and the user complains about consistency.

## Troubleshooting decision tree

`status=unavailable` even though ComfyUI is running:
- Check `COMFYUI_HOST` / `COMFYUI_PORT` env vars match where ComfyUI is bound
- ComfyUI started with `--listen 0.0.0.0` but bridge defaults to `127.0.0.1`? Match them.

`comfyui execution failed: prompt outputs failed validation`:
- The workflow references a node class that isn't installed. Read the
  template's `_meta.required_custom_nodes` and verify each one is in
  `ComfyUI/custom_nodes/`.
- Or a model file is missing. Check `_meta.required_models` for paths.

`OOM` / `CUDA out of memory`:
- Lower resolution first (drop to 768x768 for images, 576x320 for SVD)
- Then drop `video_frames` for SVD (try 8-10 instead of 14)
- For FLUX: ensure `t5xxl_fp8_e4m3fn.safetensors` is the FP8 (not FP16) version
- As a last resort: `--cpu-vae` flag on ComfyUI server start

Output looks dull / overexposed (FLUX):
- FLUX schnell at cfg=1.0 sometimes washes out. Move to `flux_dev_gguf` if
  you have ≥10GB VRAM (not provided as default template).

Output has visible repeating tiling:
- VAE tiled decode artifact. Reduce resolution; ComfyUI auto-tiles VAE
  decode at high res on low-VRAM GPUs.

SVD output is barely moving:
- Bump `motion_bucket_id` from 127 to 160-180.

SVD output is morphing / warping faces:
- Drop `motion_bucket_id` to 80-100.
- Or set `augmentation_level=0.0` if it isn't already.

## What this skill doesn't cover

- Custom workflow design (use ComfyUI GUI then "Save (API Format)")
- LoRA training pipelines
- Real-time / streaming generation
- AnimateDiff workflows (would need new template)
- Wan 2.1 / LTX local t2v (existing tools `wan_video` and `ltx_video_local`
  handle these directly via diffusers — don't go through ComfyUI for them)
