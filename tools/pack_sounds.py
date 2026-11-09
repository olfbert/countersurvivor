#!/usr/bin/env python3
"""Sounds (WAV aus cstrike/sound) -> kompaktes Paket: 8 Bit mono PCM, Originalrate, Stille am Ende gekuerzt.

Aufruf: python3 -I pack_sounds.py <sound-ordner> <out.bin>
Aufbau wie die anderen Pakete: [u32 Laenge JSON][JSON][Binaerteil]; Schluessel = Dateiname ohne .wav
"""
import json
import os
import struct
import sys
import wave


def read_u8_mono(path):
    with wave.open(path, "rb") as w:
        ch, sw, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw == 1:
        s = [b - 128 for b in raw]
    elif sw == 2:
        s = [v >> 8 for v in struct.unpack(f"<{len(raw) // 2}h", raw)]
    else:
        raise ValueError(f"{path}: {sw * 8} Bit nicht unterstuetzt")
    if ch > 1:
        s = [sum(s[i:i + ch]) // ch for i in range(0, len(s), ch)]
    end = len(s)
    while end > 1 and abs(s[end - 1]) <= 1:
        end -= 1
    return rate, bytes(max(0, min(255, v + 128)) for v in s[:end])


def main():
    src, out = sys.argv[1:3]
    blobs = bytearray()
    man = {"sounds": {}}
    for root, _, files in sorted(os.walk(src)):
        for f in sorted(files):
            if not f.lower().endswith(".wav"):
                continue
            key = f[:-4].lower()
            rate, pcm = read_u8_mono(os.path.join(root, f))
            while len(blobs) % 4:
                blobs.append(128)
            man["sounds"][key] = {"rate": rate, "data": [len(blobs), len(pcm)]}
            blobs += pcm
    js = json.dumps(man, separators=(",", ":")).encode()
    while len(js) % 4:
        js += b" "
    open(out, "wb").write(struct.pack("<I", len(js)) + js + bytes(blobs))
    print(f"{len(man['sounds'])} Sounds, {len(blobs) // 1024} KB PCM")


if __name__ == "__main__":
    main()
