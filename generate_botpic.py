"""
generate_botpic.py
Genera la foto profilo ufficiale del bot Telegram Venus Vortex.
Output: botpic.png (640x640) — formato ottimale Telegram.
Design: galassia a spirale logaritmica + nucleo dorato + Venere (♀)
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import os
import math
import random

SIZE = 640
CX = CY = SIZE // 2

# Palette
SPACE_DEEP = (6, 4, 15)       # nero cosmico
SPACE_PURPLE = (30, 12, 52)    # viola scuro
VENUS = (192, 38, 211)         # magenta
NEBULA = (236, 72, 153)        # rosa
VORTEX = (6, 182, 212)         # ciano
SOLAR = (251, 191, 36)         # oro
WHITE = (255, 255, 255)
TEXT_SOFT = (241, 232, 255)


def lerp(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def draw_radial_background(img, cx, cy, size):
    """Gradient radiale: viola scuro al centro -> nero ai bordi."""
    draw = ImageDraw.Draw(img)
    steps = 320
    max_r = int(size * 0.75)
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(max_r * t)
        # Curva di intensità: più luminoso al centro
        intensity = (1 - t) ** 2.0
        color = lerp(SPACE_DEEP, SPACE_PURPLE, intensity)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=color
        )


def add_stars(draw, cx, cy, size, n=220, seed=42):
    """Aggiunge stelle sparse nel background con distribuzione realistica."""
    rng = random.Random(seed)
    for _ in range(n):
        # Distribuzione radiale: più dense vicino al centro
        angle = rng.uniform(0, 2 * math.pi)
        # sqrt per distribuzione uniforme sull'area
        dist = math.sqrt(rng.random()) * size * 0.47
        x = cx + math.cos(angle) * dist
        y = cy + math.sin(angle) * dist

        # Dimensione e luminosità variabili
        r = rng.uniform(0.4, 2.2)
        brightness = rng.uniform(0.25, 1.0)

        # Colore: bianco tendente al viola/ciano
        if rng.random() < 0.15:
            color = lerp(SPACE_DEEP, VORTEX, brightness)
        elif rng.random() < 0.15:
            color = lerp(SPACE_DEEP, VENUS, brightness)
        else:
            color = lerp(SPACE_DEEP, WHITE, brightness)

        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def draw_spiral_arm(draw, glow_draw, cx, cy, size,
                    n_points=400, twist=2.8, start_radius=0.05,
                    end_radius=0.44, color_a=VENUS, color_b=VORTEX,
                    start_angle=0.0, dot_size_max=3.2, alpha_max=1.0):
    """
    Disegna un braccio di spirale logaritmica con punti di dimensione crescente.
    """
    for i in range(n_points):
        t = i / (n_points - 1)
        # Angolo: crescita logaritmica
        angle = start_angle + twist * math.log(1 + 8 * t) * 3
        # Raggio: da start a end
        radius_t = t ** 0.85
        r = size * (start_radius + (end_radius - start_radius) * radius_t)

        x = cx + math.cos(angle) * r
        y = cy + math.sin(angle) * r

        # Dimensione punto: cresce verso l'esterno
        dot_r = dot_size_max * (0.25 + 0.75 * t)

        # Colore: dal centro all'esterno (viola -> ciano)
        color = lerp(color_a, color_b, t)

        # Alpha crescente all'esterno (più visibile fuori)
        alpha_factor = (0.35 + 0.65 * t) * alpha_max

        # Disegna punto
        final_color = lerp(SPACE_DEEP, color, alpha_factor)
        draw.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r],
                     fill=final_color)

        # Glow più intenso al centro
        glow_r = dot_r * 3
        glow_color = lerp((0, 0, 0), color, alpha_factor * 0.6)
        glow_draw.ellipse(
            [x - glow_r, y - glow_r, x + glow_r, y + glow_r],
            fill=glow_color
        )


def draw_venus_symbol(draw, cx, cy, size, color=SOLAR):
    """
    Disegna il simbolo di Venere (♀) stilizzato.
    Cerchio con croce in basso.
    """
    # Cerchio
    r = size * 0.055
    width = max(3, int(size * 0.012))
    draw.ellipse([cx - r, cy - r - size * 0.012,
                  cx + r, cy + r - size * 0.012],
                 outline=color, width=width)

    # Asta verticale
    stem_top = cy + r - size * 0.012
    stem_bottom = cy + r + size * 0.045
    draw.line([(cx, stem_top), (cx, stem_bottom)],
              fill=color, width=width)

    # Asta orizzontale
    hw = size * 0.028
    hw_y = stem_bottom - size * 0.008
    draw.line([(cx - hw, hw_y), (cx + hw, hw_y)],
              fill=color, width=width)


def draw_monogram(draw, cx, cy_bottom, size, text="VX", color=TEXT_SOFT):
    """Disegna il monogramma VX in basso."""
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            size=int(size * 0.055)
        )
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", size=int(size * 0.055))
        except Exception:
            font = ImageFont.load_default()

    # Bbox per centrare
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = cx - tw / 2
    y = cy_bottom - th / 2

    # Leggera ombra
    draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0))
    # Testo
    draw.text((x, y), text, font=font, fill=color)


def make_botpic(size=SIZE, path="botpic.png"):
    print(f"[*] Generazione botpic {size}x{size}...")

    # ==========================================
    # 1. IMMAGINE BASE
    # ==========================================
    img = Image.new("RGB", (size, size), SPACE_DEEP)
    draw_radial_background(img, CX, CY, size)

    # ==========================================
    # 2. LAYER GLOW (sfocato)
    # ==========================================
    glow = Image.new("RGB", (size, size), (0, 0, 0))
    gdraw = ImageDraw.Draw(glow)

    # ==========================================
    # 3. SPIRALE VORTEX — 3 bracci
    # ==========================================
    # Braccio 1: viola -> ciano
    draw_spiral_arm(
        ImageDraw.Draw(img), gdraw, CX, CY, size,
        n_points=450, twist=2.6,
        start_radius=0.06, end_radius=0.44,
        color_a=VENUS, color_b=VORTEX,
        start_angle=0.0,
        dot_size_max=3.0,
        alpha_max=1.0,
    )
    # Braccio 2: sfalsato di 120°
    draw_spiral_arm(
        ImageDraw.Draw(img), gdraw, CX, CY, size,
        n_points=450, twist=2.6,
        start_radius=0.06, end_radius=0.44,
        color_a=NEBULA, color_b=VORTEX,
        start_angle=2 * math.pi / 3,
        dot_size_max=2.8,
        alpha_max=0.95,
    )
    # Braccio 3: sfalsato di 240°
    draw_spiral_arm(
        ImageDraw.Draw(img), gdraw, CX, CY, size,
        n_points=450, twist=2.6,
        start_radius=0.06, end_radius=0.44,
        color_a=VENUS, color_b=NEBULA,
        start_angle=4 * math.pi / 3,
        dot_size_max=2.8,
        alpha_max=0.95,
    )

    # ==========================================
    # 4. STELLE NEL BACKGROUND
    # ==========================================
    add_stars(ImageDraw.Draw(img), CX, CY, size, n=220, seed=42)

    # ==========================================
    # 5. NUCLEO CENTRALE
    # ==========================================
    draw = ImageDraw.Draw(img)
    # Alone esterno
    for i in range(60, 0, -1):
        t = i / 60
        r = size * 0.10 * t
        intensity = (1 - t) ** 1.8
        color = lerp(SPACE_PURPLE, VENUS, intensity)
        draw.ellipse([CX - r, CY - r, CX + r, CY + r], fill=color)

    # Sole dorato
    r_sun = size * 0.032
    draw.ellipse([CX - r_sun, CY - r_sun, CX + r_sun, CY + r_sun], fill=SOLAR)
    gdraw.ellipse([CX - r_sun * 4, CY - r_sun * 4,
                   CX + r_sun * 4, CY + r_sun * 4], fill=SOLAR)

    # ==========================================
    # 6. SIMBOLO VENERE (♀)
    # ==========================================
    draw_venus_symbol(draw, CX, CY, size, color=SOLAR)
    draw_venus_symbol(gdraw, CX, CY, size, color=SOLAR)

    # ==========================================
    # 7. ANELLO ESTERNO
    # ==========================================
    r_border = size * 0.47
    border_color = lerp(VENUS, NEBULA, 0.3)
    draw.ellipse(
        [CX - r_border, CY - r_border, CX + r_border, CY + r_border],
        outline=border_color, width=max(2, size // 240)
    )
    # Doppio anello sottile esterno
    r_border2 = size * 0.485
    draw.ellipse(
        [CX - r_border2, CY - r_border2, CX + r_border2, CY + r_border2],
        outline=lerp(SPACE_PURPLE, VENUS, 0.5),
        width=max(1, size // 500)
    )

    # ==========================================
    # 8. MONOGRAMMA VX
    # ==========================================
    draw_monogram(draw, CX, size * 0.88, size, "VX", color=TEXT_SOFT)

    # ==========================================
    # 9. BLUR + COMPOSITE del GLOW
    # ==========================================
    glow_blurred = glow.filter(ImageFilter.GaussianBlur(radius=size // 16))
    final = Image.blend(img, glow_blurred, alpha=0.55)

    # ==========================================
    # 10. SALVA
    # ==========================================
    final.save(path, "PNG", optimize=True)
    file_size_kb = os.path.getsize(path) / 1024
    print(f"[+] Creato: {path} ({size}x{size}, {file_size_kb:.1f} KB)")
    return path


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    make_botpic(640, os.path.join(base, "botpic.png"))
    print("\n[OK] Botpic Venus Vortex generata.")
