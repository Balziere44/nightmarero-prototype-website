#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reads the item descriptions out of the game client and writes
tools/data/client-items.json, which build_database.py then trusts over every
sheet.

    python tools/fetch_client_items.py ["E:/NightmareRO (Release)"]

The client keeps its English tooltips in SystemEN/LuaFiles514/itemInfo.lua, and
that file is the same text the item description window shows in game, which
makes it the last word on what an item does: the reference sheets are typed by
hand and lag behind, a screenshot of a tooltip does not, and this is where the
screenshot's text comes from.

It is *not* a list of the items this server has. The file is llchrisll's
ROenglishRE, a community translation of the whole official database, and it
ships the same 19,315 entries to every server that installs it -- Siege White
Potion, the anniversary cakes, event coins from 2011, none of which exist here.
The owner edits that file in place for his own content, so the only entries this
script will publish are the ones he changed:

  * custom  -- an id the translation never had, so it is his
  * edited  -- an id whose name, description or slot count he rewrote
  * vanilla -- byte for byte the translation, therefore no evidence at all

The base it diffs against is the exact release the client was built from, taken
from the "Last updated" stamp in the client file's own header and pinned below
by commit. If that stamp ever names a release we have no pin for, the script
stops instead of guessing, because guessing here is what put items that are not
in the game on the site.

An untouched entry is not a claim that the item is missing -- Jellopy is
untouched and obviously real. It only means nothing we can read says it is
here, so it stays out until a sheet, a print or an answer in the Discord says
otherwise.

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
CACHE = os.path.join(ROOT, "tools", "cache")

DEFAULT_CLIENTS = (
    r"E:/NightmareRO (Release)",
    r"C:/NightmareRO (Release)",
)
INSIDE = os.path.join("SystemEN", "LuaFiles514", "itemInfo.lua")

# The translation release the client was built from, by the stamp in its header.
# Add a line here when a patch moves the client to a newer release: find the
# commit whose itemInfo carries that "Last updated" date in
# https://github.com/llchrisll/ROenglishRE/commits/master
BASE_REPO = "llchrisll/ROenglishRE"
BASE_RAW = "https://raw.githubusercontent.com/%s/%s/%s"
BASE_PINS = {
    "20210313": ("74ab56c59184b4b2b2f5f8276333e083ba14bb4a",
                 "Renewal/System/itemInfo_EN.lua"),
}
STAMP = re.compile(r"^--\s*Last updated:\s*(\d{8})", re.M)

ENTRY = re.compile(r"^\t\[(\d+)\]\s*=\s*\{")
STRING = r'"((?:[^"\\]|\\.)*)"'
NAME = re.compile(r'(?<!un)identifiedDisplayName\s*=\s*' + STRING)
SLOTS = re.compile(r"slotCount\s*=\s*(\d+)")
ONE_LINE = re.compile(r'^\s*' + STRING + r',?\s*$')

# ^FF0000 turns a word red in the client. The site colours the same words
# itself from the status codex, so the codes go. SHORT_COLOUR catches the ones
# written with a digit missing -- three cards say ^00000 where they mean
# ^000000, and without this the site prints "Water^00000".
COLOUR = re.compile(r"\^[0-9a-fA-F]{6}")
SHORT_COLOUR = re.compile(r"\^[0-9a-fA-F]{3,5}(?![0-9a-fA-F])")

# <NAVI>Mayomayo<INFO>malangdo,213,167,0,100,0,0</INFO></NAVI> is a link the
# client turns into "Mayomayo", clickable, walking you there. Keep the name and
# the place, which is more than the site would otherwise know.
NAVI = re.compile(r"<NAVI>(.*?)<INFO>([a-z0-9_@]+),(\d+),(\d+)[^<]*</INFO></NAVI>")
ANGLE = re.compile(r"<(/?[A-Za-z][A-Za-z ]*)>")

RULE = re.compile(r"^_{3,}$")

# the first line of most tooltips, and never useful
NOISE = ("Can be identified by using a Magnifier.",)

LABEL = re.compile(r"^([A-Z][A-Za-z /]*):\s*(.*)$")

STAT_LABELS = ("Attack", "Magic Attack", "Defense", "Magic Defense")

# Entries the owner wrote and then left lying around: a dev weapon, a crash
# test, and the placeholder the enchant window shows when a spot has no random
# enchants. Named by id because the names are ordinary words.
DEV_ITEMS = {
    1100,       # Test Sword, "Test weapon do not steal"
    180001,     # Crash Test, "Time to Crash"
    170085,     # No Enchants Available, a line of interface text
}


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


