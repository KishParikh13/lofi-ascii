# lofi-ascii — Distribution Plan

Positioning: **"The Asciinator for design engineers."**
A tiny CLI + Claude skill that turns webpages and images into *readable* ASCII —
headlines stay text, buttons stay buttons, only photos become art. Paste it into a
PR, a Linear ticket, a Claude chat, or a code comment.

The double-barrel angle is the wedge: it's a useful standalone CLI **and** a Claude
skill. Lead with the CLI on dev channels; lead with the skill on AI/Claude channels.

---

## 0. Pre-launch checklist (do this first)

- [ ] `npm publish` is done and `npx lofi-ascii url stripe.com` works from a clean machine.
- [ ] GitHub repo has: the social preview set (`assets/social-preview.png` via Settings → Social preview), topics (`ascii-art`, `cli`, `design`, `claude-skill`, `wireframe`), and the README rendering correctly.
- [ ] A demo GIF exists at `assets/demo.gif` (run `vhs site/demo.tape`) and is embedded at the top of the README.
- [ ] Tag + GitHub Release `v0.1.0` published with notes.
- [ ] You have ~2 free hours on launch day to reply to comments fast (first hour is everything on HN/Reddit).

---

## 1. Show HN

**Best day/time:** Tue–Thu, 8–10am ET. Avoid weekends and Fri.

**Title** (paste exactly):

```
Show HN: lofi-ascii – turn any webpage into ASCII you can actually read
```

**URL:** the GitHub repo (`https://github.com/KishParikh13/lofi-ascii`).

**First comment** (post immediately as the author — this is where the story goes):

```
I'm a design engineer and I kept wanting to drop a quick "here's the layout"
into PRs, Linear tickets, and Claude chats without attaching a screenshot.
Screenshots don't render in a code comment, don't diff, and get stale.

So I built lofi-ascii. One command turns a whole page into ASCII:

  npx lofi-ascii url stripe.com --width=120

The trick is it's NOT a brightness ramp. Naive image→ASCII turns a dark hero
into a solid █ blob. lofi-ascii walks the live DOM in headless Chrome: real
text stays as text, buttons render as boxes, nav stays legible — and only the
image regions get rendered, per-tile and edge-aware, so a black phone, a white
phone, and a pink phone on the same page each keep their shape.

It's also a Claude Code skill, so you can just say "make an ASCII wireframe of
stripe.com" and it picks the right mode.

Modes: url (text-aware), url-image (whole screenshot, dependency-free renderer),
render (local images), compare (A/B), to-png (back to an image for Figma).

It's MIT, runs on macOS/Linux, Node 18+. Would love feedback on the renderer —
the per-tile normalization is the part I'm proudest of and most unsure about.
```

**Reply-fast playbook:** answer every "how is this different from chafa / jp2a /
ascii-image-converter?" with the *text-aware DOM* angle — that's the genuine
differentiator. Have the GIF link ready.

---

## 2. Reddit — r/commandline

**Title:**

```
lofi-ascii: turn a webpage into readable ASCII (text stays text, only images become art)
```

**Body:**

```
Made a small CLI for turning webpages and images into ASCII you can paste into
PRs, tickets, and chats. The webpage mode is text-aware — it walks the DOM so
headlines and buttons stay readable instead of melting into a brightness blob.

  npx lofi-ascii url stripe.com --width=120

Modes: url, url-image, render (local files), compare (A/B), to-png. MIT, Node 18+,
macOS/Linux. Repo + GIF in the comments. Feedback welcome, especially on the
renderer.
```

