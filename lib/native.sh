# lofi-ascii native renderer — dependency-free PNG -> ASCII.
# Args: image_path style width theme charset density height_scale brightness contrast gamma pixelate sample_mode detail_weight

render_image_native() {
  local image="$1"
  local style="${2:-standard}"
  local width="${3:-120}"
  local theme="${4:-light}"
  local charset="${5:-}"
  local density="${6:-1.0}"
  local height_scale="${7:-1.0}"
  local brightness="${8:-8}"
  local contrast="${9:-22}"
  local gamma="${10:-1.0}"
  local pixelate="${11:-0}"
  local sample_mode="${12:-detail}"
  local detail_weight="${13:-0.2}"

  if [[ ! -f "$image" ]]; then
    echo "native-render: file not found: $image" >&2
    return 1
  fi

  local invert_flag=""
  [[ "$theme" == "dark" ]] && invert_flag="--invert"

  local cmd=(
    python3 "$LIB_DIR/native_render.py" "$image"
    --style="$style"
    --width="$width"
    --density-bias="$density"
    --height-scale="$height_scale"
    --brightness="$brightness"
    --contrast="$contrast"
    --gamma="$gamma"
    --pixelate="$pixelate"
    --sample-mode="$sample_mode"
    --detail-weight="$detail_weight"
  )
  if [[ -n "$charset" ]]; then
    cmd+=(--charset "$charset")
  fi
  if [[ -n "$invert_flag" ]]; then
    cmd+=("$invert_flag")
  fi

  "${cmd[@]}"
}
