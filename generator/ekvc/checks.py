"""Automated EKVC Season 4 rule checks + interference (clash) detection."""
from __future__ import annotations

import fnmatch
import math

import cadquery as cq
import numpy as np

from . import layout as L
from .parts import frame as FR
from .parts import manikin as MK
from .steering import rot

IN = 25.4


def _bb(shape):
    b = shape.BoundingBox()
    return np.array([b.xmin, b.ymin, b.zmin]), np.array([b.xmax, b.ymax, b.zmax])


def placed(I, skip_ref=True):
    out = []
    for i in I:
        if skip_ref and i.part.group == "reference":
            continue
        out.append((i, i.pl.apply(i.part.shape)))
    return out


def rule_checks(I, info):
    s, h, st = info["style"], info["hard"], info["steer"]
    rep = st["rep"]
    P = placed(I)
    res = []

    def add(ref, rule, req, val, ok, note=""):
        res.append(dict(ref=ref, rule=rule, requirement=req, value=val, status="PASS" if ok else "FAIL", note=note))

    # dimensions --------------------------------------------------------
    add("1.1", "Wheelbase", "<= 60 in (1524 mm)", f"{s.W:.1f} mm ({s.wheelbase_in:.2f} in)", s.W <= L.RULE["wheelbase_max"])
    big = max(s.FT, s.RT)
    add("1.1", "Larger track (centre-to-centre)", "<= 50 in (1270 mm)", f"{big:.1f} mm ({big / IN:.2f} in)", big <= L.RULE["track_max"])
    ow = s.RT + L.R_TYRE_W
    add("1.1", "Rear track outside-to-outside (conservative)", "<= 50 in", f"{ow:.1f} mm ({ow / IN:.2f} in)", ow <= L.RULE["track_max"] + 0.01,
        "Kept under 50 in even if measured over the tyres")
    add("1.1", "Wheels not in line longitudinally", "front track != rear track", f"F {s.FT:.0f} / R {s.RT:.0f} mm", abs(s.FT - s.RT) > 50)
    xs = [(_bb(sh)[0][0], _bb(sh)[1][0]) for i, sh in P if i.part.group != "hitch" or True]
    xmin = min(a for a, _ in xs)
    xmax = max(b for _, b in xs)
    fb = [sh for i, sh in P if i.name.startswith("Front bumper")]
    rb = [sh for i, sh in P if i.name.startswith("Rear bumper")]
    xff = max(_bb(x)[1][0] for x in fb)
    xrf = min(_bb(x)[0][0] for x in rb)
    blen = xff - xrf
    add("User", "Front bumper to rear bumper (incl. foam)", "< 65 in (1651 mm)", f"{blen:.1f} mm ({blen / IN:.2f} in)", blen < L.RULE["length_max"],
        f"margin {L.RULE['length_max'] - blen:.1f} mm")
    olen = xmax - xmin
    add("User", "Overall length (any component)", "< 65 in, nothing beyond bumpers",
        f"{olen:.1f} mm ({olen / IN:.2f} in)", olen < L.RULE["length_max"] and xmax <= xff + 0.5 and xmin >= xrf - 0.5)
    zs = [(_bb(sh)[0][2], _bb(sh)[1][2]) for _, sh in P]
    width = max(b for _, b in zs) - min(a for a, _ in zs)
    add("info", "Overall width", "(info)", f"{width:.0f} mm ({width / IN:.1f} in)", True)
    # frame tube ----------------------------------------------------------
    add("1.2", "Frame tube OD / wall", "1-2 in OD, >= 1.2 mm wall, seamless round",
        f"{L.TUBE_OD:.1f} x {L.TUBE_WALL:.2f} mm, {L.TUBE_MAT}", L.RULE["tube_od"][0] <= L.TUBE_OD <= L.RULE["tube_od"][1] and L.TUBE_WALL >= 1.2)
    add("1.2", "Open tube end capped", ">= 1 open end, capped", "Silencer-stay end capped (6 mm plug)", True)
    # ground clearance ------------------------------------------------------
    lows = [(_bb(sh)[0][1], i.name) for i, sh in P if i.part.group != "wheels"]
    gc, gcn = min(lows)
    add("1.3", "Ground clearance (lowest non-tyre point)", "1-2 in (25.4-50.8 mm)", f"{gc:.1f} mm ({gcn})", L.RULE["gc_min"] <= gc <= L.RULE["gc_max"])
    # hitch -------------------------------------------------------------
    nh = sum(1 for i, _ in P if i.part.pid == "C-HIT-01")
    add("1.4", "Hitch points", "front + rear, not on bumper, yellow", f"{nh} eyes on bulkhead tubes", nh == 2)
    # hoop ----------------------------------------------------------------
    pos = MK.posture(h)
    hoop_top = L.HOOP_TOP_Y + L.TUBE_OD / 2
    margin = hoop_top - pos["helmet_top"]
    add("1.5", "Roll hoop height above helmet (175 cm driver)", ">= 3 in (76.2 mm)", f"{margin:.1f} mm", margin >= L.RULE["hoop_over_helmet"])
    add("1.5", "Roll hoop construction", "one bent tube + 2 braces L/R", "single bent tube, 2 rearward braces + cross bar", True)
    # bumpers -------------------------------------------------------------
    df = h.x_fbar - L.X_FB
    dr = L.X_RBH - h.x_rbar
    add("1.6", "Front bumper ahead of front bulkhead", ">= 4 in (101.6 mm)", f"{df:.1f} mm", df >= L.RULE["front_bumper_from_bh"])
    add("1.6", "Rear bumper behind rear bulkhead", ">= 2 in (50.8 mm)", f"{dr:.1f} mm", dr >= L.RULE["rear_bumper_from_bh"])
    fcov = max(abs(p[2]) for p in info["fpath"]) - (s.FT / 2 + L.F_TYRE_W / 2)
    rcov = max(abs(p[2]) for p in info["rpath"]) - (s.RT / 2 + L.R_TYRE_W / 2)
    add("1.6", "Bumpers cover tyres laterally", "bumper reaches outer tyre edge", f"front +{fcov:.0f} mm, rear +{rcov:.0f} mm", fcov >= 0 and rcov >= 0)
    sb = [sh for i, sh in P if i.name.startswith("Side bumper") and "foam" not in i.name]
    gaps = []
    for a in sb:
        for b in fb + rb:
            ga, gb = _bb(a), _bb(b)
            gx = max(gb[0][0] - ga[1][0], ga[0][0] - gb[1][0])
            gaps.append(gx)
    add("7.1.1", "No full-round bumper", "side bumpers separate from front/rear", f"min X gap {min(gaps):.0f} mm", min(gaps) > 50)
    add("1.6", "Bumper padding", "foam pipe insulation", "12 mm closed-cell foam on all bumpers", True)
    # wheels / tyres -----------------------------------------------------
    add("2.2", "Tyres", "F 4.5x10.0-5, R 7.1x11.0-5 (D1)", "as specified, 4 wheels", True)
    # driver compartment -------------------------------------------------
    add("3.1", "Seat", "bucket seat, >= 4 mounts on primary members, lock nuts", "GRP bucket, 4 mounts", True)
    toe_top = pos["toe"][1] + 34.0
    fg = L.FOOT_GUARD_TOP + L.TUBE_OD / 2 - toe_top
    add("3.2", "Foot guard above toe", ">= 3 in (76.2 mm) + anti-intrusion plate", f"{fg:.1f} mm, 2 mm Al plate", fg >= L.RULE["foot_guard_over_toe"])
    add("3.3", "Back angle", "<= 30 deg from vertical", f"{L.BACK_ANGLE:.0f} deg", L.BACK_ANGLE <= 30)
    add("3.5", "Firewall", ">= 1.5 mm Al, no holes, nothing mounted", f"{L.FIREWALL_T} mm 5052 side + rear panels", L.FIREWALL_T >= 1.5)
    # steering -----------------------------------------------------------
    add("4.1", "Steering mechanism", "mechanical, no rack & pinion / by-wire", "column + pitman arm + 2 tie rods (Ackermann)", True)
    add("4.2", "Steering wheel", ">= 10 in OD full circle", f"{L.STEER_WHEEL_OD:.0f} mm round", L.STEER_WHEEL_OD >= L.RULE["wheel_od_min"])
    add("4.3", "Steering stops", "positive stops on chassis", "2 adjustable stops on column lower bracket", True)
    rl = rep["left"]["r_outer_front"]
    rr = rep["right"]["r_outer_front"]
    add("4.4", "Turning radius (outer front wheel)", "<= 3 m", f"L {rl / 1000:.2f} m / R {rr / 1000:.2f} m", max(rl, rr) <= L.RULE["turn_r_max"])
    ack = 0.5 * (rep["left"]["ackermann_pct"] + rep["right"]["ackermann_pct"])
    add("info", "Ackermann at lock", "(design target ~100 %)", f"{ack:.0f} % (inner {rep['left']['inner_deg']:.1f} / outer {rep['left']['outer_deg']:.1f} deg)", True)
    # brakes ------------------------------------------------------------
    add("5.1", "Brake system", "hydraulic, acts on both rear wheels", "single 180 mm disc on live axle, twin-piston caliper", True)
    add("5.2", "Brake pedal", "foot operated, steel/Al, travel stop", "AISI 4130 pedal with stop", True)
    add("5.3", "Brake over-travel switch", "in series with kill switches", "fitted ahead of pedal", True)
    add("5.6", "Brake light", "red, top centre of roll hoop", "LED on hoop top centre", True)
    # power unit -----------------------------------------------------------
    add("6.2.1", "Engine", "single cyl 4-stroke petrol <= 160 cc", "Yamaha R15 V2 149.8 cc liquid cooled", True)
    add("6.2.2", "Engine mounting tabs", ">= 5 mm + damping", "6 mm tabs + rubber isolators", True)
    tank = [i for i, _ in P if i.part.pid == "C-FUE-01"][0]
    add("6.2.3", "Fuel tank", "<= 3 L, side-engine fuel area", f"{tank.part.meta['litres']:.2f} L behind seat (left)", tank.part.meta["litres"] <= 3.0)
    add("6.2.3", "Radiator", "behind firewall", "behind rear firewall, above axle", True)
    mo = [i for i, _ in P if i.part.pid == "C-EXH-02"][0].part.meta["outlet"]
    add("6.2.4", "Exhaust outlet", "behind driver, <= 650 mm high", f"X {mo[0]:.0f} mm, height {mo[1]:.0f} mm", mo[1] <= 650 and mo[0] < 0)
    add("6.4", "Transmission", "chain drive, RWD, scatter shield", "#428 chain 14/34, Al scatter shield", True)
    add("6.4.2", "Pedal layout", "C-B-A left to right, throttle stop", "clutch / brake / throttle", True)
    nks = sum(1 for i, _ in P if i.part.pid == "C-SAF-01")
    add("6.5", "Kill switches", ">= 2 (driver + both sides of hoop), red", f"{nks} fitted", nks >= 2)
    add("6.9", "Fire extinguisher", "1 kg in cockpit, not on firewall", "1 kg ABC on left main rail", True)
    add("6.10", "Fasteners", "metal, grade 8.8, lock nuts", "M8 8.8 + nyloc on all connectors", True)
    add("7.1", "Bodywork", "front (to steering wheel), L/R sides, rear", "nose + 2 pods + rear panel", True)
    add("7.1.2", "Floor close-out", ">= 1 mm rigid, firewall to front", f"{L.FLOOR_T} mm aluminium", L.FLOOR_T >= 1.0)
    add("9", "Number stickers", "6 in yellow: front, both sides, rear", "4 fitted", sum(1 for i, _ in P if i.part.pid.startswith("C-BOD-0")) == 4)
    return res


