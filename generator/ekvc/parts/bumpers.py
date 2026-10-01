"""Front / rear / side bumpers (each a single seamless bent tube - rule 1.6) and the bolted
double-tab chassis-to-bumper connectors.  Side bumpers are separate from front/rear bumpers
(no full-round bumper - rule 7.1.1)."""
from __future__ import annotations

import math

import cadquery as cq
import numpy as np

from .. import geom as G
from .. import layout as L
from . import PartDef
from .colours import FOAM, STEEL, YELLOW
from .frame import z_at

V = cq.Vector
YR = L.Y_RAIL
Y_FBUMP = 100.0
Y_RBUMP = 130.0
Y_SBUMP = 130.0
BUMP_R = 60.0
FOAM_R = (L.TUBE_OD + 24) / 2


# ------------------------------------------------------------------ centre-lines
def front_path(s, h, x):
    fb = h.fb_half
    k = s.front_bumper
    y = Y_FBUMP
    if k in ("straight", "straight_wide"):
        w = fb + (35 if k == "straight_wide" else 0)
        return [(x - 45, y, -w), (x, y, -w + 45), (x, y, w - 45), (x - 45, y, w)]
    if k == "chevron":
        return [(x - 26, y, -fb), (x - 4, y, -fb + 70), (x + 4, y, L.Z_D), (x - 4, y, fb - 70), (x - 26, y, fb)]
    if k == "arc":
        n = 9
        pts = []
        for i in range(n):
            t = -1 + 2 * i / (n - 1)
            pts.append((x - 30 * t * t + 3, y, fb * t))
        return pts
    if k == "trapezoid":
        return [(x - 32, y, -fb), (x, y, -fb + 120), (x, y, fb - 120), (x - 32, y, fb)]
    if k == "U":
        return [(x, 210.0, -fb + 10), (x, y, -fb), (x, y, fb), (x, 210.0, fb - 10)]
    if k == "swept":
        return [(x - 30, y, -fb), (x - 4, y, -fb + 150), (x + 6, y, 0), (x - 4, y, fb - 150), (x - 30, y, fb)]
    raise KeyError(k)


def rear_path(s, h, x):
    rb = h.rb_half
    k = s.rear_bumper
    y = Y_RBUMP
    xt = -L.R_TYRE_D / 2 - 22.0   # bent ends stop behind the tyre
    if k == "straight":
        return [(xt, y, -rb), (x, y, -rb + 25), (x, y, rb - 25), (xt, y, rb)]
    if k == "arc":
        pts = []
        for i in range(9):
            t = -1 + 2 * i / 8
            pts.append((x + 20 * t * t - 6, y, rb * t))
        return pts
    if k == "trapezoid":
        return [(xt, y, -rb), (x + 8, y, -rb + 60), (x - 6, y, -rb + 220), (x - 6, y, rb - 220), (x + 8, y, rb - 60), (xt, y, rb)]
    if k == "U":
        return [(x, 230.0, -rb + 10), (x, y, -rb), (x, y, rb), (x, 230.0, rb - 10)]
    raise KeyError(k)


def side_path(s, h, sd):
    W = s.W
    z = sd * h.z_side
    x0, x1 = 200.0, W - 175.0
    k = s.side_bumper
    y = Y_SBUMP
    if k == "bar":
        return [(x0, y, z - sd * 45), (x0 + 50, y, z), (x1 - 50, y, z), (x1, y, z - sd * 45)]
    if k == "bar_kick":
        return [(x0, y, z - sd * 45), (x0 + 50, y, z), (x1 - 160, y, z), (x1, y, z - sd * 70)]
    if k == "double":
        return [(x0 + 40, 205.0, z), (x0, 175.0, z), (x0, 100.0, z), (x1, 100.0, z), (x1, 175.0, z), (x1 - 40, 205.0, z)]
    if k == "arc":
        pts = []
        for i in range(9):
            t = i / 8
            pts.append((x0 + (x1 - x0) * t, y, z + sd * (30 * math.sin(math.pi * t) - 40 * (abs(2 * t - 1) ** 6))))
        return pts
    if k == "hoop":
        return [(x0, 90.0, z - sd * 20), (x0, 200.0, z), (x1, 200.0, z), (x1, 90.0, z - sd * 20)]
    if k == "swept":
        return [(x0, y, z - sd * 40), (x0 + 50, y, z), (x1 - 40, y, z - sd * 55), (x1, y, z - sd * 85)]
    raise KeyError(k)


