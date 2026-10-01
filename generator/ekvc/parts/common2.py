"""Common parts: steering group, pedals, seat, safety, fuel, cooling, electrics, exhaust,
gear change, engine mounts, hitch, fasteners, firewall, anti-intrusion plate."""
from __future__ import annotations

import math

import cadquery as cq

from .. import geom as G
from .. import layout as L
from . import PartDef
from .colours import ALU, BLACK, BLUE, COPPER, DARK, RED, RUBBER, STEEL, YELLOW, ZINC

V = cq.Vector
D2R = math.pi / 180


def _vec(*a):
    return V(*a)


A_UP = V(-math.cos(L.COL_ANGLE * D2R), math.sin(L.COL_ANGLE * D2R), 0)   # column axis towards driver
U_FWD = V(*L.col_u())                                                   # perpendicular, forward-up
Z = V(0, 0, 1)
CB_Y = L.Y_ARM + L.PITMAN_R * L.col_u()[1]
COL_LEN = (L.WHEEL_Y - CB_Y) / math.sin(L.COL_ANGLE * D2R)
HUB = A_UP * COL_LEN                      # steering wheel hub, relative to column bottom


# ================================================================== steering group (origin = column bottom)
def steering_column():
    s = G.ring(A_UP * (-15), A_UP, 22, 16, COL_LEN + 40, centered=False)
    # splined top
    s = s.fuse(G.cyl(A_UP * (COL_LEN + 25), A_UP, 24, 30, centered=False)).clean()
    return PartDef("C-STR-01", "Steering column 22x3", s, STEEL, "AISI 4130 tube 22 x 3",
                   f"Length {COL_LEN + 55:.0f} mm, {L.COL_ANGLE:.0f} deg below horizontal", "steering")


def steering_wheel():
    n = A_UP
    e_lat = Z
    e_up = U_FWD
    c = HUB + n * 25
    R = (L.STEER_WHEEL_OD - 25) / 2
    rim = cq.Solid.makeTorus(R, 12.5, c, n)
    parts = [rim, G.cyl(c, n, 62, 34)]
    for d in (e_lat, e_lat * -1, e_up * -1):
        parts.append(G.rod(c + d * 25 - n * 6, c + d * (R - 4) + n * 2, 16))
    s = G.fuse_all(parts)
    return PartDef("C-STR-02", "Steering wheel 280 OD round", s, (0.12, 0.12, 0.12),
                   "Aluminium spokes, leather-wrapped rim", "Full circle 280 mm OD (rule 4.2 >= 254 mm), quick-release hub", "steering")


def pitman_arm():
    """Arm perpendicular to the column, ending in a horizontal pad with two vertical M8 holes
    (rod ends hang below the pad, one per tie rod, 20 mm apart)."""
    d = U_FWD * -1                     # arm points rearward-down
    o = V(0, 0, 0)
    tip = d * L.PITMAN_R
    pts2 = [(-18, -16), (L.PITMAN_R - 6, -16), (L.PITMAN_R - 6, 16), (-18, 16)]
    s = G.plate_on_plane(o, d, Z, pts2, 8)
    s = s.fuse(G.ring(o, A_UP, 34, 22, 26))
    y_eye_top = (L.Y_ARM - 9.0 + 5.0) - CB_Y
    pad = G.box(tip.x - 16, tip.x + 16, y_eye_top, y_eye_top + 10, -24, 24)
    web = G.box(tip.x - 6, tip.x + 6, y_eye_top + 8, tip.y + 10, -16, 16)
    s = G.fuse_all([s, pad, web])
    for zz in (-10, 10):
        s = s.cut(G.cyl(V(tip.x, y_eye_top + 5, zz), V(0, 1, 0), 8.5, 30))
    return PartDef("C-STR-03", "Pitman steering arm 8mm", s, STEEL, "AISI 4130 plate 8 mm",
                   f"Welded to column, tie-rod pad at R{L.PITMAN_R:.0f} (2x M8 vertical)", "steering")


def column_upper_bracket():
    """Bearing housing at the upper bearing + plate down to the dash bar (top of bar at Y=312.7)."""
    c = A_UP * (COL_LEN - L.COL_UPPER_BRG)
    yb = (300.0 + L.TUBE_OD / 2) - CB_Y            # dash bar top in local coords
    housing = G.ring(c, A_UP, 44, 22.2, 30)
    plate = G.plate_xy([(c.x - 24, c.y - 4), (c.x + 24, c.y - 4), (c.x + 30, yb), (c.x - 30, yb)], -4, 8)
    foot = G.box(c.x - 32, c.x + 32, yb - 2, yb + 4, -22, 22)
    s = G.fuse_all([housing, plate, foot])
    s = s.cut(G.cyl(c, A_UP, 22.2, 40))
    return PartDef("C-STR-04", "Column upper bearing bracket", s, STEEL, "AISI 4130 + bronze bush",
                   "Bolted to dash bar (2x M8)", "steering")


