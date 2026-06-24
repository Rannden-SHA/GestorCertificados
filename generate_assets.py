# -*- coding: utf-8 -*-
"""Genera el icono, el logo y el splash de la aplicacion en gestor/assets/."""
import os
from PIL import Image, ImageDraw, ImageFont

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gestor", "assets")
os.makedirs(ASSETS, exist_ok=True)

NAVY = (31, 78, 120); NAVY2 = (12, 35, 58); GOLD = (220, 160, 48)
WHITE = (255, 255, 255); GREY = (203, 209, 218)


def font(sz, bold=True):
    name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", name), sz)
    except Exception:
        return ImageFont.load_default()


def vgrad(w, h, c1, c2):
    img = Image.new("RGB", (w, h), c1)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return img


def draw_badge(d, x, y, s):
    """Documento blanco con sello dorado y check."""
    dw, dh = int(s * 0.46), int(s * 0.58)
    dx, dy = x + int(s * 0.17), y + int(s * 0.18)
    d.rounded_rectangle([dx, dy, dx + dw, dy + dh], radius=max(2, int(s * 0.04)), fill=WHITE)
    for i in range(4):
        ly = dy + int(dh * 0.16) + i * int(dh * 0.15)
        d.rounded_rectangle([dx + int(dw * 0.15), ly, dx + int(dw * 0.72), ly + max(2, int(s * 0.022))],
                            radius=2, fill=GREY)
    cx, cy, r = x + int(s * 0.66), y + int(s * 0.66), int(s * 0.17)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=WHITE, width=max(2, int(s * 0.012)))
    w = max(3, int(s * 0.04))
    d.line([(int(cx - r * 0.45), int(cy + r * 0.02)),
            (int(cx - r * 0.08), int(cy + r * 0.42)),
            (int(cx + r * 0.5), int(cy - r * 0.42))], fill=WHITE, width=w, joint="curve")


def make_icon(sz):
    base = vgrad(sz, sz, NAVY, NAVY2).convert("RGBA")
    mask = Image.new("L", (sz, sz), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sz - 1, sz - 1], radius=int(sz * 0.22), fill=255)
    base.putalpha(mask)
    draw_badge(ImageDraw.Draw(base), 0, 0, sz)
    return base


big = make_icon(256)
big.save(os.path.join(ASSETS, "icono.ico"),
         sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
big.resize((128, 128)).save(os.path.join(ASSETS, "logo.png"))

# ---- Splash ----
W, H = 580, 340
sp = vgrad(W, H, NAVY, NAVY2)
d = ImageDraw.Draw(sp)
d.rectangle([0, 0, W, 6], fill=GOLD)
draw_badge(d, 26, 78, 190)
tx = 250
d.text((tx, 92), "Gestor de", font=font(30), fill=WHITE)
d.text((tx, 128), "Certificados", font=font(30), fill=WHITE)
d.text((tx, 164), "Fiscales", font=font(30), fill=GOLD)
d.text((tx, 212), "Lectura automatica de certificados", font=font(13, False), fill=(196, 208, 224))
d.text((tx, 230), "y avisos de caducidad", font=font(13, False), fill=(196, 208, 224))
d.text((26, H - 34), "(c) 2026 Adrian Gisbert  -  Todos los derechos reservados",
       font=font(12, False), fill=(168, 184, 206))
sp.save(os.path.join(ASSETS, "splash.png"))

print("Assets generados en", ASSETS)
