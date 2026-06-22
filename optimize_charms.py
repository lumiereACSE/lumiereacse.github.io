#!/usr/bin/env python3
"""
Charm Image Optimizer
Autocrop → center on 300x300 transparent canvas → export as .webp at quality 85
Requires: pip install Pillow
Usage:    python optimize_charms.py
"""

from pathlib import Path
from PIL import Image

INPUT_DIR  = Path("dijes")
OUTPUT_DIR = Path("dijes")
CANVAS_SIZE = (300, 300)
WEBP_QUALITY = 85


def autocrop(img: Image.Image) -> Image.Image:
    """Remove transparent/empty borders from an RGBA image."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def center_on_canvas(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    img.thumbnail((size[0] - 10, size[1] - 10), Image.LANCZOS)
    x = (size[0] - img.width)  // 2
    y = (size[1] - img.height) // 2
    canvas.paste(img, (x, y), img)
    return canvas


def sanitize(name: str) -> str:
    """Replace whitespace and special chars with underscores for safe URLs."""
    import re
    return re.sub(r"[^\w\-.]", "_", name)


def process_image(src: Path) -> None:
    try:
        with Image.open(src) as raw:
            cropped  = autocrop(raw)
            centered = center_on_canvas(cropped, CANVAS_SIZE)
            clean    = sanitize(src.stem) + ".webp"
            dst      = OUTPUT_DIR / clean
            centered.save(dst, "WEBP", quality=WEBP_QUALITY, method=6)
            orig_kb = src.stat().st_size / 1024
            new_kb  = dst.stat().st_size / 1024
            print(f"  {src.name:55s} {orig_kb:7.1f} KB → {new_kb:6.1f} KB  → {clean}")
    except Exception as exc:
        print(f"  ERROR {src.name}: {exc}")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tiff"}
    sources = [p for p in sorted(INPUT_DIR.iterdir()) if p.suffix.lower() in exts and not p.stem.endswith("_opt")]
    if not sources:
        print(f"No images found in '{INPUT_DIR}/'.")
        return
    print(f"Processing {len(sources)} image(s) from '{INPUT_DIR}/'...\n")
    for src in sources:
        process_image(src)
    print("\nDone.")


if __name__ == "__main__":
    main()