def column_lower_bracket(beam_dx=88.0):
    """Lower bearing housing at the column bottom, plate down to the front axle beam, and two
    adjustable positive steering stops acting on the pitman arm (rule 4.3 - on chassis)."""
    c = A_UP * 18
    by = L.Y_RAIL + L.TUBE_OD / 2 - CB_Y
    housing = G.ring(c, A_UP, 44, 22.2, 26)
    plate = G.plate_xy([(c.x - 18, c.y - 10), (c.x + 18, c.y + 4), (beam_dx + 20, by), (beam_dx - 26, by)], -4, 8)
    parts = [housing, plate]
    # stop collar with two stop bolts at +-(lock+clearance) around the column axis
    col = G.ring(A_UP * 9, A_UP, 70, 40, 6)
    parts.append(col)
    for sgn in (-1, 1):
        ang = sgn * 62 * D2R
        rd = (U_FWD * -1) * math.cos(ang) + Z * math.sin(ang)
        p = A_UP * 4 + rd * 30
        parts.append(G.cyl(p, A_UP, 10, 18))
    s = G.fuse_all(parts).cut(G.cyl(c, A_UP, 22.2, 60))
    return PartDef("C-STR-05", "Column lower bracket with steering stops", s, STEEL, "AISI 4130 plate 8 mm",
                   "Welded to front axle beam; M10 stop bolts set to full-lock pitman angle", "steering")


def kingpin_bolt():
    c = math.radians(L.CASTER)
    k = V(-math.sin(c), math.cos(c), 0)
    s = G.cyl(V(0, 0, 0), k, 10, 132)
    s = s.fuse(G.cyl(k * 69.5, k, 18, 7)).fuse(G.cyl(k * -70, k, 17, 9)).clean()
    return PartDef("C-STR-06", "King pin bolt M10x130 + nyloc", s, ZINC, "Grade 10.9 bolt + Nyloc nut",
                   f"Caster {L.CASTER:.0f} deg", "steering")


# ================================================================== pedal box (global coordinates)
PEDALS = (("Clutch", L.Z_D - 100), ("Brake", L.Z_D + 50), ("Throttle", L.Z_D + 140))   # C-B-A left->right


def pedal(kind):
    """Hanging pedal: pivot above/ahead of the toes, pad under the ball of the foot."""
    px, py = L.PEDAL_PIVOT
    z = dict(PEDALS)[kind]
    n = V(L.PEDAL_PAD_N[0], L.PEDAL_PAD_N[1], 0).normalized()      # towards driver
    fwd = n * -1
    pad = V(L.PEDAL_PAD[0], L.PEDAL_PAD[1], z)
    arm0 = pad + fwd * 8.0                                           # arm sits in front of the pad
    piv = V(px, py, z)
    d = (piv - arm0)
    Ln = d.Length
    d = d.normalized()
    sleeve = G.ring(piv, Z, 26, 16.5, 30)
    arm = G.plate_on_plane(arm0, d, fwd, [(0, -9), (Ln, -9), (Ln, 9), (0, 9)], 10)
    padw = 64 if kind != "Throttle" else 44
    padl = 80 if kind != "Throttle" else 110
    padp = G.plate_on_plane(pad, d, Z, G.rounded_rect(padl, padw, 8), 6)
    parts = [sleeve, arm, padp]
    if kind == "Brake":
        ul = V(-math.sin(math.radians(L.BRAKE_LEVER_TILT)), math.cos(math.radians(L.BRAKE_LEVER_TILT)), 0)
        parts.append(G.plate_on_plane(piv, ul, V(ul.y, -ul.x, 0), [(0, -8), (L.BRAKE_LEVER + 2, -8), (L.BRAKE_LEVER + 2, 8), (0, 8)], 10))
        parts.append(G.cyl(piv + ul * L.BRAKE_LEVER, Z, 18, 20))
    s = G.fuse_all(parts).cut(G.cyl(piv, Z, 16.5, 40))
    pid = {"Clutch": "C-PED-01", "Brake": "C-PED-02", "Throttle": "C-PED-03"}[kind]
    return PartDef(pid, f"{kind} pedal", s, ALU if kind != "Brake" else STEEL, "Al 6061-T6 / AISI 4130 (brake)",
                   f"Hanging pedal on 16 mm shaft, pad at Z={z:.0f} (CBA left to right, rule 6.4.2)", "pedals")


def pedal_shaft_brackets():
    px, py = L.PEDAL_PIVOT
    z0, z1 = PEDALS[0][1] - 45, PEDALS[2][1] + 40
    shaft = G.cyl(V(px, py, (z0 + z1) / 2), Z, 16, z1 - z0 + 30)
    parts = [shaft]
    xb = L.X_FB
    for z in (z0, (PEDALS[0][1] + PEDALS[1][1]) / 2, z1):
        parts.append(G.plate_xy(G.hull2d([(px - 14, py - 14), (px + 14, py - 14), (px - 14, py + 14), (px + 10, py + 16),
                                         (xb - 6, L.PEDAL_XBAR_Y - 14), (xb - 6, L.PEDAL_XBAR_Y + 12)]), z - 3, 6))
    # throttle & brake travel stops: M8 bolts in tabs ahead of the pedal arms
    for kind in ("Brake", "Throttle"):
        z = dict(PEDALS)[kind]
        parts.append(G.box(1284, 1292, 222, 232, z - 14, z + 14))
        parts.append(G.cyl(V(1287, 227, z), V(1, 0, 0), 8, 22))
        parts.append(G.box(1292, xb + L.TUBE_OD / 2 - 0.5, 224, 230, z - 6, z + 6))
    s = G.fuse_all(parts)
    return PartDef("C-PED-04", "Pedal shaft, hangers and pedal stops", s, STEEL, "AISI 4130",
                   "Hangers welded to foot-guard cross bar; stops limit pedal travel (rule 5.2, 6.4.2)", "pedals")


