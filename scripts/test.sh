#!/usr/bin/env bash
# lofi-ascii smoke tests — offline, fast. No network or Chrome required.
# Run: npm test   (or: bash scripts/test.sh)

set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
BIN="$REPO_DIR/bin/lofi-ascii"

pass=0
fail=0

check() {
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "  ✓ $name"
    pass=$((pass + 1))
  else
    echo "  ✗ $name"
    fail=$((fail + 1))
  fi
}

check_contains() {
  local name="$1" needle="$2"; shift 2
  local out
  out="$("$@" 2>&1)"
  if printf '%s' "$out" | grep -qF "$needle"; then
    echo "  ✓ $name"
    pass=$((pass + 1))
  else
    echo "  ✗ $name (expected to contain: $needle)"
    fail=$((fail + 1))
  fi
}

echo "lofi-ascii smoke tests"
echo "──────────────────────"

# Version / help
check_contains "version flag"        "lofi-ascii" "$BIN" --version
check_contains "help text"           "USAGE"      "$BIN" --help
check_contains "no-args shows usage" "USAGE"      "$BIN"

# Components
check          "components list"     "$BIN" components
check_contains "components print"    "Pricing"    "$BIN" components pricing-table
check          "missing component errors" bash -c "! '$BIN' components does-not-exist"

# Error handling
check          "unknown subcommand errors" bash -c "! '$BIN' frobnicate"
check          "unknown option errors"     bash -c "! '$BIN' render x.png --bogus"
check          "non-numeric width errors"  bash -c "! '$BIN' render x.png --width=abc"
check          "missing file errors"       bash -c "! '$BIN' render /no/such/file.png"

# render (needs chafa + Pillow). Generate a fixture on the fly.
FIXTURE="$REPO_DIR/test-fixtures/sample.png"
if command -v python3 >/dev/null 2>&1 && python3 -c "import PIL" 2>/dev/null; then
  python3 - "$FIXTURE" <<'PY' 2>/dev/null
import sys
from PIL import Image, ImageDraw
img = Image.new("RGB", (400, 240), "white")
d = ImageDraw.Draw(img)
d.rectangle([20, 20, 380, 60], outline="black", width=3)
d.rectangle([20, 90, 180, 220], fill="black")
d.ellipse([250, 160, 330, 220], fill="black")
img.save(sys.argv[1])
PY
fi

if command -v chafa >/dev/null 2>&1 && [[ -f "$FIXTURE" ]]; then
  check "render image (chafa)" "$BIN" render "$FIXTURE" --width=40 --no-save
else
  echo "  ⊘ render image (chafa) — skipped (chafa or fixture unavailable)"
fi

# native renderer (no chafa needed, just python3)
if command -v python3 >/dev/null 2>&1 && [[ -f "$FIXTURE" ]]; then
  check "to-png round-trip" bash -c "'$BIN' to-png '$REPO_DIR/examples/wireframe-blog.txt' --out=/tmp/lofi-test-$$.png && test -s /tmp/lofi-test-$$.png && rm -f /tmp/lofi-test-$$.png"
else
  echo "  ⊘ to-png round-trip — skipped (python3 unavailable)"
fi

echo ""
echo "  $pass passed, $fail failed"
[[ $fail -eq 0 ]]
