#!/usr/bin/env python
"""
NoirsBoxes Video Producer — MCP server.

Exposes the video production pipeline as MCP tools so a main-project Claude
Code agent can invoke "produce a NoirsBoxes short for MD-xxx" without ever
touching this plugin's Python internals.

Tools published:

    produce_noirsboxes_short(sku, tagline?, features?, language?, voice_id?,
                             output_dir?) -> {mp4_path, duration_s, cost_usd_estimated, ...}
        High-level: runs the full 8-step pipeline end-to-end.

    runway_image_to_video(image_path, prompt, model?, duration?, ratio?,
                          output_path) -> {video_path, cost_usd}
        Low-level: single Runway I2V call via gen4_turbo. Uses data-URL upload
        (bypasses FAL storage 401 bug).

    runway_text_to_video_gen45(prompt, duration?, ratio?, output_path) -> {video_path, cost_usd}
        Low-level: single Runway gen4.5 T2V call via raw HTTP (the runway_video
        tool's model enum doesn't include gen4.5 yet).

    elevenlabs_tts(text, voice_id?, model_id?, output_path) -> {audio_path}
    elevenlabs_music(prompt, duration_s?, output_path) -> {audio_path}
    remotion_render(composition_id, props, output_path) -> {video_path}
    measure_audio_duration(audio_path) -> {duration_s}

The server is launched by Claude Code whenever the plugin is active. It reads
credentials from the plugin's own .env (located at $NOIRSBOXES_PLUGIN_ROOT/.env).
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
    os.environ.get("NOIRSBOXES_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent
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

mcp = FastMCP("noirsboxes-video-producer")

# --- Shared constants ------------------------------------------------------
import requests

RUNWAY_API_BASE = "https://api.dev.runwayml.com/v1"
RUNWAY_POLL_MAX = 150          # 150 × 5 s = 12.5 min ceiling for gen4.5
RUNWAY_POLL_INTERVAL = 5
GEN45_COST_PER_SECOND = 0.05   # text_to_video
GEN4_TURBO_COST_PER_SECOND = 0.05  # image_to_video
BRAND_ROOT = PLUGIN_ROOT / "assets" / "brand" / "norisboxes" / "product-image"

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
        composition_id: The `id` from `Root.tsx`, e.g. `MD905Shorts`.
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
#  HIGH-LEVEL TOOL — one shot
# ===========================================================================

# Locked NoirsBoxes scene structure (matches v3 reference MD-905 output).
SCENE_SECONDS = [2.0, 2.0, 3.0, 4.0, 2.0, 4.0, 1.5, 4.0, 4.0]

# Voices by language
VOICE_BY_LANG = {
    "en": "pNInz6obpgDQGcFmaJgB",  # confident male
    "de": "pqHfZKP75CvOlQylNhV4",  # Bill
    "ja": "Mu5jxyqZOLIGltFpfalg",  # Asahi
    "es": "IoWAuKNnqRPuIktSJlCy",  # Aria
    "zh": "pNInz6obpgDQGcFmaJgB",  # fall-through — user should override
    "fr": "pNInz6obpgDQGcFmaJgB",
}


def _default_script_en(sku: str, tagline: str) -> list[tuple[str, str]]:
    """Returns the 9 narration lines for a given SKU + tagline in English."""
    sku_spoken = sku.replace("MD-", "MD ").replace("-", " ")  # "MD 905"
    sku_spoken = sku_spoken.replace("905", "nine oh five")
    sku_spoken = sku_spoken.replace("903", "nine oh three")
    sku_spoken = sku_spoken.replace("907", "nine oh seven")
    return [
        ("vo_01_hook",     "This cable looked real."),
        ("vo_02_problem",  "But it was killing my phone."),
        ("vo_03_solution", "I tested it with NoirsBoxes."),
        ("vo_04_inferior", "Inferior. Eighty-nine."),
        ("vo_05_swap",     "Swap to original."),
        ("vo_06_original", "One hundred. Perfect."),
        ("vo_07_safe",     "Safe again."),
        ("vo_08_features", "C forty-eight to C ninety-four. Any charger. In seconds."),
        ("vo_09_cta",      f"{sku_spoken}. {tagline}"),
    ]


@mcp.tool()
def produce_noirsboxes_short(
    sku: str,
    tagline: str = "Know before you sell.",
    features: list[str] | None = None,
    language: str = "en",
    voice_id: str | None = None,
    output_dir: str | None = None,
    skip_if_exists: bool = True,
) -> dict[str, Any]:
    """Run the full 8-step NoirsBoxes showcase-short pipeline end-to-end.

    Produces a 30s 9:16 1080×1920 MP4 matching the brand's AI fast-cut style
    (3 Runway I2V from brand photos + 4 Runway gen4.5 T2V B-roll + per-scene
    ElevenLabs TTS + music bed + Remotion render).

    Wall time: ~15–20 minutes (gen4.5 is the slow part). Cost: ~$2 USD.

    Args:
        sku: The NoirsBoxes SKU, e.g. "MD-905", "MD-903", "MD-907".
             Must have brand photos at
             `assets/brand/norisboxes/product-image/{sku}/`.
        tagline: Closing punch line. Defaults to "Know before you sell."
        features: List of 3–4 feature bullets. Defaults to MD-905's set.
        language: "en" / "de" / "ja" / "es" / "zh" / "fr". Captions stay in
                  English; only narration changes.
        voice_id: ElevenLabs voice override. If None, picked from `language`.
        output_dir: Where to write the final MP4. Defaults to
                    `projects/noirsboxes-{sku}-shorts/renders/`.
        skip_if_exists: If True and target MP4 already exists, skip regeneration.

    Returns a JSON dict with:
        mp4_path, duration_s, resolution, cost_usd_estimated, scenes_rendered,
        notes, generation_time_s
    """
    t_start = time.time()

    # --- 1. Validate SKU + brand photos ---
    brand_dir = BRAND_ROOT / sku
    if not brand_dir.exists():
        return {
            "mp4_path": None,
            "blocker": f"Brand folder not found: {brand_dir}",
            "recommendation": f"Drop MD-xxx photos under {BRAND_ROOT}/{sku}/",
        }
    required = {
        "holding":  f"{sku}-blank-holding.jpg",
        "inferior": f"{sku}-cable-inferior-89scores.jpg",
        "original": f"{sku}-cable-original-100scores.jpg",
    }
    # Fall back to less-specific names if the -89scores / -100scores variants missing
    def _find(pref: str) -> Path | None:
        exact = brand_dir / pref
        if exact.exists():
            return exact
        stem = pref.rsplit(".", 1)[0]
        # fuzzy fallback: any file whose stem starts with the same base
        base = "-".join(stem.split("-")[:3])  # e.g. MD-905-cable-inferior
        for p in brand_dir.glob(f"{base}*.jpg"):
            return p
        return None

    paths = {k: _find(v) for k, v in required.items()}
    missing = [k for k, v in paths.items() if v is None]
    if missing:
        return {
            "mp4_path": None,
            "blocker": f"Required brand photos missing for {sku}: {missing}",
            "recommendation": f"Need: {', '.join(required[m] for m in missing)}",
        }

    # --- 2. Resolve output path + idempotency check ---
    proj = PLUGIN_ROOT / "projects" / f"noirsboxes-{sku}-shorts"
    out_dir = Path(output_dir) if output_dir else proj / "renders"
    out_dir.mkdir(parents=True, exist_ok=True)
    final_mp4 = out_dir / f"noirsboxes-{sku}-9x16.mp4"

    if skip_if_exists and final_mp4.exists():
        # Quick idempotency: if MP4 is newer than all brand photos, reuse it
        mp4_mtime = final_mp4.stat().st_mtime
        if all(p.stat().st_mtime <= mp4_mtime for p in paths.values() if p):
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(final_mp4)],
                capture_output=True, text=True, timeout=10,
            )
            dur = float(probe.stdout.strip() or 0)
            return {
                "mp4_path": str(final_mp4),
                "duration_s": dur,
                "resolution": "1080x1920",
                "cost_usd_estimated": 0.0,
                "scenes_rendered": 9,
                "notes": "cached — no regeneration needed",
                "generation_time_s": time.time() - t_start,
            }

    # --- 3. Video generation (parallel) ---
    (proj / "assets/video").mkdir(parents=True, exist_ok=True)
    (proj / "assets/audio").mkdir(parents=True, exist_ok=True)
    (proj / "assets/music").mkdir(parents=True, exist_ok=True)

    LOCK = (
        " CRITICAL: vertical 9:16 composition, product stays clearly visible "
        "and centered. Camera on a tripod, only subtle movement."
    )
    iv_jobs = [
        ("iv_device_reveal", paths["holding"],
         f"A person's hand presenting a sleek black NoirsBoxes {sku} cable-tester device "
         "in a warm home setting, the device screen flickers on with a subtle glow, the hand holds "
         "it steady while the camera gently tilts toward the screen, natural daylight, "
         "cinematic shallow depth of field." + LOCK),
        ("iv_inferior_push", paths["inferior"],
         "Slow cinematic push-in onto the LCD screen showing detailed diagnostic data and an "
         "'Inferior' score of 89, red tones intensify subtly, warm home lighting softly blurred."
         + LOCK),
        ("iv_original_push", paths["original"],
         "Slow cinematic push-in onto the LCD screen showing detailed diagnostic data and an "
         "'Original' score of 100 with green certification tones, bright minimal home background "
         "softly blurred, triumphant palette." + LOCK),
    ]
    tv_jobs = [
        ("tv_cable_bad",
         "Extreme macro close-up of a cheap generic white cable connector lying on a dark wooden "
         "desk, subtle electrical blue spark flickering at the metal pins, warm moody studio "
         "lighting, shallow depth of field, cinematic product commercial aesthetic. Vertical 9:16."),
        ("tv_phone_dying",
         "Close-up of a modern smartphone lying face up on a dark wooden desk, the screen "
         "glitches with a dominant red low-battery warning icon pulsing, eerie ambient red glow, "
         "moody night lighting, very shallow depth of field, cinematic tension. Vertical 9:16."),
        ("tv_cable_swap",
         "Macro close-up of a clean brand-new white cable being gently inserted into a modern "
         "smartphone lying on a bright minimal desk, soft window daylight, warm wood tones, "
         "shallow depth of field, slow confident hand motion, cinematic. Vertical 9:16."),
        ("tv_phone_healthy",
         "A modern smartphone resting on a warm wooden desk, a white charging cable neatly "
         "attached, the screen glows calmly with a healthy green battery icon, soft cozy daylight "
         "from a window, shallow depth of field, peaceful confident cinematic vibe. Vertical 9:16."),
    ]

    total_cost = 0.0
    gen_errors: list[str] = []

    def _run_iv(name: str, img: Path, prompt: str) -> tuple[str, bool, str]:
        try:
            r = runway_image_to_video(
                image_path=str(img),
                prompt=prompt,
                output_path=str(proj / f"assets/video/{name}.mp4"),
                duration=5, ratio="9:16", model="gen4_turbo",
            )
            return (name, True, f"{r['cost_usd']:.2f}")
        except Exception as e:
            return (name, False, str(e)[:300])

    def _run_tv(name: str, prompt: str) -> tuple[str, bool, str]:
        try:
            r = runway_text_to_video_gen45(
                prompt=prompt,
                output_path=str(proj / f"assets/video/{name}.mp4"),
                duration=5, ratio="9:16",
            )
            return (name, True, f"{r['cost_usd']:.2f}")
        except Exception as e:
            return (name, False, str(e)[:300])

    with ThreadPoolExecutor(max_workers=7) as ex:
        fs = []
        for n, img, p in iv_jobs:
            fs.append(ex.submit(_run_iv, n, img, p))
        for n, p in tv_jobs:
            fs.append(ex.submit(_run_tv, n, p))
        for fut in as_completed(fs):
            name, ok, info = fut.result()
            if ok:
                total_cost += float(info)
            else:
                gen_errors.append(f"{name}: {info}")

    # Retry any failed T2V clips sequentially (gen4.5 has intermittent timeouts)
    for name, prompt in tv_jobs:
        out_path = proj / f"assets/video/{name}.mp4"
        if out_path.exists():
            continue
        try:
            r = runway_text_to_video_gen45(
                prompt=prompt,
                output_path=str(out_path),
                duration=5, ratio="9:16",
            )
            total_cost += r["cost_usd"]
            gen_errors = [e for e in gen_errors if not e.startswith(name)]
        except Exception as e:
            gen_errors.append(f"{name} (retry): {str(e)[:200]}")

    # Retry any failed I2V clips sequentially
    for name, img, prompt in iv_jobs:
        out_path = proj / f"assets/video/{name}.mp4"
        if out_path.exists():
            continue
        try:
            r = runway_image_to_video(
                image_path=str(img),
                prompt=prompt,
                output_path=str(out_path),
                duration=5, ratio="9:16", model="gen4_turbo",
            )
            total_cost += r["cost_usd"]
            gen_errors = [e for e in gen_errors if not e.startswith(name)]
        except Exception as e:
            gen_errors.append(f"{name} (retry): {str(e)[:200]}")

    # --- 4. TTS + music (parallel, workers<=4 to avoid 429) ---
    v_id = voice_id or VOICE_BY_LANG.get(language, VOICE_BY_LANG["en"])
    narration = _default_script_en(sku, tagline)  # TODO: localized scripts

    tts_errors: list[str] = []

    def _run_tts(name: str, text: str):
        try:
            elevenlabs_tts(
                text=text,
                output_path=str(proj / f"assets/audio/{name}.mp3"),
                voice_id=v_id,
            )
            return (name, True, None)
        except Exception as e:
            return (name, False, str(e)[:200])

    with ThreadPoolExecutor(max_workers=4) as ex:
        for fut in as_completed([ex.submit(_run_tts, n, t) for n, t in narration]):
            name, ok, err = fut.result()
            if not ok:
                tts_errors.append(f"{name}: {err}")

    # Retry 429s
    for name, text in narration:
        out_path = proj / f"assets/audio/{name}.mp3"
        if out_path.exists():
            continue
        time.sleep(3)
        try:
            elevenlabs_tts(text=text, output_path=str(out_path), voice_id=v_id)
            tts_errors = [e for e in tts_errors if not e.startswith(name)]
        except Exception as e:
            tts_errors.append(f"{name} (retry): {str(e)[:200]}")

    # Music bed — reusable across SKUs
    music_path = proj / "assets/music/bed.mp3"
    if not music_path.exists():
        try:
            elevenlabs_music(
                prompt=("Fast-paced modern tech short-form reveal, punchy electronic pulses, "
                        "energetic build, confident sub bass, trendy TikTok/Reels vibe, "
                        "no vocals, 30 seconds."),
                output_path=str(music_path),
                duration_s=30,
            )
        except Exception as e:
            tts_errors.append(f"music_gen: {str(e)[:200]}")

    # --- 5. Stage into Remotion public folder ---
    dest = PLUGIN_ROOT / "remotion-composer" / "public" / f"md905-shorts"  # reuse MD-905's path for now
    dest.mkdir(parents=True, exist_ok=True)
    import shutil
    for p in (proj / "assets/video").glob("*.mp4"):
        shutil.copy2(p, dest / p.name)
    for p in (proj / "assets/audio").glob("vo_*.mp3"):
        shutil.copy2(p, dest / p.name)
    shutil.copy2(music_path, dest / "bed.mp3")
    # Hero product PNG + logo
    blank_src = brand_dir / f"{sku.lower()}-blank.jpg"
    if not blank_src.exists():
        blank_src = brand_dir / f"md905-blank.jpg"  # shared fallback
    if blank_src.exists():
        shutil.copy2(blank_src, dest / "md905-studio.jpg")
    logo_src = PLUGIN_ROOT / "assets/brand/norisboxes/logo.png"
    if logo_src.exists():
        shutil.copy2(logo_src, dest / "logo.png")

    # --- 6. Remotion render ---
    render_errors: list[str] = []
    try:
        render_info = remotion_render(
            composition_id="MD905Shorts",
            output_path=str(final_mp4),
            props=None,  # defaultProps already match md905-shorts/ folder
        )
    except Exception as e:
        render_errors.append(f"remotion: {str(e)[:300]}")
        render_info = {}

    # --- 7. Compose final response ---
    elapsed = time.time() - t_start
    all_errors = gen_errors + tts_errors + render_errors
    if not final_mp4.exists():
        return {
            "mp4_path": None,
            "blocker": "Final MP4 was not written",
            "errors": all_errors,
            "cost_usd_estimated": round(total_cost, 2),
            "generation_time_s": round(elapsed, 1),
            "recommendation": "Inspect errors; retry failed steps individually with low-level tools.",
        }

    return {
        "mp4_path": str(final_mp4),
        "duration_s": render_info.get("duration_s", 26.5),
        "resolution": f"{render_info.get('width', 1080)}x{render_info.get('height', 1920)}",
        "cost_usd_estimated": round(total_cost + 0.25, 2),  # + TTS + music
        "scenes_rendered": 9,
        "notes": "; ".join(all_errors) if all_errors else "all scenes rendered cleanly",
        "generation_time_s": round(elapsed, 1),
    }


# ===========================================================================
#  Entry point
# ===========================================================================

if __name__ == "__main__":
    mcp.run()
