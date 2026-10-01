#!/usr/bin/env python3
"""Build a self-contained review page (HTML + JPEG renders) comparing the ten styles."""
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "output")
DEST = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "review_page")
VIEWS = [("iso", "Front three-quarter"), ("iso_rear", "Rear three-quarter"), ("top", "Plan"), ("side", "Right side"),
         ("side_driver", "Left side, 175 cm driver")]


def crop_white(im, pad=24):
    g = im.convert("L")
    bbox = g.point(lambda v: 255 if v < 250 else 0).getbbox()
    if not bbox:
        return im
    x0, y0, x1, y1 = bbox
    return im.crop((max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)))


def main():
    os.makedirs(os.path.join(DEST, "img"), exist_ok=True)
    data = []
    for d in sorted(os.listdir(OUT)):
        sj = os.path.join(OUT, d, "summary.json")
        if not os.path.exists(sj):
            continue
        js = json.load(open(sj))
        js["views"] = {}
        for v, label in VIEWS:
            src = os.path.join(OUT, d, "renders", f"{js['code']}_{v}.png")
            if not os.path.exists(src):
                continue
            im = Image.open(src).convert("RGB")
            # remove the title strip drawn by the renderer before cropping
            im.paste((255, 255, 255), (0, 0, im.width, 70))
            im = crop_white(im)
            big = im.copy()
            big.thumbnail((1200, 900))
            fn = f"img/{js['code']}_{v}.jpg"
            big.save(os.path.join(DEST, fn), quality=84, optimize=True)
            js["views"][v] = fn
            if v == "iso":
                th = im.copy()
                th.thumbnail((560, 420))
                fn2 = f"img/{js['code']}_thumb.jpg"
                th.save(os.path.join(DEST, fn2), quality=82, optimize=True)
                js["thumb"] = fn2
        js["colour_hex"] = "#%02x%02x%02x" % tuple(int(255 * c) for c in js["colour"])
        js["body_hex"] = "#%02x%02x%02x" % tuple(int(255 * c) for c in js["body_colour"])
        data.append(js)
    tpl = open(os.path.join(HERE, "review_page_template.html")).read()
    html = tpl.replace("/*__DATA__*/[]", json.dumps(data, separators=(",", ":"), default=str))
    with open(os.path.join(DEST, "index.html"), "w") as f:
        f.write(html)
    print(f"wrote {DEST}/index.html with {len(data)} styles")


if __name__ == "__main__":
    main()
