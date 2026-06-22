#!/usr/bin/env python3
"""
Charm Image Optimizer — v2
Pipeline: remove white bg → autocrop → center on 300×300 transparent canvas → export .webp
Requires: pip install Pillow
Usage:    python optimize_charms.py
"""

import argparse
import re
from pathlib import Path
from PIL import Image

INPUT_DIR    = Path("dijes")
OUTPUT_DIR   = Path("dijes")
CANVAS_SIZE  = (300, 300)
WEBP_QUALITY = 85
BG_THRESHOLD = 235  # R, G, B >= este valor → tratado como fondo blanco


def sanitize(name: str) -> str:
    return re.sub(r"[^\w\-.]", "_", name)


# ── CAMBIO 3: remoción de fondo con BFS flood-fill desde esquinas ───────────
def remove_bg_floodfill(img: Image.Image, tolerance: int = 35) -> Image.Image:
    """
    Elimina el fondo usando BFS desde las 4 esquinas de la imagen.
    Ventajas sobre el umbral simple:
      - Solo borra píxeles ALCANZABLES desde el borde (preserva blancos interiores).
      - Detecta automáticamente el color real del fondo (no asume blanco puro).
      - Maneja bordes con anti-aliasing sin dejar halos.
    Si la imagen ya tiene >5% de alfa activo se retorna sin modificar.
    """
    from collections import deque

    rgba = img.convert("RGBA")

    # Saltar imágenes que ya tienen transparencia real
    data   = rgba.getdata()
    transp = sum(1 for p in data if p[3] < 128)
    if transp / len(data) > 0.05:
        return rgba

    w, h   = rgba.size
    pixels = rgba.load()

    # Muestrear el color del fondo en las 4 esquinas
    corner_rgb = [pixels[x, y][:3] for x, y in [(0,0),(w-1,0),(0,h-1),(w-1,h-1)]]
    bg = tuple(sum(c[i] for c in corner_rgb) // 4 for i in range(3))

    def similar(r, g, b):
        return max(abs(r-bg[0]), abs(g-bg[1]), abs(b-bg[2])) <= tolerance

    # bytearray como mapa de visitados (mucho más eficiente en memoria que un set)
    visited = bytearray(w * h)
    q = deque()
    for sx, sy in [(0,0),(w-1,0),(0,h-1),(w-1,h-1)]:
        idx = sy * w + sx
        if not visited[idx]:
            visited[idx] = 1
            q.append((sx, sy))

    while q:
        x, y = q.popleft()
        r, g, b, a = pixels[x, y]
        if similar(r, g, b):
            pixels[x, y] = (r, g, b, 0)          # fondo → transparente
            for nx, ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if 0 <= nx < w and 0 <= ny < h:
                    nidx = ny * w + nx
                    if not visited[nidx]:
                        visited[nidx] = 1
                        q.append((nx, ny))
    return rgba
# ────────────────────────────────────────────────────────────────────────────


def autocrop(img: Image.Image) -> Image.Image:
    """Elimina bordes transparentes vacíos alrededor del dije."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def center_on_canvas(img: Image.Image, size: tuple) -> Image.Image:
    """Centra el dije recortado sobre un canvas cuadrado con fondo transparente."""
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))   # fondo rgba(0,0,0,0)
    img.thumbnail((size[0] - 10, size[1] - 10), Image.LANCZOS)
    x = (size[0] - img.width)  // 2
    y = (size[1] - img.height) // 2
    canvas.paste(img, (x, y), img)
    return canvas


def process_image(src: Path, center: bool = True) -> None:
    try:
        with Image.open(src) as raw:
            no_bg   = remove_bg_floodfill(raw)     # 1) eliminar fondo (BFS)
            cropped = autocrop(no_bg)               # 2) recortar bordes vacíos
            if center:
                result = center_on_canvas(cropped, CANVAS_SIZE)  # 3) centrar en canvas
            else:
                cropped.thumbnail(CANVAS_SIZE, Image.LANCZOS)
                result = cropped
            clean   = sanitize(src.stem) + ".webp"
            dst     = OUTPUT_DIR / clean
            result.save(dst, "WEBP", quality=WEBP_QUALITY, method=6)
            orig_kb = src.stat().st_size / 1024
            new_kb  = dst.stat().st_size / 1024
            mode    = "centrado" if center else "sin centrar"
            print(f"  {src.name:55s} {orig_kb:7.1f} KB → {new_kb:6.1f} KB  [{mode}] → {clean}")
    except Exception as exc:
        print(f"  ERROR {src.name}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimizador de imágenes de dijes")
    parser.add_argument(
        "--no-center",
        action="store_true",
        help="Omite el centrado en canvas cuadrado; exporta el recorte tal cual",
    )
    args = parser.parse_args()
    center = not args.no_center

    OUTPUT_DIR.mkdir(exist_ok=True)
    exts    = {".png", ".jpg", ".jpeg", ".gif", ".tiff"}
    sources = [p for p in sorted(INPUT_DIR.iterdir()) if p.suffix.lower() in exts]
    if not sources:
        print(f"No se encontraron imágenes fuente en '{INPUT_DIR}/'.")
        return
    modo = "CON centrado" if center else "SIN centrado"
    print(f"Procesando {len(sources)} imagen(es) — {modo}...\n")
    for src in sources:
        process_image(src, center=center)
    print("\nListo.")


if __name__ == "__main__":
    main()
