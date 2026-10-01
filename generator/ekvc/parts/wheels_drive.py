"""Common rolling-chassis / drive-train / brake parts (local frames, axis = Z)."""
from __future__ import annotations

import math

import cadquery as cq

from .. import geom as G
from .. import layout as L
from . import PartDef
from .colours import ALU, BLACK, DARK, ENGINE, RED, RUBBER, STEEL, ZINC

V = cq.Vector


# ------------------------------------------------------------------ tyres & rims
def _tyre_profile(r_in, r_out, half_w, corner):
    pts = [(r_in, -half_w + 6), (r_in, half_w - 6), (r_in + 8, half_w)]
    # outer shoulder (+z)
    cx, cz = r_out - corner, half_w - corner
    for k in range(0, 9):
        a = math.radians(90 - 90 * k / 8)
        pts.append((cx + corner * math.cos(a), cz + corner * math.sin(a)))
    cz = -half_w + corner
    for k in range(0, 9):
        a = math.radians(0 - 90 * k / 8)
        pts.append((cx + corner * math.cos(a), cz + corner * math.sin(a)))
    pts.append((r_in + 8, -half_w))
    # de-duplicate
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    return out


def tyre(front=True):
    if front:
        D, Wd, pid, nm = L.F_TYRE_D, L.F_TYRE_W, "C-WHL-01", "Front tyre 4.5x10.0-5 slick"
    else:
        D, Wd, pid, nm = L.R_TYRE_D, L.R_TYRE_W, "C-WHL-02", "Rear tyre 7.1x11.0-5 slick"
    prof = _tyre_profile(L.RIM_D / 2, D / 2, Wd / 2, 0.16 * Wd)
    s = G.revolve_profile_z(prof)
    return PartDef(pid, nm, s, RUBBER, "Rubber (bought out)", f"Rule 2.2 table 1 dry tyre {nm.split()[2]}", "wheels")


def rim(front=True):
    """5 in kart rim, web offset to +Z (outboard).  3 x M8 on PCD 58."""
    Wd = (L.F_TYRE_W if front else L.R_TYRE_W) - 6
    hw = Wd / 2
    r = L.RIM_D / 2
    prof = [(r - 5, -hw), (r + 6, -hw), (r + 6, -hw + 5), (r, -hw + 7), (r, hw - 7), (r + 6, hw - 5), (r + 6, hw),
            (r - 5, hw), (r - 5, hw - 30), (24, hw - 30), (24, hw - 38), (r - 5, hw - 38)]
    s = G.revolve_profile_z(prof)
    for k in range(3):
        a = math.radians(90 + 120 * k)
        s = s.cut(G.cyl((29 * math.cos(a), 29 * math.sin(a), hw - 34), (0, 0, 1), 8.5, 20))
        b = math.radians(30 + 120 * k)
        s = s.cut(G.cyl((44 * math.cos(b), 44 * math.sin(b), hw - 34), (0, 0, 1), 14, 20))
    pid, nm = ("C-WHL-03", "Front rim 5in x 4.5") if front else ("C-WHL-04", "Rear rim 5in x 7.1")
    return PartDef(pid, nm, s, ALU, "Cast aluminium A356-T6", "Bolts to hub with 3x M8 on PCD 58", "wheels")


def front_hub():
    """Rotates on the 20 mm stub axle (2x 6004 bearings).  Flange at +Z."""
    s = G.ring((0, 0, -20), (0, 0, 1), 45, 20, 70)
    s = s.fuse(G.ring((0, 0, 18), (0, 0, 1), 80, 20, 6))
    for k in range(3):
        a = math.radians(90 + 120 * k)
        s = s.fuse(G.cyl((29 * math.cos(a), 29 * math.sin(a), 30), (0, 0, 1), 8, 24))
    s = s.clean()
    return PartDef("C-WHL-05", "Front hub 20mm", s, STEEL, "EN8 steel", "Front hub on stub axle, 3x M8 studs PCD 58", "wheels")


