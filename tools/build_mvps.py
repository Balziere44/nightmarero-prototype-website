#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds mvps.html from the MVP reference sheet.

    python tools/fetch_mvps.py      # CSV tabs
    python tools/fetch_mvp_art.py   # the pictures, with their anchor cells
    python tools/build_mvps.py

Bosses do not roam here. Each one sits behind an altar on a specific map, and
you open it by handing over one of two shopping lists: a lot of ordinary drops
from that map, or a few items that only champion monsters drop. Some altars
only offer one of the two.

The sheet lays that out as a two column visual grid, so this reads the grid
rather than a table: it looks for cells starting with "MVP:", works out which
half of the page they sit in, and takes everything under them until the next
boss on that side.
"""

import csv
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_classes import (esc, head, header, footer, slugify,
                           SITE, REGISTER, DISCORD, WIKI)
from status_codex import colorize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "data")
OUT = os.path.join(ROOT, "mvps.html")

MVP_RE = re.compile(r"^MVP\s*:\s*(.+)$")
QTY_RE = re.compile(r"^(\d+)\s*x\s*(.+)$", re.I)
FROM_RE = re.compile(r"^(.*?)\s*\(([^)]+)\)\s*$")

# Where the left hand block ends and the right hand one begins.
SPLIT_COL = 8


def read_csv(name):
    path = os.path.join(SRC, name)
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8") as fh:
        return [[c.strip() for c in row] for row in csv.reader(fh)]


def grid_of(rows):
    width = max([len(r) for r in rows] + [1])
    return [(r + [""] * (width - len(r))) for r in rows], width


def parse_item(text):
    """'75x Venom Canine (Anacondaq,Sidewinder)' into its three pieces."""
    qty, name, source = "", text, ""
    found = QTY_RE.match(text)
    if found:
        qty, name = found.group(1), found.group(2).strip()
    found = FROM_RE.match(name)
    if found:
        name, source = found.group(1).strip(), found.group(2).strip()
    return {"qty": qty, "name": name, "from": source}


def parse_bosses():
    rows = read_csv("mvp-locations.csv")
    if not rows:
        return []
    grid, width = grid_of(rows)

    blocks = []
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            found = MVP_RE.match(cell)
            if found and found.group(1).strip():
                blocks.append({"row": r, "col": c,
                               "name": found.group(1).strip(),
                               "side": "left" if c < SPLIT_COL else "right"})

    for side in ("left", "right"):
        column = [b for b in blocks if b["side"] == side]
        for i, b in enumerate(column):
            b["end"] = column[i + 1]["row"] if i + 1 < len(column) else len(grid)

    for b in blocks:
        col = b["col"]
        b["map"] = grid[b["row"]][0 if b["side"] == "left" else 10]
        common, champion = [], []
        for r in range(b["row"] + 2, b["end"]):
            left = grid[r][col] if col < width else ""
            right = grid[r][col + 3] if col + 3 < width else ""
            if left:
                common.append(parse_item(left))
            if right and right.upper() != "NONE":
                champion.append(parse_item(right))
        b["common"], b["champion"] = common, champion

    return blocks


def parse_nightmare():
    """The Nightmare tab uses the same shape, minus the left hand column."""
    rows = read_csv("mvp-nightmare.csv")
    if not rows:
        return []
    grid, width = grid_of(rows)

    out = []
    marks = [r for r, row in enumerate(grid)
             if any(MVP_RE.match(c) and MVP_RE.match(c).group(1).strip()
                    for c in row)]
    for i, r in enumerate(marks):
        col = next(c for c, cell in enumerate(grid[r]) if MVP_RE.match(cell))
        end = marks[i + 1] if i + 1 < len(marks) else len(grid)
        items = [parse_item(grid[x][col]) for x in range(r + 2, end)
                 if grid[x][col] and grid[x][col].upper() != "NONE"]
        maps = [m for m in grid[r][:2] if m]
        out.append({
            "name": MVP_RE.match(grid[r][col]).group(1).strip(),
            "maps": maps,
            "common": items,
            "row": r,
        })
    return out


def parse_champions():
    rows = read_csv("mvp-summon-items.csv")
    out = []
    for row in rows:
        cells = (row + ["", "", ""])[:3]
        if not cells[0] or cells[0].lower() == "champion":
            continue
        out.append({"mob": cells[0], "map": cells[1], "item": cells[2]})
    return out


def parse_cards():
    out = {}
    for row in read_csv("mvp-cards.csv"):
        cells = (row + ["", "", ""])[:3]
        if not cells[0] or cells[0].lower() == "name":
            continue
        out[cells[0].lower()] = {"name": cells[0], "effect": cells[1],
                                 "slot": cells[2]}

    # A tooltip screenshot is the game talking, so it overrules the sheet row
    # here the same way it does in the database. Moonlight Flower is the reason
    # this exists: the sheet still describes the card it used to be.
    typed = load_json("tooltip-items.json", {})
    for card in typed.get("cards", []):
        key = card["name"].lower()
        if key in out:
            out[key]["effect"] = ". ".join(card["effect"])
    return out


def load_json(name, default):
    path = os.path.join(SRC, name)
    try:
        return json.load(io.open(path, encoding="utf-8"))
    except (IOError, ValueError):
        return default


# --------------------------------------------------------------------------
# Matching a boss to its card and its pictures
# --------------------------------------------------------------------------

def card_for(name, cards):
    key = name.lower()
    if key in cards:
        return cards[key]
    for other, card in cards.items():
        if other.startswith(key) or key.startswith(other):
            return card
    return None


def art_for(art, sheet, row_from, row_to, col_from, col_to):
    return [a for a in art
            if a["sheet"] == sheet
            and col_from <= a["col"] <= col_to
            and row_from <= a["row"] < row_to]


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

ROMAN_RE = re.compile(r"^[ilIL]{1,3}$")

# The same item is typed on two different tabs and the spellings drift. These
# are the pairs that do not line up on their own. Matching by similarity was
# tried and got Encrypted Orders I and II the wrong way round, so the list is
# spelled out instead.
ITEM_ALIASES = {
    "gliterringdiamond": "glitteringdiamond",
    "encyptedorders": "encryptedorders",
}


def item_key(name):
    """Lower case, no punctuation, and a trailing "ll" read as the roman
    numeral it was meant to be, so Encrypted Orders ll finds Orders II."""
    words = name.split()
    if words and ROMAN_RE.match(words[-1]):
        words[-1] = "i" * len(words[-1])
    key = re.sub(r"[^a-z0-9]", "", " ".join(words).lower())
    for wrong, right in ITEM_ALIASES.items():
        if key.startswith(wrong):
            key = right + key[len(wrong):]
    return key


def champion_of(name, champ_items):
    """The champion that drops this item, or None."""
    return champ_items.get(item_key(name))


def item_list(items, champ_items):
    """champ_items is the set of item names that only champion monsters drop.
    The sheet marks those with a cell colour, which the CSV export loses, so
    they are recognised by name instead."""
    if not items:
        return ""
    rows = []
    for it in items:
        qty = ('<b>%sx</b>' % esc(it["qty"])) if it["qty"] else ""
        champ = champion_of(it["name"], champ_items)
        source = it["from"] or champ or ""
        note = ('<em>%s</em>' % esc(source)) if source else ""
        mark = ' class="-champ"' if champ else ""
        rows.append("<li%s>%s<span>%s</span>%s</li>"
                    % (mark, qty, esc(it["name"]), note))
    return '<ul class="mvp-items">%s</ul>' % "".join(rows)


def drop_table(entry):
    if not entry:
        return ""
    rows = "".join(
        "<li><span>%s</span><b>%s</b></li>" % (esc(name), esc(rate))
        for name, rate in entry.get("drops", []))
    parts = ['<ul class="mvp-drops">%s</ul>' % rows] if rows else []

    if entry.get("exp"):
        parts.append('<p class="mvp-exp"><span data-i18n="mvp.exp">MVP bonus experience</span>'
                     '<b>%s</b></p>' % esc(entry["exp"]))
    if entry.get("mvpItems"):
        bits = ", ".join("%s %s" % (esc(n), esc(r)) for n, r in entry["mvpItems"])
        parts.append('<p class="mvp-exp"><span data-i18n="mvp.reward">MVP reward</span>'
                     '<b>%s</b></p>' % bits)
    return "".join(parts)


def gallery(shots):
    if not shots:
        return ""
    return '<div class="mvp-gallery">%s</div>' % "".join(
        '<img src="%s" alt="" width="%d" height="%d" loading="lazy" decoding="async">'
        % (a["file"], a["w"], a["h"]) for a in shots)


def boss_card(boss, cards, drops, art, champ_items):
    slug = slugify(boss["name"])
    card = card_for(boss["name"], cards)
    entry = drops.get(boss["name"])

    lo, hi = (0, SPLIT_COL) if boss["side"] == "left" else (SPLIT_COL + 1, 30)
    shots = art_for(art, "locations", boss["row"] - 2, boss["end"], lo, hi)
    tiles = [a for a in shots if a["kind"] != "drops"]

    thumb = ""
    if tiles:
        first = tiles[0]
        thumb = ('<img class="mvp-thumb" src="%s" alt="" width="%d" height="%d" '
                 'loading="lazy" decoding="async">'
                 % (first["file"], first["w"], first["h"]))

    paths = []
    if boss["common"]:
        paths.append("""          <div class="mvp-path">
            <h4><span data-i18n="mvp.opt1">Option 1</span></h4>
            {items}
          </div>""".format(items=item_list(boss["common"], champ_items)))
    if boss["champion"]:
        paths.append("""          <div class="mvp-path -champ">
            <h4><span data-i18n="mvp.opt2">Option 2</span></h4>
            {items}
          </div>""".format(items=item_list(boss["champion"], champ_items)))

    more = []
    if entry:
        more.append(drop_table(entry))
    if card:
        more.append('<div class="mvp-card-note"><b>%s Card</b>'
                    '<span class="mvp-slot">%s</span><p>%s</p></div>'
                    % (esc(card["name"]), esc(card["slot"]), esc(card["effect"])))
    # the rest of the pictures, drop table screenshot included, so the
    # transcription above can be checked against the source
    more.append(gallery([a for a in shots if a is not tiles[0]] if tiles
                        else shots))
    more = "".join(x for x in more if x)

    details = ""
    if more:
        details = """
          <details class="mvp-more">
            <summary data-i18n="mvp.more">Drops, card and screenshots</summary>
            <div class="mvp-more-body">{more}</div>
          </details>""".format(more=more)

    search = " ".join([boss["name"], boss["map"]] +
                      [i["name"] for i in boss["common"] + boss["champion"]])

    return """        <article class="mvp-card" id="b-{slug}" data-mvp data-search="{search}" data-champ="{champ}">
          <div class="mvp-head">
            {thumb}
            <div>
              <h3>{name}</h3>
              <span class="mvp-map">{map}</span>
            </div>
          </div>
          <div class="mvp-paths">
{paths}
          </div>{details}
        </article>""".format(
        slug=slug, name=esc(boss["name"]), map=esc(boss["map"]), thumb=thumb,
        paths="\n".join(paths), details=details,
        champ="yes" if any(champion_of(i["name"], champ_items)
                           for i in boss["common"] + boss["champion"]) else "no",
        search=esc(search.lower()))


def nightmare_card(boss, cards, drops, art, champ_items):
    card = card_for(boss["name"], cards)
    entry = drops.get(boss["name"])
    shots = [a for a in art if a["sheet"] == "nightmare"
             and boss["row"] - 1 <= a["row"] < boss["row"] + 10]
    tiles = [a for a in shots if a["kind"] != "drops"]

    thumb = ""
    if tiles:
        first = tiles[0]
        thumb = ('<img class="mvp-thumb" src="%s" alt="" width="%d" height="%d" '
                 'loading="lazy" decoding="async">'
                 % (first["file"], first["w"], first["h"]))

    more = "".join(x for x in [drop_table(entry) if entry else "",
                               ('<div class="mvp-card-note"><b>%s Card</b>'
                                '<span class="mvp-slot">%s</span><p>%s</p></div>'
                                % (esc(card["name"]), esc(card["slot"]),
                                   esc(card["effect"]))) if card else "",
                               gallery(tiles[1:])] if x)
    details = ""
    if more:
        details = """
          <details class="mvp-more">
            <summary data-i18n="mvp.more">Drops, card and screenshots</summary>
            <div class="mvp-more-body">{more}</div>
          </details>""".format(more=more)

    return """        <article class="mvp-card" id="b-{slug}" data-mvp data-search="{search}" data-champ="no">
          <div class="mvp-head">
            {thumb}
            <div>
              <h3>{name}</h3>
              <span class="mvp-map">{maps}</span>
            </div>
          </div>
          <div class="mvp-paths">
            <div class="mvp-path">
              <h4><span data-i18n="mvp.altarItems">Altar items</span></h4>
              {items}
            </div>
          </div>{details}
        </article>""".format(
        slug=slugify(boss["name"]), name=esc(boss["name"]), thumb=thumb,
        maps=esc(" and ".join(boss["maps"])),
        items=item_list(boss["common"], champ_items),
        details=details,
        search=esc((boss["name"] + " " + " ".join(boss["maps"]) + " " +
                    " ".join(i["name"] for i in boss["common"])).lower()))


def champion_rows(champions, bosses):
    """Each champion drop, with the bosses that ask for it."""
    wanted = {}
    for b in bosses:
        for it in b["champion"] + b["common"]:
            wanted.setdefault(it["name"].lower(), set()).add(b["name"])

    rows = []
    for ch in champions:
        users = sorted(wanted.get(ch["item"].lower(), []))
        opens = ", ".join(users) if users else ""
        rows.append("""          <tr data-champ-row data-search="{search}">
            <td>{mob}</td>
            <td><span class="mvp-map">{map}</span></td>
            <td>{item}</td>
            <td class="dim">{opens}</td>
          </tr>""".format(mob=esc(ch["mob"]), map=esc(ch["map"]),
                          item=esc(ch["item"]), opens=esc(opens),
                          search=esc((ch["mob"] + " " + ch["map"] + " " +
                                      ch["item"] + " " + opens).lower())))
    return "\n".join(rows)


def relic_where(item, sizes):
    """The map a piece is found on, its minimap, and the strip of icons the
    sheet uses to show what it costs. The strip is shown rather than written
    out because the sheet never names those materials: they are icons and a
    number, and guessing at the names would put words on the page that are in
    no source."""
    map_name = item.get("map", "")
    shots = []
    for part in ("map", "cost"):
        stem = "%s-%s" % (slugify(item["name"]), part)
        size = sizes.get(stem)
        if not size:
            continue
        shots.append('<img class="relic-%s" src="assets/img/relic/%s.webp" '
                     'alt="" width="%d" height="%d" loading="lazy" '
                     'decoding="async">' % (part, stem, size[0], size[1]))

    if not map_name and not shots:
        return ""

    where = ""
    if map_name:
        where = ('<p class="relic-where-line">'
                 '<span data-i18n="mvp.relicWhere">Found on</span> '
                 '<span class="mvp-map">%s</span></p>' % esc(map_name))
    art = ('<div class="relic-shots">%s</div>' % "".join(shots)) if shots else ""
    return '\n          <div class="relic-where">%s%s</div>' % (where, art)


def relic_section():
    """Relic gear, transcribed off the tooltip screenshots in the sheet. The
    same entries go into the item database, so this is the readable overview
    and the database is where you search."""
    try:
        data = json.load(io.open(os.path.join(SRC, "relic-gear.json"),
                                 encoding="utf-8"))
    except (IOError, ValueError):
        return ""
    try:
        sizes = json.load(io.open(os.path.join(SRC, "relic-art.json"),
                                  encoding="utf-8"))
    except (IOError, ValueError):
        sizes = {}                       # fetch_relic_art.py has not been run

    cards = []
    for it in data.get("items", []):
        stat = it.get("stat", "")
        label = "ATK/MATK" if it["slot"] == "weapon" else "DEF/MDEF"
        badges = ""
        if stat:
            badges += '<i class="sk-lv">%s %s</i>' % (esc(label), esc(stat))
        if it.get("level"):
            badges += ('<i class="sk-lv"><span data-i18n="mvp.relicLevel">'
                       'Level</span> %d</i>' % it["level"])

        bits = []
        for line in it.get("mastery", []):
            bits.append('<li class="-mastery">%s</li>' % colorize(esc(line)))
        for line in it.get("effect", []):
            bits.append("<li>%s</li>" % colorize(esc(line)))

        foot = []
        if it.get("classes"):
            foot.append(esc(it["classes"]))
        if it.get("weight"):
            foot.append("Weight %d" % it["weight"])

        cards.append("""        <article class="relic-card">
          <div class="relic-top">
            <strong>{name}</strong>
            <span class="relic-type">{type}</span>
          </div>
          <div class="relic-badges">{badges}</div>
          <ul class="relic-lines">{bits}</ul>
          {foot}{where}
        </article>""".format(
            name=esc(it["name"]), type=esc(it.get("type", "")), badges=badges,
            bits="".join(bits), where=relic_where(it, sizes),
            foot=('<p class="relic-foot">%s</p>' % ", ".join(foot)) if foot else ""))

    return """
  <section class="section-pad-sm" id="relics">
    <div class="shell">
      <div class="section-head">
        <p class="eyebrow" data-i18n="mvp.relicEyebrow">Relic gear</p>
        <h2 data-i18n="mvp.relicTitle">Relic gear, and where it is found</h2>
        <p class="lede" data-i18n="mvp.relicLede">Every piece is found on one map, and the sheet pairs it with the materials it takes. Each one holds three enchant options on top, unlocked one map at a time. These {n} are the ones written up so far.</p>
      </div>
      <div class="relic-grid">
{cards}
      </div>
      <p class="note" style="margin-top:1.1rem">
        <span data-i18n="mvp.relicCostNote">The sheet never names those materials. It shows their icons and a number, so the strip under each piece is the sheet's own, left as it is rather than guessed at.</span>
        <a href="quests.html#q-relic-gear-options" style="color:var(--accent-soft);text-decoration:underline;text-underline-offset:3px" data-i18n="mvp.relicOptionsLink">Where the enchant options are unlocked</a>
      </p>
      <p class="note" style="margin-top:0.5rem">
        <span data-i18n="mvp.relicNote">Every one of these is in the item database too, under the Relic Gear category, if you would rather search than scroll.</span>
        <a href="database.html?item=Assassin+Dagger" style="color:var(--accent-soft);text-decoration:underline;text-underline-offset:3px" data-i18n="mvp.relicLink">Open the database</a>
      </p>
    </div>
  </section>
