#!/usr/bin/env python3
"""
composite.py — text-aware rendering compositor for lofi-ascii.

Reads:
  - JSON: extracted text nodes + image bounding boxes (from extract.js)
  - PNG:  screenshot from the same Chrome session
Writes:
  - ASCII text where REAL text comes from the DOM, and image regions are
    chafa-rendered crops of the screenshot.

Usage:
  composite.py <json_path> <png_path> <out_path> \\
    [--width=140] [--theme=light] [--style=blocks] \\
    [--crop=y_start:y_end] [--high-contrast]
"""

import argparse
import io
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print("composite: Pillow required. pip install pillow", file=sys.stderr)
    sys.exit(2)


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
    p.add_argument("--cell-aspect", type=float, default=2.1, help="terminal cell h/w ratio")
    p.add_argument("--min-font-size", type=float, default=12,
                   help="ignore text below this px size (nav micro-labels etc.)")
    return p.parse_args()


def chafa_render(png_path, w, theme, style, high_contrast):
    """Render a PNG via chafa and return ASCII lines."""
    flags = {
        "blocks": ["--symbols", "block+border+space", "--colors", "none"],
        "lofi":   ["--symbols", "ascii",              "--colors", "none"],
        "sketch": ["--symbols", "block+border",       "--colors", "none", "--threshold", "0.3"],
        "braille":["--symbols", "braille",            "--colors", "none"],
    }.get(style, ["--symbols", "block+border+space", "--colors", "none"])

    if theme == "light":
        flags.append("--invert")

    src = png_path
    tmp_proc = None
    if high_contrast:
        tmp_proc = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img = Image.open(png_path).convert("L")
        img = img.point(lambda p: 0 if p < 235 else 255, "L")
        img.save(tmp_proc.name)
        src = tmp_proc.name

    cmd = ["chafa", *flags, "--work", "9",
           "--size", str(w), "--format", "symbols",
           "--animate", "off", "--polite", "on", src]
    try:
        out = subprocess.check_output(cmd, text=True)
    except subprocess.CalledProcessError as e:
        print(f"composite: chafa failed: {e}", file=sys.stderr)
        out = ""

    if tmp_proc is not None:
        Path(tmp_proc.name).unlink(missing_ok=True)

    return [l.rstrip("\n") for l in out.split("\n") if l.rstrip("\n")]


def display_width(s):
    """Approximate display width (most chars 1; Unicode block chars usually 1 too)."""
    return len(s)