_ul = (-math.sin(math.radians(L.BRAKE_LEVER_TILT)), math.cos(math.radians(L.BRAKE_LEVER_TILT)))
MC_X1 = L.PEDAL_PIVOT[0] + L.BRAKE_LEVER * _ul[0] - 30.0      # MC flange
MC_Y = L.PEDAL_PIVOT[1] + L.BRAKE_LEVER * _ul[1]


def master_cylinder():
    z = dict(PEDALS)["Brake"]
    y = MC_Y
    x1 = MC_X1
    body = G.cyl(V(x1 - 57.5, y, z), V(1, 0, 0), 30, 115)
    flange = G.box(x1 - 3, x1 + 5, y - 22, y + 22, z - 22, z + 22)
    rod = G.cyl(V(x1 + 20, y, z), V(1, 0, 0), 8, 34)
    res_stem = G.cyl(V(x1 - 85, y + 22, z), V(0, 1, 0), 10, 18)
    reservoir = G.cyl(V(x1 - 85, y + 48, z), V(0, 1, 0), 36, 36)
    cap = G.cyl(V(x1 - 85, y + 68, z), V(0, 1, 0), 40, 6)
    s = G.fuse_all([body, flange, rod, res_stem, reservoir, cap])
    return PartDef("C-BRK-05", "Brake master cylinder 5/8in with reservoir", s, (0.2, 0.2, 0.25),
                   "Bought out, DOT4", "Own fluid reservoir (rule 5.1); pushed by brake pedal upper lever", "brakes",
                   meta={"outlet": (x1 - 115, y, z)})


def mc_bracket():
    z = dict(PEDALS)["Brake"]
    y = MC_Y
    x1 = MC_X1
    xb = L.X_FB
    s = G.plate_yz([(z - 30, y - 30), (z + 30, y - 30), (z + 30, y + 28), (z - 30, y + 28)], x1 + 5, 6)
    s = s.cut(G.cyl(V(x1 + 8, y, z), V(1, 0, 0), 10, 10))
    arms = [G.plate_xy(G.hull2d([(x1 + 5, y - 26), (x1 + 11, y - 26), (x1 + 5, y + 26), (xb - 6, L.FOOT_GUARD_TOP - 10),
                                 (xb - 6, L.FOOT_GUARD_TOP + 8)]), zz - 3, 6) for zz in (z - 27, z + 27)]
    s = G.fuse_all([s, *arms])
    return PartDef("C-BRK-06", "Master cylinder bracket", s, STEEL, "AISI 4130 plate 6 mm",
                   "Welded to foot-guard top bar", "brakes")


def over_travel_switch():
    z = dict(PEDALS)["Brake"]
    body = G.box(1286, 1300, 250, 274, z - 12, z + 12)
    plunger = G.cyl(V(1283, 262, z), V(1, 0, 0), 8, 6)
    tab = G.box(1300, L.X_FB + L.TUBE_OD / 2 - 0.5, 254, 270, z - 16, z + 16)
    s = G.fuse_all([body, plunger, tab])
    return PartDef("C-BRK-07", "Brake over-travel switch", s, (0.9, 0.9, 0.1), "Bought out, NC micro-switch IP67",
                   "Hit by the brake pedal arm only on over-travel; in series with kill switches (rule 5.3)", "brakes")


def brake_line(caliper_global, rail_left=None, code="C"):
    """Braided line: MC -> over the tie rods inside the nose -> over the left rail at X 940 ->
    outboard along the left main rail (so it never crosses the firewall) -> caliper."""
    from .frame import z_at
    rail = rail_left or [(L.X_RBH, L.Z_LM), (L.X_FB, L.Z_LM)]
    z = dict(PEDALS)["Brake"]
    x0 = MC_X1 - 115
    y = MC_Y
    cx, cy, cz = caliper_global
    pts = [(x0, y, z), (x0 - 25, y, z), (1100, y - 10, -190), (1100, 128, -262), (965, 124, -262)]
    for x in (930, 860, 760, 600, 420, 300, 150, 40):
        zr = z_at(rail, x) - 30.0
        pts.append((x, 70.0 if x < 930 else 95.0, zr))
    pts += [(-30, 120, z_at(rail, 0) - 22), (cx - 20, cy - 10, cz - 40), (cx, cy + 22, cz - 25)]
    s = G.bent_tube(pts, 6.0, 1.5, 25)
    return PartDef(f"{code}-BRK-08", "Brake line 3/16in braided", s, (0.3, 0.3, 0.3), "Stainless braided PTFE hose",
                   "Metal P-clips every 300 mm; routed outboard of left main rail (rule 5.4)", "brakes")


# ================================================================== seat
SEAT_PATH = [(650.0, 80.0), (L.SEAT_CORNER[0], L.SEAT_CORNER[1]),
             (L.SEAT_CORNER[0] - 540 * math.tan(L.BACK_ANGLE * D2R), L.SEAT_CORNER[1] + 540)]


def seat():
    pts = [(x, y, L.Z_D) for x, y in SEAT_PATH]
    shell = G.sweep_rect(pts, 360, 5, 90, up=(0, 0, 1))
    side = [(600, 78), (520, 168), (300, 182), (140, 330), (60, 470), (34, 560), (SEAT_PATH[1][0] - 2, 52)]
    walls = [G.plate_xy(side, L.Z_D + sgn * 180 - 2.5, 5) for sgn in (-1, 1)]
    s = G.fuse_all([shell, *walls])
    return PartDef("C-SEA-01", "Bucket seat 360 fibreglass", s, (0.08, 0.08, 0.08), "GRP fibreglass 5 mm",
                   f"Back angle {L.BACK_ANGLE:.0f} deg from vertical (rule <= 30); 4 mounts (rule 3.1)", "seat")


