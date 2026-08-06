#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds quests.html from the spoiler quest sheet.

    python tools/fetch_mvps.py      # CSV tabs
    python tools/fetch_mvp_art.py   # the screenshots, with their anchor cells
    python tools/build_quests.py

Each quest is one tab: a column of numbered steps with screenshots dropped in
between them. Because the screenshots are floating images, the CSV export
cannot see them at all, so their anchor rows come from mvp-art.json and every
picture is filed under the step above it.

The sheet is written in Portuguese. tools/data/quest-text.json holds the
English for each line, keyed by the original, and anything without a
translation falls through unchanged.
"""

import csv
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_classes import esc, head, header, footer, slugify, SITE, REGISTER

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "data")
OUT = os.path.join(ROOT, "quests.html")

# (csv stem, title, one line of what it gets you)
QUESTS = [
    ("quest-lighthalzen-entrance", "Lighthalzen dungeon entrance",
     "Two ways in, neither of them signposted."),
    ("quest-amatsu", "Amatsu field and dungeon",
     "Getting to Amatsu at all, then getting under it."),
    ("quest-relic-gear-options", "Relic gear options",
     "Where each of the three enchant slots is unlocked."),
    ("quest-fallen-hero", "Fallen Hero",
     "The gate quest. Several other quests will not talk to you until this one is done."),
    ("quest-true-hero-shadow-gloves", "True Hero Shadow Gloves",
     "A long errand through Veins and Hugel for one piece of shadow gear."),
    ("quest-niflheim-challenge", "Niflheim challenge dungeon",
     "The witch, the piano and two endings you can both take."),
    ("quest-kiel-challenge", "Kiel challenge dungeon",
     "A door, a password, and a robot factory."),
    ("quest-thor-challenge", "Thor challenge dungeon",
     "Buying your way past a metal gate."),
    ("quest-black-ops", "Black Ops",
     "Collect the relics, hand in the intel, follow it to Aldebaran."),
    ("quest-celine-kimi", "Celine Kimi",
     "The longest one here. Lutie, Juno, Prontera and back again."),
    ("quest-endless-desert", "Endless Desert",
     "The map that loops. Here is the route table."),
]

STEP_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[.:)]?\s+(.*)$")

# Two tabs hold a reference table rather than a list of steps, and reading a
# table one cell per line is useless. (first row, last row, first row is a
# header). Rows in these ranges are pulled out of the step list.
TABLES = {
    "quest-endless-desert": [(1, 4, False), (8, 24, True)],
    "quest-relic-gear-options": [(1, 3, True)],
}


def read_csv(name):
    path = os.path.join(SRC, name + ".csv")
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8") as fh:
        return [[c.strip() for c in row] for row in csv.reader(fh)]


def load_json(name, default):
    try:
        return json.load(io.open(os.path.join(SRC, name), encoding="utf-8"))
    except (IOError, ValueError):
        return default


def lines_of(rows):
    """Every non empty cell, with the row it sits on. The sheet writes a step
    in the first column it feels like, so column is not worth tracking."""
    out = []
    for r, row in enumerate(rows):
        for cell in row:
            if cell:
                out.append({"row": r, "text": cell})
    return out


def table_html(rows, first, last, has_head, phrases):
    """A block of sheet rows rendered as a table, empty columns dropped."""
    block = [r for r in rows[first:last + 1] if any(c for c in r)]
    if not block:
        return ""
    width = max(len(r) for r in block)
    keep = [c for c in range(width)
            if any(c < len(r) and r[c] for r in block)]

    def cells(row, tag):
        return "".join(
            "<%s>%s</%s>" % (tag,
                             esc(phrases.get(row[c], row[c]) if c < len(row) else ""),
                             tag)
            for c in keep)

    head_html = ""
    body = block
    if has_head:
        head_html = "<thead><tr>%s</tr></thead>" % cells(block[0], "th")
        body = block[1:]
    rows_html = "".join("<tr>%s</tr>" % cells(r, "td") for r in body)
    return ('<div class="table-wrap"><table class="mvp-table">%s<tbody>%s'
            "</tbody></table></div>" % (head_html, rows_html))


def build_steps(stem, art, phrases):
    rows = read_csv(stem)
    if not rows:
        return []

    blocked = set()
    for first, last, _head in TABLES.get(stem, []):
        blocked.update(range(first, last + 1))

    lines = [ln for ln in lines_of(rows) if ln["row"] not in blocked]
    shots = sorted([a for a in art if a["sheet"] == stem],
                   key=lambda a: (a["row"], a["col"]))

    steps = []
    for i, line in enumerate(lines):
        end = lines[i + 1]["row"] if i + 1 < len(lines) else 10 ** 6
        text = phrases.get(line["text"], line["text"])
        found = STEP_RE.match(text)
        steps.append({
            "row": line["row"],
            "n": found.group(1) if found else "",
            "text": found.group(2).strip() if found else text,
            "table": "",
            "shots": [a for a in shots if line["row"] <= a["row"] < end],
        })

    # pictures anchored above the first line still belong to the quest
    if steps:
        first = lines[0]["row"]
        steps[0]["shots"] = ([a for a in shots if a["row"] < first] +
                             steps[0]["shots"])

    for first, last, has_head in TABLES.get(stem, []):
        steps.append({"row": first, "n": "", "text": "", "shots": [],
                      "table": table_html(rows, first, last, has_head, phrases)})

    steps.sort(key=lambda s: s["row"])
    return steps


def shot_html(shots):
    if not shots:
        return ""
    return '<div class="q-shots">%s</div>' % "".join(
        '<img src="%s" alt="" width="%d" height="%d" loading="lazy" decoding="async">'
        % (a["file"], a["w"], a["h"]) for a in shots)


def quest_section(stem, title, blurb, steps):
    items = []
    for step in steps:
        marker = ('<span class="q-n">%s</span>' % esc(step["n"])) if step["n"] else ""
        text = ("<p>%s</p>" % esc(step["text"])) if step["text"] else ""
        items.append("""          <li class="q-step">
            {marker}
            <div>
              {text}
              {table}
              {shots}
            </div>
          </li>""".format(marker=marker, text=text, table=step["table"],
                          shots=shot_html(step["shots"])))

    return """      <details class="q-quest" id="q-{slug}">
        <summary>
          <span class="q-title">{title}</span>
          <span class="q-blurb">{blurb}</span>
        </summary>
        <ol class="q-steps">
{items}
        </ol>
      </details>""".format(slug=slugify(title), title=esc(title),
                           blurb=esc(blurb), items="\n".join(items))


# --------------------------------------------------------------------------
# Potions, from the fan wiki
# --------------------------------------------------------------------------

POTIONS = [
    ("Health potions", [
        ("Red Potion", ["Bought, not crafted"], "Heals 100 to 200 HP"),
        ("Orange Potion", ["1 Red Potion", "15 Red Herb", "5 Yellow Herb",
                           "15 Stem"], "Heals 400 to 600 HP"),
        ("Yellow Potion", ["1 Orange Potion", "25 Yellow Herb",
                           "30 Mantis Scythe", "30 Moth Dust"],
         "Heals 1000 to 2000 HP"),
        ("White Potion", ["1 Yellow Potion", "30 White Herb",
                          "1 Burning Shard", "1 Enchanted Key", "1 Pyroxene"],
         "Heals 3000 to 6000 HP"),
    ]),
    ("Spirit potions", [
        ("Grape Juice", ["25 Grape", "10 Ant Jaw", "10 Golden Hair"],
         "Heals 50 to 100 SP"),
        ("Blue Potion", ["1 Grape Juice", "25 Blue Herb", "25 Grave Dust",
                         "25 Blazing Stone", "25 Broken Urn"],
         "Heals 400 to 600 SP"),
    ]),
    ("Attack speed potions", [
        ("Concentration Potion", ["25 Mushroom Spore", "1 Gnome's Moustache",
                                  "1 Memento"], ""),
        ("Awakening Potion", ["1 Concentration Potion", "25 Mushroom Spore",
                              "25 Poison Spore", "1 Detrimindexta",
                              "1 Ancient Tooth", "1 Cultish Mask"], ""),
        ("Berserk Potion", ["Base level 100", "1 Awakening Potion",
                            "50 Mushroom Spore", "50 Poison Spore",
                            "10 Detrimindexta", "10 Karvodailnirol"], ""),
    ]),
    ("Other", [
        ("Green Potion", ["25 Green Herb", "25 Stem", "25 Scell",
                          "25 Nine Tail"], ""),
    ]),
]

POTION_SOURCE = "https://twilight-senai.tiddlyhost.com/?page=potions"


def potion_section():
    groups = []
    for label, rows in POTIONS:
        items = "".join(
            """            <tr>
              <td><b>{name}</b></td>
              <td>{needs}</td>
              <td class="dim">{effect}</td>
            </tr>""".format(
                name=esc(name),
                needs="".join('<span class="q-mat">%s</span>' % esc(x)
                              for x in needs),
                effect=esc(effect))
            for name, needs, effect in rows)
        groups.append("""        <h3 class="q-potion-head">{label}</h3>
        <div class="table-wrap">
          <table class="mvp-table">
            <thead><tr>
              <th data-i18n="q.thPotion">Potion</th>
              <th data-i18n="q.thNeeds">Needs</th>
              <th data-i18n="q.thEffect">Effect</th>
            </tr></thead>
            <tbody>
{items}
            </tbody>
          </table>
        </div>""".format(label=esc(label), items=items))

    return """
  <section class="section-pad-sm" id="potions">
    <div class="shell">
      <div class="section-head">
        <p class="eyebrow" data-i18n="q.potionEyebrow">Potion crafting</p>
        <h2 data-i18n="q.potionTitle">Everything upgrades from the tier below</h2>
        <p class="lede" data-i18n="q.potionLede">Potions are crafted and upgraded at the Alchemist Guild in Aldebaran. Each tier eats one of the tier under it, so the ladder starts at the Red Potion and works up.</p>
      </div>
      <p class="note" data-i18n="q.potionWarn">This part comes from a player made wiki rather than from Twilight, and it was last touched in October 2024. Treat the amounts as a guide and check in game before you go farming.</p>
{groups}
      <p class="dim" style="margin-top:1rem">
        <span data-i18n="q.potionSource">Source</span>
        <a href="{src}" target="_blank" rel="noopener">twilight-senai.tiddlyhost.com</a>
      </p>
    </div>
  </section>
