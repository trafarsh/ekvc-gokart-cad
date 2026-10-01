# EKVC Season 4 – 10 engine-kart concepts (side-mounted Yamaha R15 V2)

Ten complete, rule-checked go-kart designs for the **Engine/Electric Kart Vehicle Championship –
Season 4** rulebook, generated parametrically from the team's Ackermann/layout sketch
(`therika2` / `mutusami_sterring.SLDPRT`).

Each style is a full kart: chromoly frame and roll hoop, **front, rear and side bumpers**,
**chassis-to-bumper connectors**, **single-disc hydraulic brake**, live axle and chain drive, the
R15 V2 engine on the right, Ackermann steering, CBA pedal box, seat, firewall, floor pan, bodywork,
kill switches, brake light, extinguisher, fuel tank, radiator, exhaust, and hitch points.

| | Common to all 10 styles |
|---|---|
| Overall length | **64.1 – 64.6 in bumper face to bumper face, foam included** (limit < 65 in, ≥ 11 mm margin on every kart); nothing protrudes beyond the bumpers |
| Wheelbase / track | 46.0 – 47.0 in wheelbase; front track 36 – 38 in, rear track 42.0 – 42.8 in (rear stays under 50 in even over the tyres) |
| Frame tube | **AISI 4130 chromoly, seamless, 25.4 × 1.65 mm** (rule: 1–2 in OD, ≥ 1.2 mm wall, C ≥ 0.18 %) |
| Engine | Yamaha R15 V2, 149.8 cc single-cylinder 4-stroke, liquid cooled – mounted on the **right**, chain on its inboard side |
| Drive | #428 chain 14T / 34T (66 links), live 40 mm axle, 3 flange bearings |
| Brake | Hydraulic, one 180 mm disc on the live axle (locks both rear wheels), 5/8 in master cylinder with own reservoir, over-travel switch |
| Steering | Column + pitman arm + 2 tie rods, knuckle arms tuned per style for ~100 % Ackermann at lock, outer-wheel turning radius ≈ 2.8 m (rule ≤ 3 m), 280 mm round wheel, positive stops on the chassis |
| Driver | Designed around a 175 cm driver: back angle 20°, roll-hoop top 115 mm above the helmet (rule ≥ 76 mm), foot guard 92 mm above the toes (rule ≥ 76 mm) |
| Tyres | 4.5×10.0-5 front, 7.1×11.0-5 rear (rule table 1, dry D1) |

## The ten styles

| Code | Name | Frame idea | Front / rear / side bumpers | Body |
|---|---|---|---|---|
| S01 | Classic Sprint | straight rails, 3-cross ladder | straight / straight / bar | box nose & pods |
| S02 | Arrow | rails taper into the nose + arrow-shaped outer rails | chevron / arc / kicked bar | arrow nose, wedge pods |
| S03 | Ladder Pro | 5-cross ladder + upper side-impact rails | U (up-turned ends) / U / twin-bar | box |
| S04 | Bowfin | left rail bowed outward + floor X | arc / arc / arc | round |
| S05 | X-Brace | X bracing in cockpit and engine bay | trapezoid / trapezoid / bar | wedge |
| S06 | Perimeter | outer perimeter rails carry the side bumpers | wide straight / straight / hoop | box nose, full pods |
| S07 | Spine | centre spine + V outriggers | chevron / straight / bar | F1 nose, slim pods |
| S08 | Endurance | ladder + upper rails + floor/foot-guard/engine-bay diagonals | U / U / twin-bar | round nose, full pods |
| S09 | Featherweight | minimum members | straight / straight / bar | slim |
| S10 | Wedge | plan-view wedge outer rails | swept / arc / swept | wedge |

Each style folder has its own `README.md` with the full **rule-compliance table**, steering
data, interference-check results and renders (`output/<style>/renders/`).

**Check results (all ten styles):** 45 / 45 automated rule checks pass, **0 part-to-part clashes**
(intended welds and bolted joints excluded) and **0 contacts** when both front tyres are swept
lock-to-lock against the frame, bumpers, connectors, steering and bodywork. The 175 cm reference
driver has no interference with anything except the seat and steering-wheel grips.

## Getting SolidWorks `.SLDPRT` / `.SLDASM` files

