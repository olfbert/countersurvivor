"""Uebersichtskarte (CS-Overview, gruener Hintergrund) an die Map-Geometrie anpassen.

Ermittelt die Abbildung Welt (x, y) -> Bildpixel (u, v) automatisch: Draufsicht-Maske aller nach oben
zeigenden Flaechen gegen die nicht-gruene Bildmaske, 8 Orientierungen, Massstab und Versatz per IoU.
Ergebnis: Bild als PNG mit Alpha + affine Matrix [a, b, c, d, e, f] mit u = a*x + b*y + c, v = d*x + e*y + f.
"""
import io
import struct

import numpy as np
from PIL import Image, ImageDraw


def world_mask(bsp, res=8.0):
    L = [struct.unpack_from("<ii", bsp, 4 + i * 8) for i in range(15)]
    o, l = L[1]
    planes = [struct.unpack_from("<4f", bsp, o + i * 20) for i in range(l // 20)]
    o, l = L[3]
    verts = np.frombuffer(bsp[o:o + l], dtype="<f4").reshape(-1, 3)
    o, l = L[12]
    edges = np.frombuffer(bsp[o:o + l], dtype="<u2").reshape(-1, 2)
    o, l = L[13]
    surf = np.frombuffer(bsp[o:o + l], dtype="<i4")
    to, tl = L[6]
    mo, ml = L[2]
    nmip = struct.unpack_from("<i", bsp, mo)[0]
    mipoff = struct.unpack_from(f"<{nmip}i", bsp, mo + 4)

    def texname(ti):
        mip = struct.unpack_from("<i", bsp, to + ti * 40 + 32)[0]
        off = mipoff[mip]
        return bsp[mo + off:mo + off + 16].split(b"\0")[0].decode("latin1").lower() if off >= 0 else ""

    o, l = L[14]
    first, num = struct.unpack_from("<ii", bsp, o + 56)
    fo = L[7][0]
    polys = []
    for fi in range(first, first + num):
        pl, side, fe, ne, ti = struct.unpack_from("<HhihH", bsp, fo + fi * 20)
        nz = planes[pl][2] * (-1 if side else 1)
        if nz < 0.3:
            continue
        name = texname(ti)
        if name.startswith("sky") or name in ("aaatrigger", "clip", "null", "skip", "hint", "origin"):
            continue
        pts = []
        for k in range(ne):
            e = surf[fe + k]
            vi = edges[e][0] if e >= 0 else edges[-e][1]
            pts.append(verts[vi][:2])
        polys.append(np.array(pts))
    allp = np.concatenate(polys)
    mn, mx = allp.min(0) - 64, allp.max(0) + 64
    W, H = int((mx[0] - mn[0]) / res) + 1, int((mx[1] - mn[1]) / res) + 1
    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    for p in polys:
        # Zeile 0 = groesstes y (Draufsicht, Norden oben)
        dr.polygon([((x - mn[0]) / res, (mx[1] - y) / res) for x, y in p], fill=255)
    return np.asarray(img) > 0, mn, mx, res


# 8 Orientierungen als 2x2-Matrizen auf (x, y) Welt -> (u', v') vor Skalierung, mit v nach unten
ORIENTS = [np.array(m, float) for m in (
    [[1, 0], [0, -1]], [[-1, 0], [0, 1]], [[0, 1], [1, 0]], [[0, -1], [-1, 0]],
    [[1, 0], [0, 1]], [[-1, 0], [0, -1]], [[0, 1], [-1, 0]], [[0, -1], [1, 0]],
)]


def calibrate(bsp, img_path, out_w=512):
    src = Image.open(img_path).convert("RGB")
    a = np.asarray(src).astype(np.int16)
    green = (a[..., 1] > 170) & (a[..., 0] < 110) & (a[..., 2] < 110)
    imask = ~green
    IH, IW = imask.shape
    wm, mn, mx, res = world_mask(bsp)
    ys, xs = np.nonzero(wm)
    # Weltpunkte der Maske (Stichprobe)
    rng = np.random.default_rng(1)
    sel = rng.choice(len(xs), size=min(60000, len(xs)), replace=False)
    wx = mn[0] + (xs[sel] + 0.5) * res
    wy = mx[1] - (ys[sel] + 0.5) * res
    # Bildpunkte (Stichprobe) fuer die Gegenrichtung
    iy, ix = np.nonzero(imask)
    isel = rng.choice(len(ix), size=min(60000, len(ix)), replace=False)
    ipx, ipy = ix[isel] + 0.5, iy[isel] + 0.5
    ib = (ix.min(), iy.min(), ix.max() + 1, iy.max() + 1)

    def score(M):
        """Symmetrische Trefferquote: Weltpunkte im Bild nicht gruen und Bildpunkte auf Weltgeometrie."""
        u = M[0, 0] * wx + M[0, 1] * wy + M[0, 2]
        v = M[1, 0] * wx + M[1, 1] * wy + M[1, 2]
        ok = (u >= 0) & (v >= 0) & (u < IW) & (v < IH)
        hit1 = np.zeros(len(u), bool)
        hit1[ok] = imask[v[ok].astype(int), u[ok].astype(int)]
        A = M[:, :2]
        Ai = np.linalg.inv(A)
        dx, dy = ipx - M[0, 2], ipy - M[1, 2]
        X = Ai[0, 0] * dx + Ai[0, 1] * dy
        Y = Ai[1, 0] * dx + Ai[1, 1] * dy
        c = ((X - mn[0]) / res).astype(int)
        r = ((mx[1] - Y) / res).astype(int)
        ok2 = (c >= 0) & (r >= 0) & (c < wm.shape[1]) & (r < wm.shape[0])
        hit2 = np.zeros(len(X), bool)
        hit2[ok2] = wm[r[ok2], c[ok2]]
        return hit1.mean() * hit2.mean()

    best = (-1, None)
    for R in ORIENTS:
        # Startwert: Bounding-Boxen aufeinander legen
        corners = np.array([[mn[0], mn[1]], [mx[0], mn[1]], [mn[0], mx[1]], [mx[0], mx[1]]]) @ R.T
        cmin, cmax = corners.min(0), corners.max(0)
        s = min((ib[2] - ib[0]) / (cmax[0] - cmin[0]), (ib[3] - ib[1]) / (cmax[1] - cmin[1]))
        t = np.array([(ib[0] + ib[2]) / 2, (ib[1] + ib[3]) / 2]) - s * (cmin + cmax) / 2
        params = np.array([s, t[0], t[1]])

        def mk(p):
            return np.hstack([R * p[0], p[1:3, None]])
        cur = score(mk(params))
        steps = np.array([s * 0.08, 24.0, 24.0])
        for _ in range(60):
            improved = False
            for k in range(3):
                for sg in (1, -1):
                    q = params.copy()
                    q[k] += sg * steps[k]
                    sc = score(mk(q))
                    if sc > cur:
                        cur, params, improved = sc, q, True
            if not improved:
                steps *= 0.5
                if steps[1] < 0.25:
                    break
        if cur > best[0]:
            best = (cur, mk(params))
    sc, M = best
    # Bild verkleinern, Gruen -> durchsichtig
    k = out_w / IW
    rgba = np.dstack([np.asarray(src), (imask * 255).astype(np.uint8)])
    small = Image.fromarray(rgba, "RGBA").resize((out_w, round(IH * k)), Image.LANCZOS)
    M2 = M * k
    b = io.BytesIO()
    small.save(b, "WEBP", quality=82, method=6)
    return b.getvalue(), [float(x) for x in M2.flatten()], small.size, sc