def stamp_of(path):
    """The translation release a copy of itemInfo.lua was built from."""
    head = io.open(path, encoding="cp949", errors="replace").read(4096)
    found = STAMP.search(head)
    return found.group(1) if found else ""


def base_copy(stamp):
    """The untouched translation the client started from, downloaded once.

    Cached under tools/cache because it is 15 MB and reproducible: the pin is
    a commit, so the same stamp always fetches the same bytes.
    """
    if stamp not in BASE_PINS:
        print("o cliente diz 'Last updated: %s' e não temos pin para essa\n"
              "versão da tradução. Sem a base não há como saber quais itens\n"
              "são deste servidor, então nada é escrito. Ache o commit com\n"
              "essa data em https://github.com/%s/commits/master e junte em\n"
              "BASE_PINS." % (stamp or "?", BASE_REPO))
        return None

    commit, inside = BASE_PINS[stamp]
    if not os.path.isdir(CACHE):
        os.makedirs(CACHE)
    path = os.path.join(CACHE, "itemInfo-base-%s.lua" % stamp)
    if not os.path.exists(path):
        url = BASE_RAW % (BASE_REPO, commit, inside.replace(" ", "%20"))
        print("  baixando a tradução base (%s) uma vez..." % stamp)
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=300) as answer:
                blob = answer.read()
        except Exception as exc:                     # noqa: BLE001
            print("  não deu para baixar (%s).\n"
                  "  Baixe à mão e salve em %s:\n  %s" % (exc, path, url))
            return None
        io.open(path, "wb").write(blob)

    got = stamp_of(path)
    if got != stamp:
        # a wrong base would call half the database custom, which is the exact
        # mistake this whole mechanism exists to prevent
        print("  a base baixada diz '%s' e o cliente diz '%s'; apagando %s"
              % (got or "?", stamp, path))
        os.remove(path)
        return None
    return path


def unescape(text):
    return text.replace('\\"', '"').replace("\\\\", "\\")


def clean(text):
    text = unescape(text)
    text = NAVI.sub(lambda m: "%s (%s %s,%s)" % (m.group(1), m.group(2),
                                                 m.group(3), m.group(4)), text)
    text = COLOUR.sub("", text)
    text = SHORT_COLOUR.sub("", text)
    # <None> is how the homunculus embryos say a slot has no skill
    text = ANGLE.sub(lambda m: m.group(1), text)
    return re.sub(r"\s+", " ", text).strip()


def readable(text):
    """False for a line the translation never got to.

    A handful of entries still carry their Korean, and the client reads the
    file as a Korean codepage. Hangul on an English site is a bug, so the line
    is dropped and the item keeps whatever else it has.
    """
    if not text:
        return False
    odd = sum(1 for ch in text if ord(ch) > 127)
    return odd * 3 <= len(text)


def read_client(path):
    """id -> {name, slots, lines}.

    The file is 16 MB of Lua and a third of it is Korean sprite names, so it is
    read as the codepage the client itself uses and only the fields we name are
    touched.
    """
    items, cur, in_desc = {}, None, False

    for raw in io.open(path, encoding="cp949", errors="replace"):
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


def origins(ours, base):
    """id -> custom | edited | vanilla, by what the owner changed.

    Compared on exactly what a player can read: the name, the description and
    the number of card slots. The translation and the client differ in one
    mechanical way everywhere -- the client adds costume = false -- and that is
    not an edit, so the fields are named rather than the whole block compared.
    """
    out = {}
    for iid, entry in ours.items():
        was = base.get(iid)
        if was is None:
            out[iid] = "custom"
        elif (entry["name"], entry["lines"], entry["slots"]) != \
             (was["name"], was["lines"], was["slots"]):
            out[iid] = "edited"
        else:
            out[iid] = "vanilla"
    return out


