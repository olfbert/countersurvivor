#!/usr/bin/env python3
"""Map-Paket fuer Counter-Survivors Phase 1.

Aufruf: python3 -I pack_map.py <bsp> <wad> <skydir> <out.bin>
Inhalt: BSP (ohne VIS/Marksurfaces), alle benutzten Texturen als PNG, Himmel (6 Seiten).
Aufbau: [u32 Laenge JSON][JSON, auf 4 aufgefuellt][Binaerteil]; Offsets relativ zum Binaerteil.
"""
import io
import json
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

LUMP_VIS, LUMP_MARK = 4, 11
TOOL_TEXTURES = {"hint", "skip", "clip", "null", "origin", "aaatrigger", "bevel", "sky"}


def cstr(b):
    return b.split(b"\0")[0].decode("latin1")


def strip_bsp(d):
    ver = struct.unpack("<i", d[:4])[0]
    assert ver == 30, ver
    lumps = [struct.unpack("<ii", d[4 + i * 8:12 + i * 8]) for i in range(15)]
    out = bytearray(4 + 15 * 8)
    struct.pack_into("<i", out, 0, ver)
    for i, (o, l) in enumerate(lumps):
        data = b"" if i in (LUMP_VIS, LUMP_MARK) else d[o:o + l]
        while len(out) % 4:
            out.append(0)
        struct.pack_into("<ii", out, 4 + i * 8, len(out), len(data))
        out += data
    return bytes(out)


def bsp_textures(d):
    o, l = struct.unpack("<ii", d[4 + 2 * 8:12 + 2 * 8])
    n = struct.unpack("<i", d[o:o + 4])[0]
    offs = struct.unpack(f"<{n}i", d[o + 4:o + 4 + 4 * n])
    res = []
    for off in offs:
        if off < 0:
            res.append(None)
            continue
        t = d[o + off:o + off + 40]
        name = cstr(t[:16])
        w, h = struct.unpack("<II", t[16:24])
        res.append((name, w, h))
    return res


def wad_index(wad):
    d = open(wad, "rb").read()
    magic, n, off = struct.unpack("<4sii", d[:12])
    idx = {}
    for i in range(n):
        e = d[off + i * 32: off + (i + 1) * 32]
        filepos = struct.unpack("<i", e[:4])[0]
        idx[cstr(e[16:32]).lower()] = filepos
    return d, idx


