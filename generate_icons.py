"""
Genera le icone PWA di Venus Vortex.
Logo: vortice concentrico con nucleo solare.
"""
from PIL import Image, ImageDraw, ImageFont
import os
import math

BG = (10, 6, 18)
VENUS = (192, 38, 211)
VORTEX = (6, 182, 212)
SOLAR = (251, 191, 36)
NEBULA = (236, 72, 153)
TEXT = (241, 232, 255)


def draw_vortex(img, cx, cy, size):
    """Disegna un vortice di cerchi concentrici + nucleo."""
    d = ImageDraw.Draw(img)
    max_r = size * 0.42

    # 4 anelli concentrici con colori gradienti
    rings = [
        (max_r * 1.00, VENUS, 2),
        (max_r * 0.75, NEBULA, 2),
        (max_r * 0.52, VORTEX, 2),
        (max_r * 0.30, VENUS, 3),
    ]
    for r, color, w in rings:
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  outline=color, width=max(1, int(w * size / 256)))

    # Nucleo: piccolo rombo dorato
    core = max_r * 0.15
    d.polygon([
        (cx, cy - core),
        (cx + core, cy),
        (cx, cy + core),
        (cx - core, cy),
    ], fill=SOLAR)


def make_icon(size, path, with_text=True):
    img = Image.new("RGBA", (size, size), BG)
    draw_vortex(img, size // 2, size // 2, size)

    if with_text and size >= 256:
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", size // 12)
        except Exception:
            font = ImageFont.load_default()
        text = "VENUS VORTEX"
        bbox = d.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        d.text((size // 2 - tw / 2, int(size * 0.82)),
               text, fill=TEXT, font=font)

    img.save(path, "PNG")
    print(f"[+] {path} ({size}x{size})")


def make_favicon(path):
    sizes = [16, 32, 48, 64]
    imgs = []
    for s in sizes:
        img = Image.new("RGBA", (s, s), BG)
        draw_vortex(img, s // 2, s // 2, s)
        imgs.append(img)
    imgs[0].save(path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"[+] {path}")


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    make_icon(192, os.path.join(base, "icon-192.png"), with_text=False)
    make_icon(512, os.path.join(base, "icon-512.png"), with_text=True)
    make_favicon(os.path.join(base, "favicon.ico"))
    print("\n[OK] Icone Venus Vortex generate.")
