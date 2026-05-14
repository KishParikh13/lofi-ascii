# lofi-ascii compare — render two inputs side-by-side (or stacked).
# Args: input_a input_b style width orientation out

compare_inputs() {
  local a="$1"
  local b="$2"
  local style="${3:-blocks}"
  local width="${4:-60}"
  local orientation="${5:-side}"   # side | stack
  local out="${6:-}"
  local theme="${7:-light}"

  # Resolve URL → png if needed
  local tmp_a="" tmp_b=""
  local png_a="$a" png_b="$b"

  if [[ "$a" == http://* || "$a" == https://* ]]; then
    tmp_a=$(mktemp -t lofi-cmp-a.XXXXXX).png
    take_screenshot "$a" "$tmp_a" "1280x800" 0 1500 || { rm -f "$tmp_a"; return 1; }
    png_a="$tmp_a"
  fi
  if [[ "$b" == http://* || "$b" == https://* ]]; then
    tmp_b=$(mktemp -t lofi-cmp-b.XXXXXX).png
    take_screenshot "$b" "$tmp_b" "1280x800" 0 1500 || { rm -f "$tmp_b"; return 1; }
    png_b="$tmp_b"
  fi

  local ascii_a ascii_b
  ascii_a=$(render_image "$png_a" "$style" "$width" "" "$theme") || return 1
  ascii_b=$(render_image "$png_b" "$style" "$width" "" "$theme") || return 1

  # Cleanup tmps
  [[ -n "$tmp_a" ]] && rm -f "$tmp_a"
  [[ -n "$tmp_b" ]] && rm -f "$tmp_b"

  local label_a label_b
  label_a=$(_short_label "$a")
  label_b=$(_short_label "$b")

  if [[ "$orientation" == "stack" ]]; then
    printf '═══ %s ═══\n%s\n\n═══ %s ═══\n%s\n' "$label_a" "$ascii_a" "$label_b" "$ascii_b"
  else
    _join_side_by_side "$ascii_a" "$ascii_b" "$label_a" "$label_b" "$width"
  fi
}

_short_label() {
  local s="$1"
  s="${s#http://}"
  s="${s#https://}"
  s="${s%/}"
  echo "${s:0:50}"
}

_join_side_by_side() {
  local left="$1" right="$2" lab_l="$3" lab_r="$4" width="$5"
  local pad=$((width + 4))  # left column total width
  local gap="  │  "

  # Header line
  printf "%-${pad}s%s%-${pad}s\n" "$lab_l" "$gap" "$lab_r"
  printf '%0.s─' $(seq 1 $((pad * 2 + 5)))
  echo ""

  # Use python for proper line-by-line zipping (handles uneven line counts + multibyte)
  python3 - "$left" "$right" "$pad" <<'PY'
import sys
left, right, pad = sys.argv[1], sys.argv[2], int(sys.argv[3])
l_lines = left.split("\n")
r_lines = right.split("\n")
n = max(len(l_lines), len(r_lines))
for i in range(n):
    l = l_lines[i] if i < len(l_lines) else ""
    r = r_lines[i] if i < len(r_lines) else ""
    # pad left visible-width (best effort: each char counts as 1)
    if len(l) < pad:
        l = l + " " * (pad - len(l))
    print(f"{l}  │  {r}")
PY
}
