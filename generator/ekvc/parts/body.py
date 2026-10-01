"""Bodywork per style (rule 7): nose / front panel (front bumper to steering wheel), left and
right side pods (on the side bumpers) and rear panel.  3 mm shells built by lofting sections."""
from __future__ import annotations

import math

import cadquery as cq
import numpy as np

from .. import geom as G
from .. import layout as L
from . import PartDef

V = cq.Vector
T_BODY = 3.0


def _resample(pts, n):
    P = np.array(pts, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], n)
    out = np.column_stack([np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])])
    return [tuple(p) for p in out]


def profile(shape, hw, ytop, ybot, n=26, zc=0.0, lip=None):
    """U-section contour (open polyline) from left-bottom over the top to right-bottom, (z, y)."""
    h = ytop - ybot
    if shape == "box":
        c = min(45.0, 0.3 * h, 0.3 * hw)
        pts = [(-hw, ybot), (-hw, ytop - c), (-hw + c, ytop), (hw - c, ytop), (hw, ytop - c), (hw, ybot)]
    elif shape == "arrow":
        pts = [(-hw, ybot), (-hw, ytop - 0.18 * h), (-0.3 * hw, ytop - 0.03 * h), (0, ytop), (0.3 * hw, ytop - 0.03 * h),
               (hw, ytop - 0.18 * h), (hw, ybot)]
    elif shape in ("round", "f1", "slim"):
        k = 0.45
        ym = ytop - k * h
        pts = [(-hw, ybot)]
        for a in np.linspace(math.pi, 0, 17):
            pts.append((hw * math.cos(a), ym + (ytop - ym) * math.sin(a)))
        pts.append((hw, ybot))
    elif shape == "wedge":
        pts = [(-hw, ybot), (-hw, ytop - 0.15 * h), (-0.6 * hw, ytop), (0.6 * hw, ytop), (hw, ytop - 0.15 * h), (hw, ybot)]
    else:
        raise KeyError(shape)
    pts = _resample(pts, n)
    return [(z + zc, y) for z, y in pts]


def _offset(poly_open, t):
    """Offset an open (z,y) contour towards the inside of the U by t (miter)."""
    P = np.array(poly_open, float)
    n = len(P)
    out = []
    # orientation: contour goes left-bottom -> top -> right-bottom (clockwise in z-y), inside is to the right
    for i in range(n):
        if i == 0:
            d = P[1] - P[0]
        elif i == n - 1:
            d = P[-1] - P[-2]
        else:
            d1 = P[i] - P[i - 1]
            d2 = P[i + 1] - P[i]
            d = d1 / np.linalg.norm(d1) + d2 / np.linalg.norm(d2)
        d = d / np.linalg.norm(d)
        nrm = np.array([d[1], -d[0]])          # right-hand normal (inside)
        cosh = 1.0
        if 0 < i < n - 1:
            d1 = (P[i] - P[i - 1]) / np.linalg.norm(P[i] - P[i - 1])
            cosh = max(0.35, float(np.dot(np.array([d1[1], -d1[0]]), nrm)))
        out.append(tuple(P[i] + nrm * t / cosh))
    return out


def _wire_x(x, contour, y_close=None, drop=0.0):
    pts = list(contour)
    if drop:
        pts = [(pts[0][0], pts[0][1] - drop)] + pts + [(pts[-1][0], pts[-1][1] - drop)]
    return cq.Wire.makePolygon([V(x, y, z) for z, y in pts], close=True)


def _wire_z(z, contour, drop=0.0):
    pts = list(contour)   # (x, y)
    if drop:
        pts = [(pts[0][0], pts[0][1] - drop)] + pts + [(pts[-1][0], pts[-1][1] - drop)]
    return cq.Wire.makePolygon([V(x, y, z) for x, y in pts], close=True)


def loft_shell_x(stations, t=T_BODY, open_rear=True, extend=40.0):
    """stations: list of (x, contour) ordered by x ascending.  Bottom open; rear (first) open."""
    outer = cq.Solid.makeLoft([_wire_x(x, c) for x, c in stations], ruled=True)
    inner_st = [(x, _offset(c, t)) for x, c in stations]
    if open_rear:
        x0, c0 = inner_st[0]
        inner_st = [(x0 - extend, c0)] + inner_st
    # keep front face closed: inner stops t before the last station
    xl, cl = inner_st[-1]
    xp, cp = inner_st[-2]
    inner_st[-1] = (xl - t, cl)
    inner = cq.Solid.makeLoft([_wire_x(x, c, drop=60.0) for x, c in inner_st], ruled=True)
    return outer.cut(inner)


