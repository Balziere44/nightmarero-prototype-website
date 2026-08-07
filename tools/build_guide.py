#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds guide.html, the page for people who have never played here.

    python tools/build_database.py   # guide.html reads assets/data/items.json
    python tools/build_guide.py

It carries the levelling route, one card per level band. The route itself is
written here in LEVELS: where to go, what to collect, and which monsters that
stop is about. Everything hanging off it is looked up rather than typed:

  * cards come from assets/data/items.json, matched on the monster name,
    because a card is named after the monster that drops it
  * gear comes from the same file, matched against its drop list
  * altars come from the MVP sheet, so each stop links to the bosses whose
    altar sits on those maps

That means the guide cannot drift from the database. Rebuild after a sheet
change and every card and stat on the page is current.

Monster lists are only as good as what the sheets tie to a map. Where a
monster is not named by an altar, by the champion tab or by the route itself,
it is not listed.

GUIDES is the older free form section, still here for prose guides. Append to
it and each entry gets its own card and credit line.
"""

import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_classes import esc, head, header, footer, slugify, SITE, REGISTER

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "guide.html")
ITEMS = os.path.join(ROOT, "assets", "data", "items.json")

# A guide is a title, who wrote it, one line of what it covers, and a list of
# blocks. A block is ("steps", [line, ...]) for a numbered route,
# ("split", [(heading, [line, ...]), ...]) for a fork in the road, or
# ("notes", [line, ...]) for loose advice.
GUIDES = []

# --------------------------------------------------------------------------
# Where to hunt, at a glance
# --------------------------------------------------------------------------
#
# Read off the levelled world map the server owner posted, because the levels
# baked into the client's own map are wrong and there is no patcher to fix
# them. Dungeon numbers are the ones printed on that map. Field numbers are
# the tile levels around the town named.
#
# (band, [(place, level, what it is)])

WHERE = [
    ("1 to 15", [
        ("Fields south and east of Prontera", "5", "field"),
        ("Fields around Payon and Alberta", "5 to 15", "field"),
        ("Fields west of Prontera", "5 to 10", "field"),
        ("Fields around Morroc", "5 to 10", "field"),
    ]),
    ("15 to 30", [
        ("Fields north and west of Prontera", "15 to 25", "field"),
        ("Ant Hell", "20 to 40", "dungeon"),
        ("Prontera Culvert", "20 to 40", "dungeon"),
        ("Payon Cave", "20 to 45", "dungeon"),
        ("Fields east of Payon", "15 to 25", "field"),
    ]),
    ("30 to 45", [
        ("Geffen Dungeon", "30 to 45", "dungeon"),
        ("Mjolnir Dead Pit", "30 to 40", "dungeon"),
        ("Fields between Prontera and Aldebaran", "25 to 45", "field"),
        ("Sunken Ship", "40 to 45", "dungeon"),
        ("Byalan Island", "40 to 70", "dungeon"),
    ]),
    ("45 to 60", [
        ("Sphinx", "50 to 60", "dungeon"),
        ("Pyramid", "50 to 60", "dungeon"),
        ("Fields between Comodo and Morroc", "45 to 60", "field"),
        ("Field south of Aldebaran", "50", "field"),
        ("Beach Cave North and East", "55", "dungeon"),
    ]),
    ("60 to 75", [
        ("Orc Dungeon", "65 to 70", "dungeon"),
        ("Beach Cave West", "60", "dungeon"),
        ("Clock Tower", "70 to 80", "dungeon"),
        ("Labyrinth Forest", "70 to 75", "dungeon"),
        ("Fields around Umbala and Comodo", "65 to 75", "field"),
    ]),
    ("75 to 90", [
        ("Magma Caverns", "75 to 85", "dungeon"),
        ("Magma Dungeon", "80 to 85", "dungeon"),
        ("Capitolina Catacombs", "75 to 85", "dungeon"),
        ("Pyramid, the deep floors", "75 to 85", "dungeon"),
        ("Umbala Dungeon", "80", "dungeon"),
        ("Einbech Mine", "85 to 90", "dungeon"),
        ("Fields around Einbroch and Lighthalzen", "70 to 85", "field"),
    ]),
    ("90 to 105", [
        ("Juperos Ruins", "90 to 95", "dungeon"),
        ("Turtle Island", "100 to 105", "dungeon"),
        ("Bio Laboratory", "105 to 110", "dungeon"),
        ("Fields around Yuno and Hugel", "80 to 85", "field"),
        ("Fields around Rachel", "95 to 100", "field"),
    ]),
    ("105 to 125", [
        ("Thor Volcano", "110 to 115", "dungeon"),
        ("Ice Dungeon", "110 to 115", "dungeon"),
        ("Endless Desert", "110 to 115", "dungeon"),
        ("Abyss Lake", "110 to 115", "dungeon"),
        ("Glast Heim and Old Glast Heim", "110 to 120", "dungeon"),
        ("Clock Tower, the lower floors", "110 to 120", "dungeon"),
        ("Fields around Veins", "115", "field"),
    ]),
    ("125 to 150", [
        ("Rachel Sanctuary", "125 to 135", "dungeon"),
        ("Nameless Island", "125 to 135", "dungeon"),
        ("Abyss Lake, the deep floors", "125 to 135", "dungeon"),
        ("Kiel Robot Factory", "135 to 140", "dungeon"),
        ("Geffenia", "140 to 145", "dungeon"),
        ("Odin Temple", "140 to 145", "field"),
    ]),
]

# Where each job change starts, from the server owner's own list. Third job
# changes are not here: by then you know where you are going.
JOBS = [
    ("First job", [
        ("Knight", "Prontera Chivalry, the top left corner of town"),
        ("Crusader", "Prontera Church, the left room"),
        ("Blacksmith", "The Blacksmith's Guild, bottom right of Geffen"),
        ("Alchemist", "The Alchemist's Guild, bottom left of Aldebaran"),
        ("Assassin", "The Assassin's Guild, on Morroc field 16"),
        ("Rogue", "The Old Thief's Guild, in the first basement of the "
                  "Morroc pyramid"),
        ("Hunter", "The Old Archer's Guild, top right of Payon's archer "
                   "village"),
        ("Bard and Dancer",
         "The Comodo stage, in the middle of town. Take the NPC in the Morroc "
         "ruins past St. Darmain's Fortress, then run"),
        ("Wizard", "The top level of Geffen Tower"),
        ("Sage", "Sage Castle in Juno. The NPC on the middle floor of Geffen "
                 "Tower will warp a Mage there, and you should let it"),
        ("Priest", "Prontera Church, the right room"),
        ("Monk", "Capitolina Abbey, inside the building at the bottom right. "
                 "Someone is enjoying the flowers by the entrance"),
    ]),
    ("Expanded", [
        ("Star Gladiator", "Geffen field 5"),
        ("Soul Linker", "Capitolina Abbey, outdoors"),
    ]),
]

# --------------------------------------------------------------------------
# The levelling route
# --------------------------------------------------------------------------
#
# One entry per stop:
#   levels   the band it covers
#   short    the label on the jump button, since two stops share a band
#   where    the place, in the words the route uses
#   goal     what you are there for
#   mobs     monsters the sheets tie to those maps. Cards and gear are looked
#            up from these names, so a typo here quietly drops content
#   bosses   (boss name, altar map) for altars sitting on those maps
#   who      who gets the most out of the stop, and why
#   note     anything else worth one line

LEVELS = [
    {
        "levels": "1 to 10",
        "short": "1 to 10, Prontera south",
        "where": "Prontera, the field south of town",
        "goal": "Get moving. Kill whatever is in front of you until you have "
                "your first job.",
        "mobs": ["Poring", "Lunatic", "Fabre", "Pupa", "Chonchon", "Willow",
                 "Rocker"],
        "bosses": [],
        "who": "Everyone. The Lunatic and Fabre cards grow with the stat you "
               "are already stacking, so they stay useful well past this "
               "field.",
        "note": "",
    },
    {
        "levels": "10 to 20",
        "short": "10 to 20, west of Prontera",
        "where": "Two maps west of Prontera",
        "goal": "The Creamy card, and 10 Red Herb while you are there.",
        "mobs": ["Creamy", "Creamy Fear", "Poporing", "Coco", "Vocal",
                 "Gullinbursti"],
        "bosses": [("Doppelganger", "prt_fild00")],
        "who": "Anyone who casts. Creamy raises Warp Portal by a level and "
               "Creamy Fear drops its gemstone cost entirely.",
        "note": "The champions on these fields drop the gems that open the "
                "Doppelganger altar later, so nothing you pick up here is "
                "wasted.",
    },
    {
        "levels": "20 to 30",
        "short": "20 to 30, the Grape fields",
        "where": "Three maps west of Prontera",
        "goal": "30 Grape. That is a Grape Juice, which is the bottom of the "
                "SP potion ladder.",
        "mobs": [],
        "bosses": [],
        "who": "Anything that runs on SP. The Grape Juice recipe also wants "
               "10 Ant Jaw and 10 Golden Hair, both of which are on the next "
               "two stops.",
        "note": "",
    },
    {
        "levels": "20 to 30",
        "short": "20 to 30, Ant Hell",
        "where": "Ant Hell and the field outside it",
        "goal": "10 Ant Jaw and 30 Yellow Herb.",
        "mobs": ["Andre", "Piere", "Deniro", "Vitata", "Giearth", "Ant Egg",
                 "Familiar", "Maya Purple"],
        "bosses": [("Maya", "anthell02")],
        "who": "Melee, and anyone who wants a set. The three Ant cards combo "
               "with each other, the three Soldier cards combo with each "
               "other, and Maya Purple spreads Slash, Envenom and Sand Attack "
               "across an area.",
        "note": "Maya's altar wants 75 Ant Jaw, which is the same drop you "
                "are already farming for the Grape Juice.",
    },
    {
        "levels": "30 to 40",
        "short": "30 to 40, Geffen dungeon",
        "where": "Geffen dungeon",
        "goal": "10 Golden Hair, the last piece of the Grape Juice recipe.",
        "mobs": ["Jakk", "Marionette", "Deviruchi", "Nightmare",
                 "Zombie Master", "Mini Demon"],
        "bosses": [("Dracula", "gef_dun03")],
        "who": "Ghost and undead hunters. Marionette adds physical damage to "
               "ghosts, Zombie Master swings damage both ways against undead.",
        "note": "Everything Dracula's altar asks for drops on these floors, "
                "so the boss is reachable while you are still levelling here.",
    },
    {
        "levels": "40 to 50",
        "short": "40 to 50, Aldebaran",
        "where": "South of Aldebaran",
        "goal": "Level, and start collecting for the two altars nearby.",
        "mobs": ["Mistress", "Kublin"],
        "bosses": [("Mistress", "mjolnir_04"), ("Kublin", "mjo_dun03")],
        "who": "Healers first. The Mistress card takes three seconds off both "
               "Heal and Aid Potion, and her gear leans the same way.",
        "note": "Kublin's champion drops include the Gnome's Moustache the "
                "Concentration Potion recipe asks for.",
    },
    {
        "levels": "50 to 55",
        "short": "50 to 55, Pitaya fields",
        "where": "The Pitaya fields",
        "goal": "One card per colour, and the pieces for the Nightmare Pitaya "
                "altar.",
        "mobs": ["Green Pitaya", "Red Pitaya", "Yellow Pitaya",
                 "Violet Pitaya", "Angeling", "Plateau Colossus", "Goat",
                 "Harpy", "Sleeper"],
        "bosses": [("Nightmare Pitaya", "yuno_fild10")],
        "who": "Everyone, whatever you rolled. Each colour is a different "
               "stat, so you take the one your build already wants, and the "
               "Nightmare Pitaya card triples whichever ones you are wearing.",
        "note": "",
    },
    {
        "levels": "55 to 70",
        "short": "55 to 70, Orcs",
        "where": "Orc field and Orc dungeon",
        "goal": "A long stop. Four altars sit on these maps.",
        "mobs": ["Orc Warrior", "Orc Lady", "Orc Archer", "Orc Zombie",
                 "Zenorc", "High Orc", "Orc Baby", "Orc Hero", "Kobold",
                 "Kobold Archer"],
        "bosses": [("Orc Lord", "gef_fild14"),
                   ("Orc Necromancer", "orcsdun02"),
                   ("Kobold Warchief", "gef_fild12"),
                   ("Goblin King", "gef_fild11")],
        "who": "Two handed weapons want the Kobold Warchief card. Anything "
               "that stacks HP and does not lean on skills wants Orc Lord, "
               "since the SP cost it adds hurts casters far more.",
        "note": "The Orc Lord altar only asks for the two champion drops off "
                "these same fields, Nursing Bottle and Orc Trophy.",
    },
    {
        "levels": "70 to 78",
        "short": "70 to 78, Magma",
        "where": "Magma dungeon",
        "goal": "Burning gear, and the Muspellskoll altar.",
        "mobs": ["Magmaring", "Green Ferus", "Blazer", "Explosion", "Kaho",
                 "Imp", "Lava Golem", "Earth Deleter", "Sky Deleter"],
        "bosses": [("Muspellskoll", "mag_dun02"),
                   ("Curse of Change", "mag_deep04")],
        "who": "Anything that burns. Kaho and Magmaring push burning damage, "
               "Lava Golem and Blazer take it off you, which matters because "
               "half the floor is fire.",
        "note": "mag_deep04 is a Nightmare dungeon. Do not walk in on the way "
                "past.",
    },
    {
        "levels": "78 to 95",
        "short": "78 to 95, Juperos",
        "where": "Juperos",
        "goal": "The longest single stop on the route.",
        "mobs": ["Venatu", "Dimik", "Apocalypse", "Archdam"],
        "bosses": [("Vesper", "jupe_core")],
        "who": "Gunners and casters. Dimik cuts a full second of fixed cast "
               "off a rifle, Archdam is SP, Apocalypse is HP and no knockback.",
        "note": "",
    },
    {
        "levels": "95 to 99",
        "short": "95 to 99, Vesper",
        "where": "Vesper, in the Juperos core",
        "goal": "Farm the boss itself. Its altar wants 25 of each Crest "
                "Piece, all four of which drop in the floors above.",
        "mobs": ["Vesper"],
        "bosses": [("Vesper", "jupe_core")],
        "who": "Elemental casters. The Vesper card turns your weapon wind and "
               "adds 30% wind magic damage, and the rest of the set is a "
               "resistance and movement package.",
        "note": "",
    },
]


# --------------------------------------------------------------------------
# Lookups against the item database
# --------------------------------------------------------------------------

def load_items():
    try:
        return json.load(io.open(ITEMS, encoding="utf-8")).get("items", [])
    except (IOError, ValueError):
        return []


def cards_for(items, mobs):
    """A card is named after the monster that drops it, so an exact name match
    is the whole lookup."""
    want = [m.lower() for m in mobs]
    out, seen = [], set()
    for item in items:
        if item["kind"] != "card":
            continue
        # a couple of entries in the sheet carry the word Card in the name
        key = re.sub(r"\s+card$", "", item["name"].lower())
        if key in want and key not in seen:
            seen.add(key)
            out.append(item)
    return sorted(out, key=lambda i: want.index(
        re.sub(r"\s+card$", "", i["name"].lower())))


def gear_for(items, mobs, limit=8):
    """Gear lists the monsters it drops from, so match on that."""
    patterns = [re.compile(r"\b%s\b" % re.escape(m), re.I) for m in mobs]
    out, seen = [], set()
    for item in items:
        if item["kind"] != "gear" or not item.get("drops"):
            continue
        if item["name"] in seen:
            continue
        if any(p.search(item["drops"]) for p in patterns):
            seen.add(item["name"])
            out.append(item)
    # the pieces named after one monster are the interesting ones, so put the
    # short drop lists first
    out.sort(key=lambda i: (len(i["drops"].split(",")), i["name"]))
    return out[:limit]


SLOT_WORD = {
    "weapon": "Weapon", "armor": "Armour", "shield": "Shield",
    "garment": "Garment", "shoes": "Shoes", "headgear": "Headgear",
    "accessory": "Accessory", "any": "Any slot",
}


def level_card(stop, items):
    cards = cards_for(items, stop["mobs"])
    gear = gear_for(items, stop["mobs"])

    mobs = "".join('<span class="lv-mob">%s</span>' % esc(m)
                   for m in stop["mobs"])

    card_rows = "".join(
        "<tr><td><b>%s</b></td><td class=\"dim\">%s</td><td>%s</td></tr>"
        % (esc(c["name"]), esc(SLOT_WORD.get(c["slot"], c["slot"])),
           esc(" / ".join(c["effect"])))
        for c in cards)
    card_html = ""
    if card_rows:
        card_html = """<h4 class="lv-head" data-i18n="g.lvCards">Cards that drop here</h4>
          <div class="table-wrap"><table class="mvp-table"><tbody>%s</tbody></table></div>""" % card_rows

    gear_html = ""
    if gear:
        gear_html = ('<h4 class="lv-head" data-i18n="g.lvGear">Gear that drops here</h4>'
                     '<ul class="lv-gear">%s</ul>' % "".join(
                         "<li><b>%s</b> <span class=\"dim\">%s</span>%s</li>"
                         % (esc(g["name"]),
                            esc(SLOT_WORD.get(g["slot"], g["slot"])),
                            ("<span>%s</span>" % esc(" / ".join(g["effect"])))
                            if g["effect"] else "")
                         for g in gear))

    boss_html = ""
    if stop["bosses"]:
        boss_html = ('<h4 class="lv-head" data-i18n="g.lvBosses">Altars in reach</h4>'
                     '<div class="lv-bosses">%s</div>' % "".join(
                         '<a class="lv-boss" href="mvps.html#b-%s">%s'
                         '<span class="lv-map">%s</span></a>'
                         % (slugify(name), esc(name), esc(where))
                         for name, where in stop["bosses"]))

    note = ('<p class="lv-note">%s</p>' % esc(stop["note"])) if stop["note"] else ""

    return """        <article class="lv-stop">
          <div class="lv-top">
            <span class="lv-band">{levels}</span>
            <h3>{where}</h3>
          </div>
          <p class="lv-goal">{goal}</p>
          <div class="lv-mobs">{mobs}</div>
          {cards}
          {gear}
          {bosses}
          <p class="lv-who"><span data-i18n="g.lvWho">Who wants this stop</span> {who}</p>
          {note}
        </article>""".format(
        levels=esc(stop["levels"]), where=esc(stop["where"]),
        goal=esc(stop["goal"]), mobs=mobs, cards=card_html, gear=gear_html,
        bosses=boss_html, who=esc(stop["who"]), note=note)


def leveling_section(items):
    stops = "\n".join(level_card(s, items) for s in LEVELS)
    jumps = "".join(
        '<a class="q-jump" href="#lv-%d">%s</a>' % (n, esc(s["short"]))
        for n, s in enumerate(LEVELS))
    # the anchors go on the article, so stitch the ids in afterwards
    for n in range(len(LEVELS)):
        stops = stops.replace('<article class="lv-stop">',
                              '<article class="lv-stop" id="lv-%d">' % n, 1)

    return """
  <section class="section-pad-sm" id="leveling">
    <div class="shell">
      <div class="section-head">
        <p class="eyebrow" data-i18n="g.lvEyebrow">Levelling route</p>
        <h2 data-i18n="g.lvTitle">One stop at a time, 1 to 99</h2>
        <p class="lede" data-i18n="g.lvLede">Where to go at each level band, what to pick up while you are there, and which altars sit close enough to be worth a detour. Cards, gear and altars are read straight out of the item database, so they match what is on the server.</p>
      </div>
      <nav class="q-jumps" aria-label="Jump to a level band">
        <span class="q-jumps-label" data-i18n="q.jump">Jump to</span>
        {jumps}
      </nav>
      <p class="note" data-i18n="g.lvNote">Monster lists cover what the sheets tie to each area, not every spawn on the map. Drop rates are on the database page: gear off ordinary monsters lands at 1 to 5%, cards at 1%.</p>
      <div class="lv-list">
{stops}
      </div>
    </div>
  </section>