def _path_z_at(path, x):
    pts = sorted([(p[0], p[2]) for p in path if abs(p[1] - path[len(path) // 2][1]) < 200])
    return z_at(pts, x)


def _clearance_xz(path, sweep_pts):
    """Minimum plan-view distance from the bumper centre-line to the swept tyre envelope
    (only tyre points at bumper height band are relevant)."""
    pts = [np.array(p) for p in path]
    segs = list(zip(pts[:-1], pts[1:]))
    best = 1e9
    sp = sweep_pts[(sweep_pts[:, 1] > 40) & (sweep_pts[:, 1] < 240)]
    for a, b in segs:
        ab = b - a
        L2 = float(ab @ ab)
        t = np.clip(((sp - a) @ ab) / max(L2, 1e-9), 0, 1)
        proj = a + np.outer(t, ab)
        d = np.linalg.norm((sp - proj)[:, [0, 2]], axis=1)
        best = min(best, float(d.min()))
    return best


def solve_front(s, h, sweep_pts):
    """Push the front bumper forward until it clears the swept tyre by >= 15 mm (plus tube radius)."""
    x = h.x_fbar
    for _ in range(80):
        path = front_path(s, h, x)
        c = _clearance_xz(path, sweep_pts)
        if c >= FOAM_R + 8.0:
            break
        x += 2.0
    xmax = max(p[0] for p in path)
    h.x_fbar = x
    h.x_ff = xmax + L.TUBE_OD / 2
    return path, c


def solve_rear(s, h):
    path = rear_path(s, h, h.x_rbar)
    h.x_rf = min(p[0] for p in path) - L.TUBE_OD / 2
    return path


# ------------------------------------------------------------------ parts
def bumper_part(pid, name, path, colour, desc):
    t = G.bent_tube(path, L.TUBE_OD, L.TUBE_WALL, BUMP_R)
    return PartDef(pid, name, t, colour, L.TUBE_MAT + " - single seamless tube", desc, "bumpers",
                   meta={"path": path})


def foam_part(pid, name, path):
    t = G.bent_tube(path, L.TUBE_OD + 24, 11.5, BUMP_R)
    return PartDef(pid, name, t, FOAM, "Closed-cell foam pipe insulation 12 mm", "Rule 1.6 - padding over bumper", "bumpers")


# ------------------------------------------------------------------ connectors
def connector(F, B, axis, code, label, y_pad=22.0):
    """Double-tab bolted connector between frame point F and bumper point B (tube centres).

    axis 'X' -> plates normal Z (front/rear);  axis 'Z' -> plates normal X (side).
    Returns (frame_tab PartDef, bumper_tab PartDef, bolt placements [(pos, axis)], nut placements)."""
    F, B = np.array(F, float), np.array(B, float)
    ia = 0 if axis == "X" else 2
    a_f, a_b = F[ia], B[ia]
    sg = 1.0 if a_b > a_f else -1.0
    rr = L.TUBE_OD / 2 + 3.0
    yb = B[1]
    yf_lo = F[1] - 10.0
    y_hi = yb + y_pad
    y_lo_b = yb - 30.0
    # frame tab: from frame centre-line to just short of the bumper tube
    fa0, fa1 = a_f, a_b - sg * rr
    ba0, ba1 = a_b, a_f + sg * rr
    t = 6.0
    if axis == "X":
        zc = F[2]
        ft = G.plate_xy([(fa0, yf_lo), (fa1, yf_lo), (fa1, y_hi), (fa0, y_hi)], zc, t)
        bt = G.plate_xy([(ba0, y_lo_b), (ba1, y_lo_b), (ba1, y_hi), (ba0, y_hi)], zc - t, t)
    else:
        xc = F[0]
        ft = G.plate_yz([(fa0, yf_lo), (fa1, yf_lo), (fa1, y_hi), (fa0, y_hi)], xc, t)
        bt = G.plate_yz([(ba0, y_lo_b), (ba1, y_lo_b), (ba1, y_hi), (ba0, y_hi)], xc - t, t)
    am = 0.5 * (a_f + sg * rr + a_b - sg * rr)
    bolts, nuts = [], []
    for yy in (yb - 13.0, yb + 13.0 if y_hi - yb > 20 else yb):
        if axis == "X":
            hole = G.cyl((am, yy, zc), (0, 0, 1), 8.5, 40)
            bolts.append(((am, yy, zc - t), "Z"))
            nuts.append(((am, yy, zc + t + 4.0), "Z"))
        else:
            hole = G.cyl((xc, yy, am), (1, 0, 0), 8.5, 40)
            bolts.append(((xc - t, yy, am), "X"))
            nuts.append(((xc + t + 4.0, yy, am), "X"))
        ft = ft.cut(hole)
        bt = bt.cut(hole)
    # saddle cut where the frame tab meets the frame tube and the bumper tab meets the bumper tube
    if axis == "X":
        ft = ft.cut(G.cyl((a_f, F[1], zc), (0, 0, 1), L.TUBE_OD - 0.5, 40))
        bt = bt.cut(G.cyl((a_b, yb, zc), (0, 0, 1), L.TUBE_OD - 0.5, 40))
    else:
        ft = ft.cut(G.cyl((xc, F[1], a_f), (1, 0, 0), L.TUBE_OD - 0.5, 40))
        bt = bt.cut(G.cyl((xc, yb, a_b), (1, 0, 0), L.TUBE_OD - 0.5, 40))
    ftp = PartDef(f"{code}A", f"{label} chassis tab", ft, STEEL, "AISI 4130 plate 6 mm",
                  "Welded to chassis; 2x M8 8.8 + nyloc to bumper tab", "connectors")
    btp = PartDef(f"{code}B", f"{label} bumper tab", bt, STEEL, "AISI 4130 plate 6 mm",
                  "Welded to bumper tube; bolts to chassis tab", "connectors")
    return ftp, btp, bolts, nuts, abs(a_b - a_f)
