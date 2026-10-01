"""Ackermann steering kinematics: king-pin with caster, trailing knuckle arms, single
pitman arm on an inclined column, two tie rods.  Pure numpy - no CAD."""
from __future__ import annotations

import math

import numpy as np

from . import layout as L


def rot(axis, ang):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    x, y, z = a
    c, s = math.cos(ang), math.sin(ang)
    C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


class Linkage:
    def __init__(self, s: L.Style, h: L.Hard):
        self.s, self.h = s, h
        W, KH = s.W, s.KH
        c = math.radians(L.CASTER)
        self.k_axis = np.array([-math.sin(c), math.cos(c), 0.0])
        self.kp = {sd: np.array([W, L.Y_FAX, sd * KH]) for sd in (-1, 1)}
        b = h.beta
        self.arm0 = {sd: np.array([W - L.ARM_LEN * math.cos(b), L.Y_ARM, sd * (KH - L.ARM_LEN * math.sin(b))])
                     for sd in (-1, 1)}
        self.cb = np.array(h.cb)
        self.col_axis = -np.array(L.col_dir_down())        # pointing up/back to driver
        self.p0 = {sd: np.array([h.arm_end_x, L.Y_ARM, L.Z_D + sd * 10.0]) for sd in (-1, 1)}
        self.tie_len = {sd: float(np.linalg.norm(self.arm0[sd] - self.p0[sd])) for sd in (-1, 1)}

    def arm(self, sd, delta):
        return self.kp[sd] + rot(self.k_axis, delta) @ (self.arm0[sd] - self.kp[sd])

    def pit(self, sd, phi):
        return self.cb + rot(self.col_axis, phi) @ (self.p0[sd] - self.cb)

    def solve(self, sd, phi, guess=0.0):
        p = self.pit(sd, phi)
        Lt = self.tie_len[sd]
        f = lambda d: np.linalg.norm(self.arm(sd, d) - p) - Lt
        # bracket around guess
        lo, hi = guess - 0.9, guess + 0.9
        xs = np.linspace(lo, hi, 721)
        vals = [f(x) for x in xs]
        best = None
        for i in range(len(xs) - 1):
            if vals[i] == 0 or vals[i] * vals[i + 1] < 0:
                a, b = xs[i], xs[i + 1]
                for _ in range(60):
                    m = 0.5 * (a + b)
                    if f(a) * f(m) <= 0:
                        b = m
                    else:
                        a = m
                r = 0.5 * (a + b)
                if best is None or abs(r - guess) < abs(best - guess):
                    best = r
        return best

    def heading(self, sd, delta):
        """Ground-plane steer angle (rad, +ve = wheel nose to the left/-Z)."""
        hvec = rot(self.k_axis, delta) @ np.array([1.0, 0.0, 0.0])
        return math.atan2(-hvec[2], hvec[0])

    def sweep(self, n=60, phi_max=math.radians(110)):
        out = []
        gl, gr = 0.0, 0.0
        for phi in np.linspace(0, phi_max, n):
            dl = self.solve(-1, phi, gl)
            dr = self.solve(1, phi, gr)
            if dl is None or dr is None:
                break
            gl, gr = dl, dr
            out.append((phi, dl, dr, self.heading(-1, dl), self.heading(1, dr)))
        return out

    def analyse(self):
        """Find lock (pitman angle) giving TARGET_R_OUTER and report Ackermann data."""
        W = self.s.W
        res = {}
        for direction in (1, -1):
            data = self.sweep(phi_max=direction * math.radians(120))
            lock = None
            for phi, dl, dr, hl, hr in data:
                # turning left if headings positive
                hin, hout = (hl, hr) if hl > 0 else (hr, hl)
                if abs(hout) < 1e-4:
                    continue
                Ro = W / math.sin(abs(hout))
                if Ro <= L.TARGET_R_OUTER:
                    lock = (phi, dl, dr, hin, hout, Ro)
                    break
            res[direction] = (lock, data)
        return res