""".format(cards="\n".join(cards), n=len(cards))


def build():
    bosses = parse_bosses()
    night = parse_nightmare()
    champions = parse_champions()
    cards = parse_cards()
    art = load_json("mvp-art.json", [])
    drops = load_json("mvp-drops.json", {}).get("bosses", {})

    ld = """<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "{site}/" }},
    {{ "@type": "ListItem", "position": 2, "name": "Database", "item": "{site}/database.html" }},
    {{ "@type": "ListItem", "position": 3, "name": "MVPs", "item": "{site}/mvps.html" }}
  ]
}}
</script>""".format(site=SITE)

    parts = [
        head("", "MVP altars and boss drops | Nightmare RO",
             "Every summonable boss on Nightmare RO: which map its altar is on, "
             "the two item lists that open it, what it drops and which card it "
             "leaves behind.",
             "mvps.html", ld),
        header("", "mvps.html"),
        """<main id="main">
  <section class="page-head">
    <div class="shell">
      <nav class="breadcrumb" aria-label="Breadcrumb"><ol>
        <li><a href="index.html" data-i18n="nav.home">Home</a></li>
        <li><a href="database.html" data-i18n="nav.database">Database</a></li>
        <li data-i18n="nav.mvps">MVPs and altars</li>
      </ol></nav>
      <div class="section-head">
        <p class="eyebrow">{count} <span data-i18n="mvp.eyebrow">bosses</span></p>
        <h1 data-i18n="mvp.title">Bosses do not wander here. You call them</h1>
        <p class="lede" data-i18n="mvp.lede">Every boss sits behind an altar on one map. To open it you hand over one of two lists. Option 1 is usually a pile of ordinary drops from that map. Option 2 is a handful of items that only champion monsters carry, marked in gold below. Plenty of altars offer just one of the two.</p>
        <p class="guide-credit"><span data-i18n="mvp.credit">Altars, drop tables and relic gear documented by</span> <b>guild [SENAI]</b></p>
      </div>
    </div>
  </section>

  <section class="section-pad-sm">
    <div class="shell">
      <div class="filter-bar">
        <button class="chip" type="button" data-mvp-filter="all" aria-pressed="true" data-i18n="mvp.fAll">All</button>
        <button class="chip" type="button" data-mvp-filter="champ" aria-pressed="false" data-i18n="mvp.fChamp">Needs a champion drop</button>
        <button class="chip" type="button" data-mvp-filter="farm" aria-pressed="false" data-i18n="mvp.fFarm">Ordinary drops only</button>
        <div class="search-field">
          <svg aria-hidden="true"><use href="#i-search"></use></svg>
          <label class="visually-hidden" for="mvpSearch" data-i18n="mvp.searchLabel">Search bosses, maps and items</label>
          <input id="mvpSearch" type="search" placeholder="Search a boss, a map or an item" autocomplete="off"
                 data-i18n-attr="placeholder:mvp.search">
        </div>
      </div>
      <div class="mvp-grid" id="mvpGrid">
