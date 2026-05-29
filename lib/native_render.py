#!/usr/bin/env python3
"""
Native PNG -> ASCII renderer for lofi-ascii.

This intentionally has no third-party dependencies. It is built for screenshots
captured by Chrome: decode PNG, downsample to a character grid, adjust tone, and
map luminance to an ordered character ramp.
"""

import argparse
import math
import struct
import sys
import zlib
from pathlib import Path


STYLE_RAMPS = {
    # Ramps are ordered darkest -> lightest.
    "standard": "@%#*+=-:. ",
    "blocks": "█▓▒░ ",
    "detailed": "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. ",
    "minimal": "#*:. ",
    "lofi": "@%#*+=-:. ",
    "braille": "⣿⣷⣤⣀ ",
    "sketch": "#*+=-:. ",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("png_path")
    parser.add_argument("--width", type=int, default=120)
    parser.add_argument("--height-scale", type=float, default=1.0)
    parser.add_argument("--cell-aspect", type=float, default=0.5)
    parser.add_argument("--style", default="standard")
    parser.add_argument("--charset", default=None)
    parser.add_argument("--density-bias", type=float, default=1.0)
    parser.add_argument("--brightness", type=float, default=8.0)
    parser.add_argument("--contrast", type=float, default=22.0)
    parser.add_argument("--gamma", type=float, default=1.0)
    parser.add_argument("--pixelate", type=int, default=0)
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--no-auto-invert", action="store_true")
    parser.add_argument(
        "--sample-mode",
        default="detail",
        choices=["average", "detail", "ink", "edges"],
    )
    parser.add_argument("--detail-weight", type=float, default=0.2)
    return parser.parse_args()


def paeth(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png(path):
    data = Path(path).read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("native renderer only supports PNG input")

    pos = 8
    width = height = color_type = bit_depth = None
    idat = bytearray()

    while pos < len(data):
        if pos + 8 > len(data):
            raise ValueError("truncated PNG chunk")
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk_data = data[pos + 8 : pos + 8 + length]
        pos += 12 + length

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if bit_depth != 8:
                raise ValueError("only 8-bit PNGs are supported")
            if compression != 0 or filtering != 0 or interlace != 0:
                raise ValueError("unsupported PNG encoding")
        elif chunk_type == b"IDAT":
            idat.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None or color_type is None:
        raise ValueError("PNG missing IHDR")

    channels_by_type = {0: 1, 2: 3, 4: 2, 6: 4}
    if color_type not in channels_by_type:
        raise ValueError(f"unsupported PNG color type {color_type}")
    channels = channels_by_type[color_type]

    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    rows = []
    prev = bytearray(stride)
    offset = 0

    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        cur = bytearray(raw[offset : offset + stride])
        offset += stride

        for i in range(stride):
            left = cur[i - channels] if i >= channels else 0
            up = prev[i]
            upper_left = prev[i - channels] if i >= channels else 0
            if filter_type == 1:
                cur[i] = (cur[i] + left) & 0xFF
            elif filter_type == 2:
                cur[i] = (cur[i] + up) & 0xFF
            elif filter_type == 3:
                cur[i] = (cur[i] + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                cur[i] = (cur[i] + paeth(left, up, upper_left)) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"unsupported PNG filter {filter_type}")

        rows.append(cur)
        prev = cur

    return width, height, channels, rows


def clamp(value, low, high):
    return max(low, min(high, value))


def contrast_adjust(value, contrast):
    # Same common contrast curve used in many canvas/image tools.
    c = 2.55 * clamp(contrast, -100.0, 99.5)
    factor = 259.0 * (c + 255.0) / (255.0 * (259.0 - c))
    return factor * (value - 128.0) + 128.0


def get_rgb(row, x, channels):
    i = x * channels
    if channels == 1:
        return row[i], row[i], row[i], 255
    if channels == 2:
        return row[i], row[i], row[i], row[i + 1]
    if channels == 3:
        return row[i], row[i + 1], row[i + 2], 255
    return row[i], row[i + 1], row[i + 2], row[i + 3]


def cell_average(rows, src_w, src_h, channels, x0, y0, x1, y1, pixelate):
    if pixelate >= 2:
        # Quantize sample origin for a chunkier, poster-like result.
        x0 = (x0 // pixelate) * pixelate
        y0 = (y0 // pixelate) * pixelate
        x1 = max(x0 + 1, min(src_w, x0 + pixelate))
        y1 = max(y0 + 1, min(src_h, y0 + pixelate))

    total_r = total_g = total_b = total_a = count = 0
    min_lum = 255.0
    max_lum = 0.0
    for y in range(y0, y1):
        row = rows[y]
        for x in range(x0, x1):
            r, g, b, a = get_rgb(row, x, channels)
            total_r += r
            total_g += g
            total_b += b
            total_a += a
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            min_lum = min(min_lum, lum)
            max_lum = max(max_lum, lum)
            count += 1

    if count == 0:
        return 255, 255, 255, 0, 255, 255
    return (
        total_r / count,
        total_g / count,
        total_b / count,
        total_a / count,
        min_lum,
        max_lum,
    )


def normalize_charset(raw):
    chars = []
    seen = set()
    has_space = False
    for ch in raw:
        if ch.isspace():
            has_space = True
            continue
        if ch not in seen:
            chars.append(ch)
            seen.add(ch)
    if has_space:
        chars.append(" ")
    return "".join(chars) or STYLE_RAMPS["standard"]


def tone_channel(value, gamma, contrast, brightness):
    value = clamp(255.0 * ((value / 255.0) ** (1.0 / gamma)), 0.0, 255.0)
    return clamp(contrast_adjust(value, contrast) + 2.55 * brightness, 0.0, 255.0)


def render_ascii(width, height, channels, rows, args):
    out_cols = int(clamp(round(args.width), 10, 300))
    out_rows = int(
        clamp(round(out_cols * height / width * args.cell_aspect * args.height_scale), 1, 500)
    )
    ramp = normalize_charset(args.charset or STYLE_RAMPS.get(args.style, STYLE_RAMPS["standard"]))
    last = max(0, len(ramp) - 1)
    density = max(0.05, args.density_bias)
    gamma = max(0.05, args.gamma)
    invert = args.invert
    bg_lum = 255.0
    if not args.no_auto_invert:
        # Wireframes read better when the dominant page background maps to
        # whitespace. Sample a coarse grid instead of every source pixel.
        total = count = 0
        step_x = max(1, width // 80)
        step_y = max(1, height // 80)
        for y in range(0, height, step_y):
            row = rows[y]
            for x in range(0, width, step_x):
                r, g, b, a = get_rgb(row, x, channels)
                if a / 255.0 < 0.08:
                    continue
                total += 0.2126 * r + 0.7152 * g + 0.0722 * b
                count += 1
        bg_lum = total / count if count else 255.0
        if bg_lum < 128.0:
            invert = not invert

    lines = []
    for row_idx in range(out_rows):
        y0 = int(row_idx * height / out_rows)
        y1 = max(y0 + 1, int((row_idx + 1) * height / out_rows))
        chars = []
        for col_idx in range(out_cols):
            x0 = int(col_idx * width / out_cols)
            x1 = max(x0 + 1, int((col_idx + 1) * width / out_cols))
            r, g, b, a, min_lum, max_lum = cell_average(
                rows, width, height, channels, x0, y0, x1, y1, args.pixelate
            )
            if a / 255.0 < 0.08:
                chars.append(" ")
                continue

            r = tone_channel(r, gamma, args.contrast, args.brightness)
            g = tone_channel(g, gamma, args.contrast, args.brightness)
            b = tone_channel(b, gamma, args.contrast, args.brightness)
            avg_lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            min_lum = tone_channel(min_lum, gamma, args.contrast, args.brightness)
            max_lum = tone_channel(max_lum, gamma, args.contrast, args.brightness)
            span = max_lum - min_lum
            if invert:
                avg_lum = 255.0 - avg_lum
                detail_lum = 255.0 - max_lum
            else:
                detail_lum = min_lum

            if args.sample_mode == "average":
                luminance = avg_lum
            elif args.sample_mode == "edges":
                # Edge-map-ish mode: only local contrast becomes ink.
                luminance = 255.0 - clamp(span * 2.8, 0.0, 255.0)
            elif args.sample_mode == "ink":
                # Background-aware binary-ish mode for UI screenshots. Keep
                # near-flat background cells empty, then let high-contrast
                # text/hairlines show with controlled density.
                bg_distance = abs((0.2126 * r + 0.7152 * g + 0.0722 * b) - bg_lum)
                if span < 22 and bg_distance < 28:
                    luminance = 255.0
                else:
                    luminance = min(avg_lum, detail_lum + 0.55 * (avg_lum - detail_lum))
            else:
                # Preserve small foreground details inside a cell. Pure
                # averaging erases text strokes and hairline UI borders after
                # downsampling.
                weight = clamp(args.detail_weight, 0.0, 1.0)
                luminance = min(avg_lum, detail_lum + weight * (avg_lum - detail_lum))
            idx = int(round((luminance / 255.0) ** density * last))
            chars.append(ramp[clamp(idx, 0, last)])
        lines.append("".join(chars).rstrip())

    return "\n".join(lines)


def main():
    args = parse_args()
    width, height, channels, rows = read_png(args.png_path)
    print(render_ascii(width, height, channels, rows, args))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"native-render: {exc}", file=sys.stderr)
        sys.exit(1)
