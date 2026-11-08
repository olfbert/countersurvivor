#!/usr/bin/env python3
"""Icons fuer HUD und Kaufmenue als JSON mit PNG-Data-URLs.

Aufruf: python3 -I pack_icons.py <gfx-ordner> <wad> <out.json>
Nimmt VGUI/XGUI-Icons aus Counter-Strike, zeichnet fehlende (Messer, Laufschuhe, Geldkoffer, Geldschein)
und legt Kisten-Texturen aus der WAD dazu.
"""
import base64
import io
import json
import struct
import sys

from PIL import Image, ImageDraw, ImageFilter

GFX, WAD, OUT = sys.argv[1:4]

ICONS = {
    "usp": "xgui/usp45", "glock": "xgui/glock18", "deagle": "vgui/deserteagle", "mp5": "xgui/mp5",
    "m3": "vgui/m3", "ak47": "vgui/ak47", "he": "vgui/hegrenade", "kevlar": "vgui/kevlar",
    "defuser": "vgui/defuser", "nightvision": "vgui/nightvision", "bullet": "vgui/bullet",
    "cartridge": "vgui/cartridge", "shell": "vgui/shell", "awp": "xgui/awp", "m249": "vgui/m249",
    "elites": "vgui/elites", "flash": "vgui/flashbang", "smoke": "vgui/smokegrenade",
}


def trim(im, pad=4):
    bb = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if not bb:
        return im
    im = im.crop(bb)
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad))
    out.paste(im, (pad, pad))
    return out


def fit(im, w=200, h=84):
    s = min(w / im.width, h / im.height, 1.0)
    return im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)


def data_url(im):
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def part(size, poly_fn, top, bottom, edge=(18, 18, 20)):
    """Eine Silhouette mit senkrechtem Farbverlauf (top->bottom) und dunkler Kante, doppelt aufgeloest."""
    W, H = size[0] * 2, size[1] * 2
    mask = Image.new("L", (W, H))
    poly_fn(ImageDraw.Draw(mask), W, H)
    grad = Image.new("RGBA", (W, H))
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        t = y / max(1, H - 1)
        gd.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,))
    out = Image.new("RGBA", (W, H))
    out.paste(edge + (255,), (0, 0), mask.filter(ImageFilter.MaxFilter(5)))
    out.paste(grad, (0, 0), mask)
    return out


def combine(size, parts):
    W, H = size[0] * 2, size[1] * 2
    out = Image.new("RGBA", (W, H))
    for p in parts:
        out.alpha_composite(p)
    return out.resize(size, Image.LANCZOS)


def knife_icon():
    S = (230, 70)
    P = lambda pts: (lambda d, W, H: d.polygon([(int(W * x), int(H * y)) for x, y in pts], fill=255))
    blade = part(S, P([(.40, .30), (.76, .30), (.98, .50), (.90, .58), (.74, .66), (.40, .68)]), (232, 236, 240), (120, 124, 130))
    fuller = part(S, P([(.44, .40), (.72, .40), (.72, .46), (.44, .46)]), (150, 154, 160), (150, 154, 160), edge=(120, 124, 130))
    guard = part(S, lambda d, W, H: d.rounded_rectangle([int(W * .35), int(H * .14), int(W * .40), int(H * .86)], radius=int(H * .04), fill=255), (90, 90, 96), (40, 40, 44))
    def handle(d, W, H):
        d.rounded_rectangle([int(W * .05), int(H * .30), int(W * .36), int(H * .70)], radius=int(H * .14), fill=255)
    hnd = part(S, handle, (60, 58, 56), (22, 22, 22))
    grooves = Image.new("RGBA", (S[0] * 2, S[1] * 2)); gd = ImageDraw.Draw(grooves)
    for k in range(4):
        x = int(S[0] * 2 * (.10 + k * .06)); gd.line([(x, int(S[1] * 2 * .34)), (x, int(S[1] * 2 * .66))], fill=(10, 10, 10, 255), width=3)
    pommel = part(S, lambda d, W, H: d.ellipse([int(W * .02), int(H * .34), int(W * .08), int(H * .66)], fill=255), (120, 120, 126), (50, 50, 54))
    return combine(S, [blade, fuller, hnd, grooves, guard, pommel])


def boot_icon():
    S = (200, 110)
    P = lambda pts: (lambda d, W, H: d.polygon([(int(W * x), int(H * y)) for x, y in pts], fill=255))
    upper = part(S, P([(.12, .84), (.14, .10), (.42, .10), (.44, .46), (.66, .52), (.86, .58), (.94, .70), (.95, .84)]), (92, 70, 48), (38, 28, 20))
    sole = part(S, P([(.09, .82), (.97, .82), (.97, .92), (.09, .92)]), (40, 38, 36), (14, 14, 14))
    laces = Image.new("RGBA", (S[0] * 2, S[1] * 2)); ld = ImageDraw.Draw(laces)
    for k in range(5):
        y = int(S[1] * 2 * (.18 + k * .07)); x = int(S[0] * 2 * (.38 + k * .015))
        ld.line([(x - 18, y), (x + 14, y + 6)], fill=(200, 190, 160, 255), width=3)
    return combine(S, [upper, sole, laces])


