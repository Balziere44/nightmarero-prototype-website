#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pulls the two small pictures each relic gear piece has on the MVP sheet.

The Relic Gears tab is a wall of screenshots: for every piece a minimap with
the spot marked on it, a strip showing the piece and what it costs, and a
tooltip. The tooltip is transcribed into tools/data/relic-gear.json instead of
being shipped, but the minimap and the cost strip say something the text
cannot, so those two are pulled in.

    python tools/fetch_relic_art.py

Nothing on that tab is cell text, so there is no export that can tell which
picture belongs to which piece. The xlsx export does carry the row and column
every drawing is pinned to, and relic-gear.json carries the same pair per
piece under "cell", so the two are matched on that. A piece whose anchors are
missing is reported and skipped rather than guessed at.

Writes assets/img/relic/<slug>-map.webp and <slug>-cost.webp, and their sizes
to tools/data/relic-art.json so build_mvps.py can write width and height
without needing Pillow. Two pieces share a screenshot where the sheet drew
them together, and then both slugs get their own copy, so nothing in the page
has to know about the sharing.
"""

import io
import json
import os
import re
import sys
import urllib.request
import zipfile

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_classes import slugify      # so the file names match the page

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "data", "relic-gear.json")
OUT_IMG = os.path.join(ROOT, "assets", "img", "relic")
OUT_JSON = os.path.join(ROOT, "tools", "data", "relic-art.json")

URL = "https://docs.google.com/spreadsheets/d/%s/export?format=xlsx"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NightmareRO-site-build/1.0"

BOOK = "1ojSow2JMglSDcvXii3Sppoa9Nx9mWAcVtC3c_OzApzk"
# Relic Gears is the fifth tab, and xlsx numbers its sheets in tab order.
SHEET = 5

ANCHOR_RE = re.compile(
    r"<xdr:from><xdr:col>(\d+)</xdr:col>.*?<xdr:row>(\d+)</xdr:row>.*?"
    r'r:embed="(rId\d+)"', re.S)
REL_RE = re.compile(r'Id="(rId\d+)"[^>]*Target="\.\./media/([^"]+)"')
SHEET_DRAWING_RE = re.compile(r'Target="\.\./(drawings/drawing\d+\.xml)"')


def anchors(book):
    """Every picture on the tab, keyed by the "row,col" it is pinned to."""
    rels = book.read("xl/worksheets/_rels/sheet%d.xml.rels" % SHEET)
    drawing = "xl/" + SHEET_DRAWING_RE.search(rels.decode("utf-8")).group(1)
    body = book.read(drawing).decode("utf-8")
    rel_path = drawing.replace("drawings/", "drawings/_rels/") + ".rels"
    media = dict(REL_RE.findall(book.read(rel_path).decode("utf-8")))

    found = {}
    for col, row, rid in ANCHOR_RE.findall(body):
        name = media.get(rid)
        if name:
            found["%s,%s" % (row, col)] = "xl/media/" + name
    return found


def main():
    items = json.load(io.open(SRC, encoding="utf-8"))["items"]

    request = urllib.request.Request(URL % BOOK, headers={"User-Agent": UA})
    blob = urllib.request.urlopen(request, timeout=180).read()
    print("workbook %s...: %.1f MB" % (BOOK[:8], len(blob) / 1048576.0))
    book = zipfile.ZipFile(io.BytesIO(blob))
    found = anchors(book)

    if not os.path.isdir(OUT_IMG):
        os.makedirs(OUT_IMG)

    sizes, missing = {}, []
    for it in items:
        cell = it.get("cell") or {}
        for part in ("map", "cost"):
            path = found.get(cell.get(part, ""))
            if not path:
                missing.append("%s %s" % (it["name"], part))
                continue
            image = Image.open(io.BytesIO(book.read(path)))
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA")
            stem = "%s-%s" % (slugify(it["name"]), part)
            image.save(os.path.join(OUT_IMG, stem + ".webp"),
                       "WEBP", quality=88, method=6)
            sizes[stem] = [image.width, image.height]

    io.open(OUT_JSON, "w", encoding="utf-8", newline="\n").write(
        json.dumps(sizes, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

    total = sum(os.path.getsize(os.path.join(OUT_IMG, f))
                for f in os.listdir(OUT_IMG))
    print("assets/img/relic: %d files, %.0f KB" % (len(sizes), total / 1024.0))
    for name in missing:
        print("  no picture anchored for %s" % name)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
