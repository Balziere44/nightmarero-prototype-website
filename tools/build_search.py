#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds the index behind the site search.

    python tools/build_search.py

The site got wide. Fifty five classes, two hundred and seventy five skills,
thirteen hundred items and cards, forty three bosses, a dozen quests and eight
reference pages, all behind a menu. Someone who wants to know what the
Moonlight Flower card does should not have to work out that cards live under
Database and not under The game.

So every one of those things gets a row in one file, and the header search
reads it. The file is fetched the first time somebody opens the search and
never again, which is why the rows are arrays and not objects: the shape is
[title, subtitle, url, group, extra search words].

Sources are the ones already built, so this runs last:

    classes-brief.json   the classes and their skills
    items.json           every item and card
    mvps.html            the boss anchors, which only exist once it is built
    quests.html          the quest anchors, same
    status_codex.py      the status families
    build_guide.py       the fields and dungeons, with their levels

Groups are ordered by how likely they are to be what was meant, and the
search bumps exact prefix matches above that.
"""

import io
import json
import os
import re
import urllib.parse
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from status_codex import STATUS
from build_guide import WHERE

DATA = os.path.join(ROOT, "assets", "data")
OUT = os.path.join(DATA, "search.json")

# group keys, in the order they are shown. The labels are translated in the
# locale files as find.g<key>.
GROUPS = ["page", "class", "skill", "item", "drops", "boss", "quest",
          "status", "map"]


# The pages and the sections inside them. Hand written, because a heading is
# not a destination: these are the answers people actually arrive looking for,
# with the words they arrive typing.
PAGES = [
    ("Home", "", "index.html", "download client install play inicio home jogar"),
    ("Download the client", "How to get in", "download.html",
     "install patch launcher setup client exe baixar instalar cliente"),
    ("Loading screens", "Class art, free to download", "loading-screens.html",
     "loading screen wallpaper art download image jpg tela de carregamento "
     "wallpaper arte baixar imagem"),
    ("Levelling route", "Where to grind at every level", "guide.html",
     "leveling level up grind route where to hunt xp exp new player upar level guia iniciante novato onde cacar"),
    ("Fields and dungeons by level", "The short list", "guide.html#where",
     "map level range where hunt field dungeon mapa nivel campo masmorra onde upar"),
    ("The world map", "Every field with its level", "guide.html#map",
     "world map ctrl tab levels mapa mundi"),
    ("Job change", "Where every job is taken", "guide.html#jobs",
     "job change npc first second third class change mudanca de classe trocar"),
    ("How it works", "Stats, elements, refining, commands", "mechanics.html",
     "mechanics formula stat cast speed aspd mecanicas formula atributos como funciona"),
    ("The element table", "What beats what", "mechanics.html#elements",
     "element fire water wind earth holy dark undead ghost poison neutral elemento tabela elemental fogo agua vento terra sagrado sombrio veneno fantasma"),
    ("Status effects", "Every family and what it does", "mechanics.html#status",
     "status bleed burn poison blind vulnerable breach frozen stun sleep slow sangramento queimadura cego lento congelado atordoado"),
    ("Random options", "What every piece can roll", "mechanics.html#options",
     "random option roll reroll slot suffix bonus opcoes aleatorias opcao "
     "rolagem atributo extra"),
    ("Shadow enchants", "Every enchant, by stat", "endgame.html#shadow",
     "shadow gear enchant nightmare costume encante encantamento sombra"),
    ("Refining", "Rates, ores and the +10 cap", "mechanics.html#refine",
     "refine upgrade ore enrich safe break refino refinar minerio upar item"),
    ("Potions", "What to carry", "mechanics.html#potions",
     "potion heal hp sp consumable pocao cura consumivel"),
    ("Commands", "The ones worth knowing", "mechanics.html#commands",
     "command slash autoloot noks storage comandos armazem"),
    ("Warps and travel", "Getting around", "mechanics.html#warps",
     "warp teleport travel town viajar cidade teleporte"),
    ("End game", "Champions, bosses, raids, reputation", "endgame.html",
     "endgame late game 150 max level fim de jogo nivel maximo"),
    ("Champion monsters", "Green aura, better drops", "endgame.html#champions",
     "champion aura relic convex mirror campeao reliquia espelho"),
    ("Nightmare mode", "The hard version", "endgame.html#nightmare",
     "nightmare hard mode difficulty pesadelo dificuldade"),
    ("Reputation", "What the factions want", "endgame.html#reputation",
     "reputation faction rep grind reputacao faccao"),
    ("Classes", "All 55, filterable", "classes.html",
     "class job tier list first second third classe profissao lista"),
    ("Status codex", "The colour key", "classes.html#codex",
     "codex status colour legend key cores legenda"),
    ("Items and cards", "Every drop, card and set", "database.html",
     "database item card gear weapon armour armor shadow relic search itens cartas equipamento arma armadura buscar"),
    ("MVPs and altars", "What to hand in, what drops", "mvps.html",
     "mvp boss altar summon drop card chefe altar invocar"),
    ("Quests", "Walkthroughs, spoilers gated", "quests.html",
     "quest walkthrough guide spoiler missao passo a passo"),
    ("The server", "What makes it different", "index.html#server",
     "about server rates pve rules sobre servidor taxas regras"),
    ("FAQ", "The short answers", "index.html#faq",
     "faq question answer free pay to win pvp woe autoloot potion quest per "
     "character where does this drop mvp altar perguntas duvidas gratis "
     "pocao onde dropa"),
    ("Class test", "Six questions, one class to try", "quiz.html",
     "quiz test personality which class should i play teste qual classe jogar"),
]


def load(name):
    return json.load(io.open(os.path.join(DATA, name), encoding="utf-8"))


def classes_rows():
    """Every class, and every skill on it.

    The brief carries five skills per class, which is what the class hub
    shows. The search wants all of them, so the skill names come off the
    scraped tables instead, matched to the class by its display name."""
    rows = []
    tiers = {1: "First job", 2: "Second job", 3: "Third job"}
    skills = json.load(io.open(os.path.join(ROOT, "tools", "data",
                                            "wiki-classes.json"),
                               encoding="utf-8"))
    for cls in load("classes-brief.json")["classes"]:
        url = "classes/%s.html" % cls["slug"]
        rows.append([cls["name"], tiers.get(cls["tier"], "Class"), url,
                     "class", cls["family"].lower()])
        for group in skills.get(cls["name"], []):
            for sk in group.get("skills", []):
                rows.append([sk["name"], cls["name"], url, "skill",
                             (sk.get("desc") or "").lower()])
    return rows


def items_rows():
    """Cards and gear both open the database with the item already picked."""
    rows = []
    for it in load("items.json")["items"]:
        name = it["name"]
        url = "database.html?item=" + name.replace(" ", "+")
        rows.append([name, it.get("cat") or it.get("slot") or "Item", url,
                     "item", (it.get("slot") or "").lower()])
    return rows


# What a "Drops From" cell can hold that is not a monster. The sheets use the
# same column for a place, and the client cannot say where anything drops.
NOT_A_MONSTER = ("not confirmed yet", "unknown", "quest", "npc", "shop",
                 "craft", "vending", "event", "cash", "unobtainable")


def drops_rows():
    """The other direction: given a monster, what does it drop?

    This is the question players actually ask, and until now the site could
    only answer it backwards, one item at a time. Every name in a "Drops From"
    cell becomes a row that opens the database already filtered to that name,
    so one click lists everything it is known to leave behind.
    """
    from_who = {}
    for it in load("items.json")["items"]:
        for name in re.split(r",(?![^(]*\))", it.get("drops") or ""):
            name = re.sub(r"\s+", " ", name).strip(" .")
            if len(name) < 3 or not re.search(r"[A-Za-z]", name):
                continue          # the sheets use ??? for "nobody knows"
            if any(bad in name.lower() for bad in NOT_A_MONSTER):
                continue
            from_who.setdefault(name, []).append(it["name"])

    rows = []
    for name, items in sorted(from_who.items()):
        # a relic's "where from" is a map code, not a monster
        what = "On this map" if re.match(r"^[a-z0-9_]+$", name) else                "%d drop%s" % (len(items), "" if len(items) == 1 else "s")
        rows.append([name, what,
                     "database.html?drops=" + urllib.parse.quote(name),
                     "drops", " ".join(items).lower()])
    return rows


def anchored(page, pattern, group, sub, flags=0):
    """Pull anchors and their headings straight out of a built page."""
    text = io.open(os.path.join(ROOT, page), encoding="utf-8").read()
    return [[name.strip(), sub, "%s#%s" % (page, anchor), group, terms]
            for anchor, terms, name in re.findall(pattern, text, flags)]


def boss_rows():
    return anchored(
        "mvps.html",
        r'id="(b-[a-z0-9-]+)" data-mvp data-search="([^"]*)"'
        r'[^>]*>.{0,400}?<h3>([^<]+)</h3>',
        "boss", "Boss", re.S)


def quest_rows():
    return anchored(
        "quests.html",
        r'id="(q-[a-z0-9-]+)">\s*<summary>\s*'
        r'<span class="q-title">([^<]+)</span>'
        r'\s*<span class="q-blurb">([^<]*)</span>',
        "quest", "Quest")


def status_rows():
    return [[label, "Status", "mechanics.html#status", "status",
             " ".join(terms).lower()]
            for _key, label, terms, _desc in STATUS]


def map_rows():
    """One row per field and dungeon, carrying the level it is good for."""
    seen = {}
    for _band, places in WHERE:
        for place, level, kind in places:
            row = seen.setdefault(place, [place, "", "guide.html#where",
                                          "map", kind])
            row[1] = "%s, level %s" % (kind.capitalize(), level)
    return list(seen.values())


def main():
    rows = ([[t, s, u, "page", k] for t, s, u, k in PAGES]
            + classes_rows() + items_rows() + drops_rows()
            + boss_rows() + quest_rows()
            + status_rows() + map_rows())

    # Two things with the same name and the same destination are one thing.
    out, seen = [], set()
    for row in rows:
        key = (row[0].lower(), row[2])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)

    order = {g: i for i, g in enumerate(GROUPS)}
    out.sort(key=lambda r: (order[r[3]], r[0].lower()))

    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps({"groups": GROUPS, "rows": out},
                   ensure_ascii=False, separators=(",", ":")))

    count = {}
    for row in out:
        count[row[3]] = count.get(row[3], 0) + 1
    print("%d rows -> assets/data/search.json (%d KB)"
          % (len(out), os.path.getsize(OUT) // 1024))
    for group in GROUPS:
        print("  %-8s %5d" % (group, count.get(group, 0)))


if __name__ == "__main__":
    sys.exit(main())