def blocks(lines):
    """The tooltip is written as blocks divided by a rule of underscores."""
    out, current = [], []
    for line in lines:
        text = clean(line)
        if not text or not readable(text):
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
                # A homunculus embryo lists its skills as "Attack: Caprice"
                # and "Defense: None". Only a number is a stat.
                if re.search(r"\d", value):
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

            # the salvagers and a few chests repeat their own name as the
            # description, which tells the reader nothing twice
            if line == entry["name"]:
                continue

            # "For each Refine:" and friends head a block; fold the heading
            # into each line under it so one bullet reads on its own. A whole
            # sentence ending in a colon is not a heading -- the homunculus
            # embryos open with one, and folding it in repeated it on every
            # line under it.
            if line.endswith(":") and len(line) <= 40 and line.count(" ") <= 5:
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
    "mace": "Maces", "katar": "Katars", "legendary katar": "Katars",
    "knuckle": "Fists", "fist": "Fists",
    "bow": "Bows", "staff": "Staffs", "one-handed staff": "Staffs",
    "two-handed staff": "Staffs", "legendary staff": "Staffs",
    "book": "Books", "soul": "Souls",
    "instrument": "Instruments & Whips",
    "musical instrument": "Instruments & Whips",
    "whip": "Instruments & Whips", "revolver": "Revolvers", "rifle": "Rifles",
    "shotgun": "Shotguns", "gatling gun": "Gatling Guns",
    "grenade launcher": "Grenade Launchers",
    "huuma shuriken": "Huuma Shurikens", "huuma": "Huuma Shurikens",
    "taekwon glove": "Taekwon Gloves",
    "armor": "Armors", "garment": "Garments", "shoes": "Shoes",
    "shield": "Shields", "accessory": "Accessories",
    "godly armor": "Armors", "godly garment": "Garments",
    "godly shoes": "Shoes", "godly shield": "Shields",
    "godly accessory": "Accessories",
}


# The Type lines for the things that are not worn, folded into the few groups a
# reader would actually filter by. The owner's own wording is kept wherever he
# has one -- these are his systems and his words for them are what the game and
# the Discord use.
ETC_CAT = {
    # the loot you pick up
    "collectible": "Loot", "???": "Loot", "trophy": "Trophy",
    "valuable": "Valuable", "essential": "Essential", "artifact": "Artifact",
    "relic": "Relic material",
    "crafting ingredient": "Crafting ingredient",
    "crafting material": "Crafting ingredient",
    "cooking ingredient": "Crafting ingredient",
    "forging material": "Forging material",
    "refining material": "Refining material",
    "skill catalyst": "Skill catalyst", "skill necessity": "Skill catalyst",
    "skill requirement": "Skill catalyst", "skill material": "Skill catalyst",
    "quest": "Quest item", "currency": "Currency",
    # what you drink, read or throw away
    "potion": "Consumable", "restorative": "Consumable",
    "throwable potion": "Consumable", "consumable": "Consumable",
    "apple": "Consumable", "usable": "Consumable", "supportive": "Consumable",
    "stat bonus": "Stat booster", "attack speed potion": "Stat booster",
    "guild exp boost": "Stat booster",
    # this server's own systems
    "enchant": "Enchant", "option enchanter": "Enchant scroll",
    "rune": "Rune", "homunculus embryo": "Homunculus embryo",
    "container": "Container", "card album": "Container",
    "shadow coffer": "Container",
    "salvager": "Salvager",
    "weapon modification": "Modification",
    "armor modification": "Modification",
    "weapon maintenance kit": "Maintenance kit",
    "armor maintenance kit": "Maintenance kit",
    "teleporter": "Travel", "warper": "Travel", "travel permit": "Travel",
    "summoning ticket": "Summoning", "utility": "Utility",
    "arrow": "Ammunition", "ammo": "Ammunition", "kunai": "Ammunition",
    "shuriken": "Ammunition",
}


def etc_cat(kind):
    return ETC_CAT.get(kind.strip().lower(), "")


def client_cat(kind):
    """Category for a client Type line, or "" when it says nothing useful."""
    kind = kind.strip().lower()
    if not kind:
        return ""
    if kind.startswith("relic ") or kind == "relic gear":
        return "Relic Gear"
    if kind.startswith("shadow ") or kind.startswith("relic shadow "):
        return "Shadow Gear"
    if kind.startswith("headgear"):
        return "Headgears"
    if kind.startswith("costume"):
        return "Costumes"
    if kind in ("card", "card?"):
        return "Card"
    return TYPE_CAT.get(kind, "")


