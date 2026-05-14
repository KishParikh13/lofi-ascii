# lofi-ascii text-aware mode — extract DOM text + image bounding boxes from a
# URL, then composite real text + chafa-rendered image regions into ASCII.

# Args: url out_txt_path viewport width crop_y_start crop_y_end high_contrast theme min_font_size
render_url_text_aware() {
  local url="$1"
  local out_txt="$2"
  local viewport="${3:-1440x1800}"
  local width="${4:-140}"
  local crop_start="${5:-70}"
  local crop_end="${6:-820}"
  local high_contrast="${7:-1}"
  local theme="${8:-light}"
  local min_fs="${9:-14}"
  local wait_ms="${10:-1500}"
  local style="${11:-blocks}"

  local node_dir
  node_dir="$(dirname "$LIB_DIR")/node"
  if [[ ! -f "$node_dir/extract.js" ]]; then
    echo "text-aware: extract.js not found at $node_dir" >&2
    return 1
  fi
  if ! command -v node >/dev/null 2>&1; then
    echo "text-aware: node not found. Falling back to pixel-only mode." >&2
    return 2
  fi

  local tmp_json tmp_png
  tmp_json=$(mktemp -t lofi-ta-json.XXXXXX).json
  tmp_png=$(mktemp -t lofi-ta-png.XXXXXX).png

  # 1. Extract via headless Chrome
  if ! (cd "$node_dir" && node extract.js "$url" "$tmp_png" "$viewport" "$wait_ms" > "$tmp_json" 2>/dev/null); then
    echo "text-aware: extraction failed for $url" >&2
    rm -f "$tmp_json" "$tmp_png"
    return 1
  fi

  # 2. Composite
  local hc_flag=""
  [[ "$high_contrast" == "1" ]] && hc_flag="--high-contrast"
  local crop_flag="--crop=${crop_start}:${crop_end}"

  if ! python3 "$LIB_DIR/composite.py" "$tmp_json" "$tmp_png" "$out_txt" \
       --width="$width" --theme="$theme" --style="$style" \
       --min-font-size="$min_fs" $hc_flag $crop_flag 2>/dev/null; then
    echo "text-aware: composite failed" >&2
    rm -f "$tmp_json" "$tmp_png"
    return 1
  fi

  rm -f "$tmp_json" "$tmp_png"
  return 0
}
