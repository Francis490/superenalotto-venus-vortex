"""
Genera automaticamente le icone PWA per la dashboard TITAN.
Richiede Pillow. Eseguito automaticamente dal workflow generate_icons.yml.
"""
from PIL import Image, ImageDraw, ImageFont
import os

BG = (9, 9, 11)
PURPLE = (168, 85, 247)
TEAL = (20, 184, 166)
WHITE = (248, 250, 252)

def make_icon(size, path, with_text=True):
    img = Image.new("RGBA", (size, size), BG)
    d = ImageDraw.Draw(img)

    margin = size * 0.06
    d.ellipse([margin, margin, size - margin, size - margin],
              outline=PURPLE, width=max(3, size // 40))

    cx, cy = size // 2, size // 2
    r = size * 0.28
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
              fill=TEAL)

    r2 = r * 0.55
    d.polygon([(cx, cy - r2), (cx + r2, cy), (cx, cy + r2), (cx - r2, cy)],
              fill=PURPLE)

    if with_text and size >= 256:
        try:
            font = ImageFont.truetype("arial.ttf", size // 8)
        except Exception:
            font = ImageFont.load_default()
        text = "TITAN"
        bbox = d.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        d.text((cx - tw / 2, size - margin - th - size * 0.06),
               text, fill=WHITE, font=font)

    img.save(path, "PNG")
    print(f"[+] Creato: {path} ({size}x{size})")

def make_favicon(path):
    sizes = [16, 32, 48, 64]
    imgs = []
    for s in sizes:
        img = Image.new("RGBA", (s, s), BG)
        d = ImageDraw.Draw(img)
        d.ellipse([1, 1, s - 2, s - 2], outline=PURPLE, width=max(1, s // 16))
        cx, cy = s // 2, s // 2
        r = s * 0.28
        d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
                  fill=TEAL)
        imgs.append(img)
    imgs[0].save(path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"[+] Creato: {path}")

if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    make_icon(192, os.path.join(base, "icon-192.png"), with_text=False)
    make_icon(512, os.path.join(base, "icon-512.png"), with_text=True)
    make_favicon(os.path.join(base, "favicon.ico"))
    print("\n[OK] Tutte le icone sono state generate.")
