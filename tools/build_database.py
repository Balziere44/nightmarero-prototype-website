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
        name = game_name(clean(cells[0]))
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


# Names the sheets spell one way and the game spells another, found by
# checking every sheet row against the client's display names. The game's
# spelling wins: it is what the player reads in the item window and types into
# the search, and half of these were showing up twice on the site, once under
# each spelling. Corrected here rather than in the CSVs, which are refetched.
#
# Only unambiguous cases are listed. "Glacial Shield" has no client entry and
# is left alone rather than folded into the Gaia Shield it merely resembles.
GAME_SPELLING = {
    # gear
    "Bloody Knight Shield": "Bloody Knight's Shield",
    "Faceworm Queen's Leg": "Faceworm Queen Leg",
    "Glacier Manteau": "Glacial Manteau",
    "Glacier Muffler": "Glacial Muffler",
    "High Arcanist Robes": "High Arcanist Robe",
    "Iron Knuckles": "Iron Knuckle",
    "Legacy of Dragons": "Legacy of Dragon",
    "Operative's Scarf": "Operative Scarf",
    "Operative's Shoes": "Operative Shoes",
    "Operative's Suit": "Operative Suit",
    "Pariah's Cloth": "Pariah Cloth",
    # cards, which the site names after the monster
    "Cat O' Ninetails": "Cat O' Nine Tails",
    "Desert Wofl": "Desert Wolf",
    "Gran Papilia": "Grand Papilia",
    "Matrix Nanounit": "Matrix Nanonunit",
    "Muspellkoll": "Muspellskoll",
    "Peco Peco": "Pecopeco",
    "Peco Peco Egg": "Pecopeco Egg",
    "Pirate Skeleton": "Pirate Skel",
    "Skeleton Prisoner": "Skel Prisoner",
    "Skeleton Worker": "Skel Worker",
    "Worm Tail": "Wormtail",
}


def game_name(name):
    return GAME_SPELLING.get(name, name)


# Five of the 583 card rows are typed differently from the rest. Corrected
# here rather than in the CSV, because the CSV is refetched and would bring
# them back. The wiki's own card page spells all five the short way.
CARD_NAME_FIX = {
    "Geographer Card": "Geographer",
    "Ignis Fang Card": "Ignis Fang",
    "Santer Kloss Card": "Santer Kloss",
    "Yellow Pitaya Card": "Yellow Pitaya",
    "Violet PItaya": "Violet Pitaya",
}


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
        name = game_name(CARD_NAME_FIX.get(name, name))
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


# The MVP card sheet writes the slot out in words, with a typo or two.
MVP_CARD_SLOT = {
    "weapon": "weapon", "headgear": "headgear", "armor": "armor",
    "garment": "garment", "shoes": "shoes", "shield": "shield",
    "accessory": "accessory", "acessory": "accessory",
}


def parse_mvp_cards(path):
    """Boss cards. Same shape as an ordinary card, but they come from the MVP
    sheet and get their own category so the filter can single them out."""
    items = []
    for row in read(path):
        cells = (list(row) + [""] * 3)[:3]
        name = game_name(clean(cells[0]))
        if not name or name.lower() == "name":
            continue
        slot = MVP_CARD_SLOT.get(clean(cells[2]).lower(), "any")
        items.append({
            "name": name,
            "kind": "card",
            "slot": slot,
            "cat": "MVP Card",
            "effect": split_lines(cells[1]),
            "affix": "",
            "source": "mvp-card",
        })
    return items


def parse_relics(path):
    """Relic gear only exists in the sheet as tooltip screenshots, so it is
    transcribed into tools/data/relic-gear.json instead. Everything about the
    shape here matches ordinary gear so one search covers both."""
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except (IOError, ValueError):
        return []

    items = []
    for it in data.get("items", []):
        effect = list(it.get("mastery", [])) + list(it.get("effect", []))
        if it.get("classes"):
            effect.append("Usable by %s" % it["classes"])
        if it.get("map"):
            # so searching the map name finds the piece, the same way a
            # monster name finds what it drops
            effect.append("Found on %s" % it["map"])
        items.append({
            "name": it["name"],
            "kind": "gear",
            "slot": it["slot"],
            "cat": "Relic Gear",
            "slots": 0,
            "stat": it.get("stat", ""),
            "statLabel": ("ATK/MATK" if it["slot"] == "weapon" else "DEF/MDEF"),
            "effect": effect,
            "level": it.get("level", 0),
            # the map is the answer to "where do I get this", which is what
            # the field is for. The type is already the category.
            "drops": it.get("map", ""),
            "source": "relic",
        })
    return items


