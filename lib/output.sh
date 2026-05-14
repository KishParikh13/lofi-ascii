# lofi-ascii output — print + save policy.
# Args: ascii_text source_path_or_url style_name out_override no_save_flag

handle_output() {
  local ascii="$1"
  local source="$2"
  local style="$3"
  local out="$4"
  local no_save="${5:-0}"

  # Always print to stdout — Claude reads it from here.
  printf '%s\n' "$ascii"

  if [[ "$no_save" == "1" ]]; then
    return 0
  fi

  local path="$out"
  if [[ -z "$path" ]]; then
    local slug
    slug=$(_slug_from_source "$source")
    local ts
    ts=$(date +%Y%m%d-%H%M%S)
    path="./ascii-${slug}-${style}-${ts}.txt"
  fi

  # Write a clean file with header for context, then the ASCII.
  {
    echo "# lofi-ascii"
    echo "# source: $source"
    echo "# style:  $style"
    echo "# date:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo ""
    printf '%s\n' "$ascii"
  } > "$path"

  # Emit save path on stderr (so stdout stays clean for piping).
  echo "" >&2
  echo "Saved → $path" >&2
}

_slug_from_source() {
  local s="$1"
  # Strip protocol, replace non-alnum with -, lowercase, trim, cap at 40 chars.
  s="${s#http://}"
  s="${s#https://}"
  s=$(basename "$s")
  s="${s%.*}"
  # Replace anything not alnum or dash with dash; collapse runs.
  s=$(echo "$s" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9-]+/-/g; s/-+/-/g; s/^-//; s/-$//')
  s="${s:0:40}"
  [[ -z "$s" ]] && s="output"
  echo "$s"
}
