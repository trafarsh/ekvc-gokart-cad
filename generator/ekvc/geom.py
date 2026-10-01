"""Low-level geometry helpers built on CadQuery / OpenCascade."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cadquery as cq
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Vec

IN = 25.4

V = cq.Vector


def v(p) -> cq.Vector:
    if isinstance(p, cq.Vector):
        return p
    return cq.Vector(*p)


def _annulus(center: cq.Vector, normal: cq.Vector, od: float, wall: float | None) -> cq.Face:
    outer = cq.Wire.makeCircle(od / 2, center, normal)
    if wall is None or wall <= 0 or wall >= od / 2:
        return cq.Face.makeFromWires(outer)
    inner = cq.Wire.makeCircle(od / 2 - wall, center, normal)
    return cq.Face.makeFromWires(outer, [inner])


def _prism(face: cq.Face, vec: cq.Vector) -> cq.Solid:
    return cq.Solid(BRepPrimAPI_MakePrism(face.wrapped, gp_Vec(vec.x, vec.y, vec.z)).Shape())


def _revol(face: cq.Face, origin: cq.Vector, axis: cq.Vector, angle_rad: float) -> cq.Solid:
    ax = gp_Ax1(gp_Pnt(origin.x, origin.y, origin.z), gp_Dir(axis.x, axis.y, axis.z))
    return cq.Solid(BRepPrimAPI_MakeRevol(face.wrapped, ax, angle_rad).Shape())


def _fix(shape):
    try:
        from OCP.ShapeFix import ShapeFix_Shape
        sf = ShapeFix_Shape(shape.wrapped)
        sf.Perform()
        return cq.Shape.cast(sf.Shape())
    except Exception:
        return shape


def fuse_all(solids):
    solids = [s for s in solids if s is not None]
    if not solids:
        return None
    if len(solids) == 1:
        return solids[0]
    res = solids[0].fuse(*solids[1:], glue=False)
    try:
        cl = res.clean()
        if cl.isValid():
            return cl
    except Exception:
        pass
    if res.isValid():
        return res
    # sequential fallback
    acc = solids[0]
    for s in solids[1:]:
        nxt = acc.fuse(s)
        acc = nxt if nxt.isValid() else _fix(nxt)
    if not acc.isValid():
        acc = _fix(acc)
    return acc


def tube_path_segments(pts, bend_r):
    """Return list of ('line', a, b) / ('arc', t1, t2, centre, axis, angle) for a filleted polyline."""
    P = [v(p) for p in pts]
    # remove consecutive duplicates
    Q = [P[0]]
    for p in P[1:]:
        if (p - Q[-1]).Length > 1e-6:
            Q.append(p)
    P = Q
    if len(P) < 2:
        raise ValueError("tube path needs >= 2 distinct points")
    segs = []
    start = P[0]
    n = len(P)
    # precompute tangent lengths, shrink radius if segments too short
    tlen = [0.0] * n
    radii = [bend_r] * n
    for i in range(1, n - 1):
        din = (P[i] - P[i - 1]).normalized()
        dout = (P[i + 1] - P[i]).normalized()
        c = max(-1.0, min(1.0, din.dot(dout)))
        th = math.acos(c)
        if th < 1e-4:
            continue
        tlen[i] = bend_r * math.tan(th / 2)
    for i in range(1, n - 1):
        if tlen[i] == 0:
            continue
        lin = (P[i] - P[i - 1]).Length
        lout = (P[i + 1] - P[i]).Length
        avail_in = lin if i - 1 == 0 else lin / 2
        avail_out = lout if i + 1 == n - 1 else lout / 2
        lim = 0.98 * min(avail_in, avail_out)
        if tlen[i] > lim:
            din = (P[i] - P[i - 1]).normalized()
            dout = (P[i + 1] - P[i]).normalized()
            th = math.acos(max(-1.0, min(1.0, din.dot(dout))))
            radii[i] = lim / math.tan(th / 2)
            tlen[i] = lim
    cur = P[0]
    for i in range(1, n - 1):
        if tlen[i] == 0:
            continue
        din = (P[i] - P[i - 1]).normalized()
        dout = (P[i + 1] - P[i]).normalized()
        th = math.acos(max(-1.0, min(1.0, din.dot(dout))))
        t1 = P[i] - din * tlen[i]
        t2 = P[i] + dout * tlen[i]
        nvec = (dout - din * din.dot(dout)).normalized()
        centre = t1 + nvec * radii[i]
        axis = din.cross(dout).normalized()
        if (t1 - cur).Length > 1e-6:
            segs.append(("line", cur, t1))
        segs.append(("arc", t1, t2, centre, axis, th, din))
        cur = t2
    if (P[-1] - cur).Length > 1e-6:
        segs.append(("line", cur, P[-1]))
    return segs


def bent_tube(pts, od=25.4, wall=1.65, bend_r=76.2, fuse=True):
    """Hollow round tube along a polyline with bends (cylinders + torus sections).

    Uses only analytic surfaces so the STEP stays small and SolidWorks can recognise
    the geometry.  Returns a cq.Solid (or compound if fuse=False).
    """
    segs = tube_path_segments(pts, bend_r)
    solids = []
    for s in segs:
        if s[0] == "line":
            a, b = s[1], s[2]
            d = b - a
            solids.append(_prism(_annulus(a, d.normalized(), od, wall), d))
        else:
            _, t1, t2, centre, axis, th, din = s
            face = _annulus(t1, din, od, wall)
            solids.append(_revol(face, centre, axis, th))
    if fuse:
        return fuse_all(solids)
    return cq.Compound.makeCompound(solids)


def rod(p0, p1, d):
    p0, p1 = v(p0), v(p1)
    dd = p1 - p0
    return cq.Solid.makeCylinder(d / 2, dd.Length, p0, dd.normalized())


def cyl(center, axis, d, length, centered=True):
    """Solid cylinder; if centered, `center` is the mid point along the axis."""
    c, a = v(center), v(axis).normalized()
    base = c - a * (length / 2) if centered else c
    return cq.Solid.makeCylinder(d / 2, length, base, a)


def ring(center, axis, od, idia, length, centered=True):
    c, a = v(center), v(axis).normalized()
    base = c - a * (length / 2) if centered else c
    return _prism(_annulus(base, a, od, (od - idia) / 2), a * length)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def plate_xy(poly2d, z0, t):
    """Plate in an XY plane (normal +Z) from 2D outline (x,y), from z0 to z0+t."""
    w = cq.Wire.makePolygon([V(x, y, z0) for x, y in poly2d], close=True)
    return cq.Solid.extrudeLinear(w, [], V(0, 0, t))


def plate_yz(poly2d, x0, t):
    """Plate in a YZ plane: outline given as (z, y) points, extruded +X by t from x0."""
    w = cq.Wire.makePolygon([V(x0, y, z) for z, y in poly2d], close=True)
    return cq.Solid.extrudeLinear(w, [], V(t, 0, 0))


def plate_xz(poly2d, y0, t):
    """Horizontal plate: outline (x, z) at height y0, extruded +Y by t."""
    w = cq.Wire.makePolygon([V(x, y0, z) for x, z in poly2d], close=True)
    return cq.Solid.extrudeLinear(w, [], V(0, t, 0))


def plate_on_plane(origin, xdir, ydir, poly2d, t, centered=True):
    """General flat plate: outline in a local (u,v) frame defined by origin/xdir/ydir."""
    o, ux, uy = v(origin), v(xdir).normalized(), v(ydir).normalized()
    n = ux.cross(uy).normalized()
    if centered:
        o = o - n * (t / 2)
    w = cq.Wire.makePolygon([o + ux * a + uy * b for a, b in poly2d], close=True)
    return cq.Solid.extrudeLinear(w, [], n * t)


def rounded_rect(w, h, r, n=6):
    """2D rounded rectangle polygon centred at origin."""
    r = min(r, w / 2 - 1e-3, h / 2 - 1e-3)
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def circle_pts(r, n=24, cx=0.0, cy=0.0, a0=0.0):
    return [(cx + r * math.cos(a0 + 2 * math.pi * k / n), cy + r * math.sin(a0 + 2 * math.pi * k / n)) for k in range(n)]


def revolve_profile_z(profile_rz, center=(0, 0, 0)):
    """Revolve a closed (r, z) profile about the global Z axis through `center`."""
    c = v(center)
    w = cq.Wire.makePolygon([V(c.x + r, c.y, c.z + z) for r, z in profile_rz], close=True)
    f = cq.Face.makeFromWires(w)
    return _revol(f, c, V(0, 0, 1), 2 * math.pi)


def revolve_profile(profile_ra, axis_origin, axis_dir, radial_dir):
    """Revolve closed (r, a) profile (r radial, a axial) about an arbitrary axis."""
    o, a, rd = v(axis_origin), v(axis_dir).normalized(), v(radial_dir).normalized()
    w = cq.Wire.makePolygon([o + rd * r + a * z for r, z in profile_ra], close=True)
    return _revol(cq.Face.makeFromWires(w), o, a, 2 * math.pi)


def sweep_rect(path_pts, width, thick, bend_r, up=(0, 0, 1)):
    """Rectangular strip (width along `up`, thickness in path plane) along a planar polyline."""
    segs = tube_path_segments(path_pts, bend_r)
    upv = v(up).normalized()
    solids = []
    for s in segs:
        if s[0] == "line":
            a, b = s[1], s[2]
            d = (b - a).normalized()
            side = d.cross(upv).normalized()
            face = _rect_face(a, side, upv, thick, width)
            solids.append(_prism(face, b - a))
        else:
            _, t1, t2, centre, axis, th, din = s
            side = din.cross(upv).normalized()
            face = _rect_face(t1, side, upv, thick, width)
            solids.append(_revol(face, centre, axis, th))
    return fuse_all(solids)


def _rect_face(c, u, w, a, b):
    pts = [c + u * (-a / 2) + w * (-b / 2), c + u * (a / 2) + w * (-b / 2),
           c + u * (a / 2) + w * (b / 2), c + u * (-a / 2) + w * (b / 2)]
    return cq.Face.makeFromWires(cq.Wire.makePolygon(pts, close=True))


def translate(shape, d):
    return shape.translate(v(d))


def mirror_z(shape):
    """Mirror about the XY plane (Z -> -Z)."""
    return shape.mirror("XY", (0, 0, 0))


def bbox(shape):
    bb = shape.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


# ---------------------------------------------------------------- placements
@dataclass
class Placement:
    """Rigid placement: p_global = R @ p_local + t (mm).  R must be symmetric (identity or
    a 180 deg turn) so the transform is identical in row- and column-vector conventions."""
    t: tuple = (0.0, 0.0, 0.0)
    R: np.ndarray = field(default_factory=lambda: np.eye(3))

    @staticmethod
    def flip_y(t=(0, 0, 0)):
        return Placement(tuple(t), np.diag([-1.0, 1.0, -1.0]))

    @staticmethod
    def flip_x(t=(0, 0, 0)):
        return Placement(tuple(t), np.diag([1.0, -1.0, -1.0]))

    @staticmethod
    def flip_z(t=(0, 0, 0)):
        return Placement(tuple(t), np.diag([-1.0, -1.0, 1.0]))

    def location(self) -> cq.Location:
        from OCP.gp import gp_Trsf
        tr = gp_Trsf()
        R = self.R
        tr.SetValues(R[0, 0], R[0, 1], R[0, 2], self.t[0],
                     R[1, 0], R[1, 1], R[1, 2], self.t[1],
                     R[2, 0], R[2, 1], R[2, 2], self.t[2])
        return cq.Location(tr)

    def apply(self, shape):
        return shape.moved(self.location())


def fillet(shape, selector, r):
    """Fillet edges of a solid chosen with a CadQuery string selector (falls back to unfilleted)."""
    try:
        return cq.Workplane(obj=shape).edges(selector).fillet(r).val()
    except Exception:
        return shape


def hull2d(pts):
    """Convex hull (monotone chain) of 2D points, CCW."""
    P = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))
    if len(P) <= 2:
        return P

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]