# What the entries transcribed from tooltips say where the sheets say a
# monster or a map. Nobody has written down where any of them drop yet.
UNKNOWN_WHERE = "Not confirmed yet, ask on Discord or in game"


def parse_tooltips(path):
    """tools/data/tooltip-items.json, typed out of client item tooltips.

    Same shape as the sheet rows once it is through here, so one search covers
    the lot. The tooltip is the game itself talking, so it carries things the
    sheets do not: which mastery gives which bonus, what the set combo does,
    and the class restriction. Those all land in the effect list, because that
    is the only field the cards and the modal print in full.
    """
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except (IOError, ValueError):
        return []

    items = []
    for it in data.get("items", []):
        effect = []
        if it.get("position"):
            effect.append(it["position"])
        effect.extend(it.get("mastery", []))
        effect.extend(it.get("effect", []))
        combo = it.get("combo") or {}
        if combo:
            effect.append("Set: %s" % combo["with"])
            effect.extend("Set bonus: %s" % line for line in combo["gives"])
        if it.get("classes"):
            effect.append("Usable by %s" % it["classes"])

        items.append({
            "name": it["name"],
            "kind": "gear",
            "slot": it["slot"],
            "cat": it["cat"],
            "slots": None,          # the tooltip never shows card slots
            "stat": it.get("stat", ""),
            "statLabel": ("ATK/MATK" if it["slot"] == "weapon"
                          else "DEF/MDEF"),
            "effect": effect,
            "level": it.get("level"),
            "drops": UNKNOWN_WHERE,
            "source": "unknown",
        })

    for it in data.get("cards", []):
        items.append({
            "name": it["name"],
            "kind": "card",
            "slot": it["slot"],
            "cat": "Card",
            "effect": list(it.get("effect", [])),
            "affix": "",
            "drops": UNKNOWN_WHERE,
            "source": "unknown",
        })

    return items


def client_effect(got):
    lines = list(got.get("mastery", [])) + list(got.get("effect", []))
    if got.get("classes"):
        lines.append("Usable by %s" % got["classes"])
    return lines


