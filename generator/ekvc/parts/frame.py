"""Per-style main frame (multi-body weldment part) built from a member graph."""
from __future__ import annotations

import math
from dataclasses import dataclass

import cadquery as cq
import numpy as np

from .. import geom as G
from .. import layout as L
from . import PartDef

V = cq.Vector
YR = L.Y_RAIL
D2R = math.pi / 180


@dataclass
class Member:
    name: str
    pts: list
    kind: str = "primary"        # primary / secondary / hoop / bracing
    od: float = L.TUBE_OD
    wall: float = L.TUBE_WALL
    r: float = L.BEND_R


def xz(pts, y=YR):
    return [(x, y, z) for x, z in pts]


def z_at(poly_xz, x):
    """Z of a (monotonic in X) plan polyline at station x."""
    for (x0, z0), (x1, z1) in zip(poly_xz[:-1], poly_xz[1:]):
        if min(x0, x1) - 1e-6 <= x <= max(x0, x1) + 1e-6 and abs(x1 - x0) > 1e-9:
            return z0 + (z1 - z0) * (x - x0) / (x1 - x0)
    return poly_xz[0][1] if x < poly_xz[0][0] else poly_xz[-1][1]


def hoop_x(y):
    if y <= L.HOOP_KNEE_Y:
        return L.X_HOOP - (y - YR) * math.tan(L.HOOP_LEAN * D2R)
    xk = L.X_HOOP - (L.HOOP_KNEE_Y - YR) * math.tan(L.HOOP_LEAN * D2R)
    return xk - (y - L.HOOP_KNEE_Y) * math.tan(L.HOOP_UPPER_LEAN * D2R)


def foot_guard_pts():
    zc, hb, ht = L.Z_D, L.FB_HALF, L.FG_TOP_HALF
    return [(L.X_FB, YR, zc - hb), (L.X_FB, L.FOOT_GUARD_TOP, zc - ht), (L.X_FB, L.FOOT_GUARD_TOP, zc + ht), (L.X_FB, YR, zc + hb)]


def fg_half_at(y):
    """Half-width (centre-line) of the inclined foot-guard legs at height y."""
    return L.FB_HALF - (L.FB_HALF - L.FG_TOP_HALF) * (y - YR) / (L.FOOT_GUARD_TOP - YR)


def brace_x(y):
    xt = hoop_x(650.0)
    return L.X_RBH + (y - YR) / (650.0 - YR) * (xt - L.X_RBH)


