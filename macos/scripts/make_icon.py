#!/usr/bin/env python3
"""Generate a geometric ScreenTest macOS app icon without third-party deps."""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

SIZE = 1024
ROOT = Path(__file__).resolve().parents[1]
ICONSET = ROOT / "build" / "AppIcon.iconset"
ASSETS = ROOT / "ScreenTest" / "Assets.xcassets" / "AppIcon.appiconset"


def png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_png(path: Path, width: int, height: int, rgba: bytes) -> None:
    raw = b"".join(b"\x00" + rgba[y * width * 4 : (y + 1) * width * 4] for y in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(raw, 9))
        + png_chunk(b"IEND", b"")
    )


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def rounded_rect(px: float, py: float, size: int, radius: float) -> float:
    """Signed distance to a rounded square centered in the canvas."""
    cx = cy = size / 2
    hx = hy = size * 0.38
    dx = abs(px - cx) - hx + radius
    dy = abs(py - cy) - hy + radius
    outside = math.hypot(max(dx, 0), max(dy, 0))
    inside = min(max(dx, dy), 0)
    return outside + inside - radius


def pixel(x: int, y: int, size: int) -> tuple[int, int, int, int]:
    # Dark desktop background
    bg = (15, 17, 21)
    card = (26, 29, 36)
    bars = [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (0, 255, 255),
        (255, 0, 255),
        (255, 255, 0),
        (255, 255, 255),
    ]

    dist = rounded_rect(x + 0.5, y + 0.5, size, size * 0.08)
    if dist > 2:
        return (*bg, 255)
    if dist > 0:
        t = max(0.0, min(1.0, 1 - dist / 2))
        return (
            int(lerp(bg[0], 40, t)),
            int(lerp(bg[1], 44, t)),
            int(lerp(bg[2], 54, t)),
            255,
        )

    # Inner screen
    inset = size * 0.18
    if inset < x < size - inset and inset < y < size - inset:
        # Color bars occupy the upper 62%
        bar_bottom = inset + (size - 2 * inset) * 0.62
        if y < bar_bottom:
            inner_w = size - 2 * inset
            t = (x - inset) / max(1, inner_w)
            idx = min(len(bars) - 1, int(t * len(bars)))
            r, g, b = bars[idx]
            return (r, g, b, 255)
        # Checker strip
        cell = max(8, size // 28)
        on = ((x // cell) + (y // cell)) % 2 == 0
        v = 230 if on else 20
        return (v, v, v, 255)

    return (*card, 255)


def render(size: int) -> bytes:
    out = bytearray(size * size * 4)
    i = 0
    for y in range(size):
        for x in range(size):
            r, g, b, a = pixel(x, y, size)
            out[i : i + 4] = bytes((r, g, b, a))
            i += 4
    return bytes(out)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    ICONSET.mkdir(parents=True, exist_ok=True)

    master = ROOT / "build" / "icon-1024.png"
    master.parent.mkdir(parents=True, exist_ok=True)
    write_png(master, SIZE, SIZE, render(SIZE))

    contents = {
        "images": [
            {"idiom": "mac", "size": "16x16", "scale": "1x", "filename": "icon_16x16.png"},
            {"idiom": "mac", "size": "16x16", "scale": "2x", "filename": "icon_16x16@2x.png"},
            {"idiom": "mac", "size": "32x32", "scale": "1x", "filename": "icon_32x32.png"},
            {"idiom": "mac", "size": "32x32", "scale": "2x", "filename": "icon_32x32@2x.png"},
            {"idiom": "mac", "size": "128x128", "scale": "1x", "filename": "icon_128x128.png"},
            {"idiom": "mac", "size": "128x128", "scale": "2x", "filename": "icon_128x128@2x.png"},
            {"idiom": "mac", "size": "256x256", "scale": "1x", "filename": "icon_256x256.png"},
            {"idiom": "mac", "size": "256x256", "scale": "2x", "filename": "icon_256x256@2x.png"},
            {"idiom": "mac", "size": "512x512", "scale": "1x", "filename": "icon_512x512.png"},
            {"idiom": "mac", "size": "512x512", "scale": "2x", "filename": "icon_512x512@2x.png"},
        ],
        "info": {"version": 1, "author": "screentest"},
    }

    sizes = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }

    import json

    for name, px in sizes.items():
        dest = ICONSET / name
        subprocess.check_call(
            ["sips", "-z", str(px), str(px), str(master), "--out", str(dest)],
            stdout=subprocess.DEVNULL,
        )
        shutil.copy2(dest, ASSETS / name)

    (ASSETS / "Contents.json").write_text(json.dumps(contents, indent=2) + "\n", encoding="utf-8")
    print(f"icon -> {ASSETS}")


if __name__ == "__main__":
    main()