def apply_client(items, path):
    """tools/data/client-items.json, read straight out of the game client by
    fetch_client_items.py, and therefore the last word.

    It does two jobs. For an item the site already lists it replaces the stats
    and the effects, keeping the drop location, which is the one thing a
    tooltip never says. And it adds the gear that is in the game but on no
    sheet at all, which is most of what the client turned out to hold.

    Everything in that file is an entry this server wrote: fetch_client_items.py
    drops the ones that are word for word the community translation the client
    ships, because those name thousands of items no server enables. So an item
    arriving from here is an item that exists.
    """
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except (IOError, ValueError):
        print("  sem client-items.json, seguindo só com as planilhas")
        return items

    ours = {}
    for it in items:
        ours.setdefault(it["name"].lower(), it)

    fixed = added = 0
    empty = []
    for got in data.get("items", []):
        if got.get("new"):
            already = ours.get(got["name"].lower())
            kind_of = got.get("kind") or ("card" if got["cat"] == "Card"
                                          else "gear")
            # a card is named after its monster, and the monster often drops
            # loot of the same name: the card Poison Spore and the mushroom
            # Poison Spore are both real and both wanted
            if already is not None and not (already["kind"] == "card"
                                            and kind_of == "material"):
                continue
            kind = got.get("kind") or ("card" if got["cat"] == "Card"
                                       else "gear")
            card = kind == "card"
            material = kind == "material"
            # for loot and materials the description IS the information, and
            # the reader files a plain paragraph as flavour, so take it back
            effect = client_effect(got)
            if material and not effect and got.get("flavour"):
                effect = [got["flavour"]]
            items.append({
                "name": got["name"],
                "kind": kind,
                "slot": got["slot"],
                "cat": got["cat"],
                # a card has no card slots of its own, and "0 slots" on the
                # result card would just be noise
                "slots": None if card or material else got.get("slots"),
                "stat": got.get("stat", ""),
                "statLabel": got.get("statLabel", ""),
                "effect": effect,
                "level": got.get("level"),
                "drops": "" if material else UNKNOWN_WHERE,
                "source": "unknown",
            })
            if card:
                items[-1]["affix"] = ""
            added += 1
            continue

        old = ours.get(got.get("ourName", got["name"]).lower())
        if old is None:
            continue
        effect = client_effect(got)
        if not effect and old.get("effect"):
            # a tooltip that parsed down to nothing is a bug in the reader,
            # not an item without effects, so leave the sheet alone and say so
            empty.append(old["name"])
            continue
        effect += [line for line in old.get("effect", [])
                   if line.startswith("Found on ")]
        old["effect"] = effect
        if got.get("stat"):
            old["stat"] = got["stat"]
            old["statLabel"] = got["statLabel"]
        if got.get("level") is not None:
            old["level"] = got["level"]
        if (got.get("slots") is not None and old.get("slots") is None
                and old["kind"] != "card"):
            old["slots"] = got["slots"]
        fixed += 1

    print("  %-32s %4d corrigidos, %d novos"
          % ("client-items.json", fixed, added))
    if empty:
        print("  tooltip vazio, planilha mantida (%d): %s"
              % (len(empty), ", ".join(sorted(empty))))
    return items


def apply_recipes(items, path):
    """tools/data/recipes.json: what a material is for, and where the wiki says
    it comes from.

    "Which items do the quests use, and who drops those" is the question this
    answers. A material that a recipe asks for says so on its own entry, so the
    answer is where a player is already looking, and searching the potion's name
    turns up its whole shopping list.
    """
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except (IOError, ValueError):
        return items

    # a recipe asks for the loot, never for the card that shares its name
    ours = {}
    for it in items:
        key = it["name"].lower()
        if key not in ours or (ours[key]["kind"] == "card"
                               and it["kind"] == "material"):
            ours[key] = it

    used, placed, absent = 0, 0, []
    for group in data.get("groups", []):
        for recipe in group.get("makes", []):
            for need in recipe.get("needs", []):
                if "item" not in need:
                    continue
                it = ours.get(need["item"].lower())
                if it is None:
                    absent.append(need["item"])
                    continue
                line = "Used to craft: %s" % recipe["item"]
                if line not in it["effect"]:
                    it["effect"].append(line)
                    used += 1
        for hint in group.get("from", []):
            it = ours.get(hint["item"].lower())
            if it is None or (it.get("drops") and it["drops"] != UNKNOWN_WHERE):
                continue
            it["drops"] = hint["from"]
            it["source"] = "wiki"
            placed += 1

    print("  %-32s %4d materiais marcados, %d com origem do wiki"
          % ("recipes.json", used, placed))
    if absent:
        print("  receita pede o que a database não tem: %s"
              % ", ".join(sorted(set(absent))))
    return items


def apply_containers(items):
    """A chest that lists what it gives is telling you where those come from.

    The Nightmare and Abyss weapon families are only ever bought out of a
    chest, so without this they sit under "Location unknown" while the answer
    is written on the chest.
    """
    named = {}
    for it in items:
        named.setdefault(it["name"].lower(), it)

    filled = 0
    for box in items:
        if box.get("cat") != "Container":
            continue
        for line in box.get("effect", []):
            line = re.sub(r"^\d+\s+", "", line.strip()).strip(".,")
            it = named.get(line.lower())
            if it is None or it is box:
                continue
            if it.get("drops") and it["drops"] != UNKNOWN_WHERE:
                continue
            it["drops"] = box["name"]
            it["source"] = "client"
            filled += 1

    print("  %-32s %4d vindos de um baú" % ("(baús do cliente)", filled))
    return items


