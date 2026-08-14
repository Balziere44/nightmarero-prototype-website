#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pulls the pictures out of the MVP spreadsheet.

The sheet carries three kinds of image that the CSV export cannot see: a
minimap showing where the altar is, the boss sprite, and a screenshot of the
drop table. They are floating images, so the only way to find out which cell
each one belongs to is the xlsx export, where every drawing carries its anchor
row and column.

    python tools/fetch_mvp_art.py

Writes assets/img/mvp/*.webp and tools/data/mvp-art.json, which lists each
picture with the sheet, row and column it was anchored to. build_mvps.py uses
those coordinates to attach the pictures to the right boss.
"""

import io
import json
import os
import re
import sys
import urllib.request
import zipfile

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_IMG = os.path.join(ROOT, "assets", "img", "mvp")
OUT_JSON = os.path.join(ROOT, "tools", "data", "mvp-art.json")

URL = "https://docs.google.com/spreadsheets/d/%s/export?format=xlsx"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NightmareRO-site-build/1.0"

# Worksheet order in each workbook, which is also the tab order. The names
# match the CSV stems that fetch_mvps.py writes.
BOOKS = [
    ("1ojSow2JMglSDcvXii3Sppoa9Nx9mWAcVtC3c_OzApzk",
     ["summon-items", "locations", "nightmare", "cards", "relic-gears",
      "spoiler-quest"]),
    ("1Nr10_X30Okn5MgPTZVSpoSGuy50g7VdRvyOm1p9IRSk",
     ["quest-index", "quest-relic-gear-options", "quest-amatsu",
      "quest-true-hero-shadow-gloves", "quest-fallen-hero",
      "quest-niflheim-challenge", "quest-kiel-challenge",
      "quest-thor-challenge", "quest-black-ops", "quest-celine-kimi",
      "quest-endless-desert", "quest-spare-12", "quest-spare-14",
      "quest-spare-1", "quest-lighthalzen-entrance"]),
]

ANCHOR_RE = re.compile(
    r"<xdr:from><xdr:col>(\d+)</xdr:col>.*?<xdr:row>(\d+)</xdr:row>.*?"
    r'r:embed="(rId\d+)"', re.S)
REL_RE = re.compile(r'Id="(rId\d+)"[^>]*Target="\.\./media/([^"]+)"')
SHEET_DRAWING_RE = re.compile(r'Target="\.\./(drawings/drawing\d+\.xml)"')

# Anything smaller than this is a spacer or a stray icon, not content.
MIN_PIXELS = 40

# Screenshots come out of the sheet at full game resolution. Nothing on the
# site is shown wider than the content column, so cap them.
MAX_SIDE = 900

# Leftover tabs in the quest workbook, named Pagina1 and so on. They hold
# images that no longer belong to any quest.
SKIP_TABS = ("quest-spare-1", "quest-spare-12", "quest-spare-14",
             # the spoiler quest tab duplicates pictures the per quest tabs
             # already carry, and only its text is used
             "spoiler-quest",
             # relic gear is mostly tooltip screenshots, transcribed into
             # tools/data/relic-gear.json instead. The two pictures that are
             # worth keeping, the minimap and the cost strip, have to be tied
             # to a named piece rather than to a cell, so fetch_relic_art.py
             # pulls those on its own
             "relic-gears")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def kind_of(width, height):
    """What the picture is, guessed from its shape. Drop tables are wide
    strips of text, sprites and minimaps are roughly square."""
    ratio = float(width) / height
    if ratio > 2.4:
        return "drops"
    if width > 200 or height > 200:
        return "wide"
    return "tile"


def read_book(sheet_id, tabs, out, kept):
    req = urllib.request.Request(URL % sheet_id, headers={"User-Agent": UA})
    blob = urllib.request.urlopen(req, timeout=180).read()
    print("workbook %s...: %.1f MB" % (sheet_id[:8], len(blob) / 1048576.0))
    book = zipfile.ZipFile(io.BytesIO(blob))

    for index, tab in enumerate(tabs, start=1):
        if tab in SKIP_TABS:
            continue
        try:
            rels = book.read("xl/worksheets/_rels/sheet%d.xml.rels" % index)
        except KeyError:
            continue
        found = SHEET_DRAWING_RE.search(rels.decode("utf-8"))
        if not found:
            continue

        drawing = "xl/" + found.group(1)
        body = book.read(drawing).decode("utf-8")
        rel_path = drawing.replace("drawings/", "drawings/_rels/") + ".rels"
        try:
            media = dict(REL_RE.findall(book.read(rel_path).decode("utf-8")))
        except KeyError:
            continue                     # a drawing sheet with no pictures

        for col, row, rid in ANCHOR_RE.findall(body):
            name = media.get(rid)
            if not name:
                continue
            raw = book.read("xl/media/" + name)
            image = Image.open(io.BytesIO(raw))
            if image.width < MIN_PIXELS or image.height < MIN_PIXELS:
                continue

            kind = kind_of(image.width, image.height)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA")
            if max(image.size) > MAX_SIDE:
                image.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)

            stem = "%s-%s" % (tab, os.path.splitext(name)[0])
            if stem not in kept:
                image.save(os.path.join(OUT_IMG, stem + ".webp"),
                           "WEBP", quality=82, method=6)
                kept.add(stem)

            out.append({
                "sheet": tab,
                "row": int(row),
                "col": int(col),
                "file": "assets/img/mvp/%s.webp" % stem,
                "w": image.width,
                "h": image.height,
                "kind": kind,
            })


def main():
    if not os.path.isdir(OUT_IMG):
        os.makedirs(OUT_IMG)

    out, kept = [], set()
    for sheet_id, tabs in BOOKS:
        read_book(sheet_id, tabs, out, kept)

    out.sort(key=lambda a: (a["sheet"], a["row"], a["col"]))
    io.open(OUT_JSON, "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, ensure_ascii=False, indent=1))

    total = sum(os.path.getsize(os.path.join(OUT_IMG, f))
                for f in os.listdir(OUT_IMG))
    print("assets/img/mvp: %d files, %.1f MB" % (len(kept), total / 1048576.0))
    print("tools/data/mvp-art.json: %d anchors" % len(out))
    for tab in sorted(set(a["sheet"] for a in out)):
        rows = [a for a in out if a["sheet"] == tab]
        kinds = {}
        for a in rows:
            kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1
        print("  %-30s %s" % (tab, kinds))


if __name__ == "__main__":
    sys.exit(main())
