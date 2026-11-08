import numpy as np, sys, itertools
from PIL import Image
d = sys.argv[1]
imgs = [np.asarray(Image.open(f'{d}/img{i}.jpg').convert('RGB'), dtype=np.float32) for i in range(1, 7)]
for i, a in enumerate(imgs): print(i+1, a.shape, 'mean', a.mean().round(1))
sides = [1, 2, 4, 5]  # 0-basiert: img2, img3, img5, img6 (Horizont)
up = 3  # img4 (Sonne)
def edge(a, which):  # Pixelreihe entlang der Kante, Mittel ueber 2 px
    if which == 'L': return a[:, :2].mean(1)
    if which == 'R': return a[:, -2:].mean(1)
    if which == 'T': return a[:2].mean(0)
    if which == 'B': return a[-2:].mean(0)
def diff(x, y): return float(np.abs(x - y).mean())
print('Rechts(A) vs Links(B):')
M = {}
for a in sides:
    row = []
    for b in sides:
        v = diff(edge(imgs[a], 'R'), edge(imgs[b], 'L')) if a != b else 999
        M[(a, b)] = v; row.append(f'{v:6.1f}')
    print(f'  img{a+1}:', ' '.join(row))
best = None
for perm in itertools.permutations(sides[1:]):
    cyc = [sides[0]] + list(perm)
    s = sum(M[(cyc[k], cyc[(k+1) % 4])] for k in range(4))
    if best is None or s < best[0]: best = (s, cyc)
print('beste Zyklus-Reihenfolge (nach rechts drehen):', [f'img{c+1}' for c in best[1]], 'Fehler', round(best[0], 1))
# Up-Bild: welche Kante/Richtung passt zu welcher Oberkante
U = imgs[up]
cands = {'T': U[:2].mean(0), 'B': U[-2:].mean(0), 'L': U[:, :2].mean(1), 'R': U[:, -2:].mean(1)}
for s in sides:
    top = edge(imgs[s], 'T')
    res = []
    for k, e in cands.items():
        res.append((diff(top, e), k, '+')); res.append((diff(top, e[::-1]), k, '-'))
    res.sort()
    print(f'Oberkante img{s+1}: beste Up-Kante', res[0][1:], round(res[0][0], 1), '| zweitbeste', res[1][1:], round(res[1][0], 1))
# Sonne im Up-Bild
g = U.mean(2); y, x = np.unravel_index(np.argmax(g), g.shape); print('Sonne im Up-Bild bei', x, y)