""".format(jumps=jumps, stops=stops)


def map_section():
    """How to read levels off the world map, and the rule that decides where
    you should be standing."""
    return """
  <section class="section-pad-sm" id="map">
    <div class="shell">
      <div class="section-head">
        <p class="eyebrow" data-i18n="g.mapEyebrow">Before anything else</p>
        <h2 data-i18n="g.mapTitle">The map already knows where you should be</h2>
        <p class="lede" data-i18n="g.mapLede">Every field and every dungeon floor has a level printed on it. You just have to turn it on, and once you have, you rarely need a guide at all.</p>
      </div>
      <div class="map-keys">
        <div class="map-key">
          <kbd>Ctrl</kbd><span class="map-plus">+</span><kbd>'</kbd>
          <p data-i18n="g.mapK1">Opens the world map, wherever you are standing.</p>
        </div>
        <div class="map-key">
          <kbd>Tab</kbd>
          <p data-i18n="g.mapK2">Then this switches the level numbers on, one per map.</p>
        </div>
      </div>
      <figure class="map-shot">
        <a href="assets/img/world-map-levels.webp" target="_blank" rel="noopener">
          <img src="assets/img/world-map-levels.webp" width="1436" height="880" loading="lazy" decoding="async" alt="The world map of Midgard with a level printed on every field, and the level range of every dungeon labelled around the edges.">
        </a>
        <figcaption data-i18n="g.mapShot">The same thing as one picture, if you would rather not wait until you are in game. Tap it for full size. The levels built into the client itself are wrong, and there is no patcher to correct them, so this is the version to trust.</figcaption>
      </figure>
      <div class="map-rule">
        <h3 data-i18n="g.mapRuleTitle">Then pick a map at your level or a little above</h3>
        <p data-i18n="g.mapRule1">Hunting above your level pays more. Three levels above the monster and you are already earning a bonus, and it keeps climbing to ten levels above.</p>
        <p data-i18n="g.mapRule2">Never let the gap reach 15 in either direction. Fifteen levels above the monster pays you nothing at all, and fifteen below cuts what you earn by 90%. Both ends of that are a wasted evening.</p>
      </div>
    </div>
  </section>
