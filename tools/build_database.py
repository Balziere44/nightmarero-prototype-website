#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turns the published Gear and Card reference sheets into assets/data/items.json,
which is what database.html searches.

    python tools/fetch_sheets.py      # refresh tools/data/*.csv from Google
    python tools/build_database.py    # rebuild the JSON the site reads

The CSVs keep the layout the sheets use: a header row, then rows where only
the first column is filled marking a category, then the items under it.
"""

import csv
import io
import json
import os
import re
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from status_codex import STATUS, TERM_CLASS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "data")
OUT = os.path.join(ROOT, "assets", "data", "items.json")

# Heading in the "not weapons" sheets -> the equip slot it describes.
SLOT_FROM_HEADING = {
    "ARMORS": "armor",
    "GARMENTS": "garment",
    "SHOES": "shoes",
    "HEADGEARS": "headgear",
    "ACCESSORIES": "accessory",
    "SHIELDS": "shield",
}

# Card sheet file suffix -> the slot that card goes in.
CARD_SLOT = {
    "weapon": "weapon", "headgear": "headgear", "armor": "armor",
    "garment": "garment", "shoes": "shoes", "shield": "shield",
    "accessory": "accessory", "multiple": "any",
}


def split_lines(text):
    """One stat per line. Splits on sentence breaks only, so a decimal like
    0.5 (no space after the dot) is never cut in half."""
    text = clean(text)
    if not text:
        return []
    parts = [p.strip(" .") for p in re.split(r"\.\s+", text)]
    return [p for p in parts if p]


def clean(text):
    """Collapse whitespace and drop the punctuation we do not want on site."""
    text = (text or "").replace("—", ", ").replace("–", " to ")
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip()


# The two gear docs spell a few headings differently. Unify them so the
# category filter does not show near-duplicates.
CATEGORY_ALIASES = {
    "Gatlings": "Gatling Guns",
    "Instruments": "Instruments & Whips",
    "Whips": "Instruments & Whips",
    "Instruments/Whips": "Instruments & Whips",
}


def titlecase(heading):
    """ONE-HANDED SWORDS -> One-Handed Swords, without wrecking oddities."""
    heading = clean(heading)
    # a couple of headings carry a trailing note in brackets or after spaces
    heading = re.split(r"\s{2,}|\(", heading)[0].strip()
    if heading.isupper():
        parts = re.split(r"([-/ ])", heading.lower())
        heading = "".join(p if p in "-/ " else p.capitalize() for p in parts)
    return CATEGORY_ALIASES.get(heading, heading)


def as_int(value):
    m = re.search(r"\d+", value or "")
    return int(m.group(0)) if m else None


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return [r for r in csv.reader(fh)]


def is_category(row):
    return bool(row) and row[0].strip() and not any(c.strip() for c in row[1:])


def parse_gear(path, source, kind_of_sheet):
    """kind_of_sheet is 'weapons' or 'other'."""
    items, category, slot = [], None, None

    for row in read(path):
        if not row or not any(c.strip() for c in row):
            continue
        first = row[0].strip()
        if first.lower() == "name":
            continue
        if is_category(row):
            category = titlecase(first)
            slot = ("weapon" if kind_of_sheet == "weapons"
                    else SLOT_FROM_HEADING.get(first.strip().upper(), "other"))
            continue
        if category is None:
            continue

        cells = (row + [""] * 6)[:6]
        name = clean(cells[0])
        if not name:
            continue

        # accessories use a literal X where a defence value would go
        stat = clean(cells[2])
        if stat.upper() in ("X", "X/X", "-"):
            stat = ""

        items.append({
            "name": name,
            "kind": "gear",
            "slot": slot,
            "cat": category,
            "slots": as_int(cells[1]),
            "stat": stat,
            "statLabel": "ATK/MATK" if kind_of_sheet == "weapons" else "DEF/MDEF",
            "effect": split_lines(cells[3]),
            "level": as_int(cells[4]),
            "drops": clean(cells[5]),
            "source": source,
        })
    return items


def parse_cards(path, slot):
    items = []
    for row in read(path):
        if not row or not any(c.strip() for c in row):
            continue
        first = row[0].strip()
        if first.lower() == "name" or is_category(row):
            continue
        cells = (row + [""] * 4)[:4]
        name = clean(cells[0])
        if not name:
            continue
        items.append({
            "name": name,
            "kind": "card",
            "slot": slot,
            "cat": "Card",
            "effect": split_lines(cells[1]),
            "affix": clean(cells[2]),
            "source": "card",
        })
    return items


def main():
    items = []

    gear_sheets = [
        ("gear__core-weapons.csv", "core", "weapons"),
        ("gear__core-not-weapons.csv", "core", "other"),
        ("gear__mvp-weapons.csv", "mvp", "weapons"),
        ("gear__mvp-not-weapons.csv", "mvp", "other"),
    ]
    for fname, source, kind in gear_sheets:
        path = os.path.join(SRC, fname)
        if not os.path.exists(path):
            print("  faltando: %s" % fname)
            continue
        got = parse_gear(path, source, kind)
        items.extend(got)
        print("  %-32s %4d itens" % (fname, len(got)))

    for suffix, slot in CARD_SLOT.items():
        fname = "card__%s.csv" % suffix
        path = os.path.join(SRC, fname)
        if not os.path.exists(path):
            print("  faltando: %s" % fname)
            continue
        got = parse_cards(path, slot)
        items.extend(got)
        print("  %-32s %4d cartas" % (fname, len(got)))

    # de-duplicate on name + slot + source, keeping the first
    seen, unique = set(), []
    for it in items:
        key = (it["name"].lower(), it["slot"], it["source"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(it)

    unique.sort(key=lambda i: (i["kind"], i["cat"], i["name"].lower()))

    payload = {
        "generated": datetime.date.today().isoformat(),
        "count": len(unique),
        "slots": sorted(set(i["slot"] for i in unique)),
        "categories": sorted(set(i["cat"] for i in unique)),
        # term -> codex family, so database.js highlights the same words the
        # class pages do without keeping a second copy of the list
        "statusTerms": TERM_CLASS,
        "items": unique,
    }

    if not os.path.isdir(os.path.dirname(OUT)):
        os.makedirs(os.path.dirname(OUT))
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

    print("\n%d entradas -> assets/data/items.json (%.0f KB)"
          % (len(unique), os.path.getsize(OUT) / 1024.0))
    print("  equipamentos: %d" % sum(1 for i in unique if i["kind"] == "gear"))
    print("  cartas:       %d" % sum(1 for i in unique if i["kind"] == "card"))
    print("  categorias:   %d" % len(payload["categories"]))


if __name__ == "__main__":
    main()
