#!/usr/bin/env python3
"""Konverter: GoldSrc-MDL (v10) + WAD3 -> kompaktes Testpaket fuer die Modell-Testseite.

Aufruf: python3 -I convert_mdl.py <models_dir> <wad> <out.bin>
"""
import io
import json
import math
import struct
import sys
import os
import glob

from PIL import Image

SEQS = [
    ("idle1", "Stehen"),
    ("walk", "Gehen"),
    ("run", "Rennen"),
    ("ref_aim_knife", "Messer bereit"),
    ("ref_shoot_knife", "Messerangriff"),
    ("ref_aim_ak47", "Zielen (AK)"),
    ("ref_shoot_ak47", "Schießen (AK)"),
    ("death1", "Tod 1"),
    ("death2", "Tod 2"),
    ("death3", "Tod 3"),
    ("head", "Kopfschuss"),
    ("gutshot", "Bauchschuss"),
    ("back", "Tod rückwärts"),
    ("forward", "Tod vorwärts"),
]

MODELS = [
    ("urban", "Seal Team 6", "CT"),
    ("gsg9", "GSG-9", "CT"),
    ("sas", "SAS", "CT"),
    ("gign", "GIGN", "CT"),
    ("spetsnaz", "Spetsnaz", "CT"),
    ("terror", "Phoenix Connexion", "T"),
    ("leet", "L337 Krew", "T"),
    ("arctic", "Arctic Avengers", "T"),
    ("guerilla", "Guerilla Warfare", "T"),
    ("militia", "Midwest Militia", "T"),
    ("vip", "VIP", "VIP"),
]

PAD = 4


def cstr(b):
    return b.split(b"\0")[0].decode("latin1")


def angle_quat(a):
    # Half-Life AngleQuaternion
    sy, cy = math.sin(a[2] * 0.5), math.cos(a[2] * 0.5)
    sp, cp = math.sin(a[1] * 0.5), math.cos(a[1] * 0.5)
    sr, cr = math.sin(a[0] * 0.5), math.cos(a[0] * 0.5)
    return (
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy,
        cr * cp * cy + sr * sp * sy,
    )