"""


def where_section():
    """The short version of the route: every band, and the places that fit it."""
    bands = []
    for band, places in WHERE:
        items = "".join(
            '<li class="wh-%s"><span class="wh-name">%s</span>'
            '<span class="wh-lv">%s</span></li>'
            % (kind, esc(name), esc(level)) for name, level, kind in places)
        bands.append(
            '        <article class="wh-band">\n'
            '          <h3><span class="lv-band">%s</span></h3>\n'
            '          <ul class="wh-list">%s</ul>\n'
            "        </article>" % (esc(band), items))

    return """
  <section class="section-pad-sm" id="where">
    <div class="shell">
      <div class="section-head">
        <p class="eyebrow" data-i18n="g.whEyebrow">Quick reference</p>
        <h2 data-i18n="g.whTitle">Fields and dungeons, by level</h2>
        <p class="lede" data-i18n="g.whLede">The whole world on one screen. Find your level, pick anything in the box, go. The longer route below says what is worth picking up once you are there.</p>
      </div>
      <div class="wh-legend">
        <span class="wh-chip wh-field" data-i18n="g.whField">Field</span>
        <span class="wh-chip wh-dungeon" data-i18n="g.whDungeon">Dungeon</span>
      </div>
      <div class="wh-grid">
{bands}
      </div>
      <p class="note" data-i18n="g.whNote">Dungeon levels are the ones printed on the world map, and a dungeon usually climbs across its floors, so the top floor is the low end of the range. Field levels are what the maps around that town read.</p>
    </div>
  </section>