# "A tail cut from a Green Pitaya" names the monster. "An idol carved in a
# shape reminiscent of a Chimera" does not, so the shapes of the sentence have
# to be read rather than the names counted.
TAKEN_FROM = (
    r"(?:taken|cut|peeled|harvested|plucked|torn|ripped|scraped|pulled|"
    r"salvaged|recovered|collected|stripped|extracted|severed|sliced|snapped|"
    r"pried|gathered|scavenged|skinned|sheared)\s+(?:from|off|out of)",
    r"(?:shed|dropped|left|worn|wielded|carried|issued|produced|possessed)"
    r"\s+by",
    r"belong(?:ing|ed)\s+to",
)
NOT_FROM = re.compile(
    r"reminiscent of|in the shape of|shaped like|resembling|looks like|"
    r"said to (?:be|have)|rumou?red|reminds", re.I)


def apply_flavour(items):
    """Where the item's own description names the monster it came off."""
    monsters = sorted((it["name"] for it in items if it["kind"] == "card"),
                      key=len, reverse=True)
    # the server's own word for its content, not a monster reference
    monsters = [m for m in monsters if len(m) >= 4 and m != "Nightmare"]
    alt = "|".join(re.escape(m) for m in monsters)
    lead = r"(?:the\s+|a\s+|an\s+|one of the\s+|those\s+)?"
    remains = r"(?:remains of\s+" + lead + r")?"
    patterns = [re.compile(verb + r"\s+" + lead + remains + "(" + alt + r")(?![A-Za-z])")
                for verb in TAKEN_FROM]

    filled = 0
    for it in items:
        if it["kind"] != "material":
            continue
        if it.get("drops") and it["drops"] != UNKNOWN_WHERE:
            continue
        text = " ".join(it.get("effect", []))
        for pattern in patterns:
            found = pattern.search(text)
            if not found:
                continue
            if NOT_FROM.search(text[max(0, found.start() - 60):found.end()]):
                continue
            it["drops"] = found.group(1)
            it["source"] = "client"
            filled += 1
            break

    print("  %-32s %4d ditos pela própria descrição"
          % ("(descrição do item)", filled))
    return items


def apply_who_drops(items, path):
    """tools/data/who-drops.json: where an item comes from, for the items no
    sheet covers.

    The game has no working @whodrops and the client never says where anything
    drops, so for loot and materials the only answer that exists is the one a
    player gave in the Discord. Each line is credited in the JSON. A drop we
    already had always wins, and the placeholder counts as not having one.
    """
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except (IOError, ValueError):
        return items

    ours = {}
    for it in items:
        ours.setdefault(it["name"].lower(), it)

    filled, absent = 0, []
    for said in data.get("items", []):
        it = ours.get(said["name"].lower())
        if it is None:
            absent.append(said["name"])
            continue
        if it.get("drops") and it["drops"] != UNKNOWN_WHERE:
            continue
        it["drops"] = said["from"]
        # say where the answer came from: a player in the Discord, not a sheet
        it["source"] = "discord"
        filled += 1

    print("  %-32s %4d com origem do Discord" % ("who-drops.json", filled))
    if absent:
        print("  não estão na database: %s" % ", ".join(absent))
    return items


def apply_tooltips(items):
    """A tooltip is the game itself talking, so it outranks the sheets.

    Where a name is in both, the tooltip's stats and effects replace the
    sheet's and everything the tooltip cannot know is kept: the drop location,
    the card slots, the affix, and which sheet the row came from, so the item
    keeps its place in the filters. An empty stat in the tooltip file means a
    mouse cursor was over the number in the screenshot, and the sheet value is
    left alone rather than replaced by a guess.
    """
    sheet = {}
    for it in items:
        if it["source"] != "unknown":
            sheet.setdefault(it["name"].lower(), it)

    kept, fixed = [], []
    for it in items:
        if it["source"] != "unknown":
            kept.append(it)
            continue
        old = sheet.get(it["name"].lower())
        if old is None:
            kept.append(it)
            continue

        effect = list(it["effect"])
        # the map a relic is found on is ours, not the tooltip's
        effect += [line for line in old.get("effect", [])
                   if line.startswith("Found on ")]
        old["effect"] = effect
        if it.get("stat"):
            old["stat"] = it["stat"]
            old["statLabel"] = it["statLabel"]
        if it.get("level") is not None:
            old["level"] = it["level"]
        fixed.append(it["name"])

    if fixed:
        print("  %d corrigidos pelo tooltip: %s"
              % (len(fixed), ", ".join(sorted(fixed))))
    return kept


