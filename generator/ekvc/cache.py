"""Cache of the (slow) steering design per style -> generator/cache/<code>_steering.json"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

from . import layout as L
from . import steering
from .styles import BY_CODE

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, "cache")


def _path(code):
    return os.path.join(CACHE, f"{code}_steering.json")


def compute(code):
    s = BY_CODE[code]
    h, rep, lk, pts = steering.design(s)
    data = dict(code=code, beta=h.beta, sweep_x=rep["sweep_max_x"], rep={k: v for k, v in rep.items() if k != "knuckle_range"},
                knuckle_range={str(k): v for k, v in rep["knuckle_range"].items()},
                sweep_pts=np.round(pts[::3], 1).tolist(),
                inputs=dict(W=s.W, FT=s.FT, RT=s.RT, ARM_LEN=L.ARM_LEN, PITMAN_R=L.PITMAN_R, CASTER=L.CASTER,
                            Y_ARM=L.Y_ARM, COL_ANGLE=L.COL_ANGLE, Z_D=L.Z_D))
    os.makedirs(CACHE, exist_ok=True)
    with open(_path(code), "w") as f:
        json.dump(data, f)
    return data


def load(code, recompute=False):
    p = _path(code)
    if not recompute and os.path.exists(p):
        with open(p) as f:
            d = json.load(f)
        s = BY_CODE[code]
        inp = dict(W=s.W, FT=s.FT, RT=s.RT, ARM_LEN=L.ARM_LEN, PITMAN_R=L.PITMAN_R, CASTER=L.CASTER,
                   Y_ARM=L.Y_ARM, COL_ANGLE=L.COL_ANGLE, Z_D=L.Z_D)
        if all(abs(d["inputs"].get(k, 1e9) - v) < 1e-6 for k, v in inp.items()):
            return d
    return compute(code)


def hard(code):
    d = load(code)
    s = BY_CODE[code]
    h = L.derive(s, d["sweep_x"], d["beta"])
    return s, h, d


if __name__ == "__main__":
    for c in sys.argv[1:]:
        d = compute(c)
        print(c, "beta", round(math.degrees(d["beta"]), 2), "sweep", round(d["sweep_x"] - BY_CODE[c].W, 1))