""".format(bands="\n".join(bands))


def jobs_section():
    """Where each job change starts."""
    groups = []
    for title, pairs in JOBS:
        items = "".join(
            "<tr><td><b>%s</b></td><td>%s</td></tr>" % (esc(job), esc(where))
            for job, where in pairs)
        groups.append(
            '        <h3 class="mech-sub">%s</h3>\n'
            '        <div class="table-wrap"><table class="mvp-table">'
            "<tbody>%s</tbody></table></div>" % (esc(title), items))

    return """
  <section class="section-pad-sm" id="jobs">
    <div class="shell">
      <div class="section-head">
        <p class="eyebrow" data-i18n="g.jbEyebrow">Job change</p>
        <h2 data-i18n="g.jbTitle">Where each job change starts</h2>
        <p class="lede" data-i18n="g.jbLede">You get your first job inside the tutorial at level 1. The choice that matters comes at job level 50, and nobody tells you where to go for it.</p>
      </div>
{groups}
    </div>
  </section>
""".format(groups="\n".join(groups))


def steps_block(title, lines):
    items = "".join(
        '<li class="q-step"><span class="q-n">%d</span><div><p>%s</p></div></li>'
        % (n, esc(line)) for n, line in enumerate(lines, start=1))
    return ('<h3 class="guide-head">%s</h3><ol class="q-steps">%s</ol>'
            % (esc(title), items))


def split_block(title, pairs):
    cards = "".join(
        '<div class="guide-branch"><h4>%s</h4>%s</div>'
        % (esc(heading), "".join("<p>%s</p>" % esc(line) for line in lines))
        for heading, lines in pairs)
    return ('<h3 class="guide-head">%s</h3><div class="guide-branches">%s</div>'
            % (esc(title), cards))


def notes_block(title, lines):
    items = "".join("<li>%s</li>" % esc(line) for line in lines)
    return ('<h3 class="guide-head">%s</h3><ul class="guide-notes">%s</ul>'
            % (esc(title), items))


def guide_html(guide):
    blocks = []
    for kind, title, body in guide["blocks"]:
        if kind == "steps":
            blocks.append(steps_block(title, body))
        elif kind == "split":
            blocks.append(split_block(title, body))
        else:
            blocks.append(notes_block(title, body))

    return """      <article class="guide-card" id="g-{slug}">
        <div class="guide-card-head">
          <h2>{title}</h2>
          <p class="guide-credit"><span data-i18n="g.by">Written by</span> <b>{credit}</b></p>
          <p class="lede">{blurb}</p>
        </div>
        <p>{intro}</p>
{blocks}
      </article>""".format(
        slug=slugify(guide["title"]), title=esc(guide["title"]),
        credit=esc(guide["credit"]), blurb=esc(guide["blurb"]),
        intro=esc(guide["intro"]),
        blocks="\n".join("        " + b for b in blocks))


def build():
    items = load_items()
    cards = "\n".join(guide_html(g) for g in GUIDES)

    ld = """<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "{site}/" }},
    {{ "@type": "ListItem", "position": 2, "name": "New players", "item": "{site}/guide.html" }}
  ]
}}
</script>""".format(site=SITE)

    parts = [
        head("", "New player guide | Nightmare RO",
             "Where to start on Nightmare RO: every field and dungeon sorted "
             "by level, a route from 1 to 99 with the cards each stop drops, "
             "and where each job change begins.",
             "guide.html", ld),
        header("", "guide.html"),
        """<main id="main">
  <section class="page-head">
    <div class="shell">
      <nav class="breadcrumb" aria-label="Breadcrumb"><ol>
        <li><a href="index.html" data-i18n="nav.home">Home</a></li>
        <li data-i18n="nav.guide">New players</li>
      </ol></nav>
      <div class="section-head">
        <p class="eyebrow" data-i18n="g.eyebrow">First time here</p>
        <h1 data-i18n="g.title">Where to start when everything is new</h1>
        <p class="lede" data-i18n="g.lede">Every class, skill, item and monster on this server was remade, so what you remember from anywhere else is a rough guide at best. This page collects routes and advice from people who have already walked it.</p>
      </div>
      <nav class="q-jumps" aria-label="Jump to a section">
        <span class="q-jumps-label" data-i18n="q.jump">Jump to</span>
        <a class="q-jump" href="#map" data-i18n="g.jMap">Reading the map</a>
        <a class="q-jump" href="#where" data-i18n="g.jWhere">Where to hunt</a>
        <a class="q-jump" href="#leveling" data-i18n="g.jRoute">The full route</a>
        <a class="q-jump" href="#jobs" data-i18n="g.jJobs">Job change</a>
      </nav>
    </div>
  </section>