""".format(groups="\n".join(groups), src=POTION_SOURCE)


# --------------------------------------------------------------------------

def taekwon_section():
    rows = read_csv("mvp-spoiler-quest")
    missions = [c for row in rows for c in row
                if re.match(r"^\d+ mission:", c)]
    if not missions:
        return ""
    items = "".join(
        "<li><span class=\"q-n\">%s</span><div><p>%s</p></div></li>"
        % (esc(m.split(" ", 1)[0]), esc(m.split(":", 1)[1].strip()))
        for m in missions)
    return """
  <section class="section-pad-sm" id="taekwon">
    <div class="shell">
      <div class="section-head">
        <p class="eyebrow" data-i18n="q.tkEyebrow">Taekwon mission</p>
        <h2 data-i18n="q.tkTitle">Five rounds of boss hunting</h2>
        <p class="lede" data-i18n="q.tkLede">The Taekwon Mission skill raises the job level cap, and it costs you the ability to change jobs ever again. These are the five rounds it asks for.</p>
      </div>
      <ol class="q-steps">{items}</ol>
    </div>
  </section>
""".format(items=items)


def build():
    art = load_json("mvp-art.json", [])
    phrases = load_json("quest-text.json", {})

    sections, count = [], 0
    for stem, title, blurb in QUESTS:
        steps = build_steps(stem, art, phrases)
        if not steps:
            continue
        sections.append(quest_section(stem, title, blurb, steps))
        count += 1

    ld = """<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "{site}/" }},
    {{ "@type": "ListItem", "position": 2, "name": "Database", "item": "{site}/database.html" }},
    {{ "@type": "ListItem", "position": 3, "name": "Quests", "item": "{site}/quests.html" }}
  ]
}}
</script>""".format(site=SITE)

    parts = [
        head("", "Quest walkthroughs, spoilers included | Nightmare RO",
             "Step by step routes for the hidden quests on Nightmare RO: "
             "challenge dungeon keys, the Fallen Hero chain, Celine Kimi, "
             "relic gear enchants and potion crafting.",
             "quests.html", ld),
        header("", "quests.html"),
        """<main id="main">
  <section class="page-head">
    <div class="shell">
      <nav class="breadcrumb" aria-label="Breadcrumb"><ol>
        <li><a href="index.html" data-i18n="nav.home">Home</a></li>
        <li><a href="database.html" data-i18n="nav.database">Database</a></li>
        <li data-i18n="nav.quests">Quests</li>
      </ol></nav>
      <div class="section-head">
        <p class="eyebrow" data-i18n="q.eyebrow">Spoilers</p>
        <h1 data-i18n="q.title">The answers, for when you want them</h1>
        <p class="lede" data-i18n="q.lede">Half the fun here is not knowing. Several of these quests have no NPC pointing at them and no log entry, and working one out with friends is the point. So nothing below is open until you say so.</p>
      </div>
    </div>
  </section>

  <section class="section-pad-sm">
    <div class="shell">
      <div class="q-gate" id="questGate">
        <div class="q-gate-inner">
          <h2 data-i18n="q.gateTitle">This page spoils things</h2>
          <p data-i18n="q.gateText">Routes, passwords, item counts and endings. Once you open it, you cannot unread it.</p>
          <button class="btn -primary -lg" type="button" id="questReveal" data-i18n="q.gateBtn">Show me anyway</button>
          <button class="btn -ghost" type="button" id="questHide" hidden data-i18n="q.gateHide">Hide it again</button>
        </div>
      </div>

      <div class="q-body" id="questBody" hidden>