def main():
    args = parse_args()

    data = json.loads(Path(args.json_path).read_text())
    screenshot = Image.open(args.png_path)
    px_w, px_h = screenshot.size

    # Crop range
    y_start, y_end = 0, px_h
    if args.crop:
        parts = args.crop.split(":")
        y_start = int(parts[0]) if parts[0] else 0
        y_end = int(parts[1]) if len(parts) > 1 and parts[1] else px_h
    crop_h = y_end - y_start

    # Grid sizing: target_width chars wide, height proportional to crop area.
    cols = args.width
    # px-per-char horizontally
    px_per_col = px_w / cols
    # Each char is `cell_aspect` taller than wide, so px-per-row = px_per_col * cell_aspect
    px_per_row = px_per_col * args.cell_aspect
    rows = max(1, math.ceil(crop_h / px_per_row))

    # Build empty grid
    grid = [[" " for _ in range(cols)] for _ in range(rows)]

    def px_to_grid(x, y):
        col = int(round(x / px_per_col))
        row = int(round((y - y_start) / px_per_row))
        return col, row

    # ── 1. Paste image regions (chafa-rendered) ─────────────────────────────
    pictures = [i for i in data.get("images", []) if i["tag"] in ("picture", "img", "video")]
    # Filter out tiny + offscreen
    pictures = [
        p for p in pictures
        if p["w"] >= 100 and p["h"] >= 100
        and p["x"] >= 0 and p["x"] + p["w"] <= px_w
        and p["y"] + p["h"] > y_start and p["y"] < y_end
    ]
    # Deduplicate: prefer picture over inner img if they overlap
    used = []
    for p in sorted(pictures, key=lambda r: -(r["w"] * r["h"])):
        keep = True
        for u in used:
            # if p is mostly inside u (a child img), skip
            ax1, ay1, ax2, ay2 = p["x"], p["y"], p["x"]+p["w"], p["y"]+p["h"]
            bx1, by1, bx2, by2 = u["x"], u["y"], u["x"]+u["w"], u["y"]+u["h"]
            ix = max(0, min(ax2, bx2) - max(ax1, bx1))
            iy = max(0, min(ay2, by2) - max(ay1, by1))
            overlap = ix * iy
            if overlap > 0.5 * (p["w"] * p["h"]):
                keep = False
                break
        if keep:
            used.append(p)

    for img_rect in used:
        ix, iy, iw, ih = img_rect["x"], img_rect["y"], img_rect["w"], img_rect["h"]
        # Clip to crop region
        cy1 = max(iy, y_start)
        cy2 = min(iy + ih, y_end)
        if cy2 <= cy1:
            continue

        # Crop from screenshot
        crop = screenshot.crop((int(ix), int(cy1), int(ix + iw), int(cy2)))

        # Determine sub-grid dimensions
        sub_cols = max(1, int(round(iw / px_per_col)))
        sub_rows = max(1, int(round((cy2 - cy1) / px_per_row)))

        # Save crop temporarily, render with chafa
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        crop.save(tmp.name)
        sub_lines = chafa_render(tmp.name, sub_cols, args.theme, args.style, args.high_contrast)
        Path(tmp.name).unlink(missing_ok=True)

        # Paste into main grid
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

    # ── 2. Overlay text nodes ───────────────────────────────────────────────
    for t in data.get("texts", []):
        if t["fontSize"] < args.min_font_size:
            continue
        if t["y"] + t["h"] < y_start or t["y"] >= y_end:
            continue
        col, row = px_to_grid(t["x"], t["y"] + t["h"] * 0.5)  # mid-height
        if row < 0 or row >= rows:
            continue
        text = t["text"]
        text_w_cols = max(1, int(round(t["w"] / px_per_col)))
        # How many rows of grid does this text actually occupy in the source?
        # (Big headlines occupy multiple grid rows; chafa "ghost" of the text
        # in those rows looks like noise unless we clear it.)
        text_h_rows = max(1, int(round(t["h"] / px_per_row)))
        clear_w = max(text_w_cols, display_width(text))
        # Pad clear box by 1 column on each side and 1 row above to remove
        # chafa fragments from big text glyphs.
        clear_pad_x = 1
        clear_pad_y_above = max(1, text_h_rows - 1)
        clear_pad_y_below = 1 if text_h_rows > 1 else 0
        r_lo = max(0, row - clear_pad_y_above)
        r_hi = min(rows, row + clear_pad_y_below + 1)
        c_lo = max(0, col - clear_pad_x)
        c_hi = min(cols, col + clear_w + clear_pad_x)
        for r in range(r_lo, r_hi):
            for c in range(c_lo, c_hi):
                grid[r][c] = " "
        # Truncate text that overflows the right edge
        max_chars = cols - col
        if max_chars <= 0:
            continue
        text = text[:max_chars]
        for i, ch in enumerate(text):
            gc = col + i
            if 0 <= gc < cols:
                grid[row][gc] = ch

    # ── 3. Trim trailing whitespace per row + leading/trailing empty rows ────
    out_lines = ["".join(row).rstrip() for row in grid]
    # Trim leading/trailing empty rows
    while out_lines and not out_lines[0].strip():
        out_lines.pop(0)
    while out_lines and not out_lines[-1].strip():
        out_lines.pop()

    Path(args.out_path).write_text("\n".join(out_lines) + "\n")
    # Stderr: summary
    print(f"composite: {cols}x{rows} grid → {len(out_lines)} lines → {args.out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
