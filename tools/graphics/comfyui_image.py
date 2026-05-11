"""Local image generation via a running ComfyUI server.

Exposes a single BaseTool that drives any workflow template under
`tools/comfyui_workflows/` whose `_meta.kind == "image"`. The default
template is `sdxl_lightning` — vanilla ComfyUI, no custom nodes, fits 8GB.

Why this exists: the existing `local_diffusion` tool calls diffusers
pipelines directly, which works but locks each model behind hand-written
Python. ComfyUI gives us the broader model ecosystem (FLUX-GGUF, SDXL,
Hyper-SD, Lightning) for the cost of one HTTP client.
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


class ComfyUIImage(BaseTool):
    name = "comfyui_image"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "comfyui"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.SEEDED
    runtime = ToolRuntime.LOCAL_GPU

    dependencies = ["python:requests"]
    install_instructions = (
        "Run a ComfyUI server locally:\n"
        "  git clone https://github.com/comfyanonymous/ComfyUI && cd ComfyUI\n"
        "  pip install -r requirements.txt\n"
        "  python main.py --listen 127.0.0.1 --port 8188\n"
        "Then drop checkpoints into ComfyUI/models/checkpoints/ as listed by\n"
        "each workflow template's `required_models`.\n"
        "Override host/port via COMFYUI_HOST / COMFYUI_PORT."
    )
    fallback = "local_diffusion"
    fallback_tools = ["local_diffusion", "flux_image", "image_selector"]
    agent_skills = ["comfyui", "flux-best-practices"]

    capabilities = ["generate_image", "text_to_image"]
    supports = {
        "negative_prompt": True,
        "seed": True,
        "offline": True,
        "custom_size": True,
        "custom_workflows": True,
    }
    best_for = [
        "free local image generation on consumer GPUs (RTX 4060 8GB target)",
        "swapping between SDXL/Lightning/FLUX-GGUF without code changes",
        "offline / air-gapped / privacy-sensitive workflows",
    ]
    not_good_for = [
        "machines without a running ComfyUI server",
        "CPU-only hardware (use cloud providers instead)",
    ]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "negative_prompt": {"type": "string"},
            "width": {"type": "integer"},
            "height": {"type": "integer"},
            "seed": {"type": "integer"},
            "steps": {"type": "integer"},
            "cfg": {"type": "number"},
            "model_name": {"type": "string", "description": "ComfyUI checkpoint filename"},
            "workflow": {
                "type": "string",
                "description": "Template short-name under tools/comfyui_workflows/, or absolute path to a workflow JSON.",
                "default": "sdxl_lightning",
            },
            "output_path": {"type": "string"},
            "timeout_s": {"type": "number", "default": 300.0},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=1000, vram_mb=7000, disk_mb=200, network_required=False,
    )
    retry_policy = RetryPolicy(max_retries=1)
    idempotency_key_fields = ["prompt", "workflow", "width", "height", "seed", "model_name"]
    side_effects = ["writes image file to output_path", "submits a job to local ComfyUI server"]
    user_visible_verification = ["Inspect generated image for relevance and quality"]

    def __init__(self) -> None:
        super().__init__()
        self._client = ComfyUIClient()

    @property
    def provider_matrix(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for tpl in list_templates(kind="image"):
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
        return 12.0  # SDXL Lightning 4-step on a 4060 ≈ 8-15s

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(
                success=False,
                error=(
                    f"ComfyUI not reachable at {self._client.endpoint.base_url}. "
                    + self.install_instructions
                ),
            )

        start = time.time()
        workflow_name = inputs.get("workflow", "sdxl_lightning")
        try:
            template = load_template(workflow_name)
        except (FileNotFoundError, ValueError) as exc:
            return ToolResult(success=False, error=f"workflow load failed: {exc}")

        if template.kind != "image":
            return ToolResult(
                success=False,
                error=f"workflow '{template.name}' is kind='{template.kind}', expected 'image'",
            )

        slot_values = {
            "prompt": inputs.get("prompt"),
            "negative_prompt": inputs.get("negative_prompt"),
            "width": inputs.get("width"),
            "height": inputs.get("height"),
            "seed": inputs.get("seed"),
            "steps": inputs.get("steps"),
            "cfg": inputs.get("cfg"),
            "model_name": inputs.get("model_name"),
        }
        wf = apply_slots(template, slot_values)

        try:
            prompt_id = self._client.submit(wf)
            history = self._client.wait(prompt_id, timeout_s=float(inputs.get("timeout_s", 300.0)))
        except ComfyUIError as exc:
            return ToolResult(success=False, error=f"comfyui execution failed: {exc}")

        outputs = self._client.collect_outputs(history, template.output_node)
        if not outputs:
            return ToolResult(
                success=False,
                error=f"no images returned by node {template.output_node} (prompt_id={prompt_id})",
            )

        output_path = Path(inputs.get("output_path") or f"comfyui_{prompt_id}.png")
        try:
            self._client.download(outputs[0], output_path)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=f"download failed: {exc}")

        return ToolResult(
            success=True,
            data={
                "provider": "comfyui",
                "workflow": template.name,
                "model": inputs.get("model_name"),
                "prompt_id": prompt_id,
                "output": str(output_path),
                "extra_outputs": [
                    {"filename": o.filename, "subfolder": o.subfolder, "type": o.type}
                    for o in outputs[1:]
                ],
            },
            artifacts=[str(output_path)],
            cost_usd=0.0,
            duration_seconds=round(time.time() - start, 2),
            seed=inputs.get("seed"),
            model=template.name,
        )