""",
    ]

    parts.append("\n".join(sections))
    parts.append("""
      </div>
    </div>
  </section>
""")

    parts.append(potion_section())
    parts.append(taekwon_section())

    parts.append("""
  <section class="section-pad-sm">
    <div class="shell">
      <div class="cta-band">
        <div class="inner">
          <h2 data-i18n="band.title">Come find out what changed</h2>
          <p class="lede text-center" data-i18n="band.lede">Make an account now, grab the client, and be there when the servers go up.</p>
          <div class="hero-actions">
            <a class="btn -primary -lg" href="{reg}" target="_blank" rel="noopener" data-i18n="cta.registerFree">Create a free account</a>
            <a class="btn -ghost -lg" href="mvps.html" data-i18n="nav.mvps">MVPs and altars</a>
            <a class="btn -ghost -lg" href="database.html" data-i18n="nav.items">Items and cards</a>
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
        '<script src="assets/js/quests.js" defer></script>'))

    io.open(OUT, "w", encoding="utf-8", newline="\n").write("".join(parts))

    shots = sum(len(s["shots"]) for stem, _t, _b in QUESTS
                for s in build_steps(stem, art, phrases))
    missing = sum(1 for stem, _t, _b in QUESTS
                  for s in build_steps(stem, art, phrases)
                  if s["text"] and re.search(r"[ãõçáéíóúâêô]", s["text"]))
    print("quests.html: %d quests, %d screenshots (%.0f KB)"
          % (count, shots, os.path.getsize(OUT) / 1024.0))
    if missing:
        print("Lines still in Portuguese: %d" % missing)


if __name__ == "__main__":
    build()
