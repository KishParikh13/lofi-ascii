---
name: lofi-ascii
description: Use when the user wants to convert an image, screenshot, Figma export, or webpage URL into ASCII art — especially for low-fidelity design wireframes, UI mockups, design notes, README assets, or quick visual references inline in a Claude conversation. Triggers include "ascii", "wireframe", "lofi", "ascii-ify", "ASCII this", "make an ASCII version of...", "convert this design to ASCII", or any phrase combining a URL/image with words like "ascii", "wireframe", "mockup", "sketch".
---

# lofi-ascii

A two-mode skill that turns images, screenshots, and webpages into ASCII art:

- **`render` mode** — fast, deterministic pixel→ASCII via `chafa`. Best for photos, logos, icons, and any time you want a "snapshot" of an image.
- **`wireframe` mode** — *you* (Claude) look at the image and emit a structured, semantically labeled ASCII wireframe. Best for UI screenshots, Figma exports, and design conversations.

The CLI binary lives at `~/Code/lofi-ascii/bin/lofi-ascii` (symlinked into PATH via the install script). All paths in this file assume that location.

## Mode routing

Pick the mode based on what the user is asking for:

| User said... | Use this mode |
|---|---|
| "wireframe", "mockup", "lofi", "ASCII wireframe", "convert this UI" | **wireframe** |
| "ascii-ify", "ASCII art", "convert image to ASCII", "make ASCII of this photo/logo" | **render** |
| Provided a URL with no further direction | **wireframe** (URLs are almost always UI) |
| Provided a photo/illustration with no further direction | **render** |
| Unclear | Default to **wireframe** unless the image is obviously a photo/illustration (no UI structure visible) |

The user can always override: "use render mode" or "no, do a pixel ASCII version".

## Mode: render

Shell out to the `lofi-ascii` CLI. It handles screenshotting (if URL), chafa invocation, file saving, and inline output.

```bash
# Local image
lofi-ascii render /path/to/image.png --style=blocks --width=80

# URL (auto-screenshots first)
lofi-ascii url https://example.com --style=blocks --width=80

# Different styles for different vibes
lofi-ascii render image.png --style=braille --width=60    # max density, great for UI
lofi-ascii render image.png --style=lofi    --width=60    # pure 7-bit ASCII
lofi-ascii render image.png --style=sketch  --width=80    # high-contrast outline
lofi-ascii render image.png --style=photo   --width=80    # color, terminal-only

# Mobile or desktop viewport for URLs
lofi-ascii url https://example.com --mobile --style=blocks
lofi-ascii url https://example.com --desktop --full-page --style=blocks

# Suppress file save (chat-only)
lofi-ascii render image.png --no-save
```

Captures ASCII on stdout (relay to the user, wrapped in a triple-backtick code block so spacing is preserved). The "Saved → path" message is on stderr — surface that path to the user.

