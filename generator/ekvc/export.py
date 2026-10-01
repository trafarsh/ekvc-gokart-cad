"""Write STEP parts / assemblies, placement CSV (for the SolidWorks macro), BOM, renders, report."""
from __future__ import annotations

import csv
import json
import math
import os
from collections import OrderedDict

from . import checks as K
from . import layout as L
from . import render as R
from . import stepio

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "output")
COMMON_DIR = os.path.join(OUT, "common", "parts")


def style_dir(s):
    return os.path.join(OUT, s.slug)


def part_path(inst, s):
    if inst.scope == "common":
        return os.path.join(COMMON_DIR, inst.part.stem + ".step")
    return os.path.join(style_dir(s), "parts", inst.part.stem + ".step")


def write_parts(I, s, written=None, skip_common=False):
    written = written if written is not None else set()
    os.makedirs(COMMON_DIR, exist_ok=True)
    os.makedirs(os.path.join(style_dir(s), "parts"), exist_ok=True)
    for inst in I:
        p = part_path(inst, s)
        if p in written or (skip_common and inst.scope == "common"):
            continue
        stepio.write_part(inst.part.shape, p, inst.part.stem, inst.part.rgb)
        written.add(p)
    return written


def write_assembly(I, s):
    inst = []
    for i in I:
        inst.append(dict(part_id=i.part.stem, shape=i.part.shape, rgb=i.part.rgb, loc=i.pl.location(), inst_name=i.name))
    p = os.path.join(style_dir(s), f"{s.slug}_ASSEMBLY.step")
    stepio.write_assembly(inst, p, f"{s.slug}_ASSEMBLY")
    return p


def write_placements(I, s):
    p = os.path.join(style_dir(s), "placements.csv")
    sd = style_dir(s)
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance", "part_number", "file_stem", "scope", "step_relpath",
                    "xx", "xy", "xz", "yx", "yy", "yz", "zx", "zy", "zz", "tx_mm", "ty_mm", "tz_mm", "reference_only"])
        for i in I:
            R_ = i.pl.R
            rel = os.path.relpath(part_path(i, s), sd).replace(os.sep, "/")
            # columns = images of local X, Y, Z axes (R symmetric -> row/col convention identical)
            w.writerow([i.name, i.part.pid, i.part.stem, i.scope, rel,
                        R_[0, 0], R_[1, 0], R_[2, 0], R_[0, 1], R_[1, 1], R_[2, 1], R_[0, 2], R_[1, 2], R_[2, 2],
                        round(i.pl.t[0], 4), round(i.pl.t[1], 4), round(i.pl.t[2], 4),
                        "1" if i.part.group == "reference" else "0"])
    return p


def write_bom(I, s):
    rows = OrderedDict()
    for i in I:
        k = i.part.pid + "|" + i.part.stem
        if k not in rows:
            rows[k] = dict(pid=i.part.pid, name=i.part.name, group=i.part.group, material=i.part.material,
                           desc=i.part.desc, qty=0, file=os.path.relpath(part_path(i, s), style_dir(s)).replace(os.sep, "/"))
        rows[k]["qty"] += 1
    p = os.path.join(style_dir(s), "BOM.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Part number", "Name", "Qty", "Group", "Material", "Notes", "STEP file (convert to .SLDPRT)"])
        for r in sorted(rows.values(), key=lambda r: (r["group"], r["pid"])):
            w.writerow([r["pid"], r["name"], r["qty"], r["group"], r["material"], r["desc"], r["file"]])
    return p, list(rows.values())


def renders(I, s, views=("iso", "iso_rear", "top", "side"), size=(1600, 1150)):
    d = os.path.join(style_dir(s), "renders")
    os.makedirs(d, exist_ok=True)
    items = [(i.pl.apply(i.part.shape), i.part.rgb) for i in I if i.part.group != "reference"]
    out = {}
    for v in views:
        p = os.path.join(d, f"{s.code}_{v}.png")
        R.render(items, p, view=v, size=size, title=f"{s.code}  {s.name}")
        out[v] = p
    items2 = items + [(i.pl.apply(i.part.shape), i.part.rgb) for i in I if i.part.group == "reference"]
    p = os.path.join(d, f"{s.code}_side_driver.png")
    R.render(items2, p, view="side_left", size=size, title=f"{s.code}  {s.name} - 175 cm driver")
    out["side_driver"] = p
    return out