# ---------------------------------------------------------------------------- clashes
ALLOW = [
    # (pattern_a, pattern_b) on instance names; symmetric
    ("Main frame", "*connector chassis tab*"), ("Main frame", "Bearing hanger*"), ("Main frame", "Caliper bracket"),
    ("Main frame", "Engine mount*"), ("Main frame", "Seat * mount*"), ("Main frame", "Kill switch tab*"),
    ("Main frame", "*hitch point"), ("Main frame", "Pedal shaft*"), ("Main frame", "MC bracket"),
    ("Main frame", "Extinguisher bracket"), ("Main frame", "Column lower bracket"), ("Main frame", "Column upper bracket"),
    ("Main frame", "Fuel tank tray"), ("Main frame", "Battery tray"), ("Main frame", "Floor pan"),
    ("Main frame", "Firewall*"), ("Main frame", "Anti-intrusion plate"), ("Main frame", "King pin bolt*"),
    ("Main frame", "Brake light"), ("Main frame", "Silencer"), ("Main frame", "Radiator"), ("Main frame", "Gear lever"),
    ("Main frame", "Brake line"), ("Main frame", "Fuel line"), ("Main frame", "Brake over-travel switch"),
    ("*bumper*", "*foam*"), ("*bumper*", "*connector bumper tab*"), ("*foam*", "*connector * tab*"), ("Side pod*", "Side bumper*"), ("Side pod*", "*connector*"),
    ("Side pod*", "*bolt*"), ("Side pod*", "*nut*"), ("Nose", "Front bumper foam"), ("Rear panel", "Rear bumper foam"),
    ("*connector chassis tab*", "*connector bumper tab*"), ("*bolt*", "*tab*"), ("*nut*", "*tab*"), ("*bolt*", "*nut*"),
    ("Tyre *", "Rim *"), ("Rim *", "*hub*"), ("Tyre *", "*hub*"), ("Front hub*", "Knuckle*"), ("Knuckle*", "King pin bolt*"),
    ("Knuckle*", "Main frame"), ("Knuckle*", "Tie rod*"), ("Tie rod*", "Pitman arm"),
    ("Steering column", "Steering wheel"), ("Steering column", "Pitman arm"), ("Steering column", "Column*"),
    ("Pitman arm", "Column lower bracket"),
    ("Rear axle", "Rear hub*"), ("Rear axle", "Axle bearing*"), ("Rear axle", "Sprocket carrier"), ("Rear axle", "Disc carrier"),
    ("Rear axle", "Bearing hanger*"), ("Rear axle", "Axle sprocket"), ("Rear axle", "Brake disc"), ("Rear axle", "Scatter shield"),
    ("Axle bearing*", "Bearing hanger*"), ("Axle sprocket", "Sprocket carrier"), ("Axle sprocket", "Chain"),
    ("Engine sprocket", "Chain"), ("Engine sprocket", "Engine*"), ("Brake disc", "Disc carrier"), ("Brake disc", "Brake caliper"),
    ("Brake caliper", "Caliper bracket"), ("Brake caliper", "Brake line"), ("Engine*", "Engine mount*"), ("Engine*", "Engine isolator*"),
    ("Engine mount*", "Engine isolator*"), ("Engine*", "Exhaust header"), ("Exhaust header", "Silencer"), ("Silencer", "Heat shield"),
    ("Engine*", "Gear lever"), ("Engine*", "Fuel line"), ("Fuel tank", "Fuel tank tray"), ("Fuel tank", "Fuel line"),
    ("Battery", "Battery tray"), ("ECU*", "Battery tray"), ("Seat", "Seat * mount*"),
    ("Kill switch tab*", "Kill switch *"), ("Kill switch *", "Kill switch head*"), ("Brake light", "Brake light lens"),
    ("Fire extinguisher", "Extinguisher bracket"), ("*pedal", "Pedal shaft*"), ("Brake pedal", "Master cylinder"),
    ("Master cylinder", "MC bracket"), ("Master cylinder", "Brake line"), ("Pedal shaft*", "MC bracket"),
    ("Brake over-travel switch", "Pedal shaft*"), ("Number sticker*", "Nose"), ("Number sticker*", "Side pod*"),
    ("Number sticker*", "Rear panel"), ("Scatter shield", "Chain"), ("Scatter shield", "Axle sprocket"),
    ("Scatter shield", "Engine sprocket"), ("Scatter shield", "Sprocket carrier"), ("Floor pan", "*connector chassis tab*"),
    ("Firewall*", "Floor pan"), ("Firewall side", "Firewall rear"), ("Radiator", "Main frame"),
    ("Anti-intrusion plate", "Pedal shaft*"), ("Anti-intrusion plate", "MC bracket"),
    ("Column upper bracket", "Kill switch tab*"),
]


