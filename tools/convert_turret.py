#!/usr/bin/env python3
"""Portal-Geschuetzturm (Source-SMD + PNG) -> kompaktes Paket fuer Counter-Survivors.

Aufruf: python3 -I convert_turret.py <Turret-Ordner> <out.bin>
Inhalt: Vertices im Raum ihres Knochens (starr, 1 Knochen je Vertex), Bind-Pose der 9 Knochen,
Verschiebungen der Fluegel/Rohre fuer "deploy" und "fire", Textur als JPEG, Augenposition (Laser).
Modell wird so gedreht, dass die Linse nach +X schaut (wie die Spielermodelle).
"""
import io
import json
import math
import os
import struct
import sys

from PIL import Image


def parse_smd(path):
    nodes, frames, tris = [], [], []
    mode = None
    lines = open(path, encoding="latin1").read().splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        i += 1
        if ln in ("nodes", "skeleton", "triangles"):
            mode = ln
            continue
        if ln == "end":
            mode = None
            continue
        if mode == "nodes":
            a = ln.split('"')
            nodes.append((a[1], int(a[2])))
        elif mode == "skeleton":
            if ln.startswith("time"):
                frames.append({})
            else:
                v = ln.split()
                frames[-1][int(v[0])] = [float(x) for x in v[1:7]]
        elif mode == "triangles":
            corners = []
            for k in range(3):
                v = lines[i + k].split()
                bone = int(v[0])
                p = [float(x) for x in v[1:4]]
                n = [float(x) for x in v[4:7]]
                uv = [float(v[7]), float(v[8])]
                if len(v) > 9 and int(v[9]) > 0:   # staerkster Knochen gewinnt
                    links = [(int(v[10 + 2 * j]), float(v[11 + 2 * j])) for j in range(int(v[9]))]
                    bone = max(links, key=lambda t: t[1])[0]
                corners.append((bone, p, n, uv))
            i += 3
            tris.append(corners)
    return nodes, frames, tris


def euler(rx, ry, rz):
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    # R = Rz * Ry * Rx
    return [[cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
            [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
            [-sy, cy * sx, cy * cx]]


def mat(pos, rot):
    R = euler(*rot)
    return [R[0] + [pos[0]], R[1] + [pos[1]], R[2] + [pos[2]]]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) + (a[i][3] if j == 3 else 0) for j in range(4)] for i in range(3)]


def inv(m):
    R = [[m[j][i] for j in range(3)] for i in range(3)]
    t = [-sum(R[i][k] * m[k][3] for k in range(3)) for i in range(3)]
    return [R[i] + [t[i]] for i in range(3)]


def xf(m, v, w=1.0):
    return [m[i][0] * v[0] + m[i][1] * v[1] + m[i][2] * v[2] + m[i][3] * w for i in range(3)]


def main():
    src, out = sys.argv[1:3]
    nodes, frames, tris = parse_smd(os.path.join(src, "turret_01_reference.smd"))
    bind = frames[0]
    # Wurzel: +90 Grad um Z, damit "vorne" (-Y im Modell, Seite mit den Rohren) zu +X wird
    root = [[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0]]
    world = []
    for b, (name, parent) in enumerate(nodes):
        local = mat(bind[b][:3], bind[b][3:])
        world.append(mul(root if parent < 0 else world[parent], local))
    invw = [inv(m) for m in world]
    vmap, verts, idx = {}, [], []
    for c in tris:
        a, b_, cc = (xf(root, c[k][1]) for k in range(3))
        e1 = [b_[i] - a[i] for i in range(3)]
        e2 = [cc[i] - a[i] for i in range(3)]
        gn = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
        vn = [sum(c[k][2][i] for k in range(3)) for i in range(3)]
        order = (0, 1, 2) if sum(gn[i] * vn[i] for i in range(3)) >= 0 else (0, 2, 1)
        ids = []
        for k in order:
            bone, p, n, uv = c[k]
            key = (bone, tuple(round(x, 4) for x in p), tuple(round(x, 3) for x in n), tuple(round(x, 4) for x in uv))
            if key not in vmap:
                lp = xf(invw[bone], xf(root, p))
                ln = xf(invw[bone], xf(root, n, 0), 0)
                vmap[key] = len(verts)
                verts.append(lp + ln + [uv[0], 1 - uv[1], float(bone)])
            ids.append(vmap[key])
        idx.append(ids)
    # Auge (Laser): vorderster Punkt des Koerpers (Knochen Aim_LR/Aim_UD) nahe der Mitte
    # Koerper haengt am Knochen 0 (steht still); nur Fluegel und Rohre drehen sich zum Ziel
    body = [xf(root, p) for c in tris for (bone, p, n, uv) in c if bone == 0]
    cand = [q for q in body if abs(q[1]) < 1.2 and 25 < q[2] < 50]
    eyew = max(cand, key=lambda q: q[0])
    eye_local = [eyew[0] + 0.5, eyew[1], eyew[2]]   # Modellraum (nach +X gedreht), knapp vor der Linse
    # Animationen: nur Verschiebungen der Fluegel und Rohre (Knochen 3..8)
    def track(name):
        _, fr, _ = parse_smd(os.path.join(src, "turret_01_anims", name + ".smd"))
        return [[round(x, 3) for b in range(3, 9) for x in f[b][:3]] for f in fr]
    anims = {"deploy": track("deploy"), "fire": track("fire"), "retract": track("retract")}
    # Mitte der Rohrmuendungen (fuer Muendungsfeuer): vorderste Punkte der Rohrknochen
    muzzles = {}
    for gb in (4, 5, 7, 8):
        pts = [xf(root, p) for c in tris for (bone, p, n, uv) in c if bone == gb]
        m = max(pts, key=lambda q: q[0])
        muzzles[gb] = [round(x, 2) for x in xf(invw[gb], m)]
    tex = Image.open(os.path.join(src, "turret_01.png")).convert("RGB")
    b = io.BytesIO()
    tex.save(b, "JPEG", quality=88, optimize=True)
    texb = b.getvalue()
    vb = struct.pack(f"<{len(verts) * 9}f", *[x for v in verts for x in v])
    ib = struct.pack(f"<{len(idx) * 3}H", *[x for t in idx for x in t])
    blobs = bytearray()

    def add(data):
        while len(blobs) % 4:
            blobs.append(0)
        o = len(blobs)
        blobs.extend(data)
        return [o, len(data)]
    zs = [xf(world[int(v[8])], v[:3])[2] for v in verts]
    man = {
        "bones": [{"name": n, "parent": p, "pos": [round(x, 4) for x in bind[i][:3]], "rot": [round(x, 6) for x in bind[i][3:]]} for i, (n, p) in enumerate(nodes)],
        "root": root, "verts": add(vb), "idx": add(ib), "numVerts": len(verts), "numIdx": len(idx) * 3,
        "tex": add(texb), "texType": "image/jpeg", "eye": [round(x, 3) for x in eye_local], "muzzles": muzzles,
        "anims": anims, "height": round(max(zs) - min(zs), 1), "minZ": round(min(zs), 2),
    }
    js = json.dumps(man, separators=(",", ":")).encode()
    while len(js) % 4:
        js += b" "
    open(out, "wb").write(struct.pack("<I", len(js)) + js + bytes(blobs))
    print(f"Turm: {len(verts)} Vertices, {len(idx)} Dreiecke, Hoehe {man['height']}, Auge {[round(x, 1) for x in eyew]}, "
          f"Textur {len(texb) // 1024} KB, Paket {os.path.getsize(out) // 1024} KB")


if __name__ == "__main__":
    main()