def briefcase_icon():
    S = (160, 120)
    body = part(S, lambda d, W, H: d.rounded_rectangle([int(W * .14), int(H * .32), int(W * .86), int(H * .90)], radius=int(H * .06), fill=255), (70, 52, 34), (34, 24, 16))
    handle = part(S, lambda d, W, H: d.rounded_rectangle([int(W * .38), int(H * .12), int(W * .62), int(H * .34)], radius=int(H * .06), outline=255, width=int(H * .08)), (60, 60, 60), (30, 30, 30))
    locks = part(S, lambda d, W, H: (d.rectangle([int(W * .28), int(H * .36), int(W * .36), int(H * .44)], fill=255), d.rectangle([int(W * .64), int(H * .36), int(W * .72), int(H * .44)], fill=255)), (230, 200, 120), (160, 130, 60))
    return combine(S, [body, handle, locks])


def c4_icon():
    S = (200, 110)
    P = lambda box, r=6: (lambda d, W, H: d.rounded_rectangle([int(W * box[0]), int(H * box[1]), int(W * box[2]), int(H * box[3])], radius=r, fill=255))
    body = part(S, P((.08, .30, .92, .86)), (120, 124, 96), (62, 64, 48))
    tape = part(S, P((.30, .30, .40, .86), 2), (40, 40, 36), (24, 24, 22))
    tape2 = part(S, P((.62, .30, .72, .86), 2), (40, 40, 36), (24, 24, 22))
    pad = part(S, P((.36, .12, .66, .44), 4), (52, 54, 50), (20, 20, 20))
    disp = part(S, P((.40, .18, .62, .30), 2), (255, 70, 50), (190, 30, 20), edge=(40, 10, 10))
    wires = Image.new("RGBA", (S[0] * 2, S[1] * 2)); wd = ImageDraw.Draw(wires)
    wd.line([(int(S[0] * 2 * .66), int(S[1] * 2 * .3)), (int(S[0] * 2 * .86), int(S[1] * 2 * .12))], fill=(200, 40, 30, 255), width=5)
    wd.line([(int(S[0] * 2 * .36), int(S[1] * 2 * .3)), (int(S[0] * 2 * .16), int(S[1] * 2 * .14))], fill=(40, 90, 200, 255), width=5)
    return combine(S, [body, tape, tape2, wires, pad, disp])


def hs_icon():
    S = (120, 120)
    W, H = S[0] * 2, S[1] * 2
    out = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(out)
    d.ellipse([20, 20, W - 20, H - 20], outline=(20, 20, 22, 255), width=22)
    d.ellipse([24, 24, W - 24, H - 24], outline=(200, 205, 210, 255), width=12)
    for a, b in (((W // 2, 4), (W // 2, 70)), ((W // 2, H - 70), (W // 2, H - 4)), ((4, H // 2), (70, H // 2)), ((W - 70, H // 2), (W - 4, H // 2))):
        d.line([a, b], fill=(20, 20, 22, 255), width=16); d.line([a, b], fill=(200, 205, 210, 255), width=8)
    d.ellipse([W // 2 - 18, H // 2 - 18, W // 2 + 18, H // 2 + 18], fill=(230, 40, 30, 255), outline=(60, 10, 10, 255), width=4)
    return out.resize(S, Image.LANCZOS)


def main():
    out = {}
    for k, path in ICONS.items():
        im = Image.open(f"{GFX}/{path}.tga").convert("RGBA")
        out[k] = data_url(fit(trim(im)))
    # Helm aus dem Kevlar+Helm-Icon (rechte Haelfte)
    kh = Image.open(f"{GFX}/vgui/kevlar_helmet.tga").convert("RGBA")
    out["helm"] = data_url(fit(trim(kh.crop((kh.width // 2, 0, kh.width, kh.height)))))
    out["knife"] = data_url(fit(trim(knife_icon())))
    out["shoes"] = data_url(fit(trim(boot_icon())))
    out["briefcase"] = data_url(fit(trim(briefcase_icon())))
    out["c4"] = data_url(fit(trim(c4_icon())))
    out["hstrain"] = data_url(fit(trim(hs_icon())))
    # Kisten-Texturen aus der WAD (Waffenkiste)
    d = open(WAD, "rb").read()
    magic, n, off = struct.unpack("<4sii", d[:12])
    for i in range(n):
        e = d[off + i * 32: off + (i + 1) * 32]
        name = e[16:32].split(b"\0")[0].decode("latin1").lower()
        if name not in ("crate_gunt01", "crate_guns01"):
            continue
        fp = struct.unpack("<i", e[:4])[0]
        w, h = struct.unpack("<II", d[fp + 16:fp + 24])
        offs = struct.unpack("<4I", d[fp + 24:fp + 40])
        img = Image.frombytes("P", (w, h), d[fp + offs[0]: fp + offs[0] + w * h])
        palo = fp + offs[3] + (w // 8) * (h // 8) + 2
        img.putpalette(d[palo:palo + 768])
        out["tex_" + name] = data_url(img.convert("RGB"))
    js = json.dumps(out, separators=(",", ":"))
    open(OUT, "w").write(js)
    print(len(out), "Icons,", len(js) // 1024, "KB")


if __name__ == "__main__":
    main()