def rear_hub():
    """Clamps on 40 mm live axle (keyed).  Flange at +Z."""
    s = G.ring((0, 0, -26), (0, 0, 1), 64, L.AXLE_OD, 64)
    s = s.fuse(G.ring((0, 0, 10), (0, 0, 1), 92, L.AXLE_OD, 8))
    s = s.cut(G.box(-2, 2, 20, 40, -60, 4))  # clamp slit
    for k in range(3):
        a = math.radians(90 + 120 * k)
        s = s.fuse(G.cyl((29 * math.cos(a), 29 * math.sin(a), 24), (0, 0, 1), 8, 24))
    s = s.clean()
    return PartDef("C-WHL-06", "Rear hub 40mm keyed", s, ALU, "Al 7075-T6", "Keyed clamp hub on 40 mm axle", "wheels")


# ------------------------------------------------------------------ rear axle line
def axle(style_code, rtrack):
    length = rtrack + 2 * 30.0
    s = G.ring((0, 0, 0), (0, 0, 1), L.AXLE_OD, L.AXLE_OD - 8, length)
    return PartDef(f"{style_code}-DRV-01", f"Rear axle 40x4 L{length:.0f}", s, STEEL,
                   "EN24 / 4140 steel tube 40 x 4", f"Live axle, length {length:.0f} mm", "drivetrain")


def flange_bearing():
    s = G.ring((0, 0, 0), (0, 0, 1), 120, 72, 10)
    s = s.fuse(G.ring((0, 0, 0), (0, 0, 1), 72, L.AXLE_OD, 32))
    for k in range(3):
        a = math.radians(90 + 120 * k)
        s = s.cut(G.cyl((49 * math.cos(a), 49 * math.sin(a), 0), (0, 0, 1), 10.5, 14))
    s = s.clean()
    return PartDef("C-DRV-02", "Axle bearing 40mm 3-bolt flange", s, DARK, "Cast iron housing, 6208 insert",
                   "3-bolt flange bearing, M10 bolts on PCD 98", "drivetrain")


def bearing_hanger():
    """6 mm plate welded on axle cross member (X=70) and rear bulkhead (X=-125); built in
    vehicle XY with Z centred at 0 (place by translation to each bearing station)."""
    yb = L.Y_RAIL + L.TUBE_OD / 2 - 2  # sits on tube tops
    cx, cy = L.X_RAX, L.Y_RAX
    outline = [(L.X_RBH - 12, L.Y_RAIL - 4), (L.X_AXM + 12, L.Y_RAIL - 4), (L.X_AXM + 12, yb + 6), (cx + 62, cy - 10),
               (cx + 62, cy + 40), (cx + 30, cy + 66), (cx - 30, cy + 66), (cx - 62, cy + 40), (cx - 62, cy - 10),
               (L.X_RBH - 12, yb + 6)]
    s = G.plate_xy(outline, -3, 6)
    s = s.cut(G.cyl((cx, cy, 0), (0, 0, 1), 73, 20))
    for k in range(3):
        a = math.radians(90 + 120 * k)
        s = s.cut(G.cyl((cx + 49 * math.cos(a), cy + 49 * math.sin(a), 0), (0, 0, 1), 10.5, 20))
    # saddles for the two cross tubes
    for x in (L.X_RBH, L.X_AXM):
        s = s.cut(G.cyl((x, L.Y_RAIL, 0), (0, 0, 1), L.TUBE_OD, 20))
    return PartDef("C-DRV-03", "Axle bearing hanger plate 6mm", s, STEEL, "AISI 4130 plate 6 mm",
                   "Welded to rear bulkhead and axle cross member (x3)", "drivetrain")


def sprocket(n, pitch=L.CHAIN_PITCH, thick=7.0, bore=None, pid="", name=""):
    pd = pitch / math.sin(math.pi / n)
    ro = pd / 2 + 0.3 * pitch
    rr = pd / 2 - 0.39 * pitch
    pts = []
    for k in range(n):
        a0 = 2 * math.pi * k / n
        for frac, r in ((-0.30, rr), (-0.12, ro), (0.12, ro), (0.30, rr)):
            a = a0 + frac * 2 * math.pi / n
            pts.append((r * math.cos(a), r * math.sin(a)))
    s = G.plate_xy(pts, -thick / 2, thick)
    if bore:
        s = s.cut(G.cyl((0, 0, 0), (0, 0, 1), bore, thick + 4))
    return PartDef(pid, name, s, DARK, "C45 steel, induction hardened", f"{n}T #428, PCD {pd:.1f} mm", "drivetrain",
                   meta={"pcd": pd})


