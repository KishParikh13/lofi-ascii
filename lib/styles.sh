# lofi-ascii style presets — chafa flag bundles per style.
# Each style returns a flag string; --invert toggles foreground/background polarity
# (essential when output will render on a LIGHT background like markdown/Claude chat).

# All styles default to light-bg-friendly output (invert ON).
# Pass theme=dark to flip for terminal viewing.

style_flags() {
  local style="$1"
  local theme="${2:-light}"

  local invert=""
  [[ "$theme" == "light" ]] && invert="--invert"

  case "$style" in
    blocks)
      # Default. Unicode blocks + box-drawing + space. No color.
      # Best balance of fidelity + portability (renders in markdown, terminal, anywhere).
      echo "--symbols block+border+space --colors none --work 9 $invert"
      ;;
    photo)
      # Half-blocks + dithering + 256 color = photo-faithful.
      # Note: emits ANSI escapes — TERMINAL ONLY, not for markdown/files.
      echo "--symbols half --colors 256 --dither bayer --work 9"
      ;;
    lofi)
      # Pure 7-bit ASCII. Narrowest output. Maximally portable.
      echo "--symbols ascii --colors none --work 9 $invert"
      ;;
    braille)
      # Braille dots = max density. Excellent for UI/wireframe captures.
      # Needs braille-capable font (modern terminals + Claude UI both fine).
      echo "--symbols braille --colors none --work 9 $invert"
      ;;
    sketch)
      # Edge-emphasized outline style. Suppresses fills, keeps borders/UI structure.
      # Best for wireframe-like rendering from screenshots.
      echo "--symbols block+border --colors none --threshold 0.3 --work 9 $invert"
      ;;
    *)
      echo "lofi-ascii: unknown style '$style'" >&2
      echo "lofi-ascii: valid styles: blocks, photo, lofi, braille, sketch" >&2
      return 1
      ;;
  esac
}
