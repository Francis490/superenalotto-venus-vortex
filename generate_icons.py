"""
generate_icons.py
Genera le icone PWA di Venus Vortex.

Design coerente con la foto profilo del bot:
galassia a spirale + nucleo dorato + simbolo Venere (♀).

Adattivo per dimensione:
- Favicon (16-64px): solo nucleo + anello
- icon-192: spirale 2 bracci, no stelle, no testo
- icon-512: design completo con stelle e testo
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import os
import math
import random

# Palette Venus Vortex
SPACE_DEEP = (6, 4, 15)
SPACE_PURPLE = (30, 12, 52)
VENUS = (192, 38, 211)
NEBULA = (236, 72, 153)
VORTEX = (6, 182, 212)
SOLAR = (251, 191, 36)
WHITE = (255, 255, 255)
TEXT_SOFT = (241, 232, 255)


def lerp(c1, c2, t):
    """Interpolazione lineare tra due colori."""
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_radial_bg(draw, cx, cy, size):
    """Sfondo radiale viola -> nero."""
    steps = 200
    max_r = int(size * 0.72)
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(max_r * t)
        intensity = (1 - t) ** 2.0
        color = lerp(SPACE_DEEP, SPACE_PURPLE, intensity)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)


def add_stars(draw, cx, cy, size, n=80, seed=42):
    """Aggiunge stelle sparse nel background."""
    rng = random.Random(seed)
    for _ in range(n):
        angle = rng.uniform(0, 2 * math.pi)
        dist = math.sqrt(rng.random()) * size * 0.44
        x = cx + math.cos(angle) * dist
        y = cy + math.sin(angle) * dist
        r = rng.uniform(0.4, max(1.0, size / 400))
        brightness = rng.uniform(0.3, 1.0)
        if rng.random() < 0.2:
            color = lerp(SPACE_DEEP, VORTEX, brightness)
        elif rng.random() < 0.2:
            color = lerp(SPACE_DEEP, VENUS, brightness)
        else:
            color = lerp(SPACE_DEEP, WHITE, brightness)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def draw_spiral(draw, glow_draw, cx, cy, size, n_arms=3,
                n_points=200, twist=2.4,
                start_r=0.07, end_r=0.42):
    """Disegna una spirale logaritmica a N bracci."""
    colors = [(VENUS, VORTEX), (NEBULA, VORTEX), (VENUS, NEBULA)]
    dot_size_max = max(1.2, size / 180)

    for arm in range(n_arms):
        start_angle = (2 * math.pi / n_arms) * arm
        c_a, c_b = colors[arm % len(colors)]
        for i in range(n_points):
            t = i / (n_points - 1)
            angle = start_angle + twist * math.log(1 + 8 * t) * 3
            r_t = t ** 0.85
            r = size * (start_r + (end_r - start_r) * r_t)
            x = cx + math.cos(angle) * r
            y = cy + math.sin(angle) * r

            dot_r = dot_size_max * (0.3 + 0.7 * t)
            color = lerp(c_a, c_b, t)
            alpha = 0.4 + 0.6 * t
            final = lerp(SPACE_DEEP, color, alpha)
            draw.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r],
                         fill=final)

            if glow_draw:
                gr = dot_r * 3
                gc = lerp((0, 0, 0), color, alpha * 0.5)
                glow_draw.ellipse([x - gr, y - gr, x + gr, y + gr], fill=gc)


def draw_venus(draw, cx, cy, size, color=SOLAR):
    """Disegna il simbolo di Venere (♀)."""
    r = size * 0.055
    width = max(1, int(size * 0.012))

    # Cerchio
    draw.ellipse([cx - r, cy - r - size * 0.012,
                  cx + r, cy + r - size * 0.012],
                 outline=color, width=width)
    # Asta verticale
    top = cy + r - size * 0.012
    bottom = cy + r + size * 0.045
    draw.line([(cx, top), (cx, bottom)], fill=color, width=width)
    # Asta orizzontale
    hw = size * 0.028
    y_bar = bottom - size * 0.008
    draw.line([(cx - hw, y_bar), (cx + hw, y_bar)], fill=color, width=width)


def draw_core(draw, glow_draw, cx, cy, size):
    """Disegna il nucleo centrale con alone + sole + Venere."""
    # Alone concentrico
    for i in range(30, 0, -1):
        t = i / 30
        r = size * 0.09 * t
        intensity = (1 - t) ** 1.8
        color = lerp(SPACE_PURPLE, VENUS, intensity)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

    # Sole dorato
    r_sun = size * 0.030
    draw.ellipse([cx - r_sun, cy - r_sun, cx + r_sun, cy + r_sun], fill=SOLAR)
    if glow_draw:
        glow_draw.ellipse([cx - r_sun * 4, cy - r_sun * 4,
                           cx + r_sun * 4, cy + r_sun * 4], fill=SOLAR)

    # Simbolo Venere
    draw_venus(draw, cx, cy, size, color=SOLAR)


def draw_ring(draw, cx, cy, size):
    """Anello esterno luminoso."""
    r = size * 0.47
    color = lerp(VENUS, NEBULA, 0.3)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 outline=color, width=max(1, size // 240))


def make_icon(size, path, with_text=False):
    """Genera un'icona PWA adattata alla dimensione."""
    cx = cy = size // 2

    # Base RGBA
    img = Image.new("RGBA", (size, size), SPACE_DEEP + (255,))
    draw_radial_bg(ImageDraw.Draw(img), cx, cy, size)

    draw = ImageDraw.Draw(img)

    # Glow layer (sfocato alla fine)
    glow = Image.new("RGB", (size, size), (0, 0, 0))
    gdraw = ImageDraw.Draw(glow)

    # Spirale: 2 bracci per 192, 3 bracci per 512
    n_arms = 3 if size >= 256 else 2
    n_points = 200 if size >= 256 else 130
    draw_spiral(draw, gdraw, cx, cy, size, n_arms=n_arms, n_points=n_points)

    # Stelle solo per icone grandi
    if size >= 256:
        add_stars(draw, cx, cy, size, n=80)

    # Nucleo
    draw_core(draw, gdraw, cx, cy, size)

    # Anello esterno
    draw_ring(draw, cx, cy, size)

    # Blur + composite del glow
    if size >= 192:
        glow_blur = glow.filter(ImageFilter.GaussianBlur(
            radius=max(1, size // 20)))
        blended = Image.blend(img.convert("RGB"), glow_blur, alpha=0.55)
        img = blended.convert("RGBA")
        draw = ImageDraw.Draw(img)
        # Ridisegna core + ring per nitidezza
        draw_core(draw, None, cx, cy, size)
        draw_ring(draw, cx, cy, size)

    # Testo "VENUS VORTEX" solo per 512
    if with_text and size >= 512:
        try:
            font = ImageFont.truetype("arial.ttf", int(size * 0.065))
        except Exception:
            try:
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    int(size * 0.065)
                )
            except Exception:
                font = ImageFont.load_default()
        text = "VENUS VORTEX"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = (size - tw) / 2
        y = size * 0.86
        # Ombra
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0))
        # Testo
        draw.text((x, y), text, font=font, fill=TEXT_SOFT)

    img.save(path, "PNG", optimize=True)
    print(f"[+] {path} ({size}x{size})")