def sprocket_carrier():
    s = G.ring((0, 0, 0), (0, 0, 1), 64, L.AXLE_OD, 40)
    s = s.fuse(G.ring((0, 0, -8), (0, 0, 1), 110, L.AXLE_OD, 6)).clean()
    return PartDef("C-DRV-06", "Sprocket carrier 40mm keyed", s, ALU, "Al 7075-T6", "Keyed clamp hub for 34T sprocket", "drivetrain")


def chain():
    """#428 chain envelope around 34T (axle) and 14T (countershaft); local origin = axle centre."""
    p = L.CHAIN_PITCH
    r1 = p / math.sin(math.pi / L.N_REAR_SPROCKET) / 2
    r2 = p / math.sin(math.pi / L.N_FRONT_SPROCKET) / 2
    ex, ey = L.ENGINE_ORIGIN[0] - L.X_RAX, L.ENGINE_ORIGIN[1] - L.Y_RAX
    c = math.hypot(ex, ey)
    th = math.atan2(ey, ex)
    a = math.acos((r1 - r2) / c)

    def loop(off):
        R1, R2 = r1 + off, r2 + off
        pts = []
        for k in range(41):  # big sprocket arc, from +a to 2pi-a around the back
            ang = th + a + (2 * math.pi - 2 * a) * k / 40
            pts.append((R1 * math.cos(ang), R1 * math.sin(ang)))
        for k in range(21):  # small sprocket arc
            ang = th - a + (2 * a) * k / 20
            pts.append((ex + R2 * math.cos(ang), ey + R2 * math.sin(ang)))
        return pts

    outer = cq.Wire.makePolygon([V(x, y, -3.75) for x, y in loop(5.5)], close=True)
    inner = cq.Wire.makePolygon([V(x, y, -3.75) for x, y in loop(-5.5)], close=True)
    s = cq.Solid.extrudeLinear(outer, [inner], V(0, 0, 7.5))
    links = (2 * c / p + (L.N_FRONT_SPROCKET + L.N_REAR_SPROCKET) / 2
             + p * (L.N_REAR_SPROCKET - L.N_FRONT_SPROCKET) ** 2 / (4 * math.pi ** 2 * c))
    return PartDef("C-DRV-07", "Chain 428 66 links", s, (0.35, 0.35, 0.37), "Steel roller chain #428 (bought out)",
                   f"Centre distance {c:.1f} mm, {links:.2f} pitches", "drivetrain", meta={"links": links, "c": c})


def scatter_shield():
    """Sheet metal chain guard (1.5 mm) around the chain run, outboard and inboard plates + rim."""
    p = L.CHAIN_PITCH
    r1 = p / math.sin(math.pi / L.N_REAR_SPROCKET) / 2 + 22
    r2 = p / math.sin(math.pi / L.N_FRONT_SPROCKET) / 2 + 22
    ex, ey = L.ENGINE_ORIGIN[0] - L.X_RAX, L.ENGINE_ORIGIN[1] - L.Y_RAX
    c = math.hypot(ex, ey)
    th = math.atan2(ey, ex)
    a = math.acos((r1 - r2) / c)

    def loop(R1, R2):
        pts = []
        for k in range(31):
            ang = th + a + (2 * math.pi - 2 * a) * k / 30
            pts.append((R1 * math.cos(ang), R1 * math.sin(ang)))
        for k in range(15):
            ang = th - a + (2 * a) * k / 14
            pts.append((ex + R2 * math.cos(ang), ey + R2 * math.sin(ang)))
        return pts

    # cut away the lower-front part so it clears the ground (keep top + rear)
    zs = (-15.0, 7.5)
    parts = []
    for z0 in zs:
        w = cq.Wire.makePolygon([V(x, y, z0) for x, y in loop(r1, r2)], close=True)
        parts.append(cq.Solid.extrudeLinear(w, [], V(0, 0, 1.5)))
    rim_o = cq.Wire.makePolygon([V(x, y, -15) for x, y in loop(r1, r2)], close=True)
    rim_i = cq.Wire.makePolygon([V(x, y, -15) for x, y in loop(r1 - 1.5, r2 - 1.5)], close=True)
    parts.append(cq.Solid.extrudeLinear(rim_o, [rim_i], V(0, 0, 24)))
    s = G.fuse_all(parts)
    # holes for axle and countershaft
    s = s.cut(G.cyl((0, 0, 0), (0, 0, 1), 70, 60)).cut(G.cyl((ex, ey, 0), (0, 0, 1), 58, 60))
    # trim below ground clearance line (Y_global >= 45)
    s = s.cut(G.box(-400, 600, -400, 45 - L.Y_RAX, -50, 50))
    return PartDef("C-DRV-08", "Scatter shield chain guard", s, (0.30, 0.30, 0.30), "Aluminium 5052 1.5 mm",
                   "Rule 6.4.3 - rigidly bolted to chassis tabs, no contact with moving parts", "drivetrain")


