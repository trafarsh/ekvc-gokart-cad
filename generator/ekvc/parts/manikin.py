"""Reference driver manikin (175 cm male, seated) for ergonomics / roll-hoop / clash checks."""
from __future__ import annotations

import math

import cadquery as cq
import numpy as np

from .. import geom as G
from .. import layout as L
from . import PartDef

V = cq.Vector
D2R = math.pi / 180


def posture(h):
    """Key joint positions (mm, vehicle frame)."""
    zd = L.Z_D
    b = L.BACK_ANGLE * D2R
    hip = np.array([L.X_H, L.Y_H, zd])
    c7 = hip + np.array([-525 * math.sin(b), 525 * math.cos(b), 0])
    head = c7 + np.array([-170 * math.sin(5 * D2R), 170 * math.cos(5 * D2R), 0])
    helmet_r = 145.0
    th = 10 * D2R
    knee = hip + np.array([429 * math.cos(th), 429 * math.sin(th), 0])
    ankle = np.array([L.X_H + 837.0, 110.0, zd])
    toe = np.array([L.X_H + 910.0, 307.0, zd])
    heel = np.array([L.X_H + 805.0, 78.0, zd])
    sh = c7 + np.array([10.0, -35.0, 0])
    wc = np.array(h.wheel_c)
    return dict(hip=hip, c7=c7, head=head, helmet_r=helmet_r, helmet_top=head[1] + helmet_r, knee=knee, ankle=ankle,
                toe=toe, heel=heel, shoulder=sh, wheel=wc)


def _ik(s, g, l1, l2, pole):
    d = g - s
    D = np.linalg.norm(d)
    D = min(D, l1 + l2 - 1e-3)
    a = (l1 * l1 - l2 * l2 + D * D) / (2 * D)
    hgt = math.sqrt(max(l1 * l1 - a * a, 0))
    u = d / np.linalg.norm(d)
    p = pole - np.dot(pole, u) * u
    p = p / np.linalg.norm(p)
    return s + u * a + p * hgt


def _cap(a, b, r1, r2=None):
    r2 = r1 if r2 is None else r2
    a, b = V(*a), V(*b)
    d = b - a
    if abs(r1 - r2) < 1e-6:
        body = cq.Solid.makeCylinder(r1, d.Length, a, d.normalized())
    else:
        body = cq.Solid.makeCone(r1, r2, d.Length, a, d.normalized())
    parts = [body, cq.Solid.makeSphere(r1, a), cq.Solid.makeSphere(r2, b)]
    return parts


def manikin(s, h):
    P = posture(h)
    zd = L.Z_D
    parts = []
    parts += _cap(P["hip"] + [10, 25, 0], P["c7"] + [15, -40, 0], 120, 115)                  # torso
    parts += _cap(P["c7"], P["head"], 50)                                                  # neck
    parts.append(cq.Solid.makeSphere(P["helmet_r"], V(*P["head"])))                        # helmet
    up = np.array(L.col_u())
    for sd in (-1, 1):
        hipj = P["hip"] + [0, 0, sd * 85]
        knee = P["knee"] + [0, 0, sd * 92]
        zf = (-100.0 if sd < 0 else 95.0)
        ankle = P["ankle"] + [0, 0, zf]
        heel = P["heel"] + [0, 0, zf]
        toe = P["toe"] + [0, 0, zf]
        parts += _cap(hipj, knee, 70, 56)
        parts += _cap(knee, ankle, 50, 36)
        parts += _cap(heel, toe, 38, 34)
        sh = P["shoulder"] + [0, 0, sd * 190]
        grip = P["wheel"] + np.array([0, 0, sd * 127.5])
        el = _ik(sh, grip, 300.0, 290.0, np.array([0.0, -0.6, sd * 0.8]))
        parts += _cap(sh, el, 48, 40)
        parts += _cap(el, grip, 38, 30)
    shp = G.fuse_all(parts) if False else cq.Compound.makeCompound(parts)
    return PartDef(f"{s.code}-REF-01", "REF driver 175cm (not manufactured)", shp, (0.95, 0.75, 0.55),
                   "Reference geometry only", "175 cm male, back 20 deg, helmet top for roll-hoop check", "reference",
                   meta=P)