# ---------------------------------------------------------------------------- style plans
def plan(s, h):
    """Return dict with main rails (xz), extra members, left outer frame points for side
    connectors and the connector stations."""
    W = s.W
    xd = h.x_dash
    zfl, zfr = L.Z_D - L.FB_HALF, L.Z_D + L.FB_HALF
    zo = -(h.z_side - 68.0)            # left outrigger tip Z
    straight_L = [(L.X_RBH, L.Z_LM), (1040.0, L.Z_LM), (L.X_FB, zfl)]
    straight_R = [(L.X_RBH, L.Z_RM), (1040.0, L.Z_RM), (L.X_FB, zfr)]
    P = dict(L=straight_L, R=straight_R, extra=[], side_x=(300.0, 760.0), left_outer=None, outriggers=True,
             floor_x=[L.X_SEAT_XM, xd])
    f = s.frame
    if f == "ladder3":
        P["floor_x"] = [L.X_SEAT_XM, xd, 990.0]
    elif f == "taper":
        P["L"] = [(L.X_RBH, L.Z_LM), (700.0, L.Z_LM), (L.X_FB, zfl)]
        P["R"] = [(L.X_RBH, L.Z_RM), (700.0, L.Z_RM), (L.X_FB, zfr)]
        P["left_outer"] = [(L.X_AXM, -L.Z_RBOX), (300.0, zo), (760.0, zo), (985.0, -295.0)]
        P["extra"] += [Member("Arrow brace right", xz([(L.X_EBAY1, L.Z_EBAY - 5), (1000.0, z_at(P['R'], 1000.0) + 2)]), "secondary")]
        P["outriggers"] = False
        P["floor_x"] = [L.X_SEAT_XM, xd]
    elif f == "ladder5":
        P["floor_x"] = [L.X_SEAT_XM, xd, 900.0, 1000.0]
        for zz, nm in ((L.Z_LM, "left"), (L.Z_RM, "right")):
            P["extra"].append(Member(f"Upper side rail {nm}", [(hoop_x(230.0), 230.0, zz), (xd, 230.0, zz)], "secondary"))
    elif f == "bowed":
        P["L"] = [(L.X_RBH, L.Z_LM), (790.0, L.Z_LM), (870.0, -332.0), (950.0, -332.0), (1050.0, -292.0), (L.X_FB, zfl)]
        P["extra"] += [Member("Floor X brace 1", xz([(L.X_SEAT_XM, L.Z_LM), (xd, L.Z_RM)]), "bracing"),
                       Member("Floor X brace 2", xz([(L.X_SEAT_XM, L.Z_RM), (xd, L.Z_LM)]), "bracing")]
    elif f == "xbrace":
        P["extra"] += [Member("Cockpit X brace 1", xz([(xd, L.Z_LM), (1000.0, L.Z_RM)]), "bracing"),
                       Member("Cockpit X brace 2", xz([(xd, L.Z_RM), (1000.0, L.Z_LM)]), "bracing"),
                       Member("Engine bay X brace 1", xz([(L.X_CRADLE[0], L.Z_RM), (L.X_CRADLE[1], L.Z_EBAY)]), "bracing"),
                       Member("Engine bay X brace 2", xz([(L.X_CRADLE[0], L.Z_EBAY), (L.X_CRADLE[1], L.Z_RM)]), "bracing")]
        P["floor_x"] = [L.X_SEAT_XM, xd, 1000.0]
    elif f == "perimeter":
        P["left_outer"] = [(L.X_AXM, -L.Z_RBOX), (150.0, -L.Z_RBOX), (240.0, zo), (900.0, zo), (1010.0, -296.0)]
        P["extra"] += [Member("Perimeter rail right front", xz([(L.X_EBAY1, L.Z_EBAY), (900.0, L.Z_EBAY), (1010.0, 152.0)]), "primary")]
        P["extra"] += [Member(f"Perimeter tie {x:.0f}", xz([(x, L.Z_LM), (x, zo)]), "secondary") for x in (300.0, 620.0, 760.0)]
        P["outriggers"] = False
    elif f == "spine":
        P["extra"] += [Member("Centre spine", xz([(L.X_SEAT_XM, L.Z_D), (L.X_FB, L.Z_D)]), "primary"),
                       Member("Spine V left", xz([(1020.0, L.Z_D), (880.0, L.Z_LM)]), "bracing"),
                       Member("Spine V right", xz([(1020.0, L.Z_D), (880.0, L.Z_RM)]), "bracing")]
        P["floor_x"] = [L.X_SEAT_XM, xd]
    elif f == "endurance":
        P["floor_x"] = [L.X_SEAT_XM, xd, 1000.0]
        for zz, nm in ((L.Z_LM, "left"), (L.Z_RM, "right")):
            P["extra"].append(Member(f"Upper side rail {nm}", [(hoop_x(230.0), 230.0, zz), (xd, 230.0, zz)], "secondary"))
        P["extra"] += [Member("Floor diagonal", xz([(L.X_SEAT_XM, L.Z_LM), (xd, L.Z_RM)]), "bracing"),
                       Member("Foot-guard brace left", [(L.X_FB, 330.0, L.Z_D - fg_half_at(330.0)), (1110.0, YR, z_at(straight_L, 1110.0))], "bracing"),
                       Member("Foot-guard brace right", [(L.X_FB, 330.0, L.Z_D + fg_half_at(330.0)), (1110.0, YR, z_at(straight_R, 1110.0))], "bracing"),
                       Member("Engine bay diagonal", xz([(L.X_CRADLE[1], L.Z_RM), (700.0, L.Z_EBAY)]), "bracing")]
    elif f == "minimal":
        P["floor_x"] = [L.X_SEAT_XM]
    elif f == "wedge":
        P["L"] = [(L.X_RBH, L.Z_LM), (560.0, L.Z_LM), (L.X_FB, zfl)]
        P["left_outer"] = [(L.X_AXM, -L.Z_RBOX), (260.0, zo), (560.0, zo), (1000.0, -298.0)]
        P["extra"] += [Member("Wedge brace right", xz([(L.X_EBAY1, L.Z_EBAY - 5), (1000.0, L.Z_RM + 2)]), "secondary")]
        P["side_x"] = (300.0, 540.0)
        P["outriggers"] = False
    else:
        raise KeyError(f)
    return P


def left_frame_z(P, x):
    if P["left_outer"]:
        return z_at(P["left_outer"], x)
    return -(abs(P.get("zo", 0)) or 0)


