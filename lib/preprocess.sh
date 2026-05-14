# lofi-ascii preprocess — pre-process an image before passing to chafa.
# Useful when source has subtle/light UI elements that vanish in plain chafa.
# Args: input_path mode [threshold]
# Modes: threshold | contrast | edges
# Emits a path to a processed PNG on stdout.

preprocess_image() {
  local input="$1"
  local mode="${2:-none}"
  local threshold="${3:-235}"

  if [[ "$mode" == "none" || -z "$mode" ]]; then
    echo "$input"
    return 0
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    echo "$input"   # graceful fallback
    return 0
  fi

  local out
  out=$(mktemp -t lofi-pp.XXXXXX).png

  python3 - "$input" "$out" "$mode" "$threshold" <<'PY' || { echo "$input"; return 0; }
import sys
try:
    from PIL import Image, ImageOps, ImageFilter, ImageEnhance
except ImportError:
    # PIL not available — copy input as-is
    import shutil
    shutil.copyfile(sys.argv[1], sys.argv[2])
    sys.exit(0)

inp, out, mode, threshold = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
img = Image.open(inp).convert("L")

if mode == "threshold":
    # Binarize: anything below threshold → black, else white.
    # Best for clean UI screenshots; preserves both dark text and light UI edges.
    img = img.point(lambda p: 0 if p < threshold else 255, "L")
elif mode == "contrast":
    # Aggressive contrast bump. Preserves grayscale but pushes edges hard.
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Contrast(img).enhance(2.0)
elif mode == "edges":
    # Edge detection. Best for line-art / outline-style renderings.
    img = img.filter(ImageFilter.FIND_EDGES)
    img = ImageOps.invert(img)   # edges become dark on white bg
else:
    pass

img.save(out)
PY

  if [[ -f "$out" && -s "$out" ]]; then
    echo "$out"
  else
    echo "$input"
  fi
}