def wad_image(d, filepos, name):
    w, h = struct.unpack("<II", d[filepos + 16:filepos + 24])
    offs = struct.unpack("<4I", d[filepos + 24:filepos + 40])
    pix = d[filepos + offs[0]: filepos + offs[0] + w * h]
    palo = filepos + offs[3] + (w // 8) * (h // 8) + 2
    pal = d[palo:palo + 768]
    img = Image.frombytes("P", (w, h), pix)
    img.putpalette(pal)
    masked = name.startswith("{")
    if masked:
        # Index 255 = durchsichtig. Farbe der durchsichtigen Pixel aus Nachbarn auffuellen,
        # damit beim Filtern keine blauen Saeume entstehen.
        rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
        a = (np.frombuffer(pix, dtype=np.uint8).reshape(h, w) != 255).astype(np.float32)
        col, wgt = rgb * a[..., None], a.copy()
        for _ in range(8):
            if wgt.min() > 0:
                break
            acc = np.zeros_like(col); accw = np.zeros_like(wgt)
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                acc += np.roll(np.roll(col, dy, 0), dx, 1); accw += np.roll(np.roll(wgt, dy, 0), dx, 1)
            fill = (wgt == 0) & (accw > 0)
            col[fill] = acc[fill] / accw[fill, None]; wgt[fill] = 1
        out = np.concatenate([col.clip(0, 255), (a * 255)[..., None]], -1).astype(np.uint8)
        img = Image.fromarray(out, "RGBA")
    return img, masked


def png(img, **kw):
    b = io.BytesIO()
    img.save(b, "PNG", optimize=True, **kw)
    return b.getvalue()


def jpg(img, q=90):
    b = io.BytesIO()
    img.convert("RGB").save(b, "JPEG", quality=q, optimize=True)
    return b.getvalue()


def fallback(name, w, h):
    """Ersatz fuer Texturen, die nicht in der WAD stecken."""
    w, h = max(16, w), max(16, h)
    if "lgt" in name.lower() or "light" in name.lower():
        img = Image.new("RGB", (w, h), (255, 244, 214))
        dr = ImageDraw.Draw(img)
        dr.rectangle([0, 0, w - 1, h - 1], outline=(150, 132, 104), width=max(1, w // 16))
        return img
    rng = np.random.default_rng(11)
    base = rng.normal(132, 9, (h, w)).clip(0, 255).astype(np.uint8)
    return Image.fromarray(np.stack([base, (base * 0.97).astype(np.uint8), (base * 0.9).astype(np.uint8)], -1))


def edge_diff(a, b):
    return float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean())


def main():
    bsp_path, wad_path, skydir, out = sys.argv[1:5]
    bsp = open(bsp_path, "rb").read()
    blobs = bytearray()

    def add(b):
        nonlocal blobs
        while len(blobs) % 4:
            blobs.append(0)
        o = len(blobs)
        blobs += b
        return [o, len(b)]

    man = {"bsp": None, "textures": {}, "sky": {}, "skyYaw": 0}
    stripped = strip_bsp(bsp)
    man["bsp"] = add(stripped)
    wd, widx = wad_index(wad_path)
    total = 0
    for t in bsp_textures(bsp):
        if t is None:
            continue
        name, w, h = t
        key = name.lower()
        if key in TOOL_TEXTURES or key in man["textures"]:
            continue
        if key in widx:
            img, masked = wad_image(wd, widx[key], name)
            data = png(img)
            man["textures"][key] = {"data": add(data), "w": img.width, "h": img.height, "masked": masked, "type": "image/png"}
            src = "WAD"
        else:
            img = fallback(name, w, h)
            data = png(img)
            man["textures"][key] = {"data": add(data), "w": img.width, "h": img.height, "masked": False, "type": "image/png", "fallback": True}
            src = "Ersatz"
        total += len(data)
        print(f"  {name:20s} {w}x{h} {len(data) // 1024:4d} KB {src}")
    print(f"Texturen: {len(man['textures'])} Stueck, {total // 1024} KB")

    # Himmel: Zuordnung per Kantenabgleich ermittelt (siehe skymatch.py):
    # Zyklus nach rechts img2 -> img6 -> img5 -> img3; Oberkanten passen zum Up-Bild (img4).
    # Konvention im Renderer: rt=+X, ft=-Y, lf=-X, bk=+Y; Up-Bild: unterste Zeile (links->rechts) = Oberkante ft.
    # Mit skyYaw=+90 Grad liegt die Sonne bei ~233 Grad (Lightmaps: hellste Waende bei ~225 Grad).
    im = {i: Image.open(f"{skydir}/img{i}.jpg").convert("RGB") for i in range(1, 7)}
    faces = {"ft": im[3], "lf": im[2], "bk": im[6], "rt": im[5], "up": im[4]}
    # Pruefen: Oberkante ft == unterste Zeile up; rechte Kante rt == linke Kante ft usw.
    A = {k: np.asarray(v) for k, v in faces.items()}
    checks = {
        "up/ft": edge_diff(A["up"][-1], A["ft"][0]),
        "rt->ft": edge_diff(A["rt"][:, -1], A["ft"][:, 0]),
        "ft->lf": edge_diff(A["ft"][:, -1], A["lf"][:, 0]),
        "lf->bk": edge_diff(A["lf"][:, -1], A["bk"][:, 0]),
        "bk->rt": edge_diff(A["bk"][:, -1], A["rt"][:, 0]),
    }
    print("Himmel-Kanten:", {k: round(v, 1) for k, v in checks.items()})
    assert all(v < 10 for v in checks.values()), checks
    for k, v in faces.items():
        man["sky"][k] = add(jpg(v, 92))
    man["skyYaw"] = 90
    js = json.dumps(man, separators=(",", ":")).encode("utf-8")
    while len(js) % 4:
        js += b" "
    open(out, "wb").write(struct.pack("<I", len(js)) + js + bytes(blobs))
    print("Paket:", (4 + len(js) + len(blobs)) // 1024, "KB (BSP", len(stripped) // 1024, "KB)")


if __name__ == "__main__":
    main()
