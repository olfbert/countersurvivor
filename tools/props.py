"""Deko-Modelle (cycler_sprite / env_model) einer Map als statische Meshes packen.

Je Modell: Ruhepose (Sequenz 0, Frame 0) fest eingerechnet, Dreiecke gegen den Uhrzeigersinn,
alle Texturen der Map in einem gemeinsamen Atlas. Die Platzierung (origin, angles, scale)
liest das Spiel selbst aus den Entities der BSP.
"""
import hashlib
import io
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from convert_mdl import MDL, cstr, quat_mat, mat_mul, pack_atlas  # noqa: E402

from PIL import Image  # noqa: E402

PROP_CLASSES = {"cycler_sprite", "env_model", "cycler", "monster_furniture", "item_generic"}


def bsp_entities(bsp):
    off, ln = struct.unpack_from("<ii", bsp, 4)
    text = bsp[off:off + ln].decode("latin1")
    out = []
    for blk in re.findall(r"\{([^{}]*)\}", text):
        out.append(dict(re.findall(r'"([^"]*)"\s*"([^"]*)"', blk)))
    return out


def find_model(models_dir, path):
    base = os.path.basename(path.replace("\\", "/")).lower()
    for root, _, files in os.walk(models_dir):
        for f in files:
            if f.lower() == base:
                return os.path.join(root, f)
    return None


def static_mesh(m):
    """Liefert (Dreiecksliste [(tex, [(pos, nrm, s, t)]*3)], benutzte Texturen)."""
    d = m.d
    seq0 = cstr(d[m.seqindex:m.seqindex + 32]) if m.numseq else None
    mats = []
    if seq0:
        fr = m.sequence(seq0)["frames"][0]
        for j, b in enumerate(m.bones):
            q, p = fr[j]
            lm = quat_mat(q, p)
            mats.append(lm if b["parent"] < 0 else mat_mul(mats[b["parent"]], lm))
    else:
        mats = [[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]] for _ in m.bones]

    def xf(j, v, w):
        M = mats[j]
        return tuple(M[i][0] * v[0] + M[i][1] * v[1] + M[i][2] * v[2] + M[i][3] * w for i in range(3))

    tris = []
    for bp in range(m.numbodyparts):
        part = m.meshes(bp, 0)
        if not part:
            continue
        for tex, tl in part["meshes"]:
            for tri in tl:
                corners = []
                for (vi, ni, s, t) in tri:
                    corners.append((xf(part["vbone"][vi], part["verts"][vi], 1.0),
                                    xf(part["nbone"][ni], part["norms"][ni], 0.0), s, t))
                tris.append((tex, corners))
    # Windung: Geometrie-Normale gegen Vertex-Normalen, Mehrheit entscheidet
    good = bad = 0
    for _, c in tris:
        a, b, cc = c[0][0], c[1][0], c[2][0]
        e1 = [b[i] - a[i] for i in range(3)]
        e2 = [cc[i] - a[i] for i in range(3)]
        gn = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
        vn = [c[0][1][i] + c[1][1][i] + c[2][1][i] for i in range(3)]
        if sum(gn[i] * vn[i] for i in range(3)) >= 0:
            good += 1
        else:
            bad += 1
    if bad > good:
        tris = [(t, [c[0], c[2], c[1]]) for t, c in tris]
    return tris, sorted({t for t, _ in tris})


def pack_props(bsp, models_dir, add, jpg, png):
    ents = bsp_entities(bsp)
    names = sorted({e["model"].lower() for e in ents
                    if e.get("classname") in PROP_CLASSES and e.get("model", "").lower().endswith(".mdl")})
    if not names:
        return None
    found, missing = {}, []
    for n in names:
        p = find_model(models_dir, n)
        (found.__setitem__(n, p) if p else missing.append(n))
    if not found:
        return {"models": {}, "missing": missing}
    # Texturen sammeln (gleiche Textur in mehreren Modellen nur einmal)
    imgs, keyof = [], {}
    meshes = {}
    for n, p in found.items():
        m = MDL(p)
        tris, used = static_mesh(m)
        texmap = {}
        for t in used:
            T = m.textures[t]
            raw = m.d[T["idx"]:T["idx"] + T["w"] * T["h"] + 768]
            h = hashlib.sha1(raw + bytes([T["flags"] & 0x40])).hexdigest()
            if h not in keyof:
                keyof[h] = len(imgs)
                imgs.append((len(imgs), m.texture_rgba(T), bool(T["flags"] & 0x40)))
            texmap[t] = (keyof[h], T["w"], T["h"])
        meshes[n] = (tris, texmap)
    atlas, rects = pack_atlas([(i, img) for i, img, _ in imgs])
    AW, AH = atlas.size
    masked = any(mk for _, _, mk in imgs)
    out = {"models": {}, "missing": missing, "atlasSize": [AW, AH], "masked": masked}
    out["atlas"] = add(png(atlas) if masked else jpg(atlas, 86))
    out["atlasType"] = "image/png" if masked else "image/jpeg"
    for n, (tris, texmap) in meshes.items():
        vmap, verts, idx = {}, [], []
        mins, maxs = [1e9] * 3, [-1e9] * 3
        for tex, corners in tris:
            ai, tw, th = texmap[tex]
            ox, oy = rects[ai]
            ids = []
            for (p, nr, s, t) in corners:
                k = (p, nr, s, t, ai)
                if k not in vmap:
                    vmap[k] = len(verts)
                    ln = max(1e-6, (nr[0] ** 2 + nr[1] ** 2 + nr[2] ** 2) ** 0.5)
                    verts.append((*p, *(c / ln for c in nr), (ox + s) / AW, (oy + t) / AH))
                    for i in range(3):
                        mins[i] = min(mins[i], p[i]); maxs[i] = max(maxs[i], p[i])
                ids.append(vmap[k])
            idx.append(ids)
        vb = struct.pack(f"<{len(verts) * 8}f", *[c for v in verts for c in v])
        ib = struct.pack(f"<{len(idx) * 3}H", *[c for t in idx for c in t])
        out["models"][n] = {"verts": add(vb), "idx": add(ib), "numVerts": len(verts), "numIdx": len(idx) * 3,
                            "mins": [round(c, 2) for c in mins], "maxs": [round(c, 2) for c in maxs]}
        print(f"  Prop {os.path.basename(n):24s} {len(verts):5d} Vertices {len(idx):5d} Dreiecke "
              f"Groesse {[round(maxs[i] - mins[i]) for i in range(3)]}")
    print(f"  Prop-Atlas {AW}x{AH}, {len(imgs)} Texturen; fehlend: {missing or 'keine'}")
    return out