Follow community rules: put the link in a comment if the sub discourages link
posts, and engage genuinely. Cross-post candidates (read each sub's rules first):
**r/webdev**, **r/web_design**, **r/ClaudeAI** (lead with the skill angle there),
**r/programming** (only if it gets real traction elsewhere first).

---

## 3. X / Twitter thread

**Tweet 1 (hook + GIF):**

```
turn any webpage into ASCII you can actually read 👇

one command. headlines stay text, buttons stay buttons,
only the photos become art.

npx lofi-ascii url stripe.com

[attach demo.gif]
```

**Tweet 2 (the why):**

```
most image→ascii tools turn a dark hero into a solid █ blob.

lofi-ascii walks the live DOM in headless chrome — real copy stays as
characters, image regions get rendered per-tile + edge-aware so each
subject keeps its shape. it's a wireframe, not a brightness ramp.
```

**Tweet 3 (the skill angle):**

```
it's also a Claude Code skill. just say:

"make an ascii wireframe of stripe.com"
"convert this figma export to lofi ascii"

and Claude picks the right mode + pastes it inline.
```

**Tweet 4 (modes / breadth):**

```
modes:
• url        webpage → text-aware ascii
• url-image  screenshot → native ascii (no deps)
• render     any image → ascii
• compare    two sites side by side
• to-png     ascii back to a PNG for figma/docs
```

**Tweet 5 (CTA):**

```
MIT, node 18+, macOS/linux.

npm i -g lofi-ascii
github.com/KishParikh13/lofi-ascii

would love feedback 🙏
```

Tag/notify accounts that amplify dev-tools + design-eng: pick 3–5 you actually
follow rather than spamming. Quote-tweet with a fresh example a day later to ride
the algorithm a second time.

---

## 4. Dev newsletters & aggregators

Submit once the repo has a few stars + the GIF:

- **Console.dev** — "beta tools" submission form. Strong fit (CLI + dev-tool).
- **TLDR Newsletter** (tldr.tech) — has a "tools" submission; pitch the one-liner.
- **Node Weekly / JavaScript Weekly** (cooperpress) — submit via their links page; npm-installable Node CLI qualifies.
- **Terminal Trove** — curates terminal tools; great audience match, submit via their site.
- **awesome-cli-apps** / **awesome-ascii-art** GitHub lists — open a PR adding lofi-ascii.
- **Hacker Newsletter** — picks up HN traction automatically if the Show HN does well.
- **Bytes.dev** — JS newsletter, casual tone; mention the Claude-skill angle.

Pitch template (one paragraph):

```
lofi-ascii is a tiny CLI (and Claude skill) that turns webpages and images into
readable ASCII — text stays text, only photos become art. `npx lofi-ascii url
stripe.com`. MIT, Node 18+. Repo: github.com/KishParikh13/lofi-ascii
```

---

## 5. Claude-skill distribution (the second front)

This is a real, under-served channel — lean into it.

- **Anthropic / Claude communities:** r/ClaudeAI, the Claude Developers Discord,
  and any "awesome-claude-skills" lists on GitHub. Lead with: *"a skill that turns
  any URL or image into an ASCII wireframe inline — install once, then just ask."*
- **Make the skill trivially installable:** the README should have a copy-paste
  block that clones + runs `scripts/install.sh` (which symlinks into
  `~/.claude/skills/`). Consider a one-liner install in the launch post.
- **Demo content:** a 20-second screen recording of Claude Code taking
  *"make an ASCII wireframe of stripe.com"* → output. Post on X and in the Discord.
- **Cross-link:** the npm page and GitHub README both call out the skill; the
  skill's SKILL.md / launch posts both call out `npx`. Each channel feeds the other.

---

## 6. Launch-day checklist

**T-minus 1 day**
- [ ] `npm publish` (see REVIEW.md for the exact command).
- [ ] Tag `v0.1.0`, push tag, cut GitHub Release.
- [ ] Set the GitHub social preview image (`assets/social-preview.png`).
- [ ] Add GIF to the top of the README; confirm it autoplays on GitHub.
- [ ] Verify `npx lofi-ascii url stripe.com` on a machine that has never seen the repo.

**Launch morning (Tue–Thu, ~8am ET)**
- [ ] Post Show HN. Immediately post the author first-comment.
- [ ] Post the X thread; pin tweet 1.
- [ ] Post to r/commandline.
- [ ] Drop in r/ClaudeAI with the skill framing.
- [ ] Stay on comments for the first 2 hours — reply fast, ship tiny fixes live if asked.

**Same day / next day**
- [ ] Submit to Console.dev, Terminal Trove, TLDR tools.
- [ ] Open PRs to awesome-cli-apps + awesome-ascii-art.
- [ ] Quote-tweet a fresh example to get a second algorithmic push.

**Week 1**
- [ ] Triage issues; cut a `v0.1.1` if anything real surfaces.
- [ ] Note which channel converted best for the next launch (a v0.2 feature).

---

## 7. Headline / one-liners (reuse anywhere)

- **Primary:** "Turn any webpage into ASCII you can actually read."
- **Positioning:** "The Asciinator for design engineers."
- **Technical hook:** "A wireframe, not a brightness ramp — text stays text, only photos become art."
- **Skill hook:** "It's also a Claude skill: just ask, and it pastes the wireframe inline."
