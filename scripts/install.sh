#!/usr/bin/env bash
# lofi-ascii install — idempotent dep check + skill wiring.
# Run from anywhere: bash scripts/install.sh

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "lofi-ascii install"
echo "──────────────────"
echo "Repo: $REPO_DIR"
echo ""

# ── chafa ─────────────────────────────────────────────────────────────────────
if command -v chafa >/dev/null 2>&1; then
  echo "  ✓ chafa: $(chafa --version 2>&1 | head -1)"
else
  echo "  • chafa not found. Installing via homebrew…"
  if ! command -v brew >/dev/null 2>&1; then
    echo "  ✗ Homebrew not installed. Get it: https://brew.sh" >&2
    exit 1
  fi
  brew install chafa
fi

# ── Chrome / headless browser ─────────────────────────────────────────────────
if [[ -d "/Applications/Google Chrome.app" ]]; then
  echo "  ✓ Chrome: $("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --version 2>&1)"
elif command -v chromium >/dev/null 2>&1; then
  echo "  ✓ chromium found"
else
  echo "  ⚠ No Chrome detected. URL/screenshot mode will not work."
  echo "    Install: https://www.google.com/chrome/"
fi

# ── Node deps for text-aware mode ─────────────────────────────────────────────
if command -v npm >/dev/null 2>&1; then
  if [[ ! -d "$REPO_DIR/node/node_modules" ]]; then
    echo "  • installing puppeteer-core for text-aware mode…"
    (cd "$REPO_DIR/node" && npm install --silent 2>&1 | tail -3)
    echo "  ✓ puppeteer-core installed"
  else
    echo "  ✓ puppeteer-core already installed"
  fi
else
  echo "  ⚠ npm not found — text-aware mode will be unavailable."
fi

# ── Python deps for compositor ────────────────────────────────────────────────
if python3 -c "import PIL" 2>/dev/null; then
  echo "  ✓ Pillow (PIL) available"
else
  echo "  • installing Pillow for image processing…"
  python3 -m pip install --quiet pillow 2>&1 | tail -2
fi

# ── PATH wiring ───────────────────────────────────────────────────────────────
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"
if [[ ! -L "$LOCAL_BIN/lofi-ascii" || "$(readlink "$LOCAL_BIN/lofi-ascii")" != "$REPO_DIR/bin/lofi-ascii" ]]; then
  ln -sf "$REPO_DIR/bin/lofi-ascii" "$LOCAL_BIN/lofi-ascii"
  echo "  ✓ Linked $LOCAL_BIN/lofi-ascii → $REPO_DIR/bin/lofi-ascii"
else
  echo "  ✓ $LOCAL_BIN/lofi-ascii already linked"
fi

# Check PATH
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
  echo ""
  echo "  ⚠ $LOCAL_BIN is not in your PATH."
  echo "    Add to ~/.zshrc:  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# ── Claude skill wiring ───────────────────────────────────────────────────────
SKILL_DIR="$HOME/.claude/skills/lofi-ascii"
if [[ -L "$SKILL_DIR" ]]; then
  if [[ "$(readlink "$SKILL_DIR")" == "$REPO_DIR" ]]; then
    echo "  ✓ Claude skill already linked: $SKILL_DIR"
  else
    ln -sfn "$REPO_DIR" "$SKILL_DIR"
    echo "  ✓ Re-linked Claude skill: $SKILL_DIR → $REPO_DIR"
  fi
elif [[ -d "$SKILL_DIR" ]]; then
  echo "  ⚠ $SKILL_DIR exists as a directory (not a symlink). Skipping skill link."
  echo "    Move or delete it first if you want this skill to take over."
else
  mkdir -p "$HOME/.claude/skills"
  ln -sfn "$REPO_DIR" "$SKILL_DIR"
  echo "  ✓ Linked Claude skill: $SKILL_DIR → $REPO_DIR"
fi

echo ""
echo "Done. Try:"
echo "  lofi-ascii doctor"
echo "  lofi-ascii url https://stripe.com --style=blocks --width=80"
echo ""
echo "In Claude Code, the skill is available as: /lofi-ascii or by intent (e.g."
echo "\"convert this image to ASCII\" / \"make an ASCII wireframe of stripe.com\")."
