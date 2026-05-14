# lofi-ascii screenshot — capture URL → PNG via headless Chrome.
# Args: url out_path viewport full_page_flag wait_ms
# Tries Chrome → npx playwright → fail with install hint.

take_screenshot() {
  local url="$1"
  local out="$2"
  local viewport="${3:-1280x800}"
  local full_page="${4:-0}"
  local wait_ms="${5:-1500}"

  local w="${viewport%x*}"
  local h="${viewport#*x}"

  # Validate URL has scheme; auto-prefix https if not.
  if [[ "$url" != http://* && "$url" != https://* ]]; then
    url="https://$url"
  fi

  local chrome=""
  if [[ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then
    chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  elif command -v chromium >/dev/null 2>&1; then
    chrome="$(command -v chromium)"
  elif command -v google-chrome >/dev/null 2>&1; then
    chrome="$(command -v google-chrome)"
  fi

  if [[ -n "$chrome" ]]; then
    _screenshot_chrome "$chrome" "$url" "$out" "$w" "$h" "$full_page" "$wait_ms"
    return $?
  fi

  if command -v npx >/dev/null 2>&1; then
    _screenshot_playwright "$url" "$out" "$w" "$h" "$full_page" "$wait_ms"
    return $?
  fi

  echo "screenshot: no headless browser available." >&2
  echo "  Install Chrome (https://www.google.com/chrome/) or Node + Playwright." >&2
  return 1
}

_screenshot_chrome() {
  local chrome="$1" url="$2" out="$3" w="$4" h="$5" full_page="$6" wait_ms="$7"

  # Chrome's --virtual-time-budget controls how long to "wait" in headless mode.
  # --hide-scrollbars cleans up the right edge.
  local args=(
    --headless=new
    --disable-gpu
    --hide-scrollbars
    --no-sandbox
    --force-device-scale-factor=1
    --window-size="${w},${h}"
    --virtual-time-budget="$wait_ms"
    --screenshot="$out"
  )

  if [[ "$full_page" == "1" ]]; then
    # Chrome doesn't have a single flag for full-page in headless=new.
    # Workaround: use a generous height and let the page render.
    args=(
      --headless=new
      --disable-gpu
      --hide-scrollbars
      --no-sandbox
      --force-device-scale-factor=1
      --window-size="${w},4000"
      --virtual-time-budget="$wait_ms"
      --screenshot="$out"
    )
  fi

  "$chrome" "${args[@]}" "$url" >/dev/null 2>&1 || {
    echo "screenshot: Chrome failed to capture $url" >&2
    return 1
  }

  if [[ ! -f "$out" || ! -s "$out" ]]; then
    echo "screenshot: output file is empty/missing: $out" >&2
    return 1
  fi
}

_screenshot_playwright() {
  local url="$1" out="$2" w="$3" h="$4" full_page="$5" wait_ms="$6"
  local fp_flag=""
  [[ "$full_page" == "1" ]] && fp_flag="--full-page"

  npx -y playwright@latest screenshot \
    --viewport-size="${w},${h}" \
    --wait-for-timeout="$wait_ms" \
    $fp_flag \
    "$url" "$out" 2>&1 || {
    echo "screenshot: Playwright failed. Try: npx playwright install chromium" >&2
    return 1
  }
}
