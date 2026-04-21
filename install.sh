#!/usr/bin/env bash
# ----------------------------------------------------------------------
#  NoirsBoxes Video Producer — one-shot dependency installer
#
#  Usage: bash install.sh
#
#  After this runs cleanly, go to your main agent project and run:
#    /plugin add <absolute-path-to-this-folder>
# ----------------------------------------------------------------------

set -euo pipefail

# --- resolve the directory this script lives in (plugin root) ---
PLUGIN_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PLUGIN_ROOT"

echo "=============================================================="
echo "  NoirsBoxes Video Producer — installing in:"
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
    python -m pip install -q "mcp>=0.9.0" "fal-client" "requests" "python-dotenv" "fastmcp"
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
    cp .env.example .env
    echo "📝 Created .env from .env.example."
    echo ""
    echo "⚠️  EDIT .env AND FILL IN:"
    echo "      RUNWAY_API_KEY       (required — https://dev.runwayml.com/)"
    echo "      ELEVENLABS_API_KEY   (required — https://elevenlabs.io/)"
    echo "      FAL_KEY              (optional — fallback if Runway plan limits)"
    echo ""
else
    echo "✔️  .env already exists — skipping scaffold."
fi

# --- 4. sanity check the brand asset folder ---
BRAND_DIR="$PLUGIN_ROOT/assets/brand/norisboxes/product-image"
if [ -d "$BRAND_DIR" ]; then
    sku_count=$(find "$BRAND_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
    echo "✔️  Found $sku_count SKU folder(s) under assets/brand/norisboxes/product-image/"
else
    echo "⚠️  assets/brand/norisboxes/ not found — you'll need to drop MD-xxx photos here before producing a new SKU."
fi

# --- 5. final instructions ---
echo ""
echo "=============================================================="
echo "✅  DEPENDENCY INSTALL COMPLETE"
echo "=============================================================="
echo ""
echo "Next steps (runs once, then the plugin is available in every Claude Code session):"
echo ""
echo "  1. Edit .env with your real API keys (if not already done)."
echo ""
echo "  2. Register this folder as a local marketplace:"
echo "       claude plugin marketplace add $PLUGIN_ROOT"
echo ""
echo "  3. Install the plugin from the marketplace:"
echo "       claude plugin install noirsboxes-video-producer@video-producer"
echo ""
echo "  4. Verify:"
echo "       claude plugin list"
echo ""
echo "  5. From any project (in a fresh Claude Code session):"
echo "       \"Use the video-production-agent to produce a 30s short for MD-905.\""
echo ""
echo "     …or call the MCP tool directly:"
echo "       mcp__noirsboxes-video-producer__produce_noirsboxes_short(sku='MD-905')"
echo ""
echo "  After editing plugin files later, pull changes with:"
echo "       claude plugin marketplace update video-producer"
echo "       claude plugin update noirsboxes-video-producer"
echo ""
