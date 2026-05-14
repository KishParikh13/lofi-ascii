# lofi-ascii to-png — render ASCII text → PNG image via headless Chrome.
# Args: ascii_input_path out_png_path [font_size] [theme]
# ascii_input_path: file with the ASCII text (or "-" for stdin)
# theme: light (default, white bg + black text) or dark (black bg + green text)

ascii_to_png() {
  local input="$1"
  local out="$2"
  local font_size="${3:-14}"
  local theme="${4:-light}"

  local ascii=""
  if [[ "$input" == "-" ]]; then
    ascii=$(cat)
  elif [[ -f "$input" ]]; then
    ascii=$(cat "$input")
  else
    echo "to-png: file not found: $input" >&2
    return 1
  fi

  # Strip the lofi-ascii header lines if present
  ascii=$(printf '%s\n' "$ascii" | awk 'BEGIN{skip=1} /^# / && skip {next} /^$/ && skip {skip=0; next} {print}')

  # HTML-escape
  local escaped
  escaped=$(printf '%s' "$ascii" | python3 -c "import sys, html; sys.stdout.write(html.escape(sys.stdin.read()))")

  local bg fg
  if [[ "$theme" == "dark" ]]; then
    bg="#0e1014"; fg="#a8ffb1"
  else
    bg="#fbfaf7"; fg="#1a1a1a"
  fi

  local html
  html=$(mktemp -t lofi-png-html.XXXXXX).html
  cat > "$html" <<EOF
<!doctype html><html><head><meta charset="utf-8"><style>
  html, body { margin: 0; padding: 0; background: ${bg}; width: max-content; }
  body { padding: 20px; display: inline-block; }
  pre {
    margin: 0;
    font-family: "Menlo", "SF Mono", "JetBrains Mono", "Consolas", monospace;
    font-size: ${font_size}px;
    line-height: 1.0;
    letter-spacing: 0;
    color: ${fg};
    white-space: pre;
    font-feature-settings: "liga" 0, "calt" 0;
    font-variant-ligatures: none;
  }
</style></head><body><pre>${escaped}</pre></body></html>
EOF

  local chrome=""
  if [[ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then
    chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  elif command -v chromium >/dev/null 2>&1; then
    chrome="$(command -v chromium)"
  else
    echo "to-png: Chrome not found." >&2
    rm -f "$html"
    return 1
  fi

  # Calculate roughly-needed canvas. Menlo at 14px: ~8.4px/char width, ~14px line.
  # Count CHARACTERS, not bytes (UTF-8 block chars are 3 bytes each).
  local rows cols
  rows=$(printf '%s' "$ascii" | python3 -c "import sys; print(sum(1 for _ in sys.stdin))")
  cols=$(printf '%s' "$ascii" | python3 -c "import sys; print(max((len(l.rstrip('\n')) for l in sys.stdin), default=0))")
  local h=$(( rows * font_size + 60 ))
  local w=$(( cols * font_size * 62 / 100 + 60 ))
  (( w < 400 )) && w=400
  (( h < 200 )) && h=200

  "$chrome" \
    --headless=new \
    --disable-gpu \
    --hide-scrollbars \
    --no-sandbox \
    --force-device-scale-factor=2 \
    --window-size="${w},${h}" \
    --virtual-time-budget=600 \
    --screenshot="$out" \
    "file://$html" >/dev/null 2>&1

  rm -f "$html"

  if [[ ! -f "$out" || ! -s "$out" ]]; then
    echo "to-png: failed to generate $out" >&2
    return 1
  fi

  echo "$out"
}