""".format(count=len(bosses) + len(night)),
    ]

    champ_items = dict((item_key(c["item"]), c["mob"]) for c in champions)

    parts.append("\n".join(boss_card(b, cards, drops, art, champ_items)
                           for b in bosses))
    parts.append("""
      </div>
      <p class="empty-state" id="mvpEmpty" hidden data-i18n="mvp.empty">Nothing matched that search.</p>
    </div>
  </section>
""")

    if night:
        parts.append("""
  <section class="section-pad-sm" id="nightmare">
    <div class="shell">
      <div class="section-head">
        <p class="eyebrow" data-i18n="mvp.nightEyebrow">Nightmare dungeons</p>
        <h2 data-i18n="mvp.nightTitle">The ones at the deep end</h2>
        <p class="lede" data-i18n="mvp.nightLede">Same altar rule, harder dungeon, and the summon lists run into the hundreds. This part of the sheet is still being filled in.</p>
      </div>
      <div class="mvp-grid">
{cards}
      </div>
    </div>
  </section>
""".format(cards="\n".join(nightmare_card(b, cards, drops, art, champ_items) for b in night)))

    parts.append("""
  <section class="section-pad-sm" id="champions">
    <div class="shell">
      <div class="section-head">
        <p class="eyebrow" data-i18n="mvp.champEyebrow">Champion drops</p>
        <h2 data-i18n="mvp.champTitle">Where the short list comes from</h2>
        <p class="lede" data-i18n="mvp.champLede">Champion monsters are the rare, buffed version of a map's regular spawns. Each one carries a single item, and that item is the shortcut past a few hundred ordinary drops.</p>
      </div>
      <div class="table-wrap">
        <table class="mvp-table">
          <thead>
            <tr>
              <th data-i18n="mvp.thChampion">Champion</th>
              <th data-i18n="mvp.thMap">Map</th>
              <th data-i18n="mvp.thItem">Drops</th>
              <th data-i18n="mvp.thOpens">Opens</th>
            </tr>
          </thead>
          <tbody id="champBody">
{rows}
          </tbody>
        </table>
      </div>
    </div>
  </section>