# ---------------------------------------------------------------------------- members
def members(s, h):
    P = plan(s, h)
    W, KH = s.W, s.KH
    xd = h.x_dash
    zo = -(h.z_side - 68.0)
    M = []
    M.append(Member("Main rail left", xz(P["L"]), "primary"))
    M.append(Member("Main rail right", xz(P["R"]), "primary"))
    M.append(Member("Rear bulkhead", xz([(L.X_RBH, -L.Z_RBOX), (L.X_RBH, L.Z_RBOX)]), "primary"))
    M.append(Member("Axle cross member", xz([(L.X_AXM, -L.Z_RBOX), (L.X_AXM, L.Z_RBOX)]), "primary"))
    M.append(Member("Rear box side left", xz([(L.X_RBH, -L.Z_RBOX), (L.X_AXM, -L.Z_RBOX)]), "primary"))
    M.append(Member("Engine bay outer rail", xz([(L.X_RBH, L.Z_RBOX), (L.X_AXM, L.Z_RBOX), (140.0, L.Z_RBOX),
                                                 (L.X_EBAY0, L.Z_EBAY), (L.X_EBAY1, L.Z_EBAY),
                                                 (L.X_EBAY1, z_at(P["R"], L.X_EBAY1))]), "primary"))
    for i, xc in enumerate(L.X_CRADLE):
        M.append(Member(f"Engine cradle tube {i + 1}", xz([(xc, z_at(P["R"], xc)), (xc, L.Z_EBAY)]), "primary"))
    M.append(Member("Battery support", xz([(700.0, z_at(P["R"], 700.0)), (700.0, L.Z_EBAY)]), "secondary"))
    # roll hoop (single bent tube) + braces
    xt = hoop_x(L.HOOP_TOP_Y)
    xk = hoop_x(L.HOOP_KNEE_Y)
    M.append(Member("Roll hoop", [(L.X_HOOP, YR, L.Z_LM), (xk, L.HOOP_KNEE_Y, L.Z_LM), (xt, L.HOOP_TOP_Y, L.Z_LM),
                                  (xt, L.HOOP_TOP_Y, L.Z_RM), (xk, L.HOOP_KNEE_Y, L.Z_RM), (L.X_HOOP, YR, L.Z_RM)],
                    "hoop", r=L.HOOP_BEND_R))
    M.append(Member("Hoop cross bar", [(hoop_x(L.HOOP_CROSS_Y), L.HOOP_CROSS_Y, L.Z_LM),
                                       (hoop_x(L.HOOP_CROSS_Y), L.HOOP_CROSS_Y, L.Z_RM)], "secondary"))
    for zz, nm in ((L.Z_LM, "left"), (L.Z_RM, "right")):
        M.append(Member(f"Hoop brace {nm}", [(hoop_x(L.HOOP_KNEE_Y), L.HOOP_KNEE_Y, zz), (L.X_RBH, YR, zz)], "hoop"))
    M.append(Member("Brace cross bar", [(brace_x(410.0), 410.0, L.Z_LM), (brace_x(410.0), 410.0, L.Z_RM)], "secondary"))
    M.append(Member("Silencer stay", [(brace_x(420.0), 420.0, L.Z_RM), (brace_x(420.0) - 2, 412.0, 470.0)], "secondary"))
    for zz in (240.0, 400.0):
        M.append(Member(f"Radiator upright Z{zz:.0f}", [(L.X_AXM, YR, zz), (L.X_AXM, 200.0, zz)], "secondary"))
    # front
    zfl, zfr = L.Z_D - L.FB_HALF, L.Z_D + L.FB_HALF
    M.append(Member("Front bulkhead", xz([(L.X_FB, zfl), (L.X_FB, zfr)]), "primary"))
    M.append(Member("Foot guard hoop", foot_guard_pts(), "primary"))
    pz = fg_half_at(L.PEDAL_XBAR_Y)
    M.append(Member("Pedal cross bar", [(L.X_FB, L.PEDAL_XBAR_Y, L.Z_D - pz), (L.X_FB, L.PEDAL_XBAR_Y, L.Z_D + pz)], "secondary"))
    M.append(Member("Front axle beam", xz([(W, -KH + 18), (W, KH - 18)]), "primary"))
    zl, zr = z_at(P["L"], xd), z_at(P["R"], xd)
    M.append(Member("Dash hoop (steering support)", [(xd, YR, zl), (xd, 300.0, zl), (xd, 300.0, zr), (xd, YR, zr)], "secondary"))
    for x in P["floor_x"]:
        M.append(Member(f"Floor cross member X{x:.0f}", xz([(x, z_at(P["L"], x)), (x, z_at(P["R"], x))]), "secondary"))
    if P["left_outer"]:
        M.append(Member("Left outer rail", xz(P["left_outer"]), "primary"))
    elif P["outriggers"]:
        for x in P["side_x"]:
            M.append(Member(f"Left outrigger X{x:.0f}", xz([(x, z_at(P["L"], x)), (x, zo)]), "secondary"))
    M.extend(P["extra"])
    return M, P


