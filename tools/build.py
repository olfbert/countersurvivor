#!/usr/bin/env python3
"""Setzt Pakete (Base64) und Version in eine Vorlage ein.

Aufruf: build.py <vorlage> <ausgabe> <version> PACK=<datei> [MODELS=<datei> ICONS=@<textdatei> ...]
(alte Form ohne KEY= wird als PACK=<datei> verstanden)
"""
import base64, sys
tpl, out, ver = sys.argv[1:4]
s = open(tpl, encoding='utf-8').read().replace('__VERSION__', ver)
for arg in sys.argv[4:]:
    key, path = arg.split('=', 1) if '=' in arg else ('PACK', arg)
    if path.startswith('@'):   # Text (z. B. JSON) unveraendert einsetzen
        s = s.replace('__' + key + '__', open(path[1:], encoding='utf-8').read())
    else:
        s = s.replace('__' + key + '__', base64.b64encode(open(path, 'rb').read()).decode('ascii'))
open(out, 'w', encoding='utf-8').write(s)
print(out, len(s) // 1024, 'KB')
