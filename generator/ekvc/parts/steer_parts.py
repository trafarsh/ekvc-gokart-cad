"""Per-style steering parts (knuckles, tie rods) and floor pan."""
from __future__ import annotations

import math

import cadquery as cq
import numpy as np

from .. import geom as G
from .. import layout as L
from . import PartDef
from .colours import ALU, STEEL, ZINC

V = cq.Vector
Y_TIE_IN = L.Y_ARM - 9.0
Y_TIE_OUT_OFF = 9.0


def _k():
    c = math.radians(L.CASTER)
    return V(-math.sin(c), math.cos(c), 0), V(math.cos(c), math.sin(c), 0)


def arm_end(s, h, sd):
    return V(s.W - L.ARM_LEN * math.cos(h.beta), L.Y_ARM, sd * (s.KH - L.ARM_LEN * math.sin(h.beta)))


def outer_joint(s, h, sd):
    k, _ = _k()
    return arm_end(s, h, sd) + k * Y_TIE_OUT_OFF


def inner_joint(s, h, sd):
    return V(h.arm_end_x, Y_TIE_IN, L.Z_D + sd * 10.0)


def knuckle(s, h, sd):
    k, e1 = _k()
    kp = V(s.W, L.Y_FAX, sd * s.KH)
    boss = G.ring(kp, k, 32, 10.5, L.KP_BOSS_LEN)
    stub = G.cyl(kp + V(0, 0, sd * (L.SCRUB + 50) / 2), V(0, 0, 1), 20, L.SCRUB + 50)
    stub = stub.fuse(G.cyl(kp + V(0, 0, sd * (L.SCRUB + 50)), V(0, 0, 1), 12, 30))   # threaded end M12
    A = arm_end(s, h, sd)
    c0 = kp + k * ((A - kp).dot(k))
    ua, wa = (A - c0).dot(e1), (A - c0).dot(V(0, 0, 1))
    ang = math.atan2(wa, ua)
    Ln = math.hypot(ua, wa)
    # plate outline in its own (along, across) coords then rotated into (e1, Z)
    loc = [(0, -17), (Ln, -13)] + [(Ln + 13 * math.cos(a), 13 * math.sin(a)) for a in np.linspace(-math.pi / 2, math.pi / 2, 9)][1:-1] + [(Ln, 13), (0, 17)]
    pts = [(u * math.cos(ang) - w * math.sin(ang), u * math.sin(ang) + w * math.cos(ang)) for u, w in loc]
    arm = G.plate_on_plane(c0, e1, V(0, 0, 1), pts, 8)
    gus = G.plate_on_plane(kp + V(0, 0, sd * 16), e1, k, [(-14, -48), (14, -48), (14, 30), (-14, 30)], 6)
    s_ = G.fuse_all([boss, stub, arm, gus])
    s_ = s_.cut(G.cyl(A, k, 8.5, 30)).cut(G.cyl(kp, k, 10.5, 200))
    side = "left" if sd < 0 else "right"
    return PartDef(f"{s.code}-STR-1{1 if sd < 0 else 2}", f"Steering knuckle {side}", s_, STEEL,
                   "AISI 4130 (boss + 20 mm stub axle + 8 mm arm)",
                   f"Arm {L.ARM_LEN:.0f} mm at {math.degrees(h.beta):.2f} deg (Ackermann tuned), caster {L.CASTER:.0f} deg",
                   "steering")


def tie_rod(s, h, sd):
    a = inner_joint(s, h, sd)
    b = outer_joint(s, h, sd)
    d = (b - a).normalized()
    ln = (b - a).Length
    up = V(0, 1, 0)
    parts = []
    for p in (a, b):
        parts.append(G.ring(p, up, 20, 8.2, 10))
    parts.append(G.rod(a + d * 9, b - d * 9, 12))
    for p, sg in ((a, 1), (b, -1)):
        parts.append(G.cyl(p + d * sg * 26, d, 16, 14))       # rod-end shank
        parts.append(G.cyl(p + d * sg * 40, d, 19, 8))        # jam nut
    s_ = G.fuse_all(parts)
    side = "left" if sd < 0 else "right"
    return PartDef(f"{s.code}-STR-1{3 if sd < 0 else 4}", f"Tie rod {side} C-C {ln:.0f}", s_, ZINC,
                   "M10 rod ends + 12 mm steel rod, LH/RH thread", f"Centre-to-centre {ln:.1f} mm (adjustable +-10)",
                   "steering", meta={"cc": ln})


def floor_pan(s, h, P):
    """Floor close-out (rule 7.1.2) from roll-hoop/firewall to the front bulkhead, bolted under rails."""
    from .frame import z_at
    xs = np.linspace(L.X_HOOP - 20, L.X_FB + 8, 30)
    left = [(x, z_at(P["L"], x) - 10.0) for x in xs]
    right = [(x, z_at(P["R"], x) + 10.0) for x in xs[::-1]]
    poly = [(x, z) for x, z in left + right]
    y0 = L.Y_RAIL - L.TUBE_OD / 2 - L.FLOOR_T
    s_ = G.plate_xz(poly, y0, L.FLOOR_T)
    area = 0.0
    for (x0, z0), (x1, z1) in zip(poly, poly[1:] + poly[:1]):
        area += x0 * z1 - x1 * z0
    return PartDef(f"{s.code}-BOD-10", "Floor close-out pan 2mm", s_, ALU, "Aluminium 5052-H32 2 mm",
                   f"{abs(area) / 2e6:.3f} m2, gaps < 3 mm, bolted M6 every 150 mm (rule 7.1.2)", "body")