def _smooth_stations(keys, n=16):
    """keys: list of (x, dict(params)); returns n interpolated (x, params) with a C1 cubic (Catmull-Rom)."""
    xs = np.array([k[0] for k in keys])
    names = list(keys[0][1].keys())
    out = []
    tt = np.linspace(0, len(keys) - 1, n)
    for t in tt:
        i = min(int(t), len(keys) - 2)
        u = t - i
        def cr(vals):
            p0 = vals[max(i - 1, 0)]
            p1, p2 = vals[i], vals[i + 1]
            p3 = vals[min(i + 2, len(vals) - 1)]
            return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)
        x = cr(xs)
        prm = {nm: cr(np.array([k[1][nm] for k in keys])) for nm in names}
        out.append((float(x), prm))
    return out


# ---------------------------------------------------------------------------- nose
NOSE = {
    #       shape     hw_rear hw_mid hw_front  top: rear  mid  fg  front  front_bottom
    "box": ("box", 285, 288, 280, 300, 470, 478, 300, 140),
    "arrow": ("arrow", 285, 288, 190, 300, 470, 485, 260, 140),
    "round": ("round", 285, 288, 260, 305, 470, 482, 300, 140),
    "wedge": ("wedge", 285, 288, 285, 300, 470, 476, 230, 140),
    "f1": ("f1", 270, 285, 150, 300, 470, 478, 250, 150),
    "slim": ("round", 262, 284, 240, 300, 470, 476, 270, 140),
}


def nose(s, h, col_axis_pts):
    shape, hwr, hwm, hwf, ytr, ytm, ytf, ytfr, ybf = NOSE[s.nose]
    xr = h.x_dash + 36.0
    xf = h.x_fbar - L.TUBE_OD / 2 - 26.0   # behind bumper foam
    keys = [
        (xr, dict(hw=hwr, top=ytr, bot=120.0, zc=L.Z_D * 0.4)),
        (1000.0, dict(hw=hwm, top=ytm - 50, bot=122.0, zc=L.Z_D * 0.3)),
        (1150.0, dict(hw=hwm, top=ytm, bot=125.0, zc=L.Z_D * 0.2)),
        (L.X_FB + 22.0, dict(hw=hwm, top=ytf, bot=128.0, zc=L.Z_D * 0.1)),
        (xf, dict(hw=hwf, top=ytfr, bot=ybf, zc=0.0)),
    ]
    st = [(x, profile(shape, p["hw"], p["top"], p["bot"], zc=p["zc"])) for x, p in _smooth_stations(keys, 14)]
    sh = loft_shell_x(st)
    # steering column clearance hole
    a, b = col_axis_pts
    d = (b - a)
    sh = sh.cut(cq.Solid.makeCylinder(19, d.Length + 200, a - d.normalized() * 100, d.normalized()))
    return PartDef(f"{s.code}-BOD-01", f"Nose front panel {s.nose}", sh, s.body_colour, "GRP / ABS 3 mm",
                   "Covers front bumper to steering wheel (rule 7.1); metal fasteners to foot guard & front bumper",
                   "body", meta=dict(front_x=xf, front_face_y=(ybf + ytfr) / 2))


# ---------------------------------------------------------------------------- side pods
PODS = {
    #        shape   x_start  x_end_off  top  bottom  out   lip_y
    "box": ("box", 215.0, 215.0, 250.0, 72.0, 45.0, 165.0),
    "wedge": ("wedge", 215.0, 215.0, 270.0, 72.0, 45.0, 165.0),
    "round": ("round", 215.0, 215.0, 255.0, 72.0, 45.0, 165.0),
    "full": ("box", 205.0, 210.0, 285.0, 66.0, 50.0, 165.0),
    "slim": ("round", 230.0, 230.0, 215.0, 85.0, 30.0, 165.0),
}