class MDL:
    def __init__(self, path):
        self.d = d = open(path, "rb").read()
        ident, ver = struct.unpack("<4si", d[:8])
        assert ident == b"IDST" and ver == 10, (path, ident, ver)
        (self.numbones, self.boneindex, _, _, _, _, self.numseq, self.seqindex,
         self.numseqgroups, self.seqgroupindex, self.numtextures, self.textureindex,
         self.texturedataindex, self.numskinref, self.numskinfamilies, self.skinindex,
         self.numbodyparts, self.bodypartindex) = struct.unpack("<18i", d[140:212])
        self.bones = []
        for i in range(self.numbones):
            o = self.boneindex + i * 112
            name = cstr(d[o:o + 32])
            parent, flags = struct.unpack("<ii", d[o + 32:o + 40])
            value = struct.unpack("<6f", d[o + 64:o + 88])
            scale = struct.unpack("<6f", d[o + 88:o + 112])
            self.bones.append(dict(name=name, parent=parent, value=value, scale=scale))
        self.textures = []
        for i in range(self.numtextures):
            o = self.textureindex + i * 80
            name = cstr(d[o:o + 64])
            flags, w, h, idx = struct.unpack("<4i", d[o + 64:o + 80])
            self.textures.append(dict(name=name, flags=flags, w=w, h=h, idx=idx))
        self.skins = list(struct.unpack(f"<{self.numskinref * self.numskinfamilies}h",
                                        d[self.skinindex:self.skinindex + 2 * self.numskinref * self.numskinfamilies]))

    def seq_by_name(self, name):
        d = self.d
        for s in range(self.numseq):
            o = self.seqindex + s * 176
            if cstr(d[o:o + 32]) == name:
                return o
        return None

    def texture_rgba(self, t):
        d = self.d
        w, h, idx = t["w"], t["h"], t["idx"]
        pix = d[idx:idx + w * h]
        pal = d[idx + w * h: idx + w * h + 768]
        img = Image.frombytes("P", (w, h), pix)
        img.putpalette(pal)
        rgba = img.convert("RGBA")
        if t["flags"] & 0x40:  # STUDIO_NF_MASKED: Index 255 transparent
            a = Image.frombytes("L", (w, h), bytes(0 if p == 255 else 255 for p in pix))
            rgba.putalpha(a)
        return rgba

    def anim_value(self, panim_off, k, frame, bone):
        """Dekodiert einen Kanal (0..5) fuer einen Frame. panim_off = Offset von mstudioanim_t."""
        d = self.d
        offs = struct.unpack("<6H", d[panim_off:panim_off + 12])
        if offs[k] == 0:
            return bone["value"][k]
        p = panim_off + offs[k]
        f = frame
        while True:
            valid, total = d[p], d[p + 1]
            if total == 0:  # Schutz gegen defekte Daten
                return bone["value"][k]
            if total <= f:
                f -= total
                p += (valid + 1) * 2
                continue
            break
        if valid > f:
            v = struct.unpack("<h", d[p + 2 * (f + 1): p + 2 * (f + 2)])[0]
        else:
            v = struct.unpack("<h", d[p + 2 * valid: p + 2 * valid + 2])[0]
        return bone["value"][k] + v * bone["scale"][k]

    def sequence(self, name):
        o = self.seq_by_name(name)
        if o is None:
            return None
        d = self.d
        fps, flags = struct.unpack("<fi", d[o + 32:o + 40])
        numframes = struct.unpack("<i", d[o + 56:o + 60])[0]
        motiontype, motionbone = struct.unpack("<ii", d[o + 68:o + 76])
        lin = struct.unpack("<3f", d[o + 76:o + 88])
        numblends, animindex = struct.unpack("<ii", d[o + 120:o + 128])
        seqgroup = struct.unpack("<i", d[o + 156:o + 160])[0]
        assert seqgroup == 0, "externe Sequenzgruppen nicht unterstuetzt"
        blend = numblends // 2  # mittlerer Blend = 0 Grad Neigung
        base = animindex + blend * self.numbones * 12
        frames = []
        for f in range(numframes):
            fr = []
            for j, b in enumerate(self.bones):
                pa = base + j * 12
                v = [self.anim_value(pa, k, f, b) for k in range(6)]
                if j == motionbone:
                    if motiontype & 1: v[0] = 0.0
                    if motiontype & 2: v[1] = 0.0
                    if motiontype & 4: v[2] = 0.0
                q = angle_quat(v[3:6])
                fr.append((q, v[0:3]))
            frames.append(fr)
        return dict(fps=fps, loop=bool(flags & 1), frames=frames,
                    speed=math.sqrt(lin[0] ** 2 + lin[1] ** 2 + lin[2] ** 2))

    def meshes(self, bodypart, submodel):
        """Liefert Liste von (texIndex, [(vert, norm, s, t), ...] Dreiecke) plus Vert/Norm-Arrays."""
        d = self.d
        bo = self.bodypartindex + bodypart * 76
        nummodels, base, modelindex = struct.unpack("<iii", d[bo + 64:bo + 76])
        if submodel >= nummodels:
            return None
        mo = modelindex + submodel * 112
        (typ, radius, nummesh, meshindex, numverts, vertinfoindex, vertindex,
         numnorms, norminfoindex, normindex) = struct.unpack("<ifiiiiiiii", d[mo + 64:mo + 104])
        verts = [struct.unpack("<3f", d[vertindex + i * 12: vertindex + i * 12 + 12]) for i in range(numverts)]
        vbone = list(d[vertinfoindex:vertinfoindex + numverts])
        norms = [struct.unpack("<3f", d[normindex + i * 12: normindex + i * 12 + 12]) for i in range(numnorms)]
        nbone = list(d[norminfoindex:norminfoindex + numnorms])
        out = []
        for m in range(nummesh):
            me = meshindex + m * 20
            numtris, triindex, skinref, _, _ = struct.unpack("<5i", d[me:me + 20])
            tex = self.skins[skinref]
            tris = []
            p = triindex
            while True:
                n = struct.unpack("<h", d[p:p + 2])[0]
                p += 2
                if n == 0:
                    break
                fan = n < 0
                n = abs(n)
                cmd = []
                for _ in range(n):
                    vi, ni, s, t = struct.unpack("<4h", d[p:p + 8])
                    p += 8
                    cmd.append((vi, ni, s, t))
                for k in range(n - 2):
                    if fan:
                        tri = (cmd[0], cmd[k + 1], cmd[k + 2])
                    elif k % 2 == 0:
                        tri = (cmd[k], cmd[k + 1], cmd[k + 2])
                    else:
                        tri = (cmd[k + 1], cmd[k], cmd[k + 2])
                    tris.append(tri)
            out.append((tex, tris))
        return dict(meshes=out, verts=verts, vbone=vbone, norms=norms, nbone=nbone)