def seat_bracket_front():
    s = G.box(-20, 20, 0, 13, -15, 15).cut(G.cyl(V(0, 6, 0), V(0, 1, 0), 8.5, 20))
    return PartDef("C-SEA-02", "Seat front mount block", s, STEEL, "AISI 4130 5 mm plate stack",
                   "Welded on seat cross member (primary member), M8 + nyloc", "seat")


def seat_bracket_rear():
    s = G.box(0, 30, -18, 18, -3, 3)
    s = s.cut(G.cyl(V(22, 0, 0), V(0, 0, 1), 8.5, 10))
    return PartDef("C-SEA-03", "Seat back mount tab", s, STEEL, "AISI 4130 plate 6 mm",
                   "Welded on roll-hoop cross bar, M8 + nyloc", "seat")


# ================================================================== safety
def kill_switch():
    box = G.box(-34, 34, 0, 55, -34, 34)
    box = G.fillet(box, "|Y", 5)
    mush = G.cyl(V(0, 70, 0), V(0, 1, 0), 40, 14)
    stem = G.cyl(V(0, 59, 0), V(0, 1, 0), 22, 10)
    s = G.fuse_all([box, stem, mush])
    return PartDef("C-SAF-01", "Kill switch 40mm red mushroom", s, YELLOW, "Bought out, IP65, push-off twist-release",
                   "Rule 6.5 - red 40 mm head; 3 fitted (driver + both sides of roll hoop)", "safety",
                   meta={"button_rgb": RED})


def kill_switch_button():
    mush = G.cyl(V(0, 70, 0), V(0, 1, 0), 40, 14)
    return PartDef("C-SAF-01B", "Kill switch red mushroom head", mush, RED, "Bought out", "Part of C-SAF-01", "safety")


def kill_switch_box():
    box = G.fillet(G.box(-34, 34, 0, 55, -34, 34), "|Y", 5)
    s = box.fuse(G.cyl(V(0, 59, 0), V(0, 1, 0), 22, 10))
    return PartDef("C-SAF-01", "Kill switch enclosure", s, YELLOW, "Bought out, IP65",
                   "Rule 6.5 - push-off twist-release; mount on hinge tab welded to chassis", "safety")


def kill_switch_tab():
    s = G.box(-40, 40, -6, 0, -40, 40)
    s = s.fuse(G.cyl(V(0, -6, -46), V(1, 0, 0), 16, 60)).clean()
    return PartDef("C-SAF-02", "Kill switch mounting hinge tab", s, STEEL, "AISI 4130 plate 6 mm",
                   "Welded to chassis tube (rule 6.5)", "safety")


def brake_light():
    body = G.box(-30, 0, -22, 22, -45, 45)
    lens = G.box(-34, -30, -18, 18, -41, 41)
    tab = G.box(0, 12, -30, 30, -10, 10)
    s = G.fuse_all([body, tab])
    return PartDef("C-SAF-03", "Brake light LED red", s, BLACK, "Bought out 12 V LED", "Top centre of roll hoop (rule 5.6)",
                   "safety", meta={"lens": lens})


def brake_light_lens():
    lens = G.box(-34, -30, -18, 18, -41, 41)
    return PartDef("C-SAF-03L", "Brake light lens", lens, RED, "Polycarbonate red", "Part of C-SAF-03", "safety")


EXT_C = (540.0, 125.0, -345.0)


def extinguisher():
    x, y, z = EXT_C
    body = G.cyl(V(x - 20, y, z), V(1, 0, 0), 82, 260)
    dome = cq.Solid.makeSphere(41, V(x - 150, y, z), angleDegrees1=-90, angleDegrees2=90).rotate(V(x - 150, y, z), V(x - 150, y, z + 1), 90)
    neck = G.cyl(V(x + 125, y, z), V(1, 0, 0), 30, 30)
    valve = G.box(x + 140, x + 175, y - 18, y + 26, z - 14, z + 14)
    lever = G.box(x + 150, x + 230, y + 22, y + 30, z - 10, z + 10)
    hose = G.cyl(V(x + 180, y - 5, z), V(1, 0, 0), 12, 40)
    s = G.fuse_all([body, neck, valve, lever, hose])
    try:
        s = s.fuse(cq.Solid.makeSphere(41, V(x - 150, y, z)).cut(G.box(x - 150, x + 100, y - 50, y + 50, z - 50, z + 50)))
    except Exception:
        pass
    return PartDef("C-SAF-04", "Fire extinguisher 1kg ABC", s, RED, "Bought out 1 kg ABC dry powder",
                   "Rigidly mounted in driver compartment, not on firewall (rule 6.9)", "safety")


