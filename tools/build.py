#!/usr/bin/env python3
import base64, sys
tpl, pack, out, ver = sys.argv[1:5]
s = open(tpl, encoding='utf-8').read()
b64 = base64.b64encode(open(pack, 'rb').read()).decode('ascii')
s = s.replace('__VERSION__', ver).replace('__PACK__', b64)
open(out, 'w', encoding='utf-8').write(s)
print(out, len(s) // 1024, 'KB')
