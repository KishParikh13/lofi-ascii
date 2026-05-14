# lofi-ascii gallery — render one input in every style for side-by-side comparison.

gallery_inputs() {
  local input="$1"
  local width="${2:-60}"
  local theme="${3:-light}"

  # Resolve URL → png if needed
  local tmp=""
  local png="$input"
  if [[ "$input" == http://* || "$input" == https://* ]]; then
    tmp=$(mktemp -t lofi-gal.XXXXXX).png
    take_screenshot "$input" "$tmp" "1280x800" 0 1500 || { rm -f "$tmp"; return 1; }
    png="$tmp"
  fi

  for style in blocks sketch lofi braille; do
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  STYLE: $style"
    echo "═══════════════════════════════════════════════════════════════"
    render_image "$png" "$style" "$width" "" "$theme"
  done

  [[ -n "$tmp" ]] && rm -f "$tmp"
}
