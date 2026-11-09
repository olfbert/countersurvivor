#!/usr/bin/env python3
"""Roomba (Tinkercad-OBJ, einfarbig, ohne Normalen) -> kleines Mesh-Paket.

Aufruf: python3 -I convert_roomba.py <tinker.obj> <out.bin> [durchmesser_in_spieleinheiten]
Positionen als int16 (skaliert, Boden bei z=0, Mitte bei 0/0), Dreiecke als uint16.
Die Schattierung (flach, Deckel dunkel, Rand hell) macht das Spiel im Shader.
"""
import json
import struct
import sys


def main():
    src, out = sys.argv[1:3]
    diameter = float(sys.argv[3]) if len(sys.argv) > 3 else 26.0
    V, F = [], []
    for ln in open(src, encoding="latin1"):
        if ln.startswith("v "):
            V.append([float(x) for x in ln.split()[1:4]])
        elif ln.startswith("f "):
            ids = [int(t.split("/")[0]) for t in ln.split()[1:]]
            ids = [i - 1 if i > 0 else len(V) + i for i in ids]
            for k in range(1, len(ids) - 1):
                F.append((ids[0], ids[k], ids[k + 1]))
    xs, ys, zs = zip(*V)
    cx, cy, z0 = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)
    s = diameter / max(max(xs) - min(xs), max(ys) - min(ys))
    P = [((x - cx) * s, (y - cy) * s, (z - z0) * s) for x, y, z in V]
    # doppelte Punkte zusammenfassen, entartete Dreiecke weg
    key, remap, U = {}, [], []
    for p in P:
        k = tuple(round(c * 64) for c in p)
        if k not in key:
            key[k] = len(U)
            U.append(k)
        remap.append(key[k])
    tris = []
    for a, b, c in F:
        a, b, c = remap[a], remap[b], remap[c]
        if a != b and b != c and a != c:
            tris.append((a, b, c))
    # Windung pruefen: Normale soll von der Mitte weg zeigen (Mehrheit)
    good = 0
    for a, b, c in tris:
        A, B, C = U[a], U[b], U[c]
        e1 = [B[i] - A[i] for i in range(3)]
        e2 = [C[i] - A[i] for i in range(3)]
        n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
        m = [(A[i] + B[i] + C[i]) / 3 for i in range(3)]
        m[2] -= 0.5 * max(u[2] for u in (A, B, C))
        good += 1 if sum(n[i] * m[i] for i in range(3)) >= 0 else -1
    if good < 0:
        tris = [(a, c, b) for a, b, c in tris]
    assert len(U) < 65536
    height = max(u[2] for u in U) / 64
    vb = struct.pack(f"<{len(U) * 3}h", *[c for u in U for c in u])
    ib = struct.pack(f"<{len(tris) * 3}H", *[i for t in tris for i in t])
    man = {"scale": 1 / 64, "numVerts": len(U), "numIdx": len(tris) * 3, "radius": diameter / 2, "height": round(height, 2),
           "verts": [0, len(vb)], "idx": [len(vb), len(ib)]}
    js = json.dumps(man).encode()
    while len(js) % 4:
        js += b" "
    open(out, "wb").write(struct.pack("<I", len(js)) + js + vb + ib)
    print(f"Roomba: {len(U)} Punkte, {len(tris)} Dreiecke, Durchmesser {diameter}, Hoehe {height:.1f}")


if __name__ == "__main__":
    main()