# ------------------------------------------------------------------ brake
def brake_disc():
    r = L.DISC_D / 2
    s = G.ring((0, 0, 0), (0, 0, 1), L.DISC_D, 61, 5)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        s = s.cut(G.cyl((35 * math.cos(a), 35 * math.sin(a), 0), (0, 0, 1), 8.5, 10))
    for k in range(18):
        a = math.radians(20 * k)
        s = s.cut(G.cyl(((r - 22) * math.cos(a), (r - 22) * math.sin(a), 0), (0, 0, 1), 7, 10))
    return PartDef("C-BRK-01", "Brake disc 180x5", s, ZINC, "Stainless 420, hardened", "Single rear disc on live axle, locks both rear wheels (rule 5.1)", "brakes")


def disc_carrier():
    s = G.ring((0, 0, 0), (0, 0, 1), 60, L.AXLE_OD, 40)
    s = s.fuse(G.ring((0, 0, 0), (0, 0, 1), 90, L.AXLE_OD, 8))
    for k in range(4):
        a = math.radians(45 + 90 * k)
        s = s.cut(G.cyl((35 * math.cos(a), 35 * math.sin(a), 0), (0, 0, 1), 8.5, 12))
    s = s.clean()
    return PartDef("C-BRK-02", "Disc carrier 40mm keyed", s, ALU, "Al 7075-T6", "Keyed clamp hub, 4x M8 PCD 70", "brakes")


CALIPER_ANGLE = 145.0  # deg, position of caliper on disc (measured from +X, CCW about +Z in XY)


def caliper():
    """Twin-piston hydraulic caliper; local origin at disc centre, disc mid-plane z=0."""
    r = L.DISC_D / 2
    body = G.box(-35, 35, r - 28, r + 18, -22, 22)
    body = G.fillet(body, "|Z", 6)
    slot = G.box(-40, 40, r - 30, r + 2, -3.5, 3.5)
    body = body.cut(slot)
    body = body.fuse(G.cyl((0, r + 6, 26), (0, 0, 1), 34, 10)).fuse(G.cyl((0, r + 6, -26), (0, 0, 1), 34, 10))
    body = body.fuse(G.cyl((24, r + 20, 0), (0, 1, 0), 8, 14))  # bleed nipple
    body = body.fuse(G.cyl((-24, r + 22, 0), (0, 1, 0), 12, 12))  # banjo
    for x in (-26, 26):
        body = body.fuse(G.box(x - 7, x + 7, r - 46, r - 26, -22, -6))
    body = body.rotate((0, 0, 0), (0, 0, 1), CALIPER_ANGLE - 90)
    return PartDef("C-BRK-03", "Brake caliper twin piston", body, RED, "Cast aluminium (bought out)",
                   "Hydraulic caliper, DOT4", "brakes")