def ackermann_report(s, h):
    lk = Linkage(s, h)
    res = lk.analyse()
    W, KH = s.W, s.KH
    rep = {"tie_rod_len_L": lk.tie_len[-1], "tie_rod_len_R": lk.tie_len[1], "beta_deg": math.degrees(h.beta)}
    for direction, (lock, data) in res.items():
        key = "left" if direction == 1 else "right"
        if lock is None:
            rep[key] = None
            continue
        phi, dl, dr, hin, hout, Ro = lock
        hin, hout = abs(hin), abs(hout)
        ideal_in = math.atan(W / (W / math.tan(hout) - 2 * KH))
        rep[key] = dict(
            pitman_deg=math.degrees(phi), inner_deg=math.degrees(hin), outer_deg=math.degrees(hout),
            ideal_inner_deg=math.degrees(ideal_in),
            ackermann_pct=100.0 * (hin - hout) / (ideal_in - hout) if ideal_in > hout else float("nan"),
            r_outer_front=Ro, r_centre=math.hypot(W / math.tan(hout) - KH - L.SCRUB, W * 0) + 0.0,
            r_cg=math.hypot(W / math.tan(hout) - (s.FT / 2), W * 0.45),
            knuckle_deg=(math.degrees(dl), math.degrees(dr)),
        )
    return rep, lk


def _ack_score(s, beta):
    h = L.derive(s, s.W + 190.0, beta)
    rep, lk = ackermann_report(s, h)
    if rep["left"] is None or rep["right"] is None:
        return None, rep
    a = 0.5 * (rep["left"]["ackermann_pct"] + rep["right"]["ackermann_pct"])
    return a, rep


def tyre_sweep(s, h, lk, knuckle_range):
    """Points of the front tyre envelope over the steering range (both sides).
    Returns (max_x, list of (x, z) samples) for clearance design/checks."""
    pts_out = []
    for sd in (-1, 1):
        kp = lk.kp[sd]
        wc = np.array([s.W, L.Y_FAX, sd * s.FT / 2])
        lo, hi = knuckle_range[sd]
        for d in np.linspace(lo, hi, 25):
            R = rot(lk.k_axis, d)
            for zz in (-L.F_TYRE_W / 2, L.F_TYRE_W / 2):
                for a in np.linspace(0, 2 * math.pi, 36, endpoint=False):
                    p = wc + np.array([L.F_TYRE_D / 2 * math.cos(a), L.F_TYRE_D / 2 * math.sin(a), zz])
                    q = kp + R @ (p - kp)
                    pts_out.append(q)
    arr = np.array(pts_out)
    return float(arr[:, 0].max()), arr


def design(s):
    """Tune the steering arm angle, find the lock and the tyre sweep; return (Hard, report, linkage, sweep_pts)."""
    best = None
    for bdeg in np.arange(6.0, 20.01, 0.25):
        a, rep = _ack_score(s, math.radians(bdeg))
        if a is None:
            continue
        err = abs(a - 100.0)
        if best is None or err < best[0]:
            best = (err, bdeg)
    if best is None:
        raise RuntimeError(f"{s.code}: no steering solution")
    beta = math.radians(best[1])
    h = L.derive(s, s.W + 190.0, beta)
    rep, lk = ackermann_report(s, h)
    # knuckle rotation ranges at lock for each side
    kl = (rep["right"]["knuckle_deg"][0], rep["left"]["knuckle_deg"][0])
    kr = (rep["right"]["knuckle_deg"][1], rep["left"]["knuckle_deg"][1])
    rng = {-1: tuple(sorted(math.radians(x) for x in kl)), 1: tuple(sorted(math.radians(x) for x in kr))}
    sx, pts = tyre_sweep(s, h, lk, rng)
    h = L.derive(s, sx, beta)
    rep, lk = ackermann_report(s, h)
    rep["knuckle_range"] = rng
    rep["sweep_max_x"] = sx
    return h, rep, lk, pts