SolidWorks' native format can only be written by SolidWorks itself, so every part is delivered
as a STEP file (AP214, millimetres, with names and colours) plus a macro that converts the whole
set inside SolidWorks in one run:

1. In SolidWorks: **Tools ▸ Options ▸ System Options ▸ Import** → untick **Enable 3D Interconnect**
   (so STEP files open as plain imported bodies). Optionally set *Import diagnostics* to "never".
2. **Tools ▸ Macro ▸ New…** (save the new macro anywhere) → in the VBA editor **File ▸ Import File…**
   → choose `solidworks_macro/EKVC_STEP_to_SLDPRT_and_SLDASM.bas` → run `main`.
3. When asked, paste the path of this repository's `output` folder.

The macro saves an `.SLDPRT` next to every `.step` and then builds
`output/<style>/<style>.SLDASM` for all ten karts from `placements.csv`, with every component
fixed in place. Re-running skips files that already exist.

*Quick alternative:* **File ▸ Open** any `output/<style>/<style>_ASSEMBLY.step` → SolidWorks imports
the whole kart as an assembly; **File ▸ Save As** then saves the `.SLDASM` and all part files.

## Repository layout

```
output/
  common/parts/*.step              parts shared by all styles (engine, wheels, brake, pedals, seat ...)
                                   + loose items: C-STD-01 kart stand (rule 8, rails at 950 mm),
                                     C-HIT-02 yellow push-pull rod (rule 1.4)
  S01_ClassicSprint/
    S01_ClassicSprint_ASSEMBLY.step complete kart assembly
    parts/*.step                   style-specific parts (frame, bumpers, connectors, knuckles, body ...)
    placements.csv                 transform of every component (used by the macro)
    BOM.csv                        bill of materials with materials and notes
    README.md                      rule-compliance report, steering data, clash results
    renders/*.png
  ... S02 – S10
solidworks_macro/EKVC_STEP_to_SLDPRT_and_SLDASM.bas
generator/                          Python/CadQuery source that builds everything
docs/                               source sketch analysis, rule interpretation notes
```

### Coordinate system (all parts and assemblies)

Origin on the ground, on the kart centre-line, directly under the rear axle.
**+X forward, +Y up, +Z to the driver's right (engine side).** Units: mm.
(SolidWorks shows +Y as up, so the karts open the right way up.)

## Regenerating / changing the designs

```bash
pip install cadquery
cd generator
python build_all.py            # all 10 styles with full checks (~25 min)
python build_all.py S04        # one style
python build_all.py --fast S04 # skip the slow interference check
```

Global parameters (tube size, driver package, engine position, steering arm length...) live in
`generator/ekvc/layout.py`; the ten styles are in `generator/ekvc/styles.py`; frame topologies in
`generator/ekvc/parts/frame.py`; bumpers and connectors in `generator/ekvc/parts/bumpers.py`.
Changing the tube (e.g. to AISI 1018, 25.4 × 2.0) is a two-line edit (`TUBE_WALL`, `TUBE_MAT`).

## Important assumptions – please verify

* **Engine envelope.** The R15 V2 is modelled as a dimensional envelope (crankcase, inclined
  cylinder, head, covers, countershaft, mounting lugs). Measure your engine and adjust
  `parts/wheels_drive.py:engine()` and the mount positions before cutting tabs.
* **Your sketch was a 2D layout.** Its wheelbase (51 in) and overall length (73.3 in) did not fit the
  65 in limit, so the wheelbase was shortened to 46–47 in and the Ackermann arm angle re-solved per
  style. The king-pin offset from the wheel (3.52 in) and tyre sizes come from your sketch.
* **Track width rule.** "Larger track ≤ 50 in" is satisfied centre-to-centre *and* over the tyre
  sidewalls (49.9 in max), in case judges measure outside-to-outside.
* **Hoop braces** run rearward from the hoop bend (650 mm) to the rear bulkhead. If your scrutineers
  want them attached higher, raise `HOOP_KNEE_Y` in `layout.py`.
* Bodywork is a 3 mm shell for fit/visual purposes; real panels need mounting brackets.
* Bumper foam is modelled as a continuous sleeve; in practice slit it around the connector tabs and bolts.
* The orange manikin (`REF driver`) is reference geometry only – suppress it before drawings/BOM.