# Shadow gear equips in a second equipment window, so a Shadow Armor and an
# ordinary Armor are worn at the same time and need slots of their own.
SHADOW_PIECES = {
    "armor": "shadow-armor",
    "gloves": "shadow-gloves",
    "shoes": "shadow-shoes",
    "pendant": "shadow-pendant",
}
TIER_RE = re.compile(r"^Tier\s+(\d+)$", re.I)


def parse_shadow(path):
    """The Shadow Gear tab, which is laid out as sets rather than as a table.

    A tier heading, then for each set a name on its own row, its four pieces,
    and one or two set bonus rows that apply to all four. The tail of the tab
    repeats an unfinished set over and over, so a set name already seen in the
    same tier is skipped.
    """
    items, seen = [], set()
    tier, name, current, skip = 0, None, [], False

    for row in read(path):
        if not row or not any(c.strip() for c in row):
            continue
        first = clean(row[0])
        rest = clean(" ".join(row[1:]))

        found = TIER_RE.match(first)
        if found:
            tier, name, current, skip = int(found.group(1)), None, [], False
            continue

        if not rest:                       # a set name sits on its own row
            name, current = first, []
            skip = (tier, name) in seen
            seen.add((tier, name))
            continue
        if name is None or skip:
            continue

        if first.lower().startswith("set bonus"):
            which = first.split(":", 1)[1].strip() if ":" in first else ""
            label = "Set bonus (%s)" % which if which else "Set bonus"
            for it in current:
                it["effect"].append("%s: %s" % (label, rest))
            continue

        slot = SHADOW_PIECES.get(first.lower())
        if not slot:
            continue

        item = {
            "name": "%s Shadow %s" % (name, first),
            "kind": "gear",
            "slot": slot,
            "cat": "Shadow Gear",
            "slots": None,
            "stat": str(tier),
            "statLabel": "Tier",
            "effect": split_lines(rest),
            "level": None,
            "drops": "",
            "source": "shadow",
        }
        items.append(item)
        current.append(item)

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

    shadow = os.path.join(SRC, "gear__shadow-gear.csv")
    if os.path.exists(shadow):
        got = parse_shadow(shadow)
        items.extend(got)
        print("  %-32s %4d sombras" % ("gear__shadow-gear.csv", len(got)))

    relics = parse_relics(os.path.join(SRC, "relic-gear.json"))
    items.extend(relics)
    print("  %-32s %4d relíquias" % ("relic-gear.json", len(relics)))

    tooltips = parse_tooltips(os.path.join(SRC, "tooltip-items.json"))
    items.extend(tooltips)
    print("  %-32s %4d de tooltip" % ("tooltip-items.json", len(tooltips)))

    mvp_cards = os.path.join(SRC, "mvp-cards.csv")
    if os.path.exists(mvp_cards):
        got = parse_mvp_cards(mvp_cards)
        items.extend(got)
        print("  %-32s %4d cartas de MVP" % ("mvp-cards.csv", len(got)))
    else:
        print("  faltando: mvp-cards.csv")

    # hand typed screenshots first, then the client itself over the top of
    # everything, because that is the order of how much they can be trusted
    items = apply_tooltips(items)
    items = apply_client(items, os.path.join(SRC, "client-items.json"))
    # a credited answer names the floor and the monster; the wiki note behind
    # a recipe usually names only the monster, so it fills what is left
    items = apply_who_drops(items, os.path.join(SRC, "who-drops.json"))
    items = apply_recipes(items, os.path.join(SRC, "recipes.json"))
    # last, because both only fill a blank: a player's answer in the Discord
    # beats what the description implies
    items = apply_containers(items)
    items = apply_flavour(items)

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
