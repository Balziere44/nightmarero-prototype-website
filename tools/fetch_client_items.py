#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reads the item descriptions out of the game client and writes
tools/data/client-items.json, which build_database.py then trusts over every
sheet.

    python tools/fetch_client_items.py ["E:/NightmareRO (Release)"]

The client keeps its English tooltips in SystemEN/LuaFiles514/itemInfo.lua, a
plain Lua table the patcher rewrites on every patch. That file is the same text
the item description window shows in game, which makes it the last word: the
reference sheets are typed by hand and lag behind, a screenshot of a tooltip
does not, and this is where the screenshot's text comes from.

Only the items the site already lists are kept, so the committed JSON stays
about the size of the database rather than the size of the client. Everything
that looks like server made gear and is *not* on the site is reported instead,
which is how the next batch of new items gets noticed.

Nothing here needs the game running, but it does need the client installed, so
the JSON is committed and the rest of the build works without it.
"""

import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_database as db

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", "data", "client-items.json")

DEFAULT_CLIENTS = (
    r"E:/NightmareRO (Release)",
    r"C:/NightmareRO (Release)",
)
INSIDE = os.path.join("SystemEN", "LuaFiles514", "itemInfo.lua")

ENTRY = re.compile(r"^\t\[(\d+)\]\s*=\s*\{")
STRING = r'"((?:[^"\\]|\\.)*)"'
NAME = re.compile(r'(?<!un)identifiedDisplayName\s*=\s*' + STRING)
SLOTS = re.compile(r"slotCount\s*=\s*(\d+)")
ONE_LINE = re.compile(r'^\s*' + STRING + r',?\s*$')

# ^FF0000 turns a word red in the client. The site colours the same words
# itself from the status codex, so the codes go.
COLOUR = re.compile(r"\^[0-9a-fA-F]{6}")
RULE = re.compile(r"^_{3,}$")

# the first line of most tooltips, and never useful
NOISE = ("Can be identified by using a Magnifier.",)

LABEL = re.compile(r"^([A-Z][A-Za-z /]*):\s*(.*)$")

# label in the tooltip -> what we do with it
STAT_LABELS = ("Attack", "Magic Attack", "Defense", "Magic Defense")


def find_client(argv):
    if len(argv) > 1:
        roots = [argv[1]]
    else:
        roots = list(DEFAULT_CLIENTS)
    for root in roots:
        path = os.path.join(root, INSIDE)
        if os.path.exists(path):
            return path
    return None


def unescape(text):
    return text.replace('\\"', '"').replace("\\\\", "\\")


def clean(text):
    text = COLOUR.sub("", unescape(text))
    return re.sub(r"\s+", " ", text).strip()


def read_client(path):
    """id -> {name, slots, lines}. The file is 16 MB of Lua and a third of it
    is Korean sprite names in a codepage we do not care about, so it is read
    with replacement and only the ASCII fields are used."""
    items, cur, in_desc = {}, None, False

    for raw in io.open(path, encoding="utf-8", errors="replace"):
        found = ENTRY.match(raw)
        if found:
            cur = {"id": int(found.group(1)), "name": "", "slots": None,
                   "lines": []}
            items[cur["id"]] = cur
            in_desc = False
            continue
        if cur is None:
            continue

        if "identifiedDescriptionName" in raw:
            in_desc = True
            inline = re.search(r"\{(.*)\}", raw)
            if inline:
                cur["lines"].extend(re.findall(STRING, inline.group(1)))
                in_desc = False
            continue
        if in_desc:
            if "}" in raw:
                in_desc = False
            got = ONE_LINE.match(raw)
            if got:
                cur["lines"].append(got.group(1))
            continue

        got = NAME.search(raw)
        if got:
            cur["name"] = unescape(got.group(1))
            continue
        got = SLOTS.search(raw)
        if got:
            cur["slots"] = int(got.group(1))

    return items


def blocks(lines):
    """The tooltip is written as blocks divided by a rule of underscores."""
    out, current = [], []
    for line in lines:
        text = clean(line)
        if not text:
            continue
        if RULE.match(text):
            if current:
                out.append(current)
            current = []
            continue
        if text in NOISE:
            continue
        current.append(text)
    if current:
        out.append(current)
    return out


# How an effect line starts when it hands out no number at all. Without this
# list "Enables use of Coluceo Heal at the learned level of Grace Heal" reads
# like a sentence and would be mistaken for flavour text.
EFFECT_OPENERS = (
    "add", "adds", "allow", "allows", "cannot", "can't", "casting", "chance",
    "convert", "converts", "enable", "enables", "gain", "gains", "grant",
    "grants", "if", "ignore", "ignores", "immune", "increase", "increases",
    "physical", "magical", "recover", "recovers", "reduce", "reduces",
    "restore", "restores", "when", "while", "your",
)


def is_prose(block):
    """The flavour paragraph, which is kept out of the effect list the same way
    the relic transcription keeps it out.

    Flavour is the one block that hands out no numbers, does not open like an
    effect, and is written as finished sentences. Anything doubtful stays an
    effect: an extra line on a card is a blemish, a lost effect is a lie.
    """
    joined = " ".join(block)
    if len(joined) < 60 or re.search(r"\d", joined):
        return False
    if joined.split(" ")[0].strip(",.").lower() in EFFECT_OPENERS:
        return False
    return joined.endswith((".", "!", "?"))


def describe(entry):
    """Turn one client tooltip into the fields the database wants."""
    out = {
        "id": entry["id"], "name": entry["name"], "slots": entry["slots"],
        "type": "", "stat": "", "statLabel": "", "level": None, "weight": None,
        "classes": "", "compound": "", "mastery": [], "effect": [],
        "flavour": "",
    }
    stats, mastery_type = {}, None

    for block in blocks(entry["lines"]):
        if is_prose(block) and not out["flavour"]:
            out["flavour"] = " ".join(block)
            continue

        header = ""
        for line in block:
            found = LABEL.match(line)
            label = found.group(1) if found else ""
            value = found.group(2).strip() if found else ""

            if label == "Type":
                out["type"] = value
                continue
            if label in STAT_LABELS:
                stats[label] = value
                continue
            if label == "Mastery Type":
                mastery_type = value
                continue
            if label == "Mastery Bonus":
                out["mastery"].append(
                    "%s mastery: %s" % (mastery_type or "Weapon", value))
                continue
            if label == "Compound on":
                out["compound"] = value
                continue
            if label == "Weight":
                out["weight"] = db.as_int(value)
                continue
            if label == "Requirement":
                out["level"] = db.as_int(value)
                continue
            if label in ("Jobs", "Job", "Class", "Classes"):
                out["classes"] = value
                continue

            # "Combo: Novice Hat + Breastplate + Manteau" names the set, and
            # the lines under it are what wearing all of it gives, so it heads
            # them rather than standing on its own
            if label == "Combo":
                header = "Combo (%s)" % value
                continue

            # a level requirement can arrive as its own pair of lines
            if re.match(r"^Level \d+$", line) and out["level"] is None:
                out["level"] = db.as_int(line)
                continue
            if re.match(r"^[A-Z][A-Za-z' ]+ Classes$", line):
                out["classes"] = line
                continue

            # "For each Refine:" and friends head a block; fold the heading
            # into each line under it so one bullet reads on its own
            if line.endswith(":"):
                header = line.rstrip(":")
                continue
            out["effect"].append("%s: %s" % (header, line) if header else line)

    def number(text):
        """The client pads with zeros: Defense: 00. Show 0."""
        got = db.as_int(text)
        return "0" if got is None else str(got)

    if "Attack" in stats:
        out["stat"] = "%s/%s" % (number(stats.get("Attack", "")),
                                 number(stats.get("Magic Attack", "")))
        out["statLabel"] = "ATK/MATK"
    elif "Defense" in stats:
        out["stat"] = "%s/%s" % (number(stats.get("Defense", "")),
                                 number(stats.get("Magic Defense", "")))
        out["statLabel"] = "DEF/MDEF"

    return out


# A tooltip written by this server rather than by Gravity: the custom stat
# vocabulary. Used only to decide what is worth reporting as missing.
CUSTOM = re.compile(
    r"Mastery Bonus|Potency|Exuvic Blessing|Breach|Per Refine|per Refine|"
    r"Relic |Reputation")

# The client's Type line -> the category the sheets use. Needed for more than
# tidiness: a display name is not unique in the client, so this is how the
# right entry gets picked out of several. Mysteltainn is both a sword and a
# card, and RO has three different Falchions.
TYPE_CAT = {
    "dagger": "Daggers", "sword": "One-Handed Swords",
    "one-handed sword": "One-Handed Swords",
    "two-handed sword": "Two-Handed Swords",
    "axe": "One-Handed Axes", "one-handed axe": "One-Handed Axes",
    "two-handed axe": "Two-Handed Axes",
    "one-handed spear": "One-Handed Spears", "spear": "One-Handed Spears",
    "two-handed spear": "Two-Handed Spears",
    "mace": "Maces", "katar": "Katars", "knuckle": "Fists",
    "bow": "Bows", "staff": "Staffs", "one-handed staff": "Staffs",
    "two-handed staff": "Staffs", "book": "Books", "soul": "Souls",
    "instrument": "Instruments & Whips",
    "musical instrument": "Instruments & Whips",
    "whip": "Instruments & Whips", "revolver": "Revolvers", "rifle": "Rifles",
    "shotgun": "Shotguns", "gatling gun": "Gatling Guns",
    "grenade launcher": "Grenade Launchers",
    "huuma shuriken": "Huuma Shurikens",
    "armor": "Armors", "garment": "Garments", "shoes": "Shoes",
    "shield": "Shields", "accessory": "Accessories",
}


# The client's Type line for the things that are not worn: loot, materials and
# the herbs. These are the items players hunt and cannot look up anywhere, so
# they belong in the database even though they have no stats. Cosmetics, pets,
# eggs, ammunition, scrolls, runes and enchant stones are deliberately left
# out: nobody asks who drops a costume.
ETC_CAT = {
    "collectible": "Loot",
    "relic": "Relic material",
    "quest": "Quest item",
    "crafting ingredient": "Crafting ingredient",
    "cooking ingredient": "Cooking ingredient",
    "forging material": "Forging material",
    "refining material": "Refining material",
    "skill catalyst": "Skill catalyst",
    "skill necessity": "Skill catalyst",
    "restorative": "Restorative",
    "trophy": "Trophy",
    "valuable": "Valuable",
    "essential": "Essential",
    "artifact": "Artifact",
}


def etc_cat(kind):
    return ETC_CAT.get(kind.strip().lower(), "")


def client_cat(kind):
    """Category for a client Type line, or "" when it says nothing useful."""
    kind = kind.strip().lower()
    if not kind:
        return ""
    if kind.startswith("relic "):
        return "Relic Gear"
    if kind.startswith("shadow "):
        return "Shadow Gear"
    if kind.startswith("headgear"):
        return "Headgears"
    if kind == "card":
        return "Card"
    return TYPE_CAT.get(kind, "")


CAT_SLOT = {
    "Armors": "armor", "Garments": "garment", "Shoes": "shoes",
    "Shields": "shield", "Headgears": "headgear", "Accessories": "accessory",
}
SHADOW_SLOT = {
    "shadow armor": "shadow-armor", "shadow gloves": "shadow-gloves",
    "shadow shoes": "shadow-shoes", "shadow accessory": "shadow-pendant",
    "shadow pendant": "shadow-pendant",
}
COMPOUND_SLOT = {
    "weapon": "weapon", "armor": "armor", "garment": "garment",
    "shoes": "shoes", "shield": "shield", "headgear": "headgear",
    "accessory": "accessory",
}


def slot_for(got):
    """Which equipment slot a client entry belongs in."""
    kind = got["type"].strip().lower()
    cat = client_cat(got["type"])
    if cat == "Card":
        where = got["compound"].strip().lower()
        return COMPOUND_SLOT.get(where, "any")
    if cat == "Shadow Gear":
        return SHADOW_SLOT.get(kind, "shadow-armor")
    if cat in CAT_SLOT:
        return CAT_SLOT[cat]
    if kind.startswith("relic "):
        bare = client_cat(kind[6:]) or ""
        return CAT_SLOT.get(bare, "weapon")
    return "weapon"


def fits(ours, got):
    """Is this client entry the item we mean?"""
    cat = client_cat(got["type"])
    if not cat:
        return False
    if ours["kind"] == "card":
        return cat == "Card"
    if cat == "Card":
        return False
    if ours["cat"] in ("Card", "MVP Card"):
        return False
    return cat == ours["cat"]


def same_reading(a, b):
    """Two client entries that would tell the database the same story."""
    return (a["stat"], a["effect"], a["mastery"], a["level"]) == \
           (b["stat"], b["effect"], b["mastery"], b["level"])


def asked_about():
    """Names somebody asked about in the Discord, from who-drops.json.

    An item a player went looking for belongs in the database even when its
    tooltip is plain official text with none of this server's vocabulary in it.
    Sunglasses is the case that proved it: a champion drop people hunt, and the
    reader would otherwise skip it.
    """
    path = os.path.join(db.SRC, "who-drops.json")
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except (IOError, ValueError):
        return set()
    return set(it["name"].lower() for it in data.get("items", []))


def wanted_names():
    """Everything the site already lists, so the extract can be trimmed to it
    and the rest reported."""
    items = []
    for fname, source, kind in (
            ("gear__core-weapons.csv", "core", "weapons"),
            ("gear__core-not-weapons.csv", "core", "other"),
            ("gear__mvp-weapons.csv", "mvp", "weapons"),
            ("gear__mvp-not-weapons.csv", "mvp", "other")):
        path = os.path.join(db.SRC, fname)
        if os.path.exists(path):
            items += db.parse_gear(path, source, kind)
    for suffix, slot in db.CARD_SLOT.items():
        path = os.path.join(db.SRC, "card__%s.csv" % suffix)
        if os.path.exists(path):
            items += db.parse_cards(path, slot)
    shadow = os.path.join(db.SRC, "gear__shadow-gear.csv")
    if os.path.exists(shadow):
        items += db.parse_shadow(shadow)
    items += db.parse_relics(os.path.join(db.SRC, "relic-gear.json"))
    items += db.parse_tooltips(os.path.join(db.SRC, "tooltip-items.json"))
    mvp_cards = os.path.join(db.SRC, "mvp-cards.csv")
    if os.path.exists(mvp_cards):
        items += db.parse_mvp_cards(mvp_cards)

    names = {}
    for it in items:
        names[it["name"].lower()] = it
        if it["kind"] == "card":
            # the client spells a card out in full, the sheets do not
            names[it["name"].lower() + " card"] = it
    return names


def main():
    path = find_client(sys.argv)
    if not path:
            print("client não encontrado. Passe a pasta do jogo:\n"
                  "  python tools/fetch_client_items.py \"E:/NightmareRO (Release)\"")
            return 1

    print("lendo %s" % path)
    raw = read_client(path)
    print("  %d itens no cliente" % len(raw))

    wanted = wanted_names()
    asked = asked_about()
    found, unknown = {}, {}

    for entry in sorted(raw.values(), key=lambda e: e["id"]):
        if not entry["name"] or not entry["lines"]:
            continue
        low = entry["name"].lower()
        ours = wanted.get(low)
        if ours is None and low.endswith(" card"):
            ours = wanted.get(low[:-5])
        if ours is None:
            # gear the site has never listed. Kept only when it is equipment
            # or a card and the description carries this server's own stat
            # vocabulary, which is what tells a live item apart from the
            # leftovers every client ships.
            got = describe(entry)
            if client_cat(got["type"]) and (
                    low in asked or CUSTOM.search(" ".join(entry["lines"]))):
                got["ourName"] = got["name"]
                got["new"] = True
                got["custom"] = bool(CUSTOM.search(" ".join(entry["lines"])))
                unknown.setdefault(got["name"], []).append(got)
            elif etc_cat(got["type"]):
                got["ourName"] = got["name"]
                got["new"] = True
                got["material"] = True
                unknown.setdefault(got["name"], []).append(got)
            continue
        found.setdefault(ours["name"], []).append((ours, describe(entry)))

    keep, ambiguous, wrong_cat = [], [], []
    for name in sorted(found):
        ours = found[name][0][0]
        fitting = [got for _, got in found[name] if fits(ours, got)]

        if not fitting:
            # the name matched but nothing of the right kind did: the client
            # calls it something else, so say so rather than guess
            wrong_cat.append("%-30s site: %-20s cliente: %s"
                             % (name, ours["cat"],
                                ", ".join(sorted(set(g["type"] or "?"
                                          for _, g in found[name])))))
            continue

        first = fitting[0]
        if not all(same_reading(first, other) for other in fitting[1:]):
            ambiguous.append("%-30s %s" % (name, ", ".join(
                "%d (%s)" % (g["id"], g["stat"] or "sem stat")
                for g in fitting)))
            continue

        first["ourName"] = name
        keep.append(first)

    # gear the site has never carried. Same duplicate problem, so the same
    # rule: only when every candidate of that name and kind reads alike.
    added, twins = [], []
    for name in sorted(unknown):
        # Loot is grouped by name alone: the client files the same material
        # under two Type lines now and then, Enriched Elunium being both a
        # forging and a refining material, and that is one item.
        loot = [g for g in unknown[name] if g.get("material")]
        gear = [g for g in unknown[name] if not g.get("material")]

        by_cat = {}
        if loot:
            by_cat["loot"] = loot
        for got in gear:
            # an item pulled in only because somebody asked about it, whose
            # name is already a piece of loot, is the wrong item: RO has a
            # Fresh Fish you can equip and a Fresh Fish that Phen drops
            if loot and not got.get("custom"):
                continue
            by_cat.setdefault(client_cat(got["type"]), []).append(got)

        for cat, group in sorted(by_cat.items()):
            first = group[0]
            if cat != "loot" and not all(
                    same_reading(first, other) for other in group[1:]):
                twins.append("%-30s %s" % (name, ", ".join(
                    "%d (%s)" % (g["id"], g["stat"] or "sem stat")
                    for g in group)))
                continue
            if cat == "loot":
                # keep the one that actually says something
                first = max(group, key=lambda g: len(g.get("flavour", "")) +
                            len(" ".join(g.get("effect", []))))
                first["cat"] = etc_cat(first["type"])
                first["slot"] = ""
            else:
                first["cat"] = cat
                first["slot"] = slot_for(first)
            added.append(first)

    keep += added
    keep.sort(key=lambda g: g["id"])
    payload = {
        "_note": "Item tooltips read out of the client by "
                 "tools/fetch_client_items.py. This is what the game itself "
                 "shows, so build_database.py trusts it over every sheet. "
                 "Trimmed to the items the site lists. ourName is the name the "
                 "site uses, which is what the override is keyed on.",
        "_ambiguous": "A display name is not unique in the client, so an entry "
                      "is only kept when the Type line agrees with the "
                      "category the site has it under and every remaining "
                      "candidate reads the same. Anything left over is "
                      "reported by the script and deliberately not written "
                      "here, so the sheet keeps the item.",
        "_source": path.replace("\\", "/"),
        "count": len(keep),
        "items": keep,
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n")

    print("  %d do site corrigidos, %d novos -> "
          "tools/data/client-items.json (%.0f KB)"
          % (len(keep) - len(added), len(added),
             os.path.getsize(OUT) / 1024.0))

    for title, rows in (("ambíguos, mantidos com a planilha", ambiguous),
                        ("cliente discorda da categoria", wrong_cat),
                        ("novos ambíguos, deixados de fora", twins)):
        if rows:
            print("\n%s (%d):" % (title, len(rows)))
            for line in rows:
                print("  " + line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
