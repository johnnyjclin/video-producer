#!/usr/bin/env python
"""
Social Short Producer — MCP server.

Exposes low-level cloud media tools that complement the local-GPU
ComfyUI bridge (`comfyui_image`, `comfyui_video`). The host agent can
call these directly when it needs cloud capabilities (e.g. premium
fal/Runway clip for a hero shot, ElevenLabs voice).

Tools published:

    runway_image_to_video(image_path, prompt, model?, duration?, ratio?,
                          output_path) -> {video_path, cost_usd}
        Single Runway I2V call via gen4_turbo. Uses data-URL upload.

    runway_text_to_video_gen45(prompt, duration?, ratio?, output_path) -> {video_path, cost_usd}
        Single Runway gen4.5 T2V call via raw HTTP.

    elevenlabs_tts(text, voice_id?, model_id?, output_path) -> {audio_path}
    elevenlabs_music(prompt, duration_s?, output_path) -> {audio_path}
    remotion_render(composition_id, props, output_path) -> {video_path}
    measure_audio_duration(audio_path) -> {duration_s}

The server is launched by Claude Code whenever the plugin is active. It
reads credentials from the plugin's own .env (located at
$VIDEO_PRODUCER_PLUGIN_ROOT/.env).

For the structured 15-second social-short workflow, the host agent
should drive the `social-short-15s` pipeline (see
`pipeline_defs/social-short-15s.yaml`) — those stages call the registry
selectors which auto-route to local ComfyUI before falling back to
cloud.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

# --- Resolve plugin root + import plugin's internal libs --------------------
PLUGIN_ROOT = Path(
    os.environ.get("VIDEO_PRODUCER_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent
)
sys.path.insert(0, str(PLUGIN_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PLUGIN_ROOT / ".env")
except Exception:
    pass  # dotenv is optional; env vars may be set externally

# Import the plugin's existing tool registry (optional — only needed by the
# high-level tool). If the registry fails to load, low-level tools still work
# because they hit Runway / ElevenLabs directly.
try:
    from tools.tool_registry import registry as _tool_registry  # type: ignore
    _tool_registry.discover()
except Exception as _err:
    _tool_registry = None

# --- MCP server setup ------------------------------------------------------
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: install the MCP SDK — `pip install mcp`", file=sys.stderr)
    sys.exit(1)

mcp = FastMCP("video-producer")

# --- Shared constants ------------------------------------------------------
import requests

RUNWAY_API_BASE = "https://api.dev.runwayml.com/v1"
RUNWAY_POLL_MAX = 150          # 150 × 5 s = 12.5 min ceiling for gen4.5
RUNWAY_POLL_INTERVAL = 5
GEN45_COST_PER_SECOND = 0.05   # text_to_video
GEN4_TURBO_COST_PER_SECOND = 0.05  # image_to_video

RATIO_MAP = {"16:9": "1280:720", "9:16": "720:1280", "1:1": "720:720"}


def _runway_headers() -> dict[str, str]:
    key = os.environ.get("RUNWAY_API_KEY")
    if not key:
        raise RuntimeError("RUNWAY_API_KEY is not set in the plugin's .env")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "X-Runway-Version": "2024-11-06",
    }


def _poll_runway(task_id: str, timeout_poll_count: int = RUNWAY_POLL_MAX) -> str:
    """Poll a Runway task until SUCCEEDED; return the downloadable video URL."""
    for _ in range(timeout_poll_count):
        time.sleep(RUNWAY_POLL_INTERVAL)
        r = requests.get(f"{RUNWAY_API_BASE}/tasks/{task_id}",
                         headers=_runway_headers(), timeout=15)
        if r.status_code != 200:
            continue
        data = r.json()
        status = data.get("status")
        if status == "SUCCEEDED":
            return data["output"][0]
        if status == "FAILED":
            raise RuntimeError(
                f"Runway task FAILED: {data.get('failure', 'unknown')}"
            )
    raise TimeoutError(f"Runway task {task_id} timed out")


def _data_url(image_path: Path | str) -> str:
    p = Path(image_path)
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    b = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b}"


# ===========================================================================
#  LOW-LEVEL TOOLS
# ===========================================================================

@mcp.tool()
def runway_image_to_video(
    image_path: str,
    prompt: str,
    output_path: str,
    duration: int = 5,
    ratio: str = "9:16",
    model: str = "gen4_turbo",
) -> dict[str, Any]:
    """Generate a video from a single reference image via Runway.

    Uses base64 data URLs (bypasses fal.ai storage upload which is unreliable).
    Writes the final MP4 to `output_path` and returns {video_path, cost_usd, model, duration}.

    Args:
        image_path: Local file path to the source image (jpg or png).
        prompt: Director-style description of camera motion + scene.
        output_path: Where to save the MP4 (absolute or relative to plugin root).
        duration: 5 or 10 seconds. Default 5.
        ratio: "9:16" / "16:9" / "1:1". Default 9:16 for shorts.
        model: "gen4_turbo" (fast default) or "gen4_aleph" (premium).
    """
    pixel_ratio = RATIO_MAP.get(ratio, "720:1280")
    image_url = _data_url(image_path)

    submit = requests.post(
        f"{RUNWAY_API_BASE}/image_to_video",
        headers=_runway_headers(),
        json={
            "model": model,
            "promptImage": image_url,
            "promptText": prompt,
            "duration": duration,
            "ratio": pixel_ratio,
            "watermark": False,
        },
        timeout=30,
    )
    if submit.status_code != 200:
        raise RuntimeError(f"Runway I2V submit {submit.status_code}: {submit.text[:400]}")

    task_id = submit.json()["id"]
    video_url = _poll_runway(task_id)

    # Download
    out = Path(output_path)
    if not out.is_absolute():
        out = PLUGIN_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(requests.get(video_url, timeout=120).content)

    return {
        "video_path": str(out),
        "cost_usd": GEN4_TURBO_COST_PER_SECOND * duration,
        "model": model,
        "duration_s": duration,
        "task_id": task_id,
    }


@mcp.tool()
def runway_text_to_video_gen45(
    prompt: str,
    output_path: str,
    duration: int = 5,
    ratio: str = "9:16",
) -> dict[str, Any]:
    """Generate a video from a text prompt via Runway gen4.5 text_to_video.

    This is the ONLY text-to-video model available on the current Runway plan
    (gen4_turbo, gen3a_turbo, kling3.0_*, veo3* return 403 or 400). Invoked
    directly over HTTP because the built-in runway_video tool's model enum
    does not include gen4.5.

    gen4.5 is slow: typically 3–7 minutes per 5s clip. Caller should parallelize.

    Args:
        prompt: Full scene description. Keep cable/phone/cinematic scenes generic
                — do not specify connector type (Lightning/USB-C) since gen4.5
                often substitutes USB-A.
        output_path: Where to save the MP4.
        duration: 5 or 10 seconds (5 recommended — cost scales linearly).
        ratio: "9:16" / "16:9" / "1:1".
    """
    pixel_ratio = RATIO_MAP.get(ratio, "720:1280")

    submit = requests.post(
        f"{RUNWAY_API_BASE}/text_to_video",
        headers=_runway_headers(),
        json={
            "model": "gen4.5",
            "promptText": prompt,
            "duration": duration,
            "ratio": pixel_ratio,
            "watermark": False,
        },
        timeout=30,
    )
    if submit.status_code != 200:
        raise RuntimeError(f"Runway T2V submit {submit.status_code}: {submit.text[:400]}")

    task_id = submit.json()["id"]
    video_url = _poll_runway(task_id)

    out = Path(output_path)
    if not out.is_absolute():
        out = PLUGIN_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(requests.get(video_url, timeout=120).content)

    return {
        "video_path": str(out),
        "cost_usd": GEN45_COST_PER_SECOND * duration,
        "model": "gen4.5",
        "duration_s": duration,
        "task_id": task_id,
    }


@mcp.tool()
def elevenlabs_tts(
    text: str,
    output_path: str,
    voice_id: str = "pNInz6obpgDQGcFmaJgB",
    model_id: str = "eleven_turbo_v2_5",
) -> dict[str, Any]:
    """Generate English (or configured-language) TTS audio via ElevenLabs.

    Default voice (`pNInz6obpgDQGcFmaJgB`) is a confident male suitable for
    tech product narration. Swap voice_id for other languages:
        German: pqHfZKP75CvOlQylNhV4
        Japanese: Mu5jxyqZOLIGltFpfalg
        Spanish: IoWAuKNnqRPuIktSJlCy

    Args:
        text: The line to speak. Keep < 80 chars for snappy delivery.
        output_path: Where to save the mp3.
        voice_id: ElevenLabs voice ID.
        model_id: TTS model. `eleven_turbo_v2_5` is fastest.
    """
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set in the plugin's .env")

    out = Path(output_path)
    if not out.is_absolute():
        out = PLUGIN_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)

    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        json={"text": text, "model_id": model_id},
        timeout=60,
    )
    if r.status_code == 429:
        time.sleep(3)
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
            headers={"xi-api-key": key, "Content-Type": "application/json"},
            json={"text": text, "model_id": model_id},
            timeout=60,
        )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs TTS {r.status_code}: {r.text[:400]}")
    out.write_bytes(r.content)

    return {
        "audio_path": str(out),
        "voice_id": voice_id,
        "model_id": model_id,
        "char_count": len(text),
    }


@mcp.tool()
def elevenlabs_music(
    prompt: str,
    output_path: str,
    duration_s: int = 30,
) -> dict[str, Any]:
    """Generate an instrumental music bed via ElevenLabs Music.

    Args:
        prompt: Musical direction, e.g. "Fast-paced modern tech reveal, punchy
                electronic pulses, no vocals, 30 seconds."
        output_path: Where to save the mp3.
        duration_s: Total track duration in seconds (max 30 for one call).
    """
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set in the plugin's .env")

    out = Path(output_path)
    if not out.is_absolute():
        out = PLUGIN_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)

    r = requests.post(
        "https://api.elevenlabs.io/v1/music",
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        json={"prompt": prompt, "music_length_ms": duration_s * 1000},
        timeout=180,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs Music {r.status_code}: {r.text[:400]}")
    out.write_bytes(r.content)

    return {
        "audio_path": str(out),
        "duration_s": duration_s,
    }


@mcp.tool()
def measure_audio_duration(audio_path: str) -> dict[str, Any]:
    """ffprobe the audio file and return its duration in seconds.

    Used by the pipeline to right-size Remotion scene durations to actual TTS length.
    """
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", audio_path],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[:200]}")
    return {"duration_s": float(result.stdout.strip())}


@mcp.tool()
def remotion_render(
    composition_id: str,
    output_path: str,
    props: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render a Remotion composition to MP4.

    Runs `npx remotion render` inside the plugin's bundled `remotion-composer/`
    project. The composition must already be registered in `Root.tsx`.

    Args:
        composition_id: The `id` registered in `remotion-composer/src/Root.tsx`.
        output_path: Absolute path for the final MP4.
        props: Optional dict to override defaultProps at render time.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx", "remotion", "render",
        "src/index.tsx", composition_id, str(out),
    ]
    if props:
        cmd.extend(["--props", json.dumps(props)])

    result = subprocess.run(
        cmd,
        cwd=str(PLUGIN_ROOT / "remotion-composer"),
        capture_output=True, text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"remotion render failed (code {result.returncode}):\n"
            f"STDOUT: {result.stdout[-1500:]}\nSTDERR: {result.stderr[-1500:]}"
        )

    # ffprobe to read final duration / resolution
    probe = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration:stream=width,height",
         "-of", "json", str(out)],
        capture_output=True, text=True, timeout=10,
    )
    info: dict[str, Any] = {"video_path": str(out)}
    try:
        d = json.loads(probe.stdout or "{}")
        info["duration_s"] = float(d.get("format", {}).get("duration", 0))
        for stream in d.get("streams", []):
            if "width" in stream:
                info["width"] = stream["width"]
                info["height"] = stream["height"]
                break
    except Exception:
        pass
    return info


# ===========================================================================
#  Entry point
# ===========================================================================

if __name__ == "__main__":
    mcp.run()
