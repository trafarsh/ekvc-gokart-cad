# Team sketch analysis (`mutusami_sterring.SLDPRT`)

The uploaded file is internally named **`therika2.SLDPRT`** (saved 01-Aug-2026 by PUBESHVARAN S G,
SOLIDWORKS units = inches). It contains no solid bodies - only one 2D layout sketch (`Sketch2`)
on the Top plane. Preview: `team_sketch_preview.png`.

Dimensions decoded from the sketch (inches):

| Dim | Value | Meaning (from the sketch geometry) |
|---|---|---|
| D1 | 51.00 | wheelbase (front axle x = -28.147, rear axle x = 22.853) |
| D2 | 37.00 | front track, centre-to-centre |
| D3 | 43.00 | rear track, centre-to-centre |
| D4 / D5 | 4.50 / 10.00 | front tyre width / diameter |
| D6 / D7 | 7.10 / 11.00 | rear tyre width / diameter |
| D12 / D16 | 14.98 / 28.89 | king-pin position (half-spacing 14.98 -> 3.52 in scrub from wheel centre) |
| D15, D22 | 110 deg | steering-arm angle at each knuckle |
| D25 | 123.56 deg | Ackermann construction angle |
| D18 | 32.00 | main frame rail spacing |
| D9 | 52.00 | front bumper width |
| D10 | 73.31 | front bumper to rear bumper |

## What was kept / changed for the 10 styles

* Tyre sizes and king-pin scrub (3.52 in) - **kept**.
* Front track 37 in - kept for S01/S03/S07, varied 36-38 in on the other styles.
* Rear track 43 in -> **42.0-42.8 in**, so the rear stays under 50 in even measured over the tyres
  (43 + 7.1 = 50.1 in would be 0.1 in over if measured outside-to-outside).
* Wheelbase 51 in -> **46-47 in**: with 51 in the tyres alone span 61.5 in, leaving ~1.7 in per end for
  bumpers under the 65 in overall limit (and the sketch measured 73.3 in).
* The 110 deg arm angle (100 % Ackermann line to the rear-axle centre) produced ~145 % Ackermann
  with a real pitman linkage, so the arm angle is now **solved numerically per style** (6.5-8.5 deg
  with 155 mm arms) for ~100 % Ackermann at full lock and an outer-wheel radius of ~2.8 m.