CAT_SLOT = {
    "Armors": "armor", "Garments": "garment", "Shoes": "shoes",
    "Shields": "shield", "Headgears": "headgear", "Accessories": "accessory",
    "Costumes": "costume",
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
        bare = kind[6:] if kind.startswith("relic ") else kind
        return SHADOW_SLOT.get(bare, "shadow-armor")
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
    """Names somebody in the Discord answered about, from who-drops.json.

    An answer naming an item is independent evidence that the item is in the
    game, so it stands in for an edited tooltip: these come in even when the
    entry is word for word the translation. Sunglasses is the case that proved
    it, a champion drop people hunt with an entirely official description.
    """
    path = os.path.join(db.SRC, "who-drops.json")
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except (IOError, ValueError):
        return set()
    return set(it["name"].lower() for it in data.get("items", []))


def wanted_names():
    """Everything the site already lists, so a name in the client can be
    matched to the row it corrects."""
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

    stamp = stamp_of(path)
    base = base_copy(stamp)
    if not base:
        return 1
    mine = origins(raw, read_client(base))
    counts = {}
    for kind in mine.values():
        counts[kind] = counts.get(kind, 0) + 1
    print("  do servidor: %d novos + %d reescritos; da tradução: %d ignorados"
          % (counts.get("custom", 0), counts.get("edited", 0),
             counts.get("vanilla", 0)))

    wanted = wanted_names()
    asked = asked_about()
    found, unknown, untouched = {}, {}, []

    for entry in sorted(raw.values(), key=lambda e: e["id"]):
        if not entry["name"] or not entry["lines"]:
            continue
        if entry["id"] in DEV_ITEMS:
            continue
        low = entry["name"].lower()
        ours = wanted.get(low)
        if ours is None and low.endswith(" card"):
            ours = wanted.get(low[:-5])

        # the gate: only what this server wrote, or what the Discord confirms
        if mine[entry["id"]] == "vanilla" and low not in asked:
            if ours is not None:
                untouched.append(ours["name"])
            continue

        if ours is None:
            got = describe(entry)
            got["origin"] = mine[entry["id"]]
            got["ourName"] = got["name"]
            got["new"] = True
            if client_cat(got["type"]):
                unknown.setdefault(got["name"], []).append(got)
            elif etc_cat(got["type"]) or got["flavour"] or got["effect"]:
                # loot, materials and the rest of what is not worn. A few of
                # them have no Type line at all and are nothing but their
                # description, which is still the answer to "what is this".
                got["material"] = True
                unknown.setdefault(got["name"], []).append(got)
            continue

        got = describe(entry)
        got["origin"] = mine[entry["id"]]
        found.setdefault(ours["name"], []).append((ours, got))

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
            if loot and got["origin"] == "vanilla":
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
                first["cat"] = etc_cat(first["type"]) or "Loot"
                first["slot"] = ""
                first["kind"] = "material"
            else:
                first["cat"] = cat
                first["slot"] = slot_for(first)
                first["kind"] = "card" if cat == "Card" else "gear"
            added.append(first)

    keep += added
    keep.sort(key=lambda g: g["id"])
    payload = {
        "_note": "Item tooltips read out of the client by "
                 "tools/fetch_client_items.py. This is what the game itself "
                 "shows, so build_database.py trusts it over every sheet. "
                 "ourName is the name the site uses, which is what the "
                 "override is keyed on.",
        "_only": "Only entries this server wrote are here. The client's "
                 "itemInfo.lua is a translation of the whole official item "
                 "database and lists thousands of items no server enables, so "
                 "every entry is diffed against the release it was built from "
                 "and the untouched ones are dropped: origin custom means an "
                 "id the translation never had, edited means the owner "
                 "rewrote it. An untouched entry is not proof an item is "
                 "missing, only that nothing here says it is present.",
        "_ambiguous": "A display name is not unique in the client, so an entry "
                      "is only kept when the Type line agrees with the "
                      "category the site has it under and every remaining "
                      "candidate reads the same. Anything left over is "
                      "reported by the script and deliberately not written "
                      "here, so the sheet keeps the item.",
        "_source": path.replace("\\", "/"),
        "_base": "%s %s %s" % (BASE_REPO, BASE_PINS[stamp][0][:12], stamp),
        "count": len(keep),
        "items": keep,
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n")

    print("  %d do site corrigidos, %d novos -> "
          "tools/data/client-items.json (%.0f KB)"
          % (len(keep) - len(added), len(added),
             os.path.getsize(OUT) / 1024.0))
    if untouched:
        print("\n%d itens do site cuja entrada no cliente é da tradução, não\n"
              "  deste servidor: a planilha fica valendo. Ex.: %s"
              % (len(untouched), ", ".join(sorted(untouched)[:8])))

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