def extinguisher_bracket():
    x, y, z = EXT_C
    base = G.plate_yz([(L.Z_LM - 10, y - 45), (L.Z_LM - 10, y + 45), (z - 30, y + 45), (z - 30, y - 45)], x - 120, 6)
    base2 = G.plate_yz([(L.Z_LM - 10, y - 45), (L.Z_LM - 10, y + 45), (z - 30, y + 45), (z - 30, y - 45)], x + 60, 6)
    straps = []
    for xx in (x - 117, x + 63):
        straps.append(G.ring(V(xx, y, z), V(1, 0, 0), 92, 82, 25))
    rail_clamp = [G.box(xx - 3, xx + 9, L.Y_RAIL - 14, L.Y_RAIL + 70, L.Z_LM - 16, L.Z_LM - 10) for xx in (x - 120, x + 60)]
    s = G.fuse_all([base, base2, *straps, *rail_clamp])
    return PartDef("C-SAF-05", "Extinguisher quick-release bracket", s, (0.15, 0.15, 0.15), "Steel, Drake-type QR",
                   "Welded to left main rail", "safety")


# ================================================================== fuel / cooling / electrics
TANK = (-147.0, -47.0, 425.0, 585.0, -270.0, -80.0)


def fuel_tank():
    x0, x1, y0, y1, z0, z1 = TANK
    outer = G.fillet(G.box(x0, x1, y0, y1, z0, z1), "|Y", 12)
    inner = G.box(x0 + 2, x1 - 2, y0 + 2, y1 - 2, z0 + 2, z1 - 2)
    s = outer.cut(inner)
    s = s.fuse(G.cyl(V((x0 + x1) / 2, y1 + 12, z0 + 50), V(0, 1, 0), 40, 24))
    s = s.fuse(G.cyl(V(x1 - 30, y0 + 18, z1 + 8), V(0, 0, 1), 12, 16))
    vol = (x1 - x0 - 4) * (y1 - y0 - 4) * (z1 - z0 - 4) / 1e6
    return PartDef("C-FUE-01", f"Fuel tank {vol:.2f}L aluminium", s, ALU, "Al 5052 2 mm welded",
                   f"Internal volume {vol:.2f} L (rule <= 3 L); behind seat in fuel mounting area, left side", "fuel",
                   meta={"litres": vol})


def fuel_tray():
    x0, x1, y0, y1, z0, z1 = TANK
    yb = y0 - 2
    plate = G.box(x0 - 5, x1 + 5, yb - 3, yb, z0 - 5, 5)
    straps = [G.box(xx - 10, xx + 10, yb, y1 + 3, z0 - 3, z0) for xx in (x0 + 25, x1 - 25)]
    straps += [G.box(xx - 10, xx + 10, y1, y1 + 3, z0 - 3, z1 + 3) for xx in (x0 + 25, x1 - 25)]
    straps += [G.box(xx - 10, xx + 10, yb, y1 + 3, z1, z1 + 3) for xx in (x0 + 25, x1 - 25)]
    s = G.fuse_all([plate, *straps])
    return PartDef("C-FUE-02", "Fuel tank tray and straps", s, STEEL, "AISI 4130 2 mm + steel straps",
                   "Bolted to brace cross bar behind firewall (metal fasteners only)", "fuel")


def fuel_line(throttle_body_global):
    x0, x1, y0, y1, z0, z1 = TANK
    tx, ty, tz = throttle_body_global
    pts = [(x1 - 30, y0 + 18, z1 + 14), (x1 - 30, y0 + 18, z1 + 60), (-70, 470, 205),
           (60, 500, 260), (tx - 50, ty + 10, tz - 40), (tx - 20, ty + 4, tz - 20)]
    s = G.bent_tube(pts, 8, 1.5, 25)
    return PartDef("C-FUE-03", "Fuel line 8mm with clamps", s, (0.1, 0.1, 0.1), "Fuel-rated hose + metal P-clips",
                   "Rigidly clamped to frame (rule 6.2.3)", "fuel")


RAD = (85.0, 117.0, 190.0, 390.0, 225.0, 435.0)


def radiator():
    x0, x1, y0, y1, z0, z1 = RAD
    core = G.box(x0, x1, y0 + 12, y1 - 12, z0 + 14, z1 - 14)
    tanks = [G.box(x0 - 2, x1 + 2, y0, y1, z0, z0 + 14), G.box(x0 - 2, x1 + 2, y0, y1, z1 - 14, z1)]
    fan = G.ring(V(x1 + 12, (y0 + y1) / 2, (z0 + z1) / 2), V(1, 0, 0), 170, 150, 22)
    hub = G.cyl(V(x1 + 12, (y0 + y1) / 2, (z0 + z1) / 2), V(1, 0, 0), 60, 22)
    necks = [G.cyl(V((x0 + x1) / 2, y1 - 25, z1 + 7), V(0, 0, 1), 20, 14), G.cyl(V((x0 + x1) / 2, y0 + 25, z0 - 6), V(0, 0, 1), 20, 12)]
    s = G.fuse_all([core, *tanks, fan, hub, *necks])
    return PartDef("C-COL-01", "Radiator with electric fan", s, (0.25, 0.25, 0.28), "Bought out (R15 V2 radiator) + 7in fan",
                   "Behind firewall in engine mounting area (rule 6.2.3)", "cooling")


def coolant_bottle():
    s = G.fillet(G.box(-150, -100, 432, 530, -62, -12), "|Y", 8)
    s = s.fuse(G.cyl(V(-125, 538, -37), V(0, 1, 0), 26, 16))
    return PartDef("C-COL-02", "Coolant reservoir bottle", s, (0.92, 0.92, 0.92), "HDPE bottle (bought out)",
                   "In fuel mounting area as required (rule 6.2.3)", "cooling")


BATT = (650.0, 763.0, 72.0, 177.0, 230.0, 300.0)