def quat_mat(q, p):
    x, y, z, w = q
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y), p[0]],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x), p[1]],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y), p[2]],
    ]


def mat_mul(a, b):
    r = [[0.0] * 4 for _ in range(3)]
    for i in range(3):
        for j in range(4):
            r[i][j] = a[i][0] * b[0][j] + a[i][1] * b[1][j] + a[i][2] * b[2][j] + (a[i][3] if j == 3 else 0.0)
    return r


def pack_atlas(images):
    """Groesstes Bild links oben, Rest in Regalen rechts daneben, danach darunter. Randauffuellung PAD."""
    W = 1024
    order = sorted(range(len(images)), key=lambda i: -(images[i][1].width * images[i][1].height))
    first = order[0]
    fw, fh = images[first][1].width + 2 * PAD, images[first][1].height + 2 * PAD
    rects = {first: (PAD, PAD)}
    x0, x, y, shelf_h, limit = fw, fw, 0, 0, fh
    for i in sorted(order[1:], key=lambda i: -images[i][1].height):
        img = images[i][1]
        w, h = img.width + 2 * PAD, img.height + 2 * PAD
        if x + w > W:
            x, y, shelf_h = x0, y + shelf_h, 0
        if y + h > limit and x0 > 0:
            # rechte Spalte voll -> unter dem grossen Bild weiter
            x0, x, y, shelf_h, limit = 0, 0, max(fh, y + shelf_h), 0, 1 << 30
        rects[i] = (x + PAD, y + PAD)
        x += w
        shelf_h = max(shelf_h, h)
    H = max(r[1] - PAD + images[i][1].height + 2 * PAD for i, r in rects.items())
    H = (H + 3) // 4 * 4
    atlas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i, (ox, oy) in rects.items():
        img = images[i][1]
        w, h = img.size
        big = Image.new("RGBA", (w + 2 * PAD, h + 2 * PAD))
        big.paste(img, (PAD, PAD))
        for k in range(PAD):
            big.paste(img.crop((0, 0, w, 1)), (PAD, k))
            big.paste(img.crop((0, h - 1, w, h)), (PAD, PAD + h + k))
        for k in range(PAD):
            big.paste(big.crop((PAD, 0, PAD + 1, h + 2 * PAD)), (k, 0))
            big.paste(big.crop((PAD + w - 1, 0, PAD + w, h + 2 * PAD)), (PAD + w + k, 0))
        atlas.paste(big, (ox - PAD, oy - PAD))
    return atlas, {images[i][0]: (rects[i][0], rects[i][1]) for i in rects}