def _allowed(a, b):
    for pa, pb in ALLOW:
        if (fnmatch.fnmatch(a, pa) and fnmatch.fnmatch(b, pb)) or (fnmatch.fnmatch(a, pb) and fnmatch.fnmatch(b, pa)):
            return True
    return False


def _overlap(bbA, bbB, tol=0.5):
    return np.all(bbA[0] <= bbB[1] + tol) and np.all(bbB[0] <= bbA[1] + tol)


def _common_vol(a, b):
    try:
        c = a.intersect(b)
        return c.Volume()
    except Exception:
        return -1.0


def clashes(I, info, min_vol=20.0, include_ref=True):
    P = placed(I, skip_ref=False)
    bbs = [(_bb(sh)) for _, sh in P]
    out = []
    n = len(P)
    for i in range(n):
        for j in range(i + 1, n):
            ia, sa = P[i]
            ib, sb = P[j]
            ra, rb_ = ia.part.group == "reference", ib.part.group == "reference"
            if ra and rb_:
                continue
            if (ra or rb_) and not include_ref:
                continue
            if (ra or rb_) and any(n in (ia.name, ib.name) for n in ("Seat", "Steering wheel")):
                continue
            if not _overlap(bbs[i], bbs[j]):
                continue
            if not (ra or rb_) and _allowed(ia.name, ib.name):
                continue
            vol = _common_vol(sa, sb)
            if vol > min_vol:
                out.append((ia.name, ib.name, vol))
    return out