""",
        map_section(),
        where_section(),
        leveling_section(items),
        jobs_section(),
        """
  <section class="section-pad-sm">
    <div class="shell">
      <p class="note" data-i18n="g.wip">This page will keep growing. More routes, starting builds and class by class advice are on the way. If you want to write one, the Discord is the place.</p>

""",
        cards,
        """

      <div class="guide-next">
        <h3 data-i18n="g.nextTitle">Where to go from here</h3>
        <div class="hero-actions">
          <a class="btn -ghost" href="quiz.html" data-i18n="nav.quiz">Class test</a>
          <a class="btn -ghost" href="classes.html" data-i18n="nav.classes">Classes</a>
          <a class="btn -ghost" href="database.html" data-i18n="nav.items">Items and cards</a>
          <a class="btn -ghost" href="mvps.html" data-i18n="nav.mvps">MVPs and altars</a>
        </div>
      </div>
    </div>
  </section>

  <section class="section-pad-sm">
    <div class="shell">
      <div class="cta-band">
        <div class="inner">
          <h2 data-i18n="band.title">Come find out what changed</h2>
          <p class="lede text-center" data-i18n="band.lede">Make an account, grab the client, and come and see what changed.</p>
          <div class="hero-actions">
            <a class="btn -primary -lg" href="{reg}" target="_blank" rel="noopener" data-i18n="cta.registerFree">Create a free account</a>
            <a class="btn -ghost -lg" href="download.html" data-i18n="nav.download">Download</a>
          </div>
        </div>
      </div>
    </div>
  </section>
</main>
""".format(reg=REGISTER),
        footer(""),
    ]

    io.open(OUT, "w", encoding="utf-8", newline="\n").write("".join(parts))

    cards_shown = sum(len(cards_for(items, s["mobs"])) for s in LEVELS)
    gear_shown = sum(len(gear_for(items, s["mobs"])) for s in LEVELS)
    print("guide.html: %d stops, %d cards, %d gear, %d prose guide(s) (%.0f KB)"
          % (len(LEVELS), cards_shown, gear_shown, len(GUIDES),
             os.path.getsize(OUT) / 1024.0))

    empty = [s["short"] for s in LEVELS if s["mobs"] and
             not cards_for(items, s["mobs"])]
    if empty:
        print("Stops whose monsters matched no card: %s" % ", ".join(empty))


if __name__ == "__main__":
    build()