def wad_texture(wad, name):
    d = open(wad, "rb").read()
    magic, n, off = struct.unpack("<4sii", d[:12])
    for i in range(n):
        e = d[off + i * 32: off + (i + 1) * 32]
        filepos = struct.unpack("<i", e[:4])[0]
        if cstr(e[16:32]).lower() != name.lower():
            continue
        w, h = struct.unpack("<II", d[filepos + 16:filepos + 24])
        offs = struct.unpack("<4I", d[filepos + 24:filepos + 40])
        pix = d[filepos + offs[0]: filepos + offs[0] + w * h]
        palo = filepos + offs[3] + (w // 8) * (h // 8) + 2
        img = Image.frombytes("P", (w, h), pix)
        img.putpalette(d[palo:palo + 768])
        return img.convert("RGB")
    raise KeyError(name)


def png_bytes(img):
    b = io.BytesIO()
    img.save(b, "PNG", optimize=True)
    return b.getvalue()


def jpg_bytes(img, q=88):
    b = io.BytesIO()
    img.convert("RGB").save(b, "JPEG", quality=q, optimize=True)
    return b.getvalue()


def main():
    models_dir, wad, out = sys.argv[1:4]
    only = set(sys.argv[4].split(",")) if len(sys.argv) > 4 else None
    blobs = bytearray()

    def add(b):
        nonlocal blobs
        while len(blobs) % 4:
            blobs.append(0)
        o = len(blobs)
        blobs += b
        return [o, len(b)]

    manifest = dict(models=[], seqs=[{"name": n, "label": l} for n, l in SEQS], floors={})
    for key, label, team in MODELS:
        if only and key not in only:
            continue
        path = glob.glob(os.path.join(models_dir, "**", key + ".mdl"), recursive=True)[0]
        m = MDL(path)
        # --- Mesh: Koerper (Bodypart 0, Submodell 0) + Zusatz (Bodypart 1, Submodell 1 = C4/Defuse)
        parts = [("body", m.meshes(0, 0))]
        extra = m.meshes(1, 1) if m.numbodyparts > 1 else None
        if extra:
            parts.append(("extra", extra))
        used_tex = sorted({tex for _, p in parts for tex, _ in p["meshes"]})
        imgs = [(t, m.texture_rgba(m.textures[t])) for t in used_tex]
        atlas, rects = pack_atlas(imgs)
        AW, AH = atlas.size
        has_alpha = any(m.textures[t]["flags"] & 0x40 for t in used_tex)
        vmap = {}
        pos, nrm, uv, bone = [], [], [], []
        ranges = {}
        idx = []
        flips = [0, 0]
        for pname, p in parts:
            start = len(idx)
            for tex, tris in p["meshes"]:
                t = m.textures[tex]
                ox, oy = rects[tex]
                for tri in tris:
                    ids = []
                    for (vi, ni, s, tt) in tri:
                        k = (pname, vi, ni, s, tt, tex)
                        if k not in vmap:
                            vmap[k] = len(pos)
                            pos.append(p["verts"][vi])
                            nrm.append(p["norms"][ni])
                            # Texelkoordinaten -> Atlas (Texelmitte wie GoldSrc: s/w)
                            uv.append(((ox + s) / AW, (oy + tt) / AH))
                            bone.append(p["vbone"][vi])
                        ids.append(vmap[k])
                    idx.append(ids)
            ranges[pname] = [start * 3, (len(idx) - start) * 3]
        # Windungsrichtung pruefen (Geometrie-Normale vs. Vertex-Normalen im Bone-Raum gleicher Knochen)
        # -> wir pruefen in der Referenzpose
        ref = m.sequence("idle1")
        mats = []
        for j, b in enumerate(m.bones):
            q, pp = ref["frames"][0][j]
            lm = quat_mat(q, pp)
            mats.append(lm if b["parent"] < 0 else mat_mul(mats[b["parent"]], lm))

        def xf(j, v, w=1.0):
            M = mats[j]
            return [M[i][0] * v[0] + M[i][1] * v[1] + M[i][2] * v[2] + M[i][3] * w for i in range(3)]

        wpos = [xf(bone[i], pos[i]) for i in range(len(pos))]
        wn = [xf(bone[i], nrm[i], 0.0) for i in range(len(pos))]
        for a, b_, c in idx:
            e1 = [wpos[b_][i] - wpos[a][i] for i in range(3)]
            e2 = [wpos[c][i] - wpos[a][i] for i in range(3)]
            gn = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
            vn = [wn[a][i] + wn[b_][i] + wn[c][i] for i in range(3)]
            flips[0 if sum(gn[i] * vn[i] for i in range(3)) >= 0 else 1] += 1
        ccw = flips[0] >= flips[1]
        if not ccw:  # auf CCW umdrehen, damit Standard-Culling passt
            idx = [(a, c, b_) for a, b_, c in idx]
        # Bounding fuer Kamera
        zs = [v[2] for v in wpos]
        # --- Animationen: lokale Quat+Pos je Knochen und Frame, int16
        seqs_meta = []
        anim = bytearray()
        row = 0
        for sname, _ in SEQS:
            s = m.sequence(sname)
            nf = len(s["frames"])
            for j in range(m.numbones):
                prevq = None
                chans = [[] for _ in range(7)]
                for fr in s["frames"]:
                    q, pp = fr[j]
                    if prevq is not None and sum(a * b for a, b in zip(q, prevq)) < 0:
                        q = tuple(-c for c in q)
                    prevq = q
                    for c in range(4):
                        chans[c].append(max(-32767, min(32767, round(q[c] * 32767))))
                    for c in range(3):
                        chans[4 + c].append(max(-32767, min(32767, round(pp[c] * 32))))
                for ch in chans:  # Delta-Kodierung ueber die Frames
                    last = 0
                    for v in ch:
                        dlt = v - last
                        anim += struct.pack("<h", ((dlt + 32768) % 65536) - 32768)
                        last = v
            seqs_meta.append(dict(fps=s["fps"], frames=nf, loop=s["loop"],
                                  row=row, speed=round(s["speed"], 3)))
            row += nf
        import array
        pa = array.array("f", [c for v in pos for c in v])
        na = array.array("f", [c for v in nrm for c in v])
        ua = array.array("f", [c for v in uv for c in v])
        ia = array.array("H", [c for t in idx for c in t])
        tex_bytes = png_bytes(atlas) if has_alpha else jpg_bytes(atlas, 90)
        manifest["models"].append(dict(
            key=key, label=label, team=team,
            bones=[b["parent"] for b in m.bones], boneNames=[b["name"] for b in m.bones],
            numVerts=len(pos), numIdx=len(ia), ranges=ranges,
            pos=add(pa.tobytes()), nrm=add(na.tobytes()), uv=add(ua.tobytes()),
            bone=add(bytes(bone)), idx=add(ia.tobytes()),
            tex=add(tex_bytes), texType="image/png" if has_alpha else "image/jpeg",
            anim=add(bytes(anim)), rows=row, seqs=seqs_meta,
            minZ=round(min(zs), 2), maxZ=round(max(zs), 2), windingFlipped=not ccw,
        ))
        print(f"{key:9s} verts={len(pos)} tris={len(idx)} atlas={AW}x{AH} tex={len(tex_bytes)//1024}KB "
              f"anim={len(anim)//1024}KB rows={row} ccw={ccw} ({flips}) z={min(zs):.1f}..{max(zs):.1f}")
    for fname in ["duSand", "duCrtLrgSd", "duCrtLrgTp", "dusandwll"]:
        img = wad_texture(wad, fname)
        manifest["floors"][fname] = dict(data=add(jpg_bytes(img, 90)), w=img.width, h=img.height)
    js = json.dumps(manifest, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    hdr = js
    while len(hdr) % 4:
        hdr += b" "
    # Aufbau: [u32 Laenge JSON][JSON, auf 4 aufgefuellt][Binaerteil]; Offsets relativ zum Binaerteil
    open(out, "wb").write(struct.pack("<I", len(hdr)) + hdr + bytes(blobs))
    print("Paket:", os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main()
