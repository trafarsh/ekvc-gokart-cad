#!/usr/bin/env python3
"""Generate all (or selected) kart styles.

    python build_all.py                 # all 10 styles, full checks
    python build_all.py S01 S04         # selected styles
    python build_all.py --fast S01      # skip interference checks
"""
import json
import os
import sys
import time

from ekvc import assembly as A
from ekvc import checks as K
from ekvc import export as E
from ekvc.styles import STYLES

import export_kinematics as KX


def run(code, fast=False):
    t0 = time.time()
    I, info = A.build(code)
    s = info["style"]
    os.makedirs(E.style_dir(s), exist_ok=True)
    rules = K.rule_checks(I, info)
    cl = None if fast else K.clashes(I, info)
    sw = K.tyre_sweep_clashes(I, info)
    lsw = K.linkage_sweep_clashes(I, info)
    E.write_parts(I, s, skip_common=NO_COMMON)
    asm = E.write_assembly(I, s)
    pl = E.write_placements(I, s)
    kin = KX.write(KX.style_rows(s))
    bom, rows = E.write_bom(I, s)
    rn = E.renders(I, s)
    files = {"Assembly STEP": asm, "Placement table (SolidWorks macro)": pl, "Live-steering mates (SolidWorks macro)": kin,
             "Bill of materials": bom}
    files.update({f"Render {k}": v for k, v in rn.items()})
    E.report(I, info, rules, cl, sw, files, linkage=lsw)
    js = E.summary_json(info, rules, cl, sw, rows, linkage=lsw)
    with open(os.path.join(E.style_dir(s), "summary.json"), "w") as f:
        json.dump(js, f, indent=1, default=str)
    print(f"{code}: {js['rules_pass']}/{js['rules_total']} rules, clashes={js['clashes']}, sweep={js['sweep']}, linkage={js['linkage']}, "
          f"length {js['length']}, {time.time() - t0:.0f}s", flush=True)
    return js


NO_COMMON = "--no-common" in sys.argv

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fast = "--fast" in sys.argv
    codes = args or [s.code for s in STYLES]
    for c in codes:
        run(c, fast)
