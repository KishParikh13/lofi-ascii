#!/usr/bin/env python3
"""
composite.py — text-aware rendering compositor for lofi-ascii.

Reads:
  - JSON: extracted text/buttons/nav/image bounding boxes (from extract.js)
  - PNG:  screenshot from the same Chrome session
Writes:
  - ASCII text where real text comes from the DOM, buttons are drawn as
    ASCII boxes, nav items are laid out as a top text row, and image
    regions are pixel-rendered via PIL brightness-ramp with edge enhance.
"""

import argparse
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageOps, ImageFilter, ImageEnhance
except ImportError:
    print("composite: Pillow required. pip install pillow", file=sys.stderr)
    sys.exit(2)


# Brightness-ramp character sets (5 levels). For "lofi" use ASCII; for
# higher fidelity use Unicode blocks.
RAMP_BLOCKS = " ░▒▓█"
RAMP_ASCII = " .-=#"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("json_path")
    p.add_argument("png_path")
    p.add_argument("out_path")
    p.add_argument("--width", type=int, default=140)
    p.add_argument("--theme", default="light", choices=["light", "dark"])
    p.add_argument("--style", default="blocks")
    p.add_argument("--crop", default=None, help="y_start:y_end pixel range")
    p.add_argument("--high-contrast", action="store_true")
    p.add_argument("--cell-aspect", type=float, default=2.1)
    p.add_argument("--min-font-size", type=float, default=14)
    p.add_argument("--charset", default=None,
                   help="Custom brightness ramp; defaults to ' ░▒▓█'")
    p.add_argument("--ramp-brightness", type=float, default=1.0)
    p.add_argument("--ramp-sharpness", type=float, default=1.5)
    p.add_argument("--no-nav", action="store_true",
                   help="Skip rendering the nav row")
    return p.parse_args()


