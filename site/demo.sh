#!/usr/bin/env bash
# lofi-ascii — scripted terminal demo.
#
# Records a clean, paced walkthrough of the headline features. Use it two ways:
#
#   1) Just watch it:        bash site/demo.sh
#   2) Record a cast/GIF:    asciinema rec demo.cast -c "bash site/demo.sh"
#                            agg demo.cast demo.gif         # asciinema's GIF generator
#      (or)                  vhs site/demo.tape             # see the .tape below
#
# Keep the terminal at ~120 cols x ~32 rows for the cleanest framing.

set -uo pipefail
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BIN="$SCRIPT_DIR/../bin/lofi-ascii"
PROMPT="\033[38;5;208m$\033[0m"   # burnt-orange prompt
DIM="\033[2m"; RST="\033[0m"

type_cmd() {            # simulate typing a command
  printf "$PROMPT "
  local s="$1"
  for ((i=0; i<${#s}; i++)); do printf "%s" "${s:$i:1}"; sleep 0.012; done
  printf "\n"
  sleep 0.4
}

beat() { sleep "${1:-1.1}"; }
clear

echo
printf "${DIM}  lofi-ascii — turn any webpage into ASCII you can actually read${RST}\n\n"
beat 0.8

# 1. The headline move: a real site, text-aware.
type_cmd "lofi-ascii url stripe.com --width=120"
"$BIN" url https://stripe.com --width=120 --no-save 2>/dev/null | head -30
beat 1.6

# 2. Components — instant, no network.
clear
type_cmd "lofi-ascii components signup-form"
"$BIN" components signup-form 2>/dev/null
beat 1.6

# 3. Compare two products.
clear
type_cmd "lofi-ascii compare stripe.com square.com --width=46"
"$BIN" compare https://stripe.com https://square.com --width=46 --no-save 2>/dev/null | head -22
beat 1.6

clear
printf "\n  ${DIM}npx lofi-ascii url <your-site>  ·  github.com/KishParikh13/lofi-ascii${RST}\n\n"
beat 1.2