def battery():
    x0, x1, y0, y1, z0, z1 = BATT
    s = G.box(x0, x1, y0, y1, z0, z1)
    s = s.fuse(G.box(x0 + 10, x0 + 24, y1, y1 + 8, z0 + 10, z0 + 24)).fuse(G.box(x1 - 24, x1 - 10, y1, y1 + 8, z0 + 10, z0 + 24))
    return PartDef("C-ELE-01", "12V 5Ah sealed battery", s, (0.1, 0.1, 0.12), "Sealed AGM 12 V 5 Ah (YTX5L)",
                   "Aux battery <= 12 V 10 Ah (rule 6.3.1)", "electrics")


def battery_tray():
    x0, x1, y0, y1, z0, z1 = BATT
    plate = G.box(x0 - 10, x1 + 10, y0 - 4, y0, z0 - 10, 400)
    lips = [G.box(x0 - 10, x1 + 10, y0, y0 + 20, z0 - 13, z0 - 10), G.box(x0 - 10, x1 + 10, y0, y0 + 20, z1 + 2, z1 + 5)]
    strap = G.box(x0 + 45, x0 + 65, y1, y1 + 3, z0 - 13, z1 + 5)
    s = G.fuse_all([plate, *lips, strap])
    return PartDef("C-ELE-02", "Battery and ECU tray", s, STEEL, "AISI 4130 2 mm",
                   "Bolted to battery support member", "electrics")


def ecu():
    s = G.box(655, 755, 72, 100, 318, 390)
    return PartDef("C-ELE-03", "ECU and fuse box (blade fuses)", s, (0.15, 0.15, 0.15), "Bought out",
                   "Automotive blade fuses on every LV circuit (rule 6.6)", "electrics")


# ================================================================== exhaust
MUFFLER = dict(x0=-160.0, x1=130.0, y=370.0, z=520.0, d=90.0)


def exhaust_header(port_global):
    px, py, pz = port_global
    m = MUFFLER
    pts = [(px - 6, py, pz), (px + 32, py - 8, pz), (600, 420, 470), (570, 400, 552), (190, 400, 552),
           (m["x1"] + 30, m["y"] + 8, m["z"] + 14), (m["x1"] - 5, m["y"], m["z"])]
    s = G.bent_tube(pts, 32, 1.5, 45)
    return PartDef("C-EXH-01", "Exhaust header 32mm", s, (0.55, 0.4, 0.3), "SS304 32 x 1.5",
                   "Ceramic-wrapped; runs outboard above the engine-bay rail", "exhaust")


def muffler():
    m = MUFFLER
    body = G.cyl(V(m["x0"], m["y"], m["z"]), V(1, 0, 0), m["d"], m["x1"] - m["x0"], centered=False)
    outlet = G.cyl(V(m["x0"] - 26, m["y"], m["z"]), V(1, 0, 0), 30, 30, centered=False)
    hanger = G.box(-90, -66, m["y"] + 30, m["y"] + 50, m["z"] - 50, m["z"] - 30)
    s = G.fuse_all([body, outlet, hanger])
    return PartDef("C-EXH-02", "Silencer with rear outlet", s, (0.45, 0.45, 0.48), "SS304, < 120 dB",
                   f"Outlet behind driver at {m['y']:.0f} mm height (rule 6.2.4 <= 650 mm)", "exhaust",
                   meta={"outlet": (m["x0"] - 26, m["y"], m["z"])})


def heat_shield():
    m = MUFFLER
    r = m["d"] / 2 + 12
    o = G.cyl(V(m["x0"] + 10, m["y"], m["z"]), V(1, 0, 0), 2 * r, m["x1"] - m["x0"] - 20, centered=False)
    i = G.cyl(V(m["x0"], m["y"], m["z"]), V(1, 0, 0), 2 * r - 2, m["x1"] - m["x0"] + 10, centered=False)
    s = o.cut(i).cut(G.box(m["x0"] - 10, m["x1"] + 10, m["y"] - 100, m["y"] + 100, m["z"] - 100, m["z"] - 5))
    s = s.cut(G.box(m["x0"] - 10, m["x1"] + 10, m["y"] - 100, m["y"] - 10, m["z"] - 100, m["z"] + 100))
    return PartDef("C-EXH-03", "Exhaust heat shield", s, (0.75, 0.75, 0.75), "Perforated SS 0.8 mm",
                   "Shields muffler outboard/top (rule 6.2.4)", "exhaust")


# ================================================================== gear change
def gear_lever(shift_shaft_global):
    sx, sy, sz = shift_shaft_global
    pts = [(600, 92, 205), (600, 318, 205), (600, 348, 128)]
    lever = G.bent_tube(pts, 16, None, 30)
    knob = cq.Solid.makeSphere(22, V(600, 355, 120))
    pivot = G.box(585, 615, 60, 100, 172, 218).cut(G.cyl(V(600, 92, 205), V(0, 0, 1), 12, 80))
    rod = G.rod((600, 150, 214), (sx, sy, 214), 8)
    ends = [G.cyl(V(600, 150, 214), V(0, 0, 1), 18, 8), G.cyl(V(sx, sy, 214), V(0, 0, 1), 18, 8)]
    s = G.fuse_all([lever, knob, pivot, rod, *ends])
    return PartDef("C-GEA-01", "Gear lever with linkage", s, (0.15, 0.15, 0.15), "AISI 4130 bar + rod ends",
                   "Rigidly mounted pivot (rule 6.4.1); passes over the low front section of the firewall", "engine")