**Default style is `blocks`** (Unicode block + box-drawing characters, monochrome, light-theme — renders correctly in markdown, GitHub, and Claude's chat UI). Don't change defaults without reason.

## Mode: wireframe

This is *you* (Claude) producing the ASCII directly using your vision capability.

**Process:**
1. If the user gave a URL, first run `lofi-ascii screenshot <url> --out=/tmp/lofi-XXX.png` (use `--mobile` or `--desktop` based on context — desktop default), then `Read` the screenshot file to see it.
2. If the user gave a local image path, `Read` it directly.
3. Look at the image and produce an ASCII wireframe following the rules below.
4. Save the wireframe via: `lofi-ascii render` is NOT used here — you write the file yourself with `Write`, named `./wireframe-<short-slug>-<YYYYMMDD-HHMMSS>.txt`. The file should include the same header format as the render mode output (see "File header format" below).
5. Output the wireframe inline in your chat reply, wrapped in a triple-backtick fenced code block (no language tag — preserves spacing).

### Wireframe rules

**Character set — use ONLY these:**
- Borders / containers: `─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼`
- Heavy borders (for emphasis / hero / selected): `━ ┃ ┏ ┓ ┗ ┛ ┣ ┫ ┳ ┻ ╋`
- Fills (images, video, gradient backgrounds): `░ ▒ ▓ █`
- Dividers / faint lines: `┄ ┅ ╌ ╍ ┈ ┉`
- Spacers: regular space ` `
- Text labels: standard letters/numbers, plus brackets `[ ]` for buttons/inputs/badges, parens `( )` for radio/help text, `▢` `▣` `◯` `●` for checkboxes/radio dots, `…` for placeholder text
- Arrows / chevrons: `← → ↑ ↓ ▾ ▸ ⌃ ⌄`

**Do NOT use:** emojis, slashes/backslashes for borders (`\` `/`), pipe character `|` (use `│`), hyphen `-` (use `─`), plus `+` (use `┼` or `+` inside button labels is OK), asterisks, hash signs.

**Layout rules:**
- Width: default 80 chars. Use 60 for mobile-style. Cap at 100 for desktop-style. Never exceed 120.
- Aspect: terminal cells are ~2:1 tall. Don't preserve pixel aspect — preserve UI semantic proportions (a nav is short, a hero is tall-ish, a sidebar is narrow-ish).
- Preserve relative proportions: if the hero takes 50% of the page height, give it ~50% of your wireframe rows.
- Group with whitespace and lines. Empty rows ARE allowed for breathing room.
- Label every non-trivial region with a short bracketed title: `[ Logo ]`, `[ Hero image ]`, `[ Sign up ]`, `[ Search… ]`, `[ Card 1 ]`, `[ Nav ]`. Keep labels SHORT — 1-3 words.
- For repeated elements (card grid, list rows), draw 2-3 examples then use `…` to show repetition.
- For placeholder body text, use lorem-style: `▔▔▔▔▔ ▔▔▔ ▔▔▔▔▔▔▔ ▔▔▔` or just `(body text)` or dashes inside.
- Buttons: `[  Primary  ]` (heavy padding inside) or `┌──────────┐` `│ Primary  │` `└──────────┘` (boxed). Match heaviness to emphasis.
- Form fields: `┌──────────────────┐` `│ Search…          │` `└──────────────────┘` or `[ Search… ]`

**Composition order:**
1. Header / nav row at the top
2. Main hero or primary content
3. Secondary sections
4. Footer at the bottom

**Output format:**
- Pure ASCII inside a ```` ``` ```` fenced block (no language tag).
- Nothing before the block in your reply except a one-line summary like "Wireframe of stripe.com:" — no analysis, no description, no markdown bullets explaining what's in it. The wireframe IS the analysis.
- After the block, ONE line with the saved file path: `Saved → ./wireframe-stripe-20260514-054437.txt`

### Wireframe examples

Read these reference outputs before producing wireframes — they're the template Claude should model on:

- `~/Code/lofi-ascii/examples/wireframe-landing-page.txt` — generic SaaS landing page
- `~/Code/lofi-ascii/examples/wireframe-dashboard.txt` — admin dashboard
- `~/Code/lofi-ascii/examples/wireframe-mobile-feed.txt` — mobile social feed
- `~/Code/lofi-ascii/examples/wireframe-checkout.txt` — e-commerce checkout flow
- `~/Code/lofi-ascii/examples/wireframe-blog.txt` — blog index + post

## File header format

When you save a wireframe file yourself (wireframe mode), prepend this header:

```
# lofi-ascii (wireframe mode)
# source: <url-or-path>
# style:  wireframe
# date:   <ISO timestamp>

<your wireframe>
```

The render mode CLI already writes this header.

## When the user wants comparisons

Use the built-in `compare` subcommand — it handles URL screenshotting, alignment, and side-by-side/stacked rendering:

```bash
lofi-ascii compare https://stripe.com https://square.com --width=50           # side-by-side
lofi-ascii compare before.png after.png --width=60 --stack                    # stacked
```

For seeing every style of one input at once (good when the user is unsure which style they want):

```bash
lofi-ascii gallery https://stripe.com --width=60
```

## When the user wants the wireframe as an image

Run `lofi-ascii to-png` on the saved `.txt` file to produce a PNG that can be dropped into Figma, design docs, or any non-text destination. The wireframe examples (`examples/wireframe-*.txt`) all render beautifully as PNGs at `--font-size=14`.

```bash
lofi-ascii to-png wireframe.txt --out=wireframe.png --font-size=14
# or larger:
lofi-ascii to-png wireframe.txt --out=wireframe.png --font-size=20
```

## Component library quick-print

If the user describes a UI without giving a source image ("design me a sign-up page wireframe"), assemble from the component library instead of generating from scratch:

```bash
lofi-ascii components                    # list all
lofi-ascii components signup-form        # print one
```

Stitch the components together in your response and adapt as needed. Available components: `navbar`, `hero`, `feature-grid`, `pricing-table`, `cta-banner`, `footer`, `signup-form`, `card`, `data-table`, `modal`, `mobile-nav`, `notifications`, `form-fields`.

## Dependencies

Run `lofi-ascii doctor` first if any operation fails — it reports missing deps. Required: `chafa` (brew), Chrome or Chromium (for URL mode).

## Failure modes

- **`chafa not found`** → run `brew install chafa`.
- **Screenshot fails** → ensure Chrome is installed at `/Applications/Google Chrome.app` or run `npx playwright install chromium`.
- **Page rendered as solid blocks** → the image is too dark or you're missing `--invert` (already in default styles for light theme; use `--dark` if outputting to a dark terminal).
- **Output too wide for chat** → use `--width=60` or `--style=lofi`.
- **Output too sparse** → try `--style=braille` for max density, or increase width.

## Component template library

The repo ships with a library of pre-built ASCII UI components at `~/Code/lofi-ascii/components/`. Use these as building blocks when designing from a description (no image):

- `navbar.txt`, `hero.txt`, `feature-grid.txt`, `pricing-table.txt`, `cta-banner.txt`, `footer.txt`
- `signup-form.txt`, `login-form.txt`, `settings-page.txt`
- `card.txt`, `card-grid.txt`, `list-row.txt`, `data-table.txt`
- `modal.txt`, `dropdown.txt`, `toast.txt`, `breadcrumb.txt`
- `mobile-nav.txt`, `bottom-sheet.txt`, `tab-bar.txt`

Cat the relevant ones and stitch them into a layout when the user asks for "a sign-up page wireframe" or similar with no source image.