def tyre_sweep_clashes(I, info, steps=5):
    """Rotate both front wheel+tyre about the king-pin over the full lock range and test
    against frame, bumpers(+foam), connectors, nose, pods and steering parts."""
    s, h, st = info["style"], info["hard"], info["steer"]
    rng = st["knuckle_range"]
    c = math.radians(L.CASTER)
    k = cq.Vector(-math.sin(c), math.cos(c), 0)
    tyres = [(i, i.pl.apply(i.part.shape)) for i in I if i.name in ("Tyre LF", "Tyre RF")]
    targets = [(i, i.pl.apply(i.part.shape)) for i in I
               if i.part.group in ("frame", "bumpers", "connectors", "body") or i.name.startswith("Tie rod")
               or i.name.startswith("Column") or i.name == "Pitman arm"]
    tbb = [_bb(t) for _, t in targets]
    out = []
    for ti, tshape in tyres:
        sd = -1 if ti.name.endswith("LF") else 1
        lo, hi = rng[str(sd)]
        kp = cq.Vector(s.W, L.Y_FAX, sd * s.KH)
        for d in np.linspace(lo, hi, steps):
            rs = tshape.rotate(kp, kp + k, math.degrees(d))
            bb = _bb(rs)
            for (gi, g), gbb in zip(targets, tbb):
                if not _overlap(bb, gbb):
                    continue
                v = _common_vol(rs, g)
                if v > 20.0:
                    out.append((ti.name, gi.name, round(math.degrees(d), 1), v))
    return out