def report(I, info, rules, clashes, sweep, files):
    s, h, st = info["style"], info["hard"], info["steer"]
    rep = st["rep"]
    fm = info["frame_meta"]
    lines = [f"# {s.code} - {s.name}", "", s.blurb, "",
             f"* Wheelbase **{s.wheelbase_in:.2f} in** ({s.W:.1f} mm), front track {s.ftrack_in:.2f} in, rear track {s.rtrack_in:.2f} in",
             f"* Frame: `{s.frame}` - {fm['tube_length'] / 1000:.1f} m of {L.TUBE_OD:.1f} x {L.TUBE_WALL} mm {L.TUBE_MAT} (~{fm['tube_mass']:.1f} kg tube)",
             f"* Bumpers: front `{s.front_bumper}`, rear `{s.rear_bumper}`, side `{s.side_bumper}`; body: nose `{s.nose}`, pods `{s.pods}`",
             f"* Steering: arm {L.ARM_LEN:.0f} mm at {math.degrees(h.beta):.2f} deg, tie rods {rep['tie_rod_len_L']:.0f}/{rep['tie_rod_len_R']:.0f} mm (solver), "
             f"lock inner {rep['left']['inner_deg']:.1f} / outer {rep['left']['outer_deg']:.1f} deg, "
             f"R(outer front) {rep['left']['r_outer_front'] / 1000:.2f} m, Ackermann {0.5 * (rep['left']['ackermann_pct'] + rep['right']['ackermann_pct']):.0f} %",
             "", "## Rule compliance (EKVC Season 4)", "", "| Rule | Check | Requirement | This kart | Result |", "|---|---|---|---|---|"]
    for r in rules:
        lines.append(f"| {r['ref']} | {r['rule']} | {r['requirement']} | {r['value']} | {'✅' if r['status'] == 'PASS' else '❌'} {r['status']} |")
    lines += ["", "## Interference check", ""]
    if clashes is None:
        lines.append("_not run_")
    else:
        real = [c for c in clashes if "REF" not in c[0] and "REF" not in c[1]]
        drv = [c for c in clashes if "REF" in c[0] or "REF" in c[1]]
        lines.append(f"* Part-to-part clashes (excluding intended welds/bolted contacts): **{len(real)}**")
        for a, b, v in sorted(real, key=lambda x: -x[2]):
            lines.append(f"  * {a} <-> {b}: {v:.0f} mm3")
        lines.append(f"* Driver (175 cm reference manikin) contacts: {len(drv)}")
        for a, b, v in sorted(drv, key=lambda x: -x[2]):
            lines.append(f"  * {a} <-> {b}: {v:.0f} mm3")
    if sweep is not None:
        lines.append(f"* Front tyres swept lock-to-lock against frame/bumpers/body/steering: **{len(sweep)}** contacts")
        for x in sweep:
            lines.append(f"  * {x[0]} at {x[2]} deg <-> {x[1]}: {x[3]:.0f} mm3")
    lines += ["", "## Files", ""]
    for k, v in files.items():
        lines.append(f"* {k}: `{os.path.relpath(v, style_dir(s))}`")
    p = os.path.join(style_dir(s), "README.md")
    with open(p, "w") as f:
        f.write("\n".join(lines) + "\n")
    return p


def summary_json(info, rules, clashes, sweep, bom_rows):
    s, h, st = info["style"], info["hard"], info["steer"]
    rep = st["rep"]
    P = {r["rule"]: r for r in rules}
    return dict(code=s.code, name=s.name, slug=s.slug, blurb=s.blurb, wheelbase_in=s.wheelbase_in, ftrack_in=s.ftrack_in,
                rtrack_in=s.rtrack_in, frame=s.frame, front_bumper=s.front_bumper, rear_bumper=s.rear_bumper,
                side_bumper=s.side_bumper, nose=s.nose, pods=s.pods, colour=s.colour, body_colour=s.body_colour,
                length=P["Front bumper to rear bumper (incl. foam)"]["value"], overall=P["Overall length (any component)"]["value"],
                gc=P["Ground clearance (lowest non-tyre point)"]["value"], hoop=P["Roll hoop height above helmet (175 cm driver)"]["value"],
                turn=P["Turning radius (outer front wheel)"]["value"], ack=P["Ackermann at lock"]["value"],
                beta=math.degrees(h.beta), tube_m=info["frame_meta"]["tube_length"] / 1000, tube_kg=info["frame_meta"]["tube_mass"],
                rules_pass=sum(1 for r in rules if r["status"] == "PASS"), rules_total=len(rules),
                fails=[r["rule"] for r in rules if r["status"] != "PASS"],
                clashes=None if clashes is None else len([c for c in clashes if "REF" not in c[0] and "REF" not in c[1]]),
                sweep=None if sweep is None else len(sweep), n_parts=len(bom_rows), rules=rules)