def caliper_bracket():
    """6 mm plate welded on rear bulkhead tube; carries the caliper (local frame = disc centre)."""
    r = L.DISC_D / 2
    a = math.radians(CALIPER_ANGLE)
    cx, cy = (r - 36) * math.cos(a), (r - 36) * math.sin(a)
    # base on rear bulkhead tube at (X_RBH, Y_RAIL) relative to disc centre (0, Y_RAX)
    bx, by = L.X_RBH - L.X_RAX, L.Y_RAIL - L.Y_RAX
    tx, ty = -math.sin(a), math.cos(a)
    nx, ny = math.cos(a), math.sin(a)
    cand = [(bx - 18, by + 6), (bx + 18, by + 6), (bx - 18, by + 24), (bx + 18, by + 24)]
    for sgn in (-1, 1):
        ex, ey = cx + sgn * 26 * tx, cy + sgn * 26 * ty
        for rr in (-12, 10):
            cand.append((ex + rr * nx + sgn * 10 * tx, ey + rr * ny + sgn * 10 * ty))
    pts = G.hull2d(cand)
    s = G.plate_xy(pts, -30, 6)
    s = s.cut(G.cyl((bx, by, -27), (0, 0, 1), L.TUBE_OD, 12))
    return PartDef("C-BRK-04", "Caliper mounting bracket 6mm", s, STEEL, "AISI 4130 plate 6 mm",
                   "Welded to rear bulkhead", "brakes")


# ------------------------------------------------------------------ engine (Yamaha R15 V2 envelope)
def engine():
    """Yamaha R15 V2 (149.8 cc, SOHC 4V, liquid cooled, 6-speed) - dimensional ENVELOPE.

    Local origin = countershaft (output sprocket) centre in the chain plane; X forward,
    Y up, Z right.  Verify all mounting points against the actual engine before cutting tabs.
    """
    crank = (150.0, 30.0)
    zc = 165.0
    parts = []
    case = G.box(-70, 280, -120, 100, 40, 290)
    case = G.fillet(case, "|Z", 30)
    parts.append(case)
    parts.append(G.cyl((crank[0], crank[1], 32.5), (0, 0, 1), 170, 15))        # stator cover (left)
    parts.append(G.cyl((70, 10, 305), (0, 0, 1), 190, 30))                    # clutch cover (right)
    parts.append(G.cyl((215, -55, 302), (0, 0, 1), 70, 25))                   # water pump
    parts.append(G.cyl((0, 0, 25), (0, 0, 1), 52, 30))                        # countershaft boss
    parts.append(G.cyl((0, 0, -2), (0, 0, 1), 25, 28))                        # output shaft
    parts.append(G.cyl((205, -75, 20), (0, 0, 1), 16, 44))                    # gear shift shaft (left)
    tilt = math.radians(15)
    c = (math.sin(tilt), math.cos(tilt))
    n = (math.cos(tilt), -math.sin(tilt))

    def block(a0, a1, wx, wz, fil):
        b = G.box(-wx / 2, wx / 2, a0, a1, zc - wz / 2, zc + wz / 2)
        b = G.fillet(b, "|Y", fil)
        b = b.rotate((0, 0, 0), (0, 0, 1), -15)
        return b.translate(V(crank[0], crank[1], 0))

    parts.append(block(60, 215, 108, 112, 12))   # cylinder block
    parts.append(block(215, 282, 126, 132, 16))  # head
    parts.append(block(282, 302, 112, 118, 20))  # cam cover
    hx, hy = crank[0] + c[0] * 248, crank[1] + c[1] * 248
    parts.append(G.cyl((hx - 63 * n[0] - 35, hy - 63 * n[1] + 8, zc), (1, 0.15, 0), 48, 70))     # throttle body (rear)
    ex, ey = crank[0] + c[0] * 245 + 63 * n[0], crank[1] + c[1] * 245 + 63 * n[1]
    parts.append(G.cyl((ex + 6, ey - 4, zc), (n[0], n[1], 0), 46, 14))                         # exhaust flange
    for (x, z) in ((-30, 75), (-30, 255), (250, 75), (250, 255)):
        parts.append(G.cyl((x, -127.5, z), (0, 1, 0), 30, 15))                                  # mount lugs
    parts.append(G.box(150, 230, -40, 10, 38, 41))                                              # engine number pad
    s = G.fuse_all(parts)
    meta = dict(exhaust_port=(ex + 13 * n[0], ey - 6, zc), crank=crank, lugs=[(-30, -135, 75), (-30, -135, 255),
                                                                              (250, -135, 75), (250, -135, 255)])
    return PartDef("C-ENG-01", "Yamaha R15 V2 engine envelope 150cc", s, ENGINE,
                   "Bought out - Yamaha R15 V2 149.8 cc single cyl 4-stroke liquid cooled",
                   "Envelope model (+/-10 mm). Engine number pad on left side faces the cockpit side for inspection.",
                   "engine", meta=meta)