def make_favicon(path):
    """Favicon ultra-semplice: solo nucleo + anello."""
    sizes = [16, 32, 48, 64]
    imgs = []
    for s in sizes:
        img = Image.new("RGBA", (s, s), SPACE_DEEP + (255,))
        cx = cy = s // 2
        draw = ImageDraw.Draw(img)
        draw_radial_bg(draw, cx, cy, s)
        draw = ImageDraw.Draw(img)

        # Nucleo dorato
        r_sun = max(1, s * 0.22)
        draw.ellipse([cx - r_sun, cy - r_sun, cx + r_sun, cy + r_sun],
                     fill=SOLAR)

        # Inner scuro (crea effetto anello)
        r_in = max(1, s * 0.10)
        draw.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in],
                     fill=SPACE_DEEP)

        # Anello esterno
        r_ring = s * 0.42
        draw.ellipse([cx - r_ring, cy - r_ring, cx + r_ring, cy + r_ring],
                     outline=VENUS, width=max(1, s // 32))

        imgs.append(img)

    imgs[0].save(path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"[+] {path}")


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    make_icon(192, os.path.join(base, "icon-192.png"), with_text=False)
    make_icon(512, os.path.join(base, "icon-512.png"), with_text=True)
    make_favicon(os.path.join(base, "favicon.ico"))
    print("\n[OK] Icone Venus Vortex generate.")