def _detect_bg_color(img):
    """
    Guess the background color from the most common quantized color in the
    image. More robust than corner-sampling on hero images where the
    "background" actually IS the dominant colour but corners contain page
    chrome (scrollbar shadow, gradient edge, etc.).
    """
    w, h = img.size
    if w < 4 or h < 4:
        return (255, 255, 255)
    # Downscale + quantize to make mode-finding fast and tolerant of noise.
    small = img.resize((max(8, w // 8), max(8, h // 8))).quantize(colors=16).convert("RGB")
    counts = {}
    for px in small.getdata():
        counts[px] = counts.get(px, 0) + 1
    bg = max(counts.items(), key=lambda kv: kv[1])[0]
    return bg


def render_region_brightness_ramp(crop_img, cols, rows, charset, *,
                                  brightness=1.0, sharpness=1.5,
                                  edge_enhance=True, invert_for_light=True):
    """
    Render an image crop as ASCII as a *wireframe-style* product photo.

    Why this is a wireframe and not a pixel-faithful raster:
    - Pixel-faithful rendering of a near-black iPhone on a light page
      collapses to a solid █ blob: every pixel is far from the background
      so every pixel maxes out. You lose the camera bump, the bezel,
      everything that makes the silhouette recognizable.
    - Designers reading ASCII don't need photo accuracy; they need
      *shape + structure*. A mid-tone fill with crisp edges does exactly
      that.

    Algorithm:
    1. Detect background color (mode-of-quantized-pixels).
    2. Foreground mask: 1 where pixel is meaningfully far from bg.
       Handles both polarities (dark fg on light bg, light fg on dark
       bg, colored fg on neutral bg) uniformly.
    3. Edge map (FIND_EDGES), border pixels zeroed (PIL emits a false
       signal at the 1px outer border).
    4. Blend: 50% fg-fill + 50% edges. The fill gives the silhouette,
       the edges carve the structure.
    5. Map to charset. Result: body shows as ▒, bezels/camera/screen
       boundaries as █, transparent bg as space.
    """
    img = crop_img.convert("RGB")

    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if sharpness != 1.0:
        img = ImageEnhance.Sharpness(img).enhance(sharpness)

    img = img.resize((cols, rows))
    rgb_pixels = list(img.getdata())
    bg = _detect_bg_color(img)

    def dist(p):
        dr, dg, db = p[0] - bg[0], p[1] - bg[1], p[2] - bg[2]
        return (dr * dr + dg * dg + db * db) ** 0.5

    raw_dists = [dist(p) for p in rgb_pixels]

    # Global sanity: if even the 95th percentile is tiny, this crop is
    # basically all background (an empty card region). Render as empty.
    sorted_d = sorted(raw_dists)
    global_p95 = sorted_d[int(len(sorted_d) * 0.95)] if sorted_d else 1
    if global_p95 < 16:
        return [" " * cols for _ in range(rows)]

    # Per-tile histogram stretch. Apple.com puts a dark iPhone next to a
    # white iPhone next to a pink iPhone on the same light-gray bg. Global
    # normalization makes the dark phone dominate and the lighter ones
    # disappear. Splitting the image into horizontal tiles and stretching
    # each independently lets every subject use the full character range.
    n_tiles_x = max(1, cols // 14)   # ~14 cols per tile = roughly one phone
    n_tiles_y = max(1, rows // 12)
    tile_w = cols / n_tiles_x
    tile_h = rows / n_tiles_y

    stretched = [0] * len(raw_dists)
    for ty in range(n_tiles_y):
        y0 = int(ty * tile_h)
        y1 = int((ty + 1) * tile_h) if ty < n_tiles_y - 1 else rows
        for tx in range(n_tiles_x):
            x0 = int(tx * tile_w)
            x1 = int((tx + 1) * tile_w) if tx < n_tiles_x - 1 else cols
            tile_vals = []
            for r in range(y0, y1):
                for c in range(x0, x1):
                    tile_vals.append(raw_dists[r * cols + c])
            if not tile_vals:
                continue
            tile_sorted = sorted(tile_vals)
            t_p95 = tile_sorted[int(len(tile_sorted) * 0.95)]
            t_p50 = tile_sorted[len(tile_sorted) // 2]
            # If this tile is mostly bg, don't render anything (avoid
            # amplifying noise).
            if t_p95 < 12:
                continue
            floor = max(6.0, t_p50 * 0.7)
            span = max(8.0, t_p95 - floor)
            for r in range(y0, y1):
                for c in range(x0, x1):
                    i = r * cols + c
                    v = (raw_dists[i] - floor) * 255 / span
                    stretched[i] = max(0, min(255, int(v)))

    # Edge map. Zero out borders (FIND_EDGES boundary artifact).
    if edge_enhance:
        gray_orig = crop_img.convert("L").resize((cols, rows))
        edges = gray_orig.filter(ImageFilter.FIND_EDGES)
        edge_pixels = list(edges.getdata())
        for c in range(cols):
            edge_pixels[c] = 0
            edge_pixels[(rows - 1) * cols + c] = 0
        for r in range(rows):
            edge_pixels[r * cols] = 0
            edge_pixels[r * cols + (cols - 1)] = 0
        max_edge = max(edge_pixels) if edge_pixels else 0
        if max_edge > 0:
            edge_scale = 255.0 / max_edge
            edge_pixels = [min(255, int(e * edge_scale)) for e in edge_pixels]
    else:
        edge_pixels = [0] * len(rgb_pixels)

    # Blend stretched fg signal with edges. The fg gives fill, edges
    # give crisp structure (bezels, screens, camera bumps).
    combined = [
        min(255, int(stretched[i] * 0.55 + edge_pixels[i] * 0.55))
        for i in range(len(rgb_pixels))
    ]

    # Pixel-level noise floor: drop anything below ~10% combined.
    combined = [0 if v < 26 else v for v in combined]

    n = len(charset)
    idx = [min(n - 1, max(0, v * n // 256)) for v in combined]
    rows_out = []
    for r in range(rows):
        line = "".join(charset[idx[r * cols + c]] for c in range(cols))
        rows_out.append(line)
    return rows_out


def main():
    args = parse_args()

    data = json.loads(Path(args.json_path).read_text())
    screenshot = Image.open(args.png_path)
    px_w, px_h = screenshot.size

    y_start, y_end = 0, px_h
    if args.crop:
        parts = args.crop.split(":")
        y_start = int(parts[0]) if parts[0] else 0
        y_end = int(parts[1]) if len(parts) > 1 and parts[1] else px_h
    crop_h = y_end - y_start

    cols = args.width
    px_per_col = px_w / cols
    px_per_row = px_per_col * args.cell_aspect
    rows = max(1, math.ceil(crop_h / px_per_row))

    grid = [[" " for _ in range(cols)] for _ in range(rows)]

    def px_to_grid(x, y):
        c = int(round(x / px_per_col))
        r = int(round((y - y_start) / px_per_row))
        return c, r

    def write_at(r, c, s, *, clear=False):
        if r < 0 or r >= rows:
            return
        if clear:
            # Clear length-of-s columns first
            for i in range(len(s)):
                if 0 <= c + i < cols:
                    grid[r][c + i] = " "
        for i, ch in enumerate(s):
            if 0 <= c + i < cols:
                grid[r][c + i] = ch

    # ── 1. Image regions: render with brightness-ramp ───────────────────────
    pictures = [i for i in data.get("images", []) if i["tag"] in ("picture", "img", "video")]
    # Clip images that overflow the viewport horizontally rather than
    # rejecting them — Stripe's hero gradient is a 1392-wide picture at
    # x=337 (right edge past px_w), but the visible portion is the
    # important part.
    clipped = []
    for p in pictures:
        if p["w"] < 100 or p["h"] < 100:
            continue
        if p["y"] + p["h"] <= y_start or p["y"] >= y_end:
            continue
        x1 = max(0, p["x"])
        x2 = min(px_w, p["x"] + p["w"])
        if x2 - x1 < 100:
            continue
        clipped.append({**p, "x": x1, "w": x2 - x1})
    pictures = clipped
    # Dedupe overlapping (prefer larger)
    used = []
    for p in sorted(pictures, key=lambda r: -(r["w"] * r["h"])):
        keep = True
        for u in used:
            ax1, ay1, ax2, ay2 = p["x"], p["y"], p["x"]+p["w"], p["y"]+p["h"]
            bx1, by1, bx2, by2 = u["x"], u["y"], u["x"]+u["w"], u["y"]+u["h"]
            ix = max(0, min(ax2, bx2) - max(ax1, bx1))
            iy = max(0, min(ay2, by2) - max(ay1, by1))
            if ix * iy > 0.5 * (p["w"] * p["h"]):
                keep = False
                break
        if keep:
            used.append(p)

    charset = args.charset if args.charset else RAMP_BLOCKS

    for img_rect in used:
        ix, iy, iw, ih = img_rect["x"], img_rect["y"], img_rect["w"], img_rect["h"]
        cy1 = max(iy, y_start)
        cy2 = min(iy + ih, y_end)
        if cy2 <= cy1:
            continue
        # Trim 2px in from every edge before cropping. Eliminates 1-2px
        # artifacts that some pages have at picture-rect boundaries
        # (anti-aliasing seams, scrollbar shadows, divider lines, etc.)
        # which otherwise render as a thick frame around the ASCII image.
        edge_pad = 2
        cx1 = int(ix) + edge_pad
        cx2 = int(ix + iw) - edge_pad
        cy1 = int(cy1) + edge_pad
        cy2 = int(cy2) - edge_pad
        if cx2 <= cx1 or cy2 <= cy1:
            continue
        crop = screenshot.crop((cx1, cy1, cx2, cy2))

        sub_cols = max(1, int(round(iw / px_per_col)))
        sub_rows = max(1, int(round((cy2 - cy1) / px_per_row)))

        sub_lines = render_region_brightness_ramp(
            crop, sub_cols, sub_rows, charset,
            brightness=args.ramp_brightness,
            sharpness=args.ramp_sharpness,
            edge_enhance=True,
            invert_for_light=(args.theme == "light"),
        )

        col_start, row_start = px_to_grid(ix, cy1)
        for r_idx, line in enumerate(sub_lines[:sub_rows]):
            gr = row_start + r_idx
            if gr < 0 or gr >= rows:
                continue
            for c_idx, ch in enumerate(line):
                gc = col_start + c_idx
                if gc < 0 or gc >= cols:
                    continue
                if ch != " ":
                    grid[gr][gc] = ch

    # ── 2. Nav row (force-include regardless of font size) ──────────────────
    nav_written = set()
    nav_items = data.get("nav", [])
    if not args.no_nav and nav_items:
        # Drop logo / cart / micro items so the others have breathing room
        nav_items = [
            n for n in nav_items
            if n["text"]
            and len(n["text"]) >= 2
            and not n["text"].isdigit()
            and n["text"].strip() not in ("Apple", "+", "0+")
        ]
        if nav_items:
            # Pick the row from the median y, lay out as a single text row.
            ys = sorted(n["y"] for n in nav_items)
            mid_y = ys[len(ys) // 2]
            _, nav_row = px_to_grid(0, mid_y + 22)
            if 0 <= nav_row < rows:
                # Clear 3 rows: above, nav, below
                for r in (max(0, nav_row - 1), nav_row, min(rows - 1, nav_row + 1)):
                    grid[r] = [" "] * cols
                # Lay out items: if pixel positions cause overlap, fall back
                # to a uniformly-spaced grid centered on the page.
                positions = []
                for n in nav_items:
                    c, _ = px_to_grid(n["x"], 0)
                    positions.append((c, n["text"]))
                positions.sort()
                # Detect overlap
                overlap = False
                for i in range(1, len(positions)):
                    prev_end = positions[i-1][0] + len(positions[i-1][1])
                    if positions[i][0] <= prev_end:
                        overlap = True
                        break
                if overlap:
                    # Uniform spacing centered on page
                    total_text = sum(len(t) for _, t in positions)
                    gaps = len(positions) - 1
                    avail = cols - total_text - 4   # 2-col margin each side
                    spacing = max(2, avail // max(1, gaps))
                    line = ""
                    for i, (_, t) in enumerate(positions):
                        if i > 0:
                            line += " " * spacing
                        line += t
                    # center
                    pad_left = max(0, (cols - len(line)) // 2)
                    line = " " * pad_left + line
                    for i, ch in enumerate(line[:cols]):
                        grid[nav_row][i] = ch
                        nav_written.add((nav_row, i))
                else:
                    for c, text in positions:
                        for i, ch in enumerate(text):
                            gc = c + i
                            if 0 <= gc < cols:
                                grid[nav_row][gc] = ch
                                nav_written.add((nav_row, gc))

    # ── 3. Body text (headings, body copy) ──────────────────────────────────
    # Rendered BEFORE buttons so buttons sit on top — otherwise a body
    # paragraph one row above a button would clear the button's top
    # border when its clear-pad-below reaches into the button row.
    #
    # Render headlines first (largest font size). Without this, a subtitle
    # text whose clear-region happens to cover the headline's row would
    # wipe the headline. Drawing largest-first means smaller text only
    # clears empty area (or its own previous self).
    sorted_texts = sorted(
        [t for t in data.get("texts", [])],
        key=lambda t: -t["fontSize"],
    )
    written_text_cells = set()  # (row, col) cells holding rendered chars

    for t in sorted_texts:
        if t["fontSize"] < args.min_font_size:
            continue
        if t["y"] + t["h"] < y_start or t["y"] >= y_end:
            continue
        col, row = px_to_grid(t["x"], t["y"] + t["h"] * 0.5)
        if row < 0 or row >= rows:
            continue
        text = t["text"]
        text_w_cols = max(1, int(round(t["w"] / px_per_col)))
        text_h_rows = max(1, int(round(t["h"] / px_per_row)))
        clear_w = max(text_w_cols, len(text))
        clear_pad_x = 2
        clear_pad_y_above = max(1, text_h_rows - 1)
        clear_pad_y_below = 1 if text_h_rows > 1 else 0
        r_lo = max(0, row - clear_pad_y_above)
        r_hi = min(rows, row + clear_pad_y_below + 1)
        c_lo = max(0, col - clear_pad_x)
        c_hi = min(cols, col + clear_w + clear_pad_x)
        for r in range(r_lo, r_hi):
            for c in range(c_lo, c_hi):
                # Don't clear a cell that already holds rendered text
                # (from nav or earlier larger text).
                if (r, c) in written_text_cells or (r, c) in nav_written:
                    continue
                grid[r][c] = " "
        max_chars = cols - col
        if max_chars <= 0:
            continue
        text = text[:max_chars]
        for i, ch in enumerate(text):
            gc = col + i
            if 0 <= gc < cols:
                grid[row][gc] = ch
                written_text_cells.add((row, gc))

    # ── 4. Buttons: render as ASCII boxes on top of everything ──────────────
    # Two-pass: first compute every button's footprint (with a 1-col
    # outer margin to wipe any image bleed touching the box). Union the
    # footprints, then clear the union once. Then draw the boxes. This
    # avoids the "neighbor button eats my border" problem while still
    # cleaning up the area immediately adjacent to standalone buttons.
    button_specs = []
    cleared_cells = set()
    for b in data.get("buttons", []):
        if b["y"] + b["h"] < y_start or b["y"] >= y_end:
            continue
        text = b["text"]
        box_w = max(len(text) + 4, max(8, int(round(b["w"] / px_per_col))))
        box_w = min(box_w, cols - 1)
        if box_w < len(text) + 4:
            box_w = len(text) + 4
        col, row = px_to_grid(b["x"], b["y"] + b["h"] * 0.5)
        row_top = row - 1
        row_bot = row + 1
        if row_top < 0 or row_bot >= rows:
            continue
        button_specs.append({
            "text": text, "style": b.get("style"),
            "col": col, "row": row, "row_top": row_top, "row_bot": row_bot,
            "box_w": box_w,
        })
        # Mark footprint cells (with 1-col left+right padding around the
        # *outermost* button — adjacent button footprints will overlap
        # the padding, which is what we want).
        for r in range(max(0, row_top - 1), min(rows, row_bot + 2)):
            for c in range(max(0, col - 1), min(cols, col + box_w + 1)):
                cleared_cells.add((r, c))

    # Pass 1.5: when neighbors on the same row would overlap, shrink the
    # bigger one by truncating its label with an ellipsis. Adjacent buttons
    # without overlap are fine — they just share a border column.
    button_specs.sort(key=lambda s: (s["row"], s["col"]))
    for i in range(len(button_specs) - 1):
        a = button_specs[i]
        b = button_specs[i + 1]
        if a["row"] != b["row"]:
            continue
        a_end = a["col"] + a["box_w"]
        if a_end > b["col"]:
            # Overlap. Allow at most this many cols for `a` (leaving 0
            # cols between borders — they share a column).
            allowed_w = b["col"] - a["col"]
            min_w = 5  # ┏ a ┓ minimum
            if allowed_w < min_w:
                # Drop the smaller/later button entirely.
                button_specs[i + 1] = None
            else:
                a["box_w"] = allowed_w
                inner_max = allowed_w - 2
                if len(a["text"]) > inner_max - 2:
                    if inner_max > 1:
                        a["text"] = a["text"][: inner_max - 1] + "…"
                    else:
                        a["text"] = a["text"][:inner_max]
    button_specs = [s for s in button_specs if s is not None]

    # Pass 2: clear all footprints, then draw all boxes.
    # Skip cells that hold rendered text (nav or body) so adjacent labels
    # aren't eaten by a button's outer margin clear.
    protected = written_text_cells | nav_written
    for (r, c) in cleared_cells:
        if (r, c) in protected:
            continue
        grid[r][c] = " "
    for spec in button_specs:
        col = spec["col"]; row = spec["row"]
        row_top = spec["row_top"]; row_bot = spec["row_bot"]
        box_w = spec["box_w"]
        text = spec["text"]

        # Centered text inside the box
        pad = (box_w - 2 - len(text)) // 2
        inner = " " * max(0, pad) + text + " " * max(0, (box_w - 2 - len(text) - max(0, pad)))
        inner = inner[: box_w - 2]

        if spec.get("style") == "filled":
            top = "┏" + "━" * (box_w - 2) + "┓"
            mid = "┃" + inner + "┃"
            bot = "┗" + "━" * (box_w - 2) + "┛"
        else:
            top = "┌" + "─" * (box_w - 2) + "┐"
            mid = "│" + inner + "│"
            bot = "└" + "─" * (box_w - 2) + "┘"
        write_at(row_top, col, top)
        write_at(row,     col, mid)
        write_at(row_bot, col, bot)

    # ── 5. Trim trailing whitespace + leading/trailing empty rows ────────────
    out_lines = ["".join(row).rstrip() for row in grid]
    while out_lines and not out_lines[0].strip():
        out_lines.pop(0)
    while out_lines and not out_lines[-1].strip():
        out_lines.pop()

    Path(args.out_path).write_text("\n".join(out_lines) + "\n")
    print(f"composite: {cols}x{rows} grid → {len(out_lines)} lines → {args.out_path}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
