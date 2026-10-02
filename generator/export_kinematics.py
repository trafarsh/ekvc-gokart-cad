#!/usr/bin/env python3
"""Write output/<style>/kinematics.csv: the joint points / axes and mates the SolidWorks macro uses
to turn each kart assembly into a live steering mechanism.

    column        revolute about the column axis (point + point-on-line to the frame)
    knuckle L/R   revolute about the king-pin axis
    tie rod L/R   ball joint at each rod-end centre (pitman arm / knuckle arm)
    wheel, pitman arm            locked to the column
    front tyre, rim, hub         locked to their knuckle
    limit-distance mate          stops the column at full lock (same lock as the steering report)

Coordinates in the file are PART-LOCAL millimetres (what a 3D sketch inside that SLDPRT needs)."""
from __future__ import annotations

import csv
import math
import os

import numpy as np

from ekvc import cache
from ekvc import export as E
from ekvc import layout as L
from ekvc import steering as ST
from ekvc.parts import steer_parts as SP
from ekvc.styles import STYLES

R_LIMIT_PT = 120.0      # radius of the fixed limit point around the column axis (any value works)


def read_placements(sd):
    P = {}
    with open(os.path.join(sd, "placements.csv")) as f:
        for r in csv.DictReader(f):
            R = np.array([[float(r["xx"]), float(r["yx"]), float(r["zx"])],
                          [float(r["xy"]), float(r["yy"]), float(r["zy"])],
                          [float(r["xz"]), float(r["yz"]), float(r["zz"])]])
            t = np.array([float(r["tx_mm"]), float(r["ty_mm"]), float(r["tz_mm"])])
            P[r["instance"]] = (R, t, r["scope"])
    return P


def style_rows(s):
    s, h, cd = cache.hard(s.code)
    P = read_placements(E.style_dir(s))
    lk = ST.Linkage(s, h)                 # joints at the rod-end ball centres = the CAD tie rods
    rep = cd["rep"]
    a = lk.col_axis / np.linalg.norm(lk.col_axis)
    cb = lk.cb
    k = lk.k_axis

    def loc(inst, g):
        R, t, _ = P[inst]
        return R.T @ (np.asarray(g, float) - t)

    sk = []          # (instance, name, kind, coords...)

    def pt(inst, name, g):
        sk.append((inst, name, "P", *loc(inst, g)))

    def ln(inst, name, g0, g1):
        sk.append((inst, name, "L", *loc(inst, g0), *loc(inst, g1)))

    frame = "Main frame"
    # column axis
    pt(frame, "KIN_COL_P", cb)
    ln(frame, "KIN_COL_AXIS", cb - a * 80, cb + a * 400)
    pt("Steering column", "KIN_COL_P", cb)
    pt("Steering column", "KIN_COL_Q", cb + a * 200)
    # king-pin axes
    for sd, nm in ((-1, "L"), (1, "R")):
        kp = lk.kp[sd]
        pt(frame, f"KIN_KP{nm}_P", kp)
        ln(frame, f"KIN_KP{nm}_AXIS", kp - k * 80, kp + k * 80)
        pt(f"Knuckle {nm}", "KIN_KP_P", kp)
        pt(f"Knuckle {nm}", "KIN_KP_Q", kp + k * 50)
        # rod-end ball centres
        pt("Pitman arm", f"KIN_TR{nm}_IN", lk.p0[sd])
        pt(f"Tie rod {nm}", "KIN_IN", lk.p0[sd])
        pt(f"Tie rod {nm}", "KIN_OUT", lk.arm0[sd])
        pt(f"Knuckle {nm}", "KIN_TR_OUT", lk.arm0[sd])
    # steering-lock limit: fixed point Q opposite the middle of the travel, distance to the pitman tip
    phiL, phiR = math.radians(rep["left"]["pitman_deg"]), math.radians(rep["right"]["pitman_deg"])
    phic, half = 0.5 * (phiL + phiR), 0.5 * (phiL - phiR)
    m0 = 0.5 * (lk.p0[-1] + lk.p0[1])
    o = cb + a * float((m0 - cb) @ a)
    r0 = m0 - o
    uq = ST.rot(a, phic + math.pi) @ (r0 / np.linalg.norm(r0))
    q = o + uq * R_LIMIT_PT

    def dist(phi):
        return float(np.linalg.norm(o + ST.rot(a, phi) @ r0 - q))

    d0, dmax, dlock = dist(0.0), dist(phic), dist(phiL)
    assert abs(dist(phiR) - dlock) < 1e-6 and dlock < d0 <= dmax + 1e-9
    pt(frame, "KIN_LIMIT", q)
    pt("Pitman arm", "KIN_TIP", m0)

    # common parts share one SLDPRT for all styles -> their sketches must not depend on the style
    return dict(code=s.code, sk=sk, P=P, d=(d0, dlock, dmax + 1.0), rep=rep, tie=(lk.tie_len[-1], lk.tie_len[1]))