# ================================================================== engine mounts
def engine_mount():
    """Origin at engine lug bottom.  Plate + rubber isolator + bolt, base at cradle tube top."""
    top = L.ENGINE_ORIGIN[1] - 135.0
    tube_top = L.Y_RAIL + L.TUBE_OD / 2
    h = top - tube_top
    plate = G.box(-3, 3, -h - 3, -15, -26, 26)
    flange = G.box(-22, 22, -20, -15, -26, 26)
    rubber = G.cyl(V(0, -7.5, 0), V(0, 1, 0), 34, 15)
    bolt = G.cyl(V(0, -12, 0), V(0, 1, 0), 10, 34)
    s = G.fuse_all([plate, flange, bolt])
    return PartDef("C-ENG-02", "Engine mount bracket 5mm + isolator", s, STEEL, "AISI 4130 plate 6 mm (>= 5 mm rule 6.2.2)",
                   "Welded to cradle tube; M10 bolt through rubber isolator", "engine", meta={"rubber": rubber})


def engine_mount_rubber():
    rubber = G.cyl(V(0, -7.5, 0), V(0, 1, 0), 34, 15)
    return PartDef("C-ENG-03", "Anti-vibration rubber mount 34x15", rubber, RUBBER, "Natural rubber 60 Sh A",
                   "Vibration damping (rule 6.2.2)", "engine")


# ================================================================== hitch / push rod / stickers / fasteners
def hitch_eye():
    """Origin at tube surface contact; points +X.  Painted yellow (rule 1.4)."""
    pts = [(-4, -25), (28, -25)] + [(28 + 22 * math.cos(a), 22 * math.sin(a)) for a in
                                    [(-math.pi / 2 + math.pi * k / 10) for k in range(11)]] + [(28, 25), (-4, 25)]
    pts = [(x, -y) for x, y in pts[:2]] + pts[2:]
    s = G.plate_xz([(x, z) for x, z in pts], -4, 8)
    s = s.cut(G.cyl(V(30, 0, 0), V(0, 1, 0), 20.5, 20))
    return PartDef("C-HIT-01", "Hitch eye 8mm yellow", s, YELLOW, "AISI 4130 plate 8 mm, yellow paint",
                   "Front and rear hitch points, not on bumper, separate from jack points (rule 1.4)", "hitch")


def push_rod():
    shaft = G.ring(V(0, 0, 0), V(1, 0, 0), 25.4, 22.1, 1400, centered=False)
    handle = G.ring(V(1400, 0, 0), V(0, 0, 1), 25.4, 22.1, 400)
    fork = [G.box(-60, 0, -15, 15, sz - 4, sz + 4) for sz in (-14, 14)]
    pin = G.cyl(V(-35, 0, 0), V(0, 0, 1), 19, 50)
    s = G.fuse_all([shaft, handle, *fork, pin])
    return PartDef("C-HIT-02", "Detachable push-pull rod yellow", s, YELLOW, "Steel tube 25.4 x 1.65, yellow",
                   "Pins into either hitch eye (rule 1.4) - loose item, not in kart assembly", "hitch")


def number_disc(normal="X"):
    if normal == "X":
        s = G.cyl(V(0.5, 0, 0), V(1, 0, 0), 152.4, 1.0)
    else:
        s = G.cyl(V(0, 0, 0.5), V(0, 0, 1), 152.4, 1.0)
    return PartDef(f"C-BOD-0{1 if normal == 'X' else 2}", f"Kart number sticker 6in yellow ({normal})", s, YELLOW,
                   "Vinyl, yellow background, black numerals", "Rule 9 - 6 in circular, yellow/black", "body")


def _hex(af, h, axis):
    r = af / math.sqrt(3)
    pts = [(r * math.cos(math.pi / 6 + k * math.pi / 3), r * math.sin(math.pi / 6 + k * math.pi / 3)) for k in range(6)]
    if axis == "Z":
        return G.plate_xy(pts, -h / 2, h)
    return G.plate_yz([(b, a) for a, b in pts], -h / 2, h)


def bolt_m8(length=30, axis="Z"):
    a = V(0, 0, 1) if axis == "Z" else V(1, 0, 0)
    head = _hex(13, 5.3, axis).translate(a * (-2.65))
    shank = G.cyl(a * (length / 2), a, 8, length)
    s = head.fuse(shank).clean()
    return PartDef(f"C-FST-0{1 if axis == 'Z' else 2}", f"Bolt M8x{length} 8.8 hex ({axis})", s, ZINC,
                   "ISO 4017 M8 grade 8.8 zinc", "Rule 6.10 - metric grade 8.8", "fasteners")


def nut_m8(axis="Z"):
    s = _hex(13, 8, axis).cut(G.cyl(V(0, 0, 0), V(0, 0, 1) if axis == "Z" else V(1, 0, 0), 8, 12))
    return PartDef(f"C-FST-0{3 if axis == 'Z' else 4}", f"Nut M8 nyloc ({axis})", s, ZINC, "ISO 10511 M8 class 8",
                   "Lock nut (rule 6.10)", "fasteners")


# ================================================================== firewall / anti-intrusion
def _hoop_rear_x(y, off=14.0):
    t = math.tan(L.HOOP_LEAN * D2R)
    return L.X_HOOP - (y - L.Y_RAIL) * t - off / math.cos(L.HOOP_LEAN * D2R)


