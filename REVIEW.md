# lofi-ascii — Review & Launch Guide

Branch: **`polish/review-ready`** (not pushed). Everything below is committed there.

---

## TL;DR

- **Does it work?** Yes. All five core paths verified live on this machine: `render`
  (image→ASCII), `url` (text-aware webpage→ASCII), `url-image` (native screenshot
  renderer), `compare`, `to-png`, and `components`. A 12-case smoke test (`npm test`)
  passes.
- **npm-publish ready?** Yes. Added a real root `package.json` with `bin`, `files`
  allowlist, repo/keywords/description. `npm pack --dry-run` produces a clean 1.6MB
  tarball (43 files, no `experiments/`, `node_modules/`, or `.lazyweb/` leakage).
  Verified by packing + installing into a temp project: the global bin works **and**
  the text-aware `url` mode resolves `puppeteer-core` from the published package.
- **Assets:** a polished landing page, a 1280×640 social-preview PNG, and two
  reproducible demo scripts (VHS tape + shell).
- **Distribution:** `DISTRIBUTION.md` has paste-ready Show HN, Reddit, X thread,
  newsletters, the Claude-skill angle, and a launch-day checklist.

---

## What I changed

### Verified & fixed
- Installed `puppeteer-core` and ran every mode against real sites (stripe, example.com,
  github). The text-aware `url` showcase renders exactly as the README promises:
  readable headline, ASCII CTA boxes, gradient as contour.
- **`lib/compare.sh`** — `compare` headers showed the full absolute file path. Now
  shows just the basename for local files (URLs unchanged).

### CLI UX polish (`bin/lofi-ascii`)
- Unknown-option errors now name the option and point to `--help` (was a bare
  "Unknown option").
- Added `--width` validation: rejects non-numeric input with a clear message, and
  clamps to the documented 10–240 range with a heads-up instead of failing weirdly later.
- (Kept the already-staged improvements: `url-image` subcommand, native-renderer
  flags, and a `doctor` that no longer hard-fails when `chafa` is absent since the
  native path doesn't need it.)

### npm packaging (new)
- **`package.json`** (root, new) — name `lofi-ascii`, version `0.1.0`, `bin`,
  `files` allowlist, repository, keywords, description, `engines.node >=18`,
  `os: [darwin, linux]`, and `puppeteer-core` as a dependency so `url` mode works
  on a clean `npm i -g`.
- **`node/package.json`** — cleaned up the placeholder (`"name": "node"`) to a
  private dev marker; root now owns the dependency.
- **`scripts/test.sh`** (new) — offline smoke tests wired to `npm test`.
- **`.gitignore`** — added `node_modules/`, `*.tgz`, and the local-only `experiments/`
  + `.lazyweb/` scratch dirs so they never ship or get committed.

### Marketing assets (new, under `site/` + `assets/`)
- **`site/index.html`** — full landing page. Terminal/paper aesthetic, ASCII as the
  hero, before/after, the dual CLI+skill story, install block. Deliberately not AI slop.
- **`assets/social-preview.png`** — 1280×640 GitHub/OG social card (rendered, committed).
- **`site/social-preview.html`** — source for the card, re-renderable.
- **`site/demo.tape`** — `vhs site/demo.tape` → `assets/demo.gif` (one command).
- **`site/demo.sh`** — runnable/recordable scripted terminal demo.

### Docs
- **`README.md`** — install section now leads with `npx` / `npm i -g`, keeps the
  from-source + skill path.
- **`DISTRIBUTION.md`**, **`REVIEW.md`** — new.

---

## How to run / demo it (60 seconds)

```bash
cd ~/Code/lofi-ascii
git checkout polish/review-ready

npm install                 # installs puppeteer-core at the root
./bin/lofi-ascii doctor     # should be all ✓ (chafa, Chrome, node, python3, Pillow)
npm test                    # 12 passing smoke tests

# the showcase:
./bin/lofi-ascii url https://stripe.com --width=120 --no-save

# other paths:
./bin/lofi-ascii components signup-form
./bin/lofi-ascii compare https://stripe.com https://square.com --width=46 --no-save
./bin/lofi-ascii render assets/examples/stripe-com.png --width=80 --no-save
```

**See the marketing assets:**
```bash
open site/index.html
open assets/social-preview.png
```

**Generate the demo GIF (optional, needs VHS):**
```bash
brew install vhs && vhs site/demo.tape   # writes assets/demo.gif
```

---

## What Kish should review

1. **The landing page** (`open site/index.html`) — is the positioning + aesthetic right?
2. **The social card** (`assets/social-preview.png`) — this becomes the GitHub social
   preview and OG image.
3. **The Show HN copy** in `DISTRIBUTION.md` — title + author first-comment. This is
   the single highest-leverage piece of the launch; tune it to your voice.
4. **package.json metadata** — `author` field is `Kish Parikh (https://github.com/KishParikh13)`;
   confirm the npm name `lofi-ascii` is available (see below) and bump nothing else.
5. **Skill paths** — `SKILL.md` hardcodes `~/Code/lofi-ascii/` for the local-skill
   install. That's correct for the source-install path; fine to leave for v0.1.

---

## Exact launch steps

### 1. Confirm the npm name is free
```bash
npm view lofi-ascii   # should 404 ("not found") — means the name is available
```
If taken, rename in `package.json` (e.g. `@kishparikh/lofi-ascii`) and update README/docs.

### 2. Final local gate
```bash
git checkout polish/review-ready
npm install
npm test                       # must be 12/12
npm pack --dry-run             # eyeball the file list — no experiments/, node_modules/, .lazyweb/
```

### 3. Merge + push (when ready)
```bash
git checkout main
git merge --no-ff polish/review-ready
git push origin main
```

### 4. Publish to npm
```bash
npm login                      # one-time
npm publish --access public    # public scope; drop --access if unscoped name
# verify:
npx lofi-ascii@latest --version
```

### 5. Tag + GitHub Release
```bash
git tag -a v0.1.0 -m "lofi-ascii v0.1.0"
git push origin v0.1.0
gh release create v0.1.0 \
  --title "lofi-ascii v0.1.0" \
  --notes "First public release. Turn webpages and images into readable ASCII — text-aware url mode, native screenshot renderer, render/compare/to-png, component library, and a Claude skill. npm i -g lofi-ascii"
```

### 6. Set the GitHub social preview
GitHub → repo → Settings → General → Social preview → upload `assets/social-preview.png`.
Add repo topics: `ascii-art`, `cli`, `design`, `claude-skill`, `wireframe`, `terminal`.

### 7. Launch
Follow the launch-day checklist in `DISTRIBUTION.md`.

---

## Open items for Kish (none blocking)

- **`assets/demo.gif`** isn't generated (VHS/asciinema not installed here). Run
  `vhs site/demo.tape` once, commit the GIF, and embed it at the top of the README
  before launch — a GIF materially helps the Show HN / X thread.
- **npm name availability** — verify `npm view lofi-ascii` before publishing.
- **Linux note:** screenshot/url modes assume Chrome at the macOS app path or
  `chromium`/`google-chrome` on PATH. Works on Linux if Chrome is on PATH; worth a
  one-line README mention if you expect Linux users.
- The before/after "page" mock in the landing page is a CSS approximation, not a real
  screenshot — fine for a comp, swap in a real one later if you want.
