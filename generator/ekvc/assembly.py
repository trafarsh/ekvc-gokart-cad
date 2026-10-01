"""Builds the complete kart (instances of PartDefs with placements) for one style."""
from __future__ import annotations

import math
from dataclasses import dataclass

import cadquery as cq
import numpy as np

from . import cache
from . import geom as G
from . import layout as L
from .geom import Placement
from .parts import body as BD
from .parts import bumpers as BU
from .parts import common2 as C
from .parts import frame as FR
from .parts import manikin as MK
from .parts import steer_parts as SP
from .parts import wheels_drive as WD
from .parts.colours import STEEL

V = cq.Vector


@dataclass
class Inst:
    part: object          # PartDef
    pl: Placement
    name: str
    scope: str            # "common" | "style"


_COMMON = {}


def common(key, fn, *a):
    if key not in _COMMON:
        _COMMON[key] = fn(*a)
    return _COMMON[key]


def T(x, y, z):
    return Placement((float(x), float(y), float(z)))


def build(code):
    s, h, cd = cache.hard(code)
    sweep = np.array(cd["sweep_pts"])
    W, FT, RT, KH = s.W, s.FT, s.RT, s.KH
    I = []

    def add(part, pl, name, scope):
        I.append(Inst(part, pl, name, scope))

    # ------------------------------------------------------------ frame + floor
    frame = FR.frame_part(s, h)
    P = frame.meta["plan"]
    add(frame, T(0, 0, 0), "Main frame", "style")
    add(SP.floor_pan(s, h, P), T(0, 0, 0), "Floor pan", "style")

    # ------------------------------------------------------------ bumpers (+foam) and connectors
    fpath, fclr = BU.solve_front(s, h, sweep)
    rpath = BU.solve_rear(s, h)
    fb = BU.bumper_part(f"{code}-BMP-01", "Front bumper", fpath, s.colour,
                        f"Single bent tube, {s.front_bumper}; >= 4 in ahead of front bulkhead")
    rb = BU.bumper_part(f"{code}-BMP-02", "Rear bumper", rpath, s.colour,
                        f"Single bent tube, {s.rear_bumper}; >= 2 in behind rear bulkhead")
    add(fb, T(0, 0, 0), "Front bumper", "style")
    add(rb, T(0, 0, 0), "Rear bumper", "style")
    add(BU.foam_part(f"{code}-BMP-05", "Front bumper foam", fpath), T(0, 0, 0), "Front bumper foam", "style")
    add(BU.foam_part(f"{code}-BMP-06", "Rear bumper foam", rpath), T(0, 0, 0), "Rear bumper foam", "style")
    side_paths = {}
    for sd, nm, num in ((-1, "left", 3), (1, "right", 4)):
        sp = BU.side_path(s, h, sd)
        side_paths[sd] = sp
        add(BU.bumper_part(f"{code}-BMP-0{num}", f"Side bumper {nm}", sp, s.colour,
                           f"Single bent tube ({s.side_bumper}); separate from front/rear (no full-round bumper)"),
            T(0, 0, 0), f"Side bumper {nm}", "style")
        add(BU.foam_part(f"{code}-BMP-0{num + 4}", f"Side bumper {nm} foam", sp), T(0, 0, 0), f"Side bumper {nm} foam", "style")

    bolt_z = common("boltZ", C.bolt_m8, 30, "Z")
    bolt_x = common("boltX", C.bolt_m8, 30, "X")
    nut_z = common("nutZ", C.nut_m8, "Z")
    nut_x = common("nutX", C.nut_m8, "X")
    conns = []
    # front: on front bulkhead
    for i, zz in enumerate((L.Z_D - 150.0, L.Z_D + 150.0)):
        zb = BU._path_z_at(fpath, 0) if False else zz
        xb = _x_on_path(fpath, zz)
        conns.append(("Front", f"{code}-CON-0{1 + i}", (L.X_FB, L.Y_RAIL, zz), (xb, BU.Y_FBUMP, zz), "X"))
    for i, zz in enumerate((-300.0, 300.0)):
        xb = _x_on_path(rpath, zz, rear=True)
        conns.append(("Rear", f"{code}-CON-0{3 + i}", (L.X_RBH, L.Y_RAIL, zz), (xb, BU.Y_RBUMP, zz), "X"))
    zo = -(h.z_side - 68.0)
    for j, xc in enumerate(P["side_x"]):
        zl = FR.z_at(P["left_outer"], xc) if P["left_outer"] else zo
        yl, zbl = _side_anchor(side_paths[-1], xc)
        conns.append(("Side L", f"{code}-CON-{5 + j:02d}", (xc, L.Y_RAIL, zl), (xc, yl, zbl), "Z"))
        yr, zbr = _side_anchor(side_paths[1], xc)
        conns.append(("Side R", f"{code}-CON-{7 + j:02d}", (xc, L.Y_RAIL, L.Z_EBAY), (xc, yr, zbr), "Z"))
    conn_report = []
    for label, cid, F, B, ax in conns:
        ft, bt, bolts, nuts, dcc = BU.connector(F, B, ax, cid, f"{label} connector")
        add(ft, T(0, 0, 0), f"{label} connector chassis tab {cid}", "style")
        add(bt, T(0, 0, 0), f"{label} connector bumper tab {cid}", "style")
        for k, (p, a) in enumerate(bolts):
            add(bolt_z if a == "Z" else bolt_x, T(*p), f"{cid} bolt {k + 1}", "common")
        for k, (p, a) in enumerate(nuts):
            add(nut_z if a == "Z" else nut_x, T(*p), f"{cid} nut {k + 1}", "common")
        conn_report.append(dict(id=cid, where=label, frame_pt=F, bumper_pt=B, cc=dcc))

    # ------------------------------------------------------------ wheels
    ft_ = common("ftyre", WD.tyre, True)
    rt_ = common("rtyre", WD.tyre, False)
    fr_ = common("frim", WD.rim, True)
    rr_ = common("rrim", WD.rim, False)
    fh_ = common("fhub", WD.front_hub)
    rh_ = common("rhub", WD.rear_hub)
    for sd, nm in ((-1, "LF"), (1, "RF")):
        p = (W, L.Y_FAX, sd * FT / 2)
        pl = T(*p) if sd > 0 else Placement.flip_y(p)
        add(ft_, pl, f"Tyre {nm}", "common")
        add(fr_, pl, f"Rim {nm}", "common")
        add(fh_, pl, f"Front hub {nm}", "common")
    for sd, nm in ((-1, "LR"), (1, "RR")):
        p = (0.0, L.Y_RAX, sd * RT / 2)
        pl = T(*p) if sd > 0 else Placement.flip_y(p)
        add(rt_, pl, f"Tyre {nm}", "common")
        add(rr_, pl, f"Rim {nm}", "common")
        add(rh_, pl, f"Rear hub {nm}", "common")

    # ------------------------------------------------------------ steering
    for sd in (-1, 1):
        add(SP.knuckle(s, h, sd), T(0, 0, 0), f"Knuckle {'L' if sd < 0 else 'R'}", "style")
        add(SP.tie_rod(s, h, sd), T(0, 0, 0), f"Tie rod {'L' if sd < 0 else 'R'}", "style")
        add(common("kpbolt", C.kingpin_bolt), T(W, L.Y_FAX, sd * KH), f"King pin bolt {'L' if sd < 0 else 'R'}", "common")
    cb = h.cb
    for key, fn, nm in (("col", C.steering_column, "Steering column"), ("wheel", C.steering_wheel, "Steering wheel"),
                        ("pit", C.pitman_arm, "Pitman arm"), ("colup", C.column_upper_bracket, "Column upper bracket"),
                        ("collo", C.column_lower_bracket, "Column lower bracket")):
        add(common(key, fn), T(*cb), nm, "common")

    # ------------------------------------------------------------ rear axle line / brake / drive
    add(WD.axle(code, RT), T(0, L.Y_RAX, 0), "Rear axle", "style")
    brg = common("brg", WD.flange_bearing)
    hang = common("hang", WD.bearing_hanger)
    for zb in L.BEARING_Z:
        add(hang, T(0, 0, zb), f"Bearing hanger Z{zb:.0f}", "common")
        add(brg, T(0, L.Y_RAX, zb + 8.0), f"Axle bearing Z{zb:.0f}", "common")
    add(common("s34", WD.sprocket, L.N_REAR_SPROCKET, L.CHAIN_PITCH, 7.0, 66.0, "C-DRV-05", "Axle sprocket 34T 428"),
        T(0, L.Y_RAX, L.SPROCKET_Z), "Axle sprocket", "common")
    add(common("scar", WD.sprocket_carrier), T(0, L.Y_RAX, L.SPROCKET_Z + 14.5), "Sprocket carrier", "common")
    eo = L.ENGINE_ORIGIN
    add(common("s14", WD.sprocket, L.N_FRONT_SPROCKET, L.CHAIN_PITCH, 7.0, 25.0, "C-DRV-04", "Engine sprocket 14T 428"),
        T(*eo), "Engine sprocket", "common")
    add(common("chain", WD.chain), T(0, L.Y_RAX, L.SPROCKET_Z), "Chain", "common")
    add(common("shield", WD.scatter_shield), T(0, L.Y_RAX, L.SPROCKET_Z), "Scatter shield", "common")
    add(common("disc", WD.brake_disc), T(0, L.Y_RAX, L.DISC_Z), "Brake disc", "common")
    add(common("dcar", WD.disc_carrier), T(0, L.Y_RAX, L.DISC_Z - 6.5), "Disc carrier", "common")
    add(common("cal", WD.caliper), T(0, L.Y_RAX, L.DISC_Z), "Brake caliper", "common")
    add(common("calb", WD.caliper_bracket), T(0, L.Y_RAX, L.DISC_Z), "Caliper bracket", "common")
    a = math.radians(WD.CALIPER_ANGLE)
    cal_g = (90 * math.cos(a), L.Y_RAX + 90 * math.sin(a), L.DISC_Z)
    for key, fn, nm, args in (("mc", C.master_cylinder, "Master cylinder", ()), ("mcb", C.mc_bracket, "MC bracket", ()),
                              ("ots", C.over_travel_switch, "Brake over-travel switch", ())):
        add(common(key, fn, *args), T(0, 0, 0), nm, "common")
    add(C.brake_line(cal_g, P["L"], code), T(0, 0, 0), "Brake line", "style")
    for kind in ("Clutch", "Brake", "Throttle"):
        add(common("ped" + kind, C.pedal, kind), T(0, 0, 0), f"{kind} pedal", "common")
    add(common("pedbr", C.pedal_shaft_brackets), T(0, 0, 0), "Pedal shaft & hangers", "common")

    # ------------------------------------------------------------ engine & ancillaries
    eng = common("engine", WD.engine)
    add(eng, T(*eo), "Engine Yamaha R15 V2", "common")
    m = eng.meta
    port = (m["exhaust_port"][0] + eo[0], m["exhaust_port"][1] + eo[1], m["exhaust_port"][2] + eo[2])
    crank = m["crank"]
    for lx, ly, lz in m["lugs"]:
        p = (lx + eo[0], ly + eo[1], lz + eo[2])
        add(common("emount", C.engine_mount), T(*p), f"Engine mount {lx:.0f}/{lz:.0f}", "common")
        add(common("erubber", C.engine_mount_rubber), T(*p), f"Engine isolator {lx:.0f}/{lz:.0f}", "common")
    tb = (118.3 + eo[0], 293.8 + eo[1], 165 + eo[2])
    shift = (205 + eo[0], -75 + eo[1], 20 + eo[2])
    for key, fn, nm, args in (("hdr", C.exhaust_header, "Exhaust header", (port,)), ("muf", C.muffler, "Silencer", ()),
                              ("hs", C.heat_shield, "Heat shield", ()), ("gear", C.gear_lever, "Gear lever", (shift,)),
                              ("rad", C.radiator, "Radiator", ()), ("cool", C.coolant_bottle, "Coolant bottle", ()),
                              ("tank", C.fuel_tank, "Fuel tank", ()), ("tray", C.fuel_tray, "Fuel tank tray", ()),
                              ("fline", C.fuel_line, "Fuel line", (tb,)), ("batt", C.battery, "Battery", ()),
                              ("btray", C.battery_tray, "Battery tray", ()), ("ecu", C.ecu, "ECU & fuse box", ()),
                              ("fws", C.firewall_side, "Firewall side", ()), ("fwr", C.firewall_rear, "Firewall rear", ()),
                              ("aip", C.anti_intrusion_plate, "Anti-intrusion plate", ()),
                              ("seat", C.seat, "Seat", ()), ("ext", C.extinguisher, "Fire extinguisher", ()),
                              ("extb", C.extinguisher_bracket, "Extinguisher bracket", ())):
        add(common(key, fn, *args), T(0, 0, 0), nm, "common")
    sbf = common("sbf", C.seat_bracket_front)
    sbr = common("sbr", C.seat_bracket_rear)
    for sd in (-1, 1):
        add(sbf, T(L.X_SEAT_XM, L.Y_RAIL + L.TUBE_OD / 2, L.Z_D + sd * 120), f"Seat front mount {sd}", "common")
        add(sbr, T(FR.hoop_x(L.HOOP_CROSS_Y) + L.TUBE_OD / 2, L.HOOP_CROSS_Y, L.Z_D + sd * 120), f"Seat rear mount {sd}", "common")

    # ------------------------------------------------------------ safety
    ksb = common("ksbox", C.kill_switch_box)
    ksh = common("ksbtn", C.kill_switch_button)
    kst = common("kstab", C.kill_switch_tab)
    ks_pos = [("driver (dash)", (h.x_dash, 300.0 + L.TUBE_OD / 2 + 6.0, L.Z_D - 175.0)),
              ("roll hoop left", (FR.hoop_x(650.0), 650.0, L.Z_LM - L.TUBE_OD / 2 - 40.0)),
              ("roll hoop right", (FR.hoop_x(650.0), 650.0, L.Z_RM + L.TUBE_OD / 2 + 40.0))]
    for nm, p in ks_pos:
        add(kst, T(*p), f"Kill switch tab {nm}", "common")
        add(ksb, T(*p), f"Kill switch {nm}", "common")
        add(ksh, T(*p), f"Kill switch head {nm}", "common")
    bl = (FR.hoop_x(L.HOOP_TOP_Y) - L.TUBE_OD / 2 - 12.0, L.HOOP_TOP_Y, 0.5 * (L.Z_LM + L.Z_RM))
    add(common("blight", C.brake_light), T(*bl), "Brake light", "common")
    add(common("blens", C.brake_light_lens), T(*bl), "Brake light lens", "common")
    he = common("hitch", C.hitch_eye)
    add(he, T(L.X_FB + L.TUBE_OD / 2, L.Y_RAIL, L.Z_D), "Front hitch point", "common")
    add(he, Placement.flip_y((L.X_RBH - L.TUBE_OD / 2, L.Y_RAIL, L.Z_D)), "Rear hitch point", "common")

    # ------------------------------------------------------------ bodywork + stickers
    nose = BD.nose(s, h, (V(*h.cb), V(*h.wheel_c)))
    add(nose, T(0, 0, 0), "Nose", "style")
    pods = {}
    for sd in (-1, 1):
        bow = max(abs(p[2]) for p in side_paths[sd]) - h.z_side
        pods[sd] = BD.pod(s, h, sd, min_out=bow + BU.FOAM_R + 8.0)
        add(pods[sd], T(0, 0, 0), f"Side pod {'L' if sd < 0 else 'R'}", "style")
    rp = BD.rear_panel(s, h)
    add(rp, T(0, 0, 0), "Rear panel", "style")
    ndx = common("ndx", C.number_disc, "X")
    ndz = common("ndz", C.number_disc, "Z")
    nx = nose.meta["front_x"]
    add(ndx, T(nx + 0.2, 225.0, 0.0), "Number sticker front", "common")
    for sd in (-1, 1):
        pm = pods[sd].meta
        p = (pm["mid_x"], pm["sticker_y"], pm["outer_z"] + sd * 0.3)
        add(ndz, T(*p) if sd > 0 else Placement.flip_y(p), f"Number sticker {'left' if sd < 0 else 'right'}", "common")
    add(ndx, Placement.flip_y((rp.meta["x"] - 0.2, 232.0, 0.0)), "Number sticker rear", "common")

    # ------------------------------------------------------------ reference driver
    add(MK.manikin(s, h), T(0, 0, 0), "REF driver", "style")

    info = dict(style=s, hard=h, steer=cd, front_clear=fclr, connectors=conn_report, plan=P,
                frame_meta=frame.meta, fpath=fpath, rpath=rpath, side_paths=side_paths)
    return I, info


def _x_on_path(path, z, rear=False):
    """X of a (front/rear) bumper centre-line at lateral position z (main horizontal run)."""
    pts = [(p[2], p[0]) for p in path]
    best = None
    for (z0, x0), (z1, x1) in zip(pts[:-1], pts[1:]):
        if min(z0, z1) - 1e-6 <= z <= max(z0, z1) + 1e-6 and abs(z1 - z0) > 1e-6:
            x = x0 + (x1 - x0) * (z - z0) / (z1 - z0)
            if best is None or (x < best if not rear else x > best):
                best = x
    return best if best is not None else pts[len(pts) // 2][1]


def _side_anchor(path, x):
    """(y, z) of the side bumper's longest run at station x."""
    segs = list(zip(path[:-1], path[1:]))
    best = max(segs, key=lambda ab: math.dist(ab[0], ab[1]))
    (x0, y0, z0), (x1, y1, z1) = best
    # find segment of the same run covering x (allow multi-segment runs at same height)
    run = sorted([(p[0], p[2]) for p in path if abs(p[1] - y0) < 1.0])
    return y0, FR.z_at(run, x)
