#!/usr/bin/env python3
"""Export loose (not-on-kart) common items: push-pull rod and kart stand."""
import os
from ekvc import export as E, render as R, stepio
from ekvc.parts import common2 as C

os.makedirs(E.COMMON_DIR, exist_ok=True)
for p in (C.push_rod(), C.kart_stand()):
    path = os.path.join(E.COMMON_DIR, p.stem + ".step")
    stepio.write_part(p.shape, path, p.stem, p.rgb)
    print("wrote", path, p.shape.isValid())
    rd = os.path.join(E.OUT, "common", "renders")
    os.makedirs(rd, exist_ok=True)
    R.render([(p.shape, p.rgb)], os.path.join(rd, p.pid + ".png"), view="iso", size=(1000, 800), title=p.name)
