"""Workflow template loader for ComfyUI bridge tools.

Templates live under `tools/comfyui_workflows/*.json` in *API format* (the
"Save (API Format)" export from the GUI), with one extra `_meta` key the
loader strips before submission. `_meta` declares which node id holds each
friendly slot (prompt, seed, width, etc.) so callers can patch by name.

Format example:
{
  "_meta": {
    "name": "sdxl_lightning",
    "kind": "image",
    "slots": {
      "prompt":          ["6.text"],
      "negative_prompt": ["7.text"],
      "seed":            ["3.seed"],
      "width":           ["5.width"],
      "height":          ["5.height"],
      "filename_prefix": ["9.filename_prefix"]
    },
    "output_node": "9",
    "required_custom_nodes": []
  },
  "3": {"class_type": "KSampler", "inputs": {...}},
  ...
}
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


def workflows_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "comfyui_workflows"


@dataclass(frozen=True)
class Template:
    name: str
    kind: str  # "image" or "video"
    output_node: str
    slots: dict[str, list[str]]
    workflow: dict[str, Any]
    required_custom_nodes: list[str]
    description: str = ""

    @property
    def slot_names(self) -> list[str]:
        return sorted(self.slots.keys())


def load_template(name_or_path: str) -> Template:
    """Load a template by short name (filename without .json) or absolute path."""
    path = Path(name_or_path)
    if not path.suffix:
        path = workflows_dir() / f"{name_or_path}.json"
    if not path.is_file():
        raise FileNotFoundError(f"comfyui workflow template not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    meta = raw.pop("_meta", None)
    if not isinstance(meta, dict):
        raise ValueError(
            f"template {path.name} is missing required `_meta` block "
            "(slots, output_node, kind)"
        )
    workflow = {k: v for k, v in raw.items() if not k.startswith("_")}
    return Template(
        name=meta.get("name", path.stem),
        kind=meta.get("kind", "image"),
        output_node=str(meta["output_node"]),
        slots={k: list(v) for k, v in meta.get("slots", {}).items()},
        workflow=workflow,
        required_custom_nodes=list(meta.get("required_custom_nodes", []) or []),
        description=meta.get("description", ""),
    )


def list_templates(kind: Optional[str] = None) -> list[Template]:
    out: list[Template] = []
    for path in sorted(workflows_dir().glob("*.json")):
        try:
            tpl = load_template(path.stem)
        except Exception:
            continue
        if kind is None or tpl.kind == kind:
            out.append(tpl)
    return out


def apply_slots(template: Template, values: dict[str, Any]) -> dict[str, Any]:
    """Return a new workflow dict with `values` patched into the template's slots.

    Unknown slot names in `values` are silently ignored. `None` values are
    skipped — the template default stays in place.
    """
    wf = copy.deepcopy(template.workflow)
    for slot_name, value in values.items():
        if value is None:
            continue
        targets = template.slots.get(slot_name, [])
        for target in targets:
            node_id, _, input_name = target.partition(".")
            if not node_id or not input_name:
                continue
            node = wf.get(node_id)
            if node is None or "inputs" not in node:
                continue
            node["inputs"][input_name] = value
    return wf