FLOAT = ["Steering column", "Steering wheel", "Pitman arm", "Knuckle L", "Knuckle R", "Tie rod L", "Tie rod R",
         "Tyre LF", "Rim LF", "Front hub LF", "Tyre RF", "Rim RF", "Front hub RF"]


def write(res):
    sd = E.style_dir(next(s for s in STYLES if s.code == res["code"]))
    p = os.path.join(sd, "kinematics.csv")
    F = "Main frame"
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kind", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j"])
        for inst, name, kind, *xyz in res["sk"]:
            w.writerow(["SKETCH", inst, name, kind] + [f"{v:.4f}" for v in xyz])
        for inst in FLOAT:
            w.writerow(["FLOAT", inst])
        # revolutes: point-point + point-on-axis
        w.writerow(["COINCIDENT", "Steering column", "KIN_COL_P", "P", F, "KIN_COL_P", "P"])
        w.writerow(["COINCIDENT", "Steering column", "KIN_COL_Q", "P", F, "KIN_COL_AXIS", "L"])
        for nm in ("L", "R"):
            w.writerow(["COINCIDENT", f"Knuckle {nm}", "KIN_KP_P", "P", F, f"KIN_KP{nm}_P", "P"])
            w.writerow(["COINCIDENT", f"Knuckle {nm}", "KIN_KP_Q", "P", F, f"KIN_KP{nm}_AXIS", "L"])
        # rigid groups
        w.writerow(["LOCK", "Steering wheel", "Steering column"])
        w.writerow(["LOCK", "Pitman arm", "Steering column"])
        for nm, side in (("L", "LF"), ("R", "RF")):
            for part in ("Front hub", "Rim", "Tyre"):
                w.writerow(["LOCK", f"{part} {side}", f"Knuckle {nm}"])
        # tie rods: ball joints at both rod ends
        for nm in ("L", "R"):
            w.writerow(["COINCIDENT", f"Tie rod {nm}", "KIN_IN", "P", "Pitman arm", f"KIN_TR{nm}_IN", "P"])
            w.writerow(["COINCIDENT", f"Tie rod {nm}", "KIN_OUT", "P", f"Knuckle {nm}", "KIN_TR_OUT", "P"])
        d0, dlo, dhi = res["d"]
        w.writerow(["LIMIT", "Pitman arm", "KIN_TIP", F, "KIN_LIMIT", f"{d0:.4f}", f"{dlo:.4f}", f"{dhi:.4f}"])
    return p


def main():
    allres = [style_rows(s) for s in STYLES]
    # check that sketches on common (shared) parts are identical in every style
    ref = {}
    for r in allres:
        for inst, name, kind, *xyz in r["sk"]:
            if r["P"][inst][2] != "common":
                continue
            key = (inst, name)
            if key in ref:
                assert np.allclose(ref[key], xyz, atol=1e-3), f"{r['code']} {key} differs between styles"
            ref[key] = xyz
    for r in allres:
        p = write(r)
        lL, lR = r["rep"]["left"], r["rep"]["right"]
        print(f"{r['code']}: column {lR['pitman_deg']:+.1f} .. {lL['pitman_deg']:+.1f} deg, "
              f"left lock in/out {lL['inner_deg']:.1f}/{lL['outer_deg']:.1f} ({lL['ackermann_pct']:.0f} %), "
              f"right {lR['inner_deg']:.1f}/{lR['outer_deg']:.1f} ({lR['ackermann_pct']:.0f} %), "
              f"tie rods {r['tie'][0]:.1f}/{r['tie'][1]:.1f} -> {os.path.relpath(p, E.OUT)}")


if __name__ == "__main__":
    main()