def _pod_contour(shape, z_in, z_out, ytop, ybot, ylip, sd, n=24):
    """Section in (z, y): inner lip -> up inner wall -> over the top -> down outer wall.
    Returned left-to-right in z (so the U-offset convention applies)."""
    w = abs(z_out - z_in)
    zi, zo = 0.0, w                     # local: inner at 0, outer at w
    if shape == "box":
        c = 35.0
        loc = [(zi, ylip), (zi, ytop - c), (zi + c, ytop), (zo - c, ytop), (zo, ytop - c), (zo, ybot)]
    elif shape == "wedge":
        loc = [(zi, ylip), (zi, ytop), (zo - 25, ytop - 30), (zo, ytop - 60), (zo, ybot)]
    else:  # round
        r = min(w / 2, ytop - ylip)
        loc = [(zi, ylip)]
        cy = ytop - r
        for a in np.linspace(math.pi, 0, 15):
            loc.append((w / 2 + (w / 2) * math.cos(a), cy + r * math.sin(a)))
        loc.append((zo, ybot))
    loc = _resample(loc, n)
    if sd > 0:
        return [(z_in + z, y) for z, y in loc]
    # left side: mirror and reverse so contour runs left->right in z
    return [(z_in - z, y) for z, y in loc][::-1]


def pod(s, h, sd, min_out=0.0):
    shape, x0, xoff, ytop, ybot, out, ylip = PODS[s.pods]
    out = max(out, min_out)
    x1 = s.W - xoff
    z_in = sd * (h.z_side - 60.0)
    z_out = sd * (h.z_side + out)
    nst = 11
    stations = []
    for i in range(nst):
        t = i / (nst - 1)
        x = x0 + (x1 - x0) * t
        taper = 1.0 - 0.18 * (abs(2 * t - 1) ** 3)
        yt = ytop * (1.0 if shape != "wedge" else (1.08 - 0.25 * t)) * taper + ybot * (1 - taper)
        zo = z_in + (z_out - z_in) * (0.85 + 0.15 * taper)
        c = _pod_contour(shape, z_in, zo, yt, ybot, ylip, 1 if sd > 0 else -1)
        stations.append((x, c))
    outer = cq.Solid.makeLoft([_wire_x(x, c) for x, c in stations], ruled=True)
    inner_st = [(x, _offset(c, T_BODY)) for x, c in stations]
    xa, ca = inner_st[0]
    xb, cb = inner_st[-1]
    inner_st = [(xa + T_BODY, ca)] + inner_st[1:-1] + [(xb - T_BODY, cb)]
    inner = cq.Solid.makeLoft([_wire_x(x, c, drop=70.0) for x, c in inner_st], ruled=True)
    sh = outer.cut(inner)
    side = "left" if sd < 0 else "right"
    mid = stations[nst // 2]
    zmax = max(abs(z) for z, _ in mid[1])
    return PartDef(f"{s.code}-BOD-0{2 if sd < 0 else 3}", f"Side pod {side} {s.pods}", sh, s.body_colour,
                   "GRP / ABS 3 mm", "Left/right side bodywork on side bumper (rule 7.1.1)", "body",
                   meta=dict(mid_x=mid[0], outer_z=sd * zmax, sticker_y=0.5 * (ytop + ybot) + 10))


# ---------------------------------------------------------------------------- rear panel
def rear_panel(s, h):
    x = h.x_rbar + L.TUBE_OD / 2 + 14.5
    hw = h.rb_half - 20.0
    pts = []
    for z, y in [(-hw, 165.0), (-hw, 260.0), (-hw + 40, 300.0), (hw - 40, 300.0), (hw, 260.0), (hw, 165.0)]:
        pts.append((z, y))
    plate = G.plate_yz(pts, x - 3.0, 3.0)
    lip = G.plate_xz([(x - 3.0, -hw + 40), (x - 3.0 + 1.0, hw - 40), (x - 3.0 - 30, hw - 40), (x - 3.0 - 30, -hw + 40)], 300.0, 3.0)
    lip = G.box(x - 3.0, x + 30.0, 297.0, 300.0, -hw + 40, hw - 40)
    sh = G.fuse_all([plate, lip])
    return PartDef(f"{s.code}-BOD-04", "Rear panel", sh, s.body_colour, "GRP / ABS 3 mm",
                   "Rear bodywork behind rear tyres, on rear bumper (rule 7.1.1)", "body", meta=dict(x=x - 3.0))
