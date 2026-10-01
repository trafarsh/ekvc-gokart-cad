#!/usr/bin/env python3
"""Export the bare chassis of every style as one STEP part: the welded frame (main rails, roll hoop
and braces, foot guard, bulkheads, front axle beam, king-pin C-brackets, jack pads, radiator tabs)
plus the chassis-side bumper connector tabs, which are welded to it.  No bumpers, body or
components.  Written to output/chassis_only/."""
import glob
import json
import os

import cadquery as cq
from PIL import Image

from ekvc import export as E, render as R, stepio
from ekvc.styles import STYLES

DEST = os.path.join(E.OUT, "chassis_only")


def bodies(path):
    return list(cq.importers.importStep(path).val().Solids())


def main():
    os.makedirs(os.path.join(DEST, "renders"), exist_ok=True)
    rows, thumbs = [], []
    for s in STYLES:
        sd = E.style_dir(s)
        frame = glob.glob(os.path.join(sd, "parts", f"{s.code}-FRM-01_*.step"))[0]
        tabs = sorted(glob.glob(os.path.join(sd, "parts", f"{s.code}-CON-*A_*.step")))
        solids = bodies(frame)
        n_frame = len(solids)
        for t in tabs:
            solids += bodies(t)
        comp = cq.Compound.makeCompound(solids)
        stem = f"{s.slug}_Chassis"
        out = os.path.join(DEST, stem + ".step")
        stepio.write_part(comp, out, stem, s.colour)
        bb = comp.BoundingBox()
        js = json.load(open(os.path.join(sd, "summary.json")))
        rows.append((s, stem, n_frame, len(tabs), bb, js))
        for v in ("iso", "side", "top"):
            p = os.path.join(DEST, "renders", f"{s.code}_chassis_{v}.png")
            R.render([(comp, s.colour)], p, view=v, size=(1400, 1000), title=f"{s.code}  {s.name} - chassis")
        thumbs.append(os.path.join(DEST, "renders", f"{s.code}_chassis_iso.png"))
        print(f"{s.code}: {n_frame} frame bodies + {len(tabs)} tabs, valid={comp.isValid()}, "
              f"{bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm -> {out}")

    # contact sheet of the ten chassis
    ims = [Image.open(p).convert("RGB") for p in thumbs]
    w, h = 700, 500
    sheet = Image.new("RGB", (w * 5, h * 2), "white")
    for i, im in enumerate(ims):
        im.thumbnail((w, h))
        sheet.paste(im, ((i % 5) * w, (i // 5) * h))
    sheet.save(os.path.join(DEST, "renders", "all_chassis_iso.png"))

    lines = ["# Chassis only - all 10 styles", "",
             "One STEP part per kart: the welded chromoly frame with roll hoop, hoop braces, foot guard, "
             "bulkheads, front axle beam with king-pin C-brackets, jack pads, radiator tabs and the "
             "chassis-side bumper connector tabs. No bumpers, bodywork or components.", "",
             f"Tube: {L_TUBE}. Coordinates are the same as the full karts (origin on the ground under the rear "
             "axle, +X forward, +Y up, +Z right), so each chassis drops straight into the kart assembly.", "",
             "**To get .SLDPRT:** SolidWorks > File > Open > pick the .step > File > Save As > Part (*.sldprt). "
             "It opens as a multi-body part (one body per tube / plate), like a weldment.", "",
             "| Kart | File | Tube bodies + plates | Connector tabs | Size L x H x W (mm) | Tube length | Tube mass |",
             "|---|---|---|---|---|---|---|"]
    for s, stem, nf, nt, bb, js in rows:
        lines.append(f"| {s.code} {s.name} | `{stem}.step` | {nf} | {nt} | {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} | "
                     f"{js['tube_m']:.1f} m | {js['tube_kg']:.1f} kg |")
    lines += ["", "Renders: `renders/` (iso, side, top for each kart; `all_chassis_iso.png` shows all ten)."]
    with open(os.path.join(DEST, "README.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


L_TUBE = "AISI 4130 chromoly, seamless, 25.4 x 1.65 mm"

if __name__ == "__main__":
    main()
