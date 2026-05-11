#!/usr/bin/env bash
# ----------------------------------------------------------------------
#  Social Short Producer — one-shot dependency installer
#
#  A Claude Code plugin for producing 15-second social shorts on a local
#  RTX 4060 8GB (or comparable) GPU via ComfyUI. No mandatory cloud APIs.
#
#  Usage: bash install.sh
# ----------------------------------------------------------------------

set -euo pipefail

# --- resolve the directory this script lives in (plugin root) ---
PLUGIN_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PLUGIN_ROOT"

echo "=============================================================="
echo "  Social Short Producer — installing in:"
echo "  $PLUGIN_ROOT"
echo "=============================================================="

# --- 0. prerequisite binaries ---
need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "❌ Missing required binary: $1"
    echo "   $2"
    exit 1
  }
}
need python "Install Python 3.11+"
need node   "Install Node.js 22+ (https://nodejs.org)"
need npm    "Install Node.js 22+ (ships with npm)"
need ffmpeg "brew install ffmpeg   (macOS)   |   apt install ffmpeg   (Debian/Ubuntu)"

# --- 1. Python deps ---
echo ""
echo "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    python -m pip install -q -r requirements.txt
elif command -v uv >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
    uv sync
else
    echo "⚠️  No requirements.txt or uv project found — installing minimum MCP + core deps"
    python -m pip install -q "mcp>=0.9.0" "requests" "python-dotenv" "fastmcp"
fi

# Also install MCP server's own deps (kept separate so it's minimal)
if [ -f "mcp/requirements.txt" ]; then
    python -m pip install -q -r mcp/requirements.txt
fi

# --- 2. Node / Remotion deps ---
echo ""
echo "📦 Installing Remotion composer dependencies (may take 1–2 min on first run)..."
cd "$PLUGIN_ROOT/remotion-composer"
if [ ! -d node_modules ] || [ package.json -nt node_modules ]; then
    npm install --no-audit --no-fund --loglevel=error
else
    echo "   node_modules up-to-date — skipping"
fi
cd "$PLUGIN_ROOT"

# --- 3. .env scaffold ---
echo ""
if [ ! -f .env ]; then
    [ -f .env.example ] && cp .env.example .env || touch .env
    echo "📝 Created .env."
    echo ""
    echo "ℹ️  This plugin runs locally by default — no API keys are required."
    echo "    Optional cloud fallbacks (only used when a registry tool calls them):"
    echo "      COMFYUI_HOST / COMFYUI_PORT  (defaults: 127.0.0.1 / 8188)"
    echo "      RUNWAY_API_KEY               (optional — premium hero clips)"
    echo "      ELEVENLABS_API_KEY           (optional — better TTS)"
    echo "      FAL_KEY                      (optional — fal.ai fallbacks)"
    echo ""
else
    echo "✔️  .env already exists — skipping scaffold."
fi

# --- 4. ComfyUI reachability check (best-effort, non-blocking) ---
echo ""
HOST="${COMFYUI_HOST:-127.0.0.1}"
PORT="${COMFYUI_PORT:-8188}"
if curl -fsS --max-time 2 "http://$HOST:$PORT/system_stats" >/dev/null 2>&1; then
    echo "✔️  ComfyUI reachable at $HOST:$PORT"
else
    echo "ℹ️  ComfyUI not running at $HOST:$PORT — that's OK, you can start it later."
    echo "    See tools/comfyui_workflows/README.md for setup + model download list."
fi

# --- 5. final instructions ---
echo ""
echo "=============================================================="
echo "✅  DEPENDENCY INSTALL COMPLETE"
echo "=============================================================="
echo ""
echo "Next steps (runs once, then the plugin is available in every Claude Code session):"
echo ""
echo "  1. Start ComfyUI on your GPU machine (see tools/comfyui_workflows/README.md)."
echo ""
echo "  2. Register this folder as a local marketplace:"
echo "       claude plugin marketplace add $PLUGIN_ROOT"
echo ""
echo "  3. Install the plugin from the marketplace:"
echo "       claude plugin install video-producer@video-producer"
echo ""
echo "  4. Verify:"
echo "       claude plugin list"
echo ""
echo "  5. From your host editor agent: ask for a 15s social short and the"
echo "     social-short-15s pipeline will run end-to-end on local GPU."
echo ""
echo "  After editing plugin files later, pull changes with:"
echo "       claude plugin marketplace update video-producer"
echo "       claude plugin update video-producer"
echo ""