""".format(rows=champion_rows(champions, bosses)))

    parts.append(relic_section())

    parts.append("""
  <section class="section-pad-sm">
    <div class="shell">
      <div class="cta-band">
        <div class="inner">
          <h2 data-i18n="band.title">Come find out what changed</h2>
          <p class="lede text-center" data-i18n="band.lede">Make an account, grab the client, and come and see what changed.</p>
          <div class="hero-actions">
            <a class="btn -primary -lg" href="{reg}" target="_blank" rel="noopener" data-i18n="cta.registerFree">Create a free account</a>
            <a class="btn -ghost -lg" href="database.html" data-i18n="nav.items">Items and cards</a>
            <a class="btn -ghost -lg" href="quests.html" data-i18n="nav.quests">Quests</a>
          </div>
        </div>
      </div>
    </div>
  </section>
</main>
""".format(reg=REGISTER))

    parts.append(footer("").replace(
        '<script src="assets/js/main.js" defer></script>',
        '<script src="assets/js/main.js" defer></script>\n'
        '<script src="assets/js/mvps.js" defer></script>'))

    io.open(OUT, "w", encoding="utf-8", newline="\n").write("".join(parts))
    print("mvps.html: %d bosses, %d nightmare, %d champion drops (%.0f KB)"
          % (len(bosses), len(night), len(champions),
             os.path.getsize(OUT) / 1024.0))

    missing = [b["name"] for b in bosses if b["name"] not in drops]
    if missing:
        print("No drop table yet for: %s" % ", ".join(missing))


if __name__ == "__main__":
    build()