# ---------------------------------------------------------------------------- plates welded to frame
def c_brackets(s):
    """King-pin C-brackets (two ears + web) at both ends of the front axle beam."""
    W, KH = s.W, s.KH
    c = math.radians(L.CASTER)
    k = V(-math.sin(c), math.cos(c), 0)
    e1 = V(math.cos(c), math.sin(c), 0)
    out = []
    for sd in (-1, 1):
        kp = V(W, L.Y_FAX, sd * KH)
        half = L.KP_BOSS_LEN / 2 + 3.5
        wi = L.KP_WEB_INBOARD             # web inboard of the boss, clear of the knuckle arm at full lock
        ears = []
        for t in (-1, 1):
            o = kp + k * (t * half)
            ears.append(G.plate_on_plane(o, e1, V(0, 0, sd), [(-22, -wi), (22, -wi), (22, 0)] +
                                         [(22 * math.cos(a), 22 * math.sin(a)) for a in np.linspace(0, math.pi, 9)][1:-1] +
                                         [(-22, 0)], 6))
        # web plate inboard of the boss, from lower ear down to the beam
        lo = kp + k * (-half) + V(0, 0, -sd * wi)
        hi = kp + k * (half) + V(0, 0, -sd * wi)
        web = G.plate_on_plane(V(0, 0, sd * (KH - wi)), V(1, 0, 0), V(0, 1, 0),
                               [(W - 24, YR - 6), (W + 24, YR - 6), (lo.x + 24, lo.y), (hi.x + 24, hi.y + 3),
                                (hi.x - 24, hi.y + 3), (lo.x - 24, lo.y)], 6)
        b = G.fuse_all([*ears, web])
        b = b.cut(G.cyl(kp, k, 10.5, 200))
        out.append((f"King-pin C-bracket {'left' if sd < 0 else 'right'}", b))
    return out


def jack_pads():
    out = []
    for zz in (-200.0, 200.0):
        p = G.box(L.X_RBH - 30, L.X_RBH + 30, YR - L.TUBE_OD / 2, YR - L.TUBE_OD / 2 + 6, zz - 25, zz + 25)
        out.append((f"Jack pad Z{zz:.0f}", p))
    return out


def radiator_tabs():
    out = []
    for zz in (240.0, 400.0):
        out.append((f"Radiator tab Z{zz:.0f}", G.box(L.X_AXM, 86.0, 186.0, 196.0, zz - 15, zz + 15)))
    return out


# ---------------------------------------------------------------------------- coping & part
def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-9)))
    return (a + ab * t - p).Length


def _segments(m):
    P = [V(*p) for p in m.pts]
    return list(zip(P[:-1], P[1:]))


def build_frame(s, h, cope=True):
    M, P = members(s, h)
    bodies = []
    for i, m in enumerate(M):
        tube = G.bent_tube(m.pts, m.od, m.wall, m.r)
        if cope:
            ends = [V(*m.pts[0]), V(*m.pts[-1])]
            for j, n in enumerate(M):
                if j == i:
                    continue
                for e in ends:
                    for a, b in _segments(n):
                        if _seg_dist(e, a, b) < 3.0 and (e - a).Length > 3 and (e - b).Length > 3:
                            d = (b - a)
                            cutter = cq.Solid.makeCylinder(n.od / 2 - 0.2, d.Length, a, d.normalized())
                            win = G.box(e.x - 30, e.x + 30, e.y - 30, e.y + 30, e.z - 30, e.z + 30)
                            try:
                                c2 = cutter.intersect(win)
                                t2 = tube.cut(c2)
                                if t2.isValid() and t2.Volume() > 0.5 * tube.Volume():
                                    tube = t2
                            except Exception:
                                pass
        bodies.append((m.name, tube, m))
    plates = c_brackets(s) + jack_pads() + radiator_tabs()
    return bodies, plates, M, P


def frame_part(s, h):
    bodies, plates, M, P = build_frame(s, h)
    shapes = [b for _, b, _ in bodies] + [p for _, p in plates]
    comp = cq.Compound.makeCompound(shapes)
    length = 0.0
    for m in M:
        pts = [V(*p) for p in m.pts]
        length += sum((b - a).Length for a, b in zip(pts[:-1], pts[1:]))
    area = math.pi / 4 * (L.TUBE_OD ** 2 - (L.TUBE_OD - 2 * L.TUBE_WALL) ** 2)
    mass = length * area * 7.85e-6
    pd = PartDef(f"{s.code}-FRM-01", f"Main frame {s.name}", comp, s.colour, L.TUBE_MAT,
                 f"{len(M)} members, {length / 1000:.1f} m of 25.4x{L.TUBE_WALL} tube (~{mass:.1f} kg tube mass), "
                 f"multi-body weldment", "frame",
                 meta=dict(members=[(m.name, m.kind, m.pts) for m in M], plan=P, tube_length=length, tube_mass=mass))
    return pd
