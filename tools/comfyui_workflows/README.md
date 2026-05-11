# ComfyUI Workflow Templates

These JSON files drive `tools/graphics/comfyui_image.py` and
`tools/video/comfyui_video.py`. Each is a ComfyUI **API-format** workflow
plus a `_meta` block that names the friendly slots the bridge can patch
(`prompt`, `seed`, `width`, etc.) without knowing the graph internals.

ComfyUI runs **entirely on your local GPU** — `127.0.0.1:8188` is loopback,
no traffic leaves the machine. The only network step is the one-time
weight download from HuggingFace; after that it's fully offline.

## Targets

All three templates are tuned for **RTX 4060 8GB**.

| Template | Use | VRAM | Custom nodes |
|---|---|---|---|
| `sdxl_lightning` | Fast text-to-image, 4 steps | ~6 GB | none |
| `flux_schnell_gguf` | Best-quality text-to-image (8GB-class) | ~7 GB | `ComfyUI-GGUF` |
| `svd_image_to_video` | Image-to-video, 14 frames | ~7-8 GB | `ComfyUI-VideoHelperSuite` |

## One-time setup

```bash
# 1. ComfyUI itself
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI
pip install -r requirements.txt

# 2. ComfyUI-Manager (recommended — gives you a "Manager" button in the UI)
cd custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager
cd ..

# 3. Custom nodes for FLUX + SVD templates
cd custom_nodes
git clone https://github.com/city96/ComfyUI-GGUF
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
cd ..

# 4. Start the server (the bridge connects here)
python main.py --listen 127.0.0.1 --port 8188
```

The bridge defaults to `127.0.0.1:8188`. Override with `COMFYUI_HOST` /
`COMFYUI_PORT` if needed.

## Model downloads

All paths below are relative to your `ComfyUI/` directory. File sizes are
approximate.

### `sdxl_lightning` — minimal (one file)

| File | Path | Source |
|---|---|---|
| `sd_xl_lightning_4step.safetensors` (~6.5 GB) | `models/checkpoints/` | huggingface `ByteDance/SDXL-Lightning` (or any merged SDXL-Lightning checkpoint, e.g. DreamShaper-XL-Lightning) |

### `flux_schnell_gguf` — four files

| File | Path | Source |
|---|---|---|
| `flux1-schnell-Q4_K_S.gguf` (~6.5 GB) | `models/unet/` | `city96/FLUX.1-schnell-gguf` |
| `t5xxl_fp8_e4m3fn.safetensors` (~5 GB) | `models/clip/` | `comfyanonymous/flux_text_encoders` |
| `clip_l.safetensors` (~250 MB) | `models/clip/` | `comfyanonymous/flux_text_encoders` |
| `ae.safetensors` (~340 MB) | `models/vae/` | `black-forest-labs/FLUX.1-schnell` (the `vae/` subfolder; rename `diffusion_pytorch_model.safetensors` → `ae.safetensors`) |

Notes:
- FLUX-schnell is distilled for `cfg=1.0` and 4 steps; the `negative_prompt`
  slot exists for parity with other templates but has no effect on output.
- If you have ≥10 GB VRAM, swap to `Q5_K_S` or `Q6_K` for better quality.
- For ≤6 GB VRAM, swap T5 to a GGUF variant (`t5-v1_1-xxl-encoder-Q5_K_S.gguf`)
  and switch the `DualCLIPLoader` node to `DualCLIPLoaderGGUF` — at that
  point the workflow needs editing, not just a slot patch.

### `svd_image_to_video` — one file (plus a custom node)

| File | Path | Source |
|---|---|---|
| `svd.safetensors` (~9.5 GB) | `models/checkpoints/` | `stabilityai/stable-video-diffusion-img2vid` |

⚠️ **Use the 14-frame `svd.safetensors`, NOT `svd_xt.safetensors`.** XT is
25-frame and needs ≥10 GB VRAM — it will OOM on a 4060.

## Calling the bridge from Python

```python
from tools.tool_registry import registry
registry.discover()

# Image — pick a workflow by name
result = registry.get("comfyui_image").execute({
    "prompt": "a cinematic close-up of a Taipei street vendor at night",
    "workflow": "flux_schnell_gguf",   # or "sdxl_lightning"
    "width": 1024, "height": 1024,
    "seed": 42,
    "output_path": "out.png",
})

# Image-to-video — feed it the keyframe you just made
result = registry.get("comfyui_video").execute({
    "operation": "image_to_video",
    "reference_image_path": "out.png",
    "workflow": "svd_image_to_video",
    "video_frames": 14,
    "motion_bucket_id": 127,
    "fps": 7,
    "seed": 42,
    "output_path": "clip.mp4",
})
```

Or let `image_selector` / `video_selector` pick — they auto-discover any
provider with the right `capability` and pick the highest-priority one
that's `AVAILABLE`. With ComfyUI running and no API keys set, that's the
local route.

## Adding a new template

1. Build the graph in the ComfyUI GUI, then **Save (API Format)** to JSON.
2. Wrap the JSON with a top-level `_meta` block:

   ```json
   {
     "_meta": {
       "name": "my_workflow",
       "kind": "image",
       "description": "...",
       "slots": {
         "prompt":         ["<node_id>.text"],
         "seed":           ["<node_id>.seed"],
         "width":          ["<node_id>.width"],
         "height":         ["<node_id>.height"],
         "filename_prefix":["<node_id>.filename_prefix"]
       },
       "output_node": "<node_id of SaveImage / VHS_VideoCombine>",
       "required_custom_nodes": [],
       "required_models": []
     },
     "<node_id>": { "class_type": "...", "inputs": { ... } }
   }
   ```

3. Drop it into this directory. No code changes — `provider_matrix` and
   `image_selector` / `video_selector` pick it up automatically on the next
   `registry.discover()`.

A slot value can patch multiple nodes (e.g. SVD's `fps` writes both
`5.fps` and `9.frame_rate`). List multiple targets in the slot's array.

## Quick health check

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

If `status` shows `unavailable`, ComfyUI isn't reachable on the configured
host/port. If `status` is `available` but a generation fails with
"prompt outputs failed validation", the workflow likely references a
custom node or model file that isn't installed yet — check the template's
`required_custom_nodes` and `required_models` sections.
