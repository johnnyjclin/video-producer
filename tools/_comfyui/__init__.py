"""ComfyUI HTTP bridge — shared client + workflow template helpers.

This package is the shared substrate behind `tools.graphics.comfyui_image`
and `tools.video.comfyui_video`. It does NOT register any BaseTool itself,
so the registry ignores it during discovery.
"""

from tools._comfyui.client import ComfyUIClient, ComfyUIError, default_endpoint
from tools._comfyui.templates import (
    Template,
    apply_slots,
    list_templates,
    load_template,
    workflows_dir,
)

__all__ = [
    "ComfyUIClient",
    "ComfyUIError",
    "default_endpoint",
    "Template",
    "apply_slots",
    "list_templates",
    "load_template",
    "workflows_dir",
]