def firewall_side():
    zf = L.FIREWALL_Z
    ytop_e, ytop_f = 600.0, 300.0
    pts = [(_hoop_rear_x(40), 40), (760, 40), (760, ytop_f), (585, ytop_f), (565, ytop_e), (_hoop_rear_x(ytop_e), ytop_e)]
    s = G.plate_xy(pts, zf - L.FIREWALL_T / 2, L.FIREWALL_T)
    return PartDef("C-FWL-01", "Firewall side panel 1.5mm", s, ALU, "Aluminium 5052 1.5 mm",
                   "Seals driver from engine/chain on the right; no holes, nothing mounted on it (rule 3.5)", "firewall")


def firewall_rear():
    t = math.radians(L.HOOP_LEAN)
    h = V(-math.sin(t), math.cos(t), 0)
    n = V(-math.cos(t), -math.sin(t), 0)
    o = V(L.X_HOOP, L.Y_RAIL, 0) + n * 14 + h * ((40 - L.Y_RAIL) / math.cos(t))
    z0, z1 = L.Z_LM - L.TUBE_OD / 2, L.FIREWALL_Z + L.FIREWALL_T / 2
    length = (636 - 40) / math.cos(t)
    pts = [(0, z0), (length, z0), (length, z1), (0, z1)]
    s = G.plate_on_plane(o, h, Z, pts, L.FIREWALL_T)
    return PartDef("C-FWL-02", "Firewall rear panel 1.5mm", s, ALU, "Aluminium 5052 1.5 mm",
                   "Behind seat on rear face of roll hoop; seals driver's back (rule 3.5)", "firewall")


def _rot_about(p, c, ax, ang):
    from ..steering import rot
    import numpy as _np
    q = rot(_np.array([ax.x, ax.y, ax.z]), ang) @ _np.array([p.x - c.x, p.y - c.y, p.z - c.z])
    return V(c.x + q[0], c.y + q[1], c.z + q[2])


def anti_intrusion_plate():
    """Covers the foot-guard opening; outline follows the hoop centre-line (bolted to it)."""
    from .frame import foot_guard_pts
    pts3 = []
    for sg in G.tube_path_segments(foot_guard_pts(), L.BEND_R):
        if sg[0] == "line":
            pts3 += [sg[1], sg[2]]
        else:
            _, t1, t2, c, ax, th, din = sg
            for k in range(9):
                pts3.append(t1.rotate if False else _rot_about(t1, c, ax, th * k / 8))
    pts = [(p.z, max(p.y, 66.0)) for p in pts3]
    s = G.plate_yz(pts, L.X_FB + L.TUBE_OD / 2, 2.0)
    for zz in (L.Z_D - 150.0, L.Z_D + 150.0):
        s = s.cut(G.box(L.X_FB, L.X_FB + 40, 50, 130, zz - 8, zz + 14))
    return PartDef("C-FWL-03", "Anti-intrusion plate 2mm", s, ALU, "Aluminium 6061-T6 2 mm",
                   "Bolted to foot guard (rule 3.2)", "firewall")


# ================================================================== kart stand (rule 8) - loose item
def kart_stand():
    """Mobile kart stand: lifts the kart so the frame rails sit at 950 mm (rule 8: 36-40 in),
    4 braked castors on a widened base, locating forks for the kart's main rails.
    Own frame: origin on the ground at the stand centre; kart main rails (Z -290 / +150) rest on the beams."""
    sq = 40.0
    top = 950.0 - L.TUBE_OD / 2 - sq
    zl, zr = L.Z_LM, L.Z_RM
    zbl, zbr = zl - 160.0, zr + 160.0
    xl, xc = 450.0, 410.0
    yb = 130.0
    parts = []
    for z in (zl, zr):
        parts.append(G.box(-xl, xl, top, top + sq, z - sq / 2, z + sq / 2))                       # top beams
        for x in (-xc, xc):
            parts.append(G.box(x - sq / 2, x + sq / 2, yb + sq, top, z - sq / 2, z + sq / 2))       # legs
            parts.append(G.box(x - 6, x + 6, top + sq, top + sq + 40, z - 22 - 6, z - 22))         # locating fork
            parts.append(G.box(x - 6, x + 6, top + sq, top + sq + 40, z + 22, z + 22 + 6))
    for x in (-xc, xc):
        parts.append(G.box(x - sq / 2, x + sq / 2, yb, yb + sq, zbl - sq / 2, zbr + sq / 2))       # base cross
        parts.append(G.box(x - sq / 2, x + sq / 2, top, top + sq, zl, zr))                         # top cross
    for z in (zbl, zbr):
        parts.append(G.box(-xc - sq / 2, xc + sq / 2, yb, yb + sq, z - sq / 2, z + sq / 2))       # base rails
        for x in (-xc, xc):
            parts.append(G.box(x - 22, x + 22, 75.0, yb, z - 22, z + 22))                          # castor fork + brake
            parts.append(G.cyl(V(x, 50.0, z), V(0, 0, 1), 100, 30))                                # 100 mm wheel
    s = cq.Compound.makeCompound(parts)
    return PartDef("C-STD-01", "Kart stand mobile 950mm with braked castors", s, (0.2, 0.35, 0.6),
                   "40x40x2 steel box section + 4x 100 mm braked castors",
                   "Rule 8 - holds frame rails at 950 mm (37.4 in, within 36-40 in); loose item, not in kart assembly",
                   "stand")
