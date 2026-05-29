# lofi-ascii demo — render a polished GIF with charmbracelet/vhs.
#
#   brew install vhs           # https://github.com/charmbracelet/vhs
#   vhs site/demo.tape         # → writes assets/demo.gif
#
# Run from the repo root so the relative paths resolve.

Output assets/demo.gif

Set FontSize 16
Set Width 1200
Set Height 760
Set Padding 24
Set Theme "Builtin Solarized Dark"
Set TypingSpeed 18ms
Set PlaybackSpeed 1.0

Hide
Type "clear" Enter
Show

Sleep 600ms
Type "lofi-ascii url stripe.com --width=120 --no-save | head -28" Sleep 400ms Enter
Sleep 4s

Type "clear" Enter
Sleep 300ms
Type "lofi-ascii components signup-form" Sleep 400ms Enter
Sleep 3s

Type "clear" Enter
Sleep 300ms
Type "lofi-ascii compare stripe.com square.com --width=46 --no-save | head -20" Sleep 400ms Enter
Sleep 4s
