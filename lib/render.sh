# lofi-ascii render — call chafa with style preset + size.
# Args: image_path style width extra_flags
# Prints ASCII to stdout.

render_image() {
  local image="$1"
  local style="$2"
  local width="$3"
  local extra="${4:-}"
  local theme="${5:-light}"

  if ! command -v chafa >/dev/null 2>&1; then
    echo "render: chafa not installed. Run: brew install chafa" >&2
    return 1
  fi

  if [[ ! -f "$image" ]]; then
    echo "render: file not found: $image" >&2
    return 1
  fi

  if (( width < 10 )); then width=10; fi
  if (( width > 240 )); then width=240; fi

  local flags
  flags=$(style_flags "$style" "$theme") || return 1

  # chafa --size W = auto height. --format symbols = text-only (unless color is on).
  # --animate off prevents GIF playback. --polite on forces output even for non-tty.
  # shellcheck disable=SC2086
  chafa $flags --size "${width}" --format symbols --animate off --polite on $extra "$image"
}
