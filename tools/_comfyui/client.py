"""Minimal HTTP client for a local ComfyUI server.

We intentionally use blocking `requests` polling instead of the WebSocket
progress stream — generation jobs are batch-style and the registry tools
return a single ToolResult, so a 1s poll loop is the simpler contract.

Endpoints:
  GET  /system_stats              → liveness + GPU info (used by get_status)
  POST /upload/image              → upload reference image, returns filename
  POST /prompt                    → enqueue workflow, returns prompt_id
  GET  /history/{prompt_id}       → fetch outputs once finished
  GET  /view?filename=&subfolder=&type=output → download a result file
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


class ComfyUIError(RuntimeError):
    pass


@dataclass(frozen=True)
class Endpoint:
    host: str
    port: int

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


def default_endpoint() -> Endpoint:
    host = os.environ.get("COMFYUI_HOST", "127.0.0.1")
    port = int(os.environ.get("COMFYUI_PORT", "8188"))
    return Endpoint(host=host, port=port)


@dataclass
class OutputFile:
    filename: str
    subfolder: str
    type: str


class ComfyUIClient:
    """Talk to a local ComfyUI server over HTTP."""

    def __init__(self, endpoint: Optional[Endpoint] = None, *, request_timeout: float = 10.0):
        self.endpoint = endpoint or default_endpoint()
        self.request_timeout = request_timeout
        self.client_id = str(uuid.uuid4())

    def is_running(self) -> bool:
        try:
            import requests
        except ImportError:
            return False
        try:
            r = requests.get(f"{self.endpoint.base_url}/system_stats", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def system_stats(self) -> dict[str, Any]:
        import requests
        r = requests.get(f"{self.endpoint.base_url}/system_stats", timeout=self.request_timeout)
        r.raise_for_status()
        return r.json()

    def upload_image(self, path: Path | str, *, overwrite: bool = True) -> str:
        """Upload a local image to ComfyUI's input/ folder. Returns server-side filename."""
        import requests

        path = Path(path)
        if not path.is_file():
            raise ComfyUIError(f"upload_image: file not found: {path}")
        with open(path, "rb") as fh:
            files = {"image": (path.name, fh, "application/octet-stream")}
            data = {"overwrite": "true" if overwrite else "false"}
            r = requests.post(
                f"{self.endpoint.base_url}/upload/image",
                files=files,
                data=data,
                timeout=60.0,
            )
        r.raise_for_status()
        body = r.json()
        return body.get("name") or path.name

    def submit(self, workflow: dict[str, Any]) -> str:
        """Submit a workflow (API-format JSON). Returns prompt_id."""
        import requests

        payload = {"prompt": workflow, "client_id": self.client_id}
        r = requests.post(
            f"{self.endpoint.base_url}/prompt",
            json=payload,
            timeout=self.request_timeout,
        )
        if r.status_code >= 400:
            raise ComfyUIError(f"submit failed: HTTP {r.status_code}: {r.text[:500]}")
        body = r.json()
        prompt_id = body.get("prompt_id")
        if not prompt_id:
            raise ComfyUIError(f"submit response missing prompt_id: {body}")
        return prompt_id

    def history(self, prompt_id: str) -> Optional[dict[str, Any]]:
        import requests
        r = requests.get(
            f"{self.endpoint.base_url}/history/{prompt_id}",
            timeout=self.request_timeout,
        )
        r.raise_for_status()
        body = r.json()
        return body.get(prompt_id)

    def wait(self, prompt_id: str, *, timeout_s: float = 600.0, poll_s: float = 1.0) -> dict[str, Any]:
        """Block until the prompt finishes; return its history entry."""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            entry = self.history(prompt_id)
            if entry is not None and entry.get("status", {}).get("completed"):
                return entry
            if entry is not None:
                status_messages = entry.get("status", {}).get("messages", [])
                for kind, payload in status_messages:
                    if kind == "execution_error":
                        raise ComfyUIError(f"execution_error: {payload}")
            time.sleep(poll_s)
        raise ComfyUIError(f"timeout after {timeout_s}s waiting for prompt {prompt_id}")

    def collect_outputs(self, history_entry: dict[str, Any], node_id: str) -> list[OutputFile]:
        """Pull output files (images, gifs, videos) from a finished node."""
        node_outputs = history_entry.get("outputs", {}).get(node_id, {})
        files: list[OutputFile] = []
        for key in ("images", "gifs", "videos"):
            for item in node_outputs.get(key, []) or []:
                files.append(
                    OutputFile(
                        filename=item.get("filename", ""),
                        subfolder=item.get("subfolder", ""),
                        type=item.get("type", "output"),
                    )
                )
        return files

    def download(self, output: OutputFile, dest: Path | str) -> Path:
        import requests

        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        params = {
            "filename": output.filename,
            "subfolder": output.subfolder,
            "type": output.type,
        }
        r = requests.get(
            f"{self.endpoint.base_url}/view",
            params=params,
            timeout=120.0,
            stream=True,
        )
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                if chunk:
                    fh.write(chunk)
        return dest
