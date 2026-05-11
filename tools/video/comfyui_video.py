"""Local video generation via a running ComfyUI server.

Drives any workflow template under `tools/comfyui_workflows/` whose
`_meta.kind == "video"`. The default template is `svd_image_to_video` —
Stable Video Diffusion 14-frame at 768x432, sized for an RTX 4060 8GB.

Replaces the cloud video providers (fal.ai Seedance, Runway, Kling) for
the common "still keyframe → 2-3s motion clip" use case in social shorts.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)
from tools._comfyui import (
    ComfyUIClient,
    ComfyUIError,
    apply_slots,
    list_templates,
    load_template,
)


class ComfyUIVideo(BaseTool):
    name = "comfyui_video"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "comfyui"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.SEEDED
    runtime = ToolRuntime.LOCAL_GPU

    dependencies = ["python:requests"]
    install_instructions = (
        "Run a ComfyUI server locally and install the VideoHelperSuite custom node:\n"
        "  python main.py --listen 127.0.0.1 --port 8188\n"
        "  cd ComfyUI/custom_nodes && \\\n"
        "    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite\n"
        "Drop the SVD checkpoint into ComfyUI/models/checkpoints/ (svd.safetensors\n"
        "for 8GB GPUs; svd_xt.safetensors needs ≥10GB). Override host/port via\n"
        "COMFYUI_HOST / COMFYUI_PORT."
    )
    fallback = "wan_video"
    fallback_tools = ["wan_video", "ltx_video_local", "image_selector"]
    agent_skills = ["comfyui", "ai-video-gen", "ltx2"]

    capabilities = ["image_to_video"]
    supports = {
        "image_to_video": True,
        "reference_image": True,
        "offline": True,
        "native_audio": False,
        "local_gpu": True,
        "custom_workflows": True,
    }
    best_for = [
        "free image-to-video on consumer GPUs (RTX 4060 8GB target)",
        "the keyframe→short-clip step in social-short pipelines",
        "offline / privacy-sensitive workflows that can't ship to fal.ai or Runway",
    ]
    not_good_for = [
        "long clips (>4s) — use cloud providers for those",
        "text-to-video without a reference image (no t2v template ships by default)",
        "machines without a running ComfyUI server",
    ]

    input_schema = {
        "type": "object",
        "required": ["operation"],
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["image_to_video", "text_to_video"],
                "default": "image_to_video",
            },
            "prompt": {
                "type": "string",
                "description": "Optional motion-direction prompt; SVD itself is image-conditioned and ignores text.",
            },
            "reference_image_path": {"type": "string"},
            "video_frames": {"type": "integer"},
            "motion_bucket_id": {
                "type": "integer",
                "description": "SVD motion intensity (1-255). 127 = default, lower = subtler, higher = more motion.",
            },
            "fps": {"type": "integer"},
            "augmentation_level": {"type": "number"},
            "width": {"type": "integer"},
            "height": {"type": "integer"},
            "seed": {"type": "integer"},
            "steps": {"type": "integer"},
            "cfg": {"type": "number"},
            "model_name": {"type": "string"},
            "workflow": {
                "type": "string",
                "description": "Template short-name under tools/comfyui_workflows/, or absolute path.",
                "default": "svd_image_to_video",
            },
            "output_path": {"type": "string"},
            "timeout_s": {"type": "number", "default": 600.0},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=2000, vram_mb=8000, disk_mb=300, network_required=False,
    )
    retry_policy = RetryPolicy(max_retries=1)
    idempotency_key_fields = [
        "workflow", "reference_image_path", "video_frames",
        "motion_bucket_id", "seed", "model_name",
    ]
    side_effects = ["writes video file to output_path", "submits a job to local ComfyUI server"]
    user_visible_verification = ["Watch generated clip for motion coherence and artifacts"]

    def __init__(self) -> None:
        super().__init__()
        self._client = ComfyUIClient()

    @property
    def provider_matrix(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for tpl in list_templates(kind="video"):
            out[tpl.name] = {
                "tool": self.name,
                "kind": tpl.kind,
                "description": tpl.description,
                "slots": tpl.slot_names,
                "required_custom_nodes": tpl.required_custom_nodes,
                "mode": "local_gpu_via_comfyui",
            }
        return out

    def get_status(self) -> ToolStatus:
        try:
            import requests  # noqa: F401
        except ImportError:
            return ToolStatus.UNAVAILABLE
        return ToolStatus.AVAILABLE if self._client.is_running() else ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        # SVD 14 frames @ 768x432, 20 steps, on a 4060 ≈ 60-120s
        return 90.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(
                success=False,
                error=(
                    f"ComfyUI not reachable at {self._client.endpoint.base_url}. "
                    + self.install_instructions
                ),
            )

        operation = inputs.get("operation", "image_to_video")
        start = time.time()

        workflow_name = inputs.get("workflow", "svd_image_to_video")
        try:
            template = load_template(workflow_name)
        except (FileNotFoundError, ValueError) as exc:
            return ToolResult(success=False, error=f"workflow load failed: {exc}")

        if template.kind != "video":
            return ToolResult(
                success=False,
                error=f"workflow '{template.name}' is kind='{template.kind}', expected 'video'",
            )

        slot_values: dict[str, Any] = {
            "seed": inputs.get("seed"),
            "steps": inputs.get("steps"),
            "cfg": inputs.get("cfg"),
            "video_frames": inputs.get("video_frames"),
            "motion_bucket_id": inputs.get("motion_bucket_id"),
            "fps": inputs.get("fps"),
            "augmentation_level": inputs.get("augmentation_level"),
            "width": inputs.get("width"),
            "height": inputs.get("height"),
            "model_name": inputs.get("model_name"),
        }

        if operation == "image_to_video":
            if "image_filename" not in template.slots:
                return ToolResult(
                    success=False,
                    error=f"workflow '{template.name}' has no image_filename slot — pick an i2v template",
                )
            ref_path = inputs.get("reference_image_path")
            if not ref_path:
                return ToolResult(
                    success=False,
                    error="image_to_video requires reference_image_path",
                )
            try:
                uploaded_name = self._client.upload_image(ref_path)
            except (ComfyUIError, FileNotFoundError) as exc:
                return ToolResult(success=False, error=f"reference upload failed: {exc}")
            slot_values["image_filename"] = uploaded_name
        elif operation == "text_to_video":
            return ToolResult(
                success=False,
                error=(
                    "text_to_video is not provided as a default template. "
                    "Add a t2v workflow JSON under tools/comfyui_workflows/ "
                    "(kind='video', no image_filename slot) and set workflow=<name>."
                ),
            )

        wf = apply_slots(template, slot_values)

        try:
            prompt_id = self._client.submit(wf)
            history = self._client.wait(prompt_id, timeout_s=float(inputs.get("timeout_s", 600.0)))
        except ComfyUIError as exc:
            return ToolResult(success=False, error=f"comfyui execution failed: {exc}")

        outputs = self._client.collect_outputs(history, template.output_node)
        if not outputs:
            return ToolResult(
                success=False,
                error=f"no video returned by node {template.output_node} (prompt_id={prompt_id})",
            )

        # VHS_VideoCombine emits both a preview (gif/webp) and the actual MP4.
        # Prefer .mp4, then fall back to the first output.
        primary = next(
            (o for o in outputs if o.filename.lower().endswith(".mp4")),
            outputs[0],
        )

        suffix = Path(primary.filename).suffix or ".mp4"
        output_path = Path(inputs.get("output_path") or f"comfyui_{prompt_id}{suffix}")
        try:
            self._client.download(primary, output_path)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=f"download failed: {exc}")

        return ToolResult(
            success=True,
            data={
                "provider": "comfyui",
                "workflow": template.name,
                "operation": operation,
                "model": inputs.get("model_name"),
                "prompt_id": prompt_id,
                "output": str(output_path),
                "extra_outputs": [
                    {"filename": o.filename, "subfolder": o.subfolder, "type": o.type}
                    for o in outputs if o is not primary
                ],
            },
            artifacts=[str(output_path)],
            cost_usd=0.0,
            duration_seconds=round(time.time() - start, 2),
            seed=inputs.get("seed"),
            model=template.name,
        )
