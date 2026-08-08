#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds classes.html and every page under classes/ from tools/classes.json.

Run it from the project root:

    python tools/build_classes.py

classes.json is the text of the Class Overviews document, already split by
class. To refresh it after Twilight updates the doc, re-run tools/extract.py.
"""

import io
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from status_codex import STATUS, colorize, families_in
from skills import build as build_skills, load_wiki, mark_mechanics, type_family

WIKI_SKILLS = load_wiki()

# The eight colour families the wiki's seventy type labels fold into, in the
# order they show up in the key under the status legend.
TYPE_KEY = [
    ("physical", "Physical"),
    ("magic", "Magic"),
    ("support", "Support"),
    ("debuff", "Debuff"),
    ("summon", "Summon"),
    ("stance", "Stance"),
    ("passive", "Passive"),
    ("utility", "Utility"),
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tools", "classes.json")
OUT_DIR = os.path.join(ROOT, "classes")
IMG_DIR = os.path.join(ROOT, "assets", "img", "classes")
SIZES_FILE = os.path.join(ROOT, "tools", "art-sizes.json")

# Real pixel sizes for the artwork, written by prepare_art.py. Missing
# entries just mean no width/height attribute, which still renders fine.
try:
    ART_SIZES = json.load(io.open(SIZES_FILE, encoding="utf-8"))
except (IOError, ValueError):
    ART_SIZES = {}


def art_dims(name):
    size = ART_SIZES.get(name)
    return ' width="%d" height="%d"' % (size[0], size[1]) if size else ""


# Three classes where the "male" and "female" artwork is really two separate
# jobs that share one page. They get shown side by side and labelled, rather
# than hidden behind a gender toggle.
PAIRED = {
    "Bard and Dancer": ("Bard", "Dancer"),
    "Clown/Gypsy": ("Clown", "Gypsy"),
    "Minstrel/Wanderer": ("Minstrel", "Wanderer"),
}

SITE = "https://nightmarero.pages.dev"
REGISTER = "https://nightmareofragnarok.com/?module=account&amp;action=create"
DISCORD = "https://discord.gg/gHgFtmvudD"
WIKI = "https://wiki.nightmareofragnarok.com/"

# --------------------------------------------------------------------------
# Class tree. (family label, [(first, [(second, [third, third]), ...])])
# --------------------------------------------------------------------------

TREE = [
    ("Swordsman", [
        ("Knight", ["Lord Knight", "Rune Knight"]),
        ("Crusader", ["Paladin", "Royal Guard"]),
    ]),
    ("Merchant", [
        ("Blacksmith", ["Mastersmith", "Mechanic"]),
        ("Alchemist", ["Biochemist", "Geneticist"]),
    ]),
    ("Thief", [
        ("Assassin", ["Assassin Cross", "Guillotine Cross"]),
        ("Rogue", ["Stalker", "Shadow Chaser"]),
    ]),
    ("Mage", [
        ("Wizard", ["High Wizard", "Warlock"]),
        ("Sage", ["Scholar", "Sorcerer"]),
    ]),
    ("Archer", [
        ("Hunter", ["Sniper", "Ranger"]),
        ("Bard and Dancer", ["Clown/Gypsy", "Minstrel/Wanderer"]),
    ]),
    ("Acolyte", [
        ("Priest", ["High Priest", "Arch Bishop"]),
        ("Monk", ["Champion", "Sura"]),
    ]),
    ("Taekwon", [
        ("Star Gladiator", ["Star Emperor", "Sky Emperor"]),
        ("Soul Linker", ["Soul Reaper", "Soul Ascetic"]),
    ]),
    ("Ninja", [
        (None, ["Kagemusha", "Maboroshi"]),
    ]),
    ("Gunslinger", [
        (None, ["Rebel", "Night Watch"]),
    ]),
]

TIER_LABEL = {1: "First tier", 2: "Second tier", 3: "Third tier"}
LEVEL_RANGE = {1: "Base level 1 to 50", 2: "Base level 51 to 99", 3: "Base level 100 to 150"}
LEVEL_RANGE_SOLO = {1: "Base level 1 to 99", 3: "Base level 100 to 150"}

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

QUOTES = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": " to ", "—": ", ", "…": "...", " ": " ",
    "�": "'",
}


def tidy(text):
    """Normalise punctuation. Em dashes are deliberately removed."""
    for bad, good in QUOTES.items():
        text = text.replace(bad, good)
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()


def esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


def slugify(name):
    s = name.lower().replace("/", "-").replace(" and ", "-")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def has_art(slug):
    """Returns the sexes that have artwork available, in display order."""
    out = []
    for sex in ("male", "female"):
        if os.path.exists(os.path.join(IMG_DIR, "%s-%s.webp" % (slug, sex))):
            out.append(sex)
    return out


# --------------------------------------------------------------------------
# Shared chrome
# --------------------------------------------------------------------------

SPRITE = """<svg width="0" height="0" aria-hidden="true" style="position:absolute">
  <symbol id="i-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2v2.4M12 19.6V22M2 12h2.4M19.6 12H22M4.9 4.9l1.7 1.7M17.4 17.4l1.7 1.7M19.1 4.9l-1.7 1.7M6.6 17.4l-1.7 1.7"/></symbol>
  <symbol id="i-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20.5 14.3A8.6 8.6 0 0 1 9.7 3.5a8.6 8.6 0 1 0 10.8 10.8Z"/></symbol>
  <symbol id="i-globe" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.7 3.9 6.1 3.9 9s-1.3 6.3-3.9 9c-2.6-2.7-3.9-6.1-3.9-9S9.4 5.7 12 3Z"/></symbol>
  <symbol id="i-menu" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></symbol>
  <symbol id="i-close" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></symbol>
  <symbol id="i-discord" viewBox="0 0 24 24" fill="currentColor"><path d="M19.3 5.3A16.9 16.9 0 0 0 15.1 4l-.3.6a12.6 12.6 0 0 1 3.7 1.9 15.5 15.5 0 0 0-12.9 0 12.6 12.6 0 0 1 3.7-1.9L9 4a16.9 16.9 0 0 0-4.2 1.3C2.1 9.3 1.4 13.2 1.7 17a17 17 0 0 0 5.2 2.6l1.1-1.7a11 11 0 0 1-1.8-.9l.4-.3a12.1 12.1 0 0 0 10.4 0l.4.3a11 11 0 0 1-1.8.9l1.1 1.7A17 17 0 0 0 22 17c.4-4.4-.7-8.3-2.7-11.7ZM8.4 14.7c-1 0-1.9-.9-1.9-2.1s.8-2.1 1.9-2.1 1.9 1 1.9 2.1-.8 2.1-1.9 2.1Zm7.2 0c-1 0-1.9-.9-1.9-2.1s.8-2.1 1.9-2.1 1.9 1 1.9 2.1-.8 2.1-1.9 2.1Z"/></symbol>
  <symbol id="i-download" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12M7.5 10.5 12 15l4.5-4.5M4 17v2.5a1.5 1.5 0 0 0 1.5 1.5h13a1.5 1.5 0 0 0 1.5-1.5V17"/></symbol>
  <symbol id="i-book" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H19v15H5.5A1.5 1.5 0 0 0 4 19.5Z"/><path d="M4 19.5A1.5 1.5 0 0 1 5.5 21H19v-3"/></symbol>
  <symbol id="i-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h13M12.5 5.5 19 12l-6.5 6.5"/></symbol>
  <symbol id="i-search" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="11" cy="11" r="6.4"/><path d="m16 16 4.5 4.5"/></symbol>
  <symbol id="i-image" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"><rect x="3" y="4.5" width="18" height="15" rx="2"/><circle cx="8.5" cy="10" r="1.6"/><path d="m4 17 5-4.5 4 3.5 3-2.5 4 3.5"/></symbol>
</svg>"""


def head(prefix, title, description, canonical, extra_ld="", og_image="assets/social/og-cover.jpg"):
    return """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{site}/{canon}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<meta name="theme-color" content="#07060a" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f4f1ee" media="(prefers-color-scheme: light)">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Nightmare RO">
<meta property="og:url" content="{site}/{canon}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{site}/{ogimg}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{site}/{ogimg}">
<link rel="icon" href="{p}assets/img/icon-32.png" sizes="32x32">
<link rel="apple-touch-icon" href="{p}assets/img/icon-180.png">
<link rel="manifest" href="{p}site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{p}assets/css/style.css">
<!-- The webfonts are on someone else's server, so they are loaded out of the
     critical path: the page paints in the fallback face and swaps when they
     arrive, instead of holding first paint on a third party round trip. -->
<link rel="stylesheet" media="print" onload="this.media='all'" href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap"></noscript>
<script>
(function () {{
  try {{
    var t = localStorage.getItem('nm-theme');
    if (!t) t = matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    document.documentElement.dataset.theme = t;
  }} catch (e) {{}}
}})();
</script>
{ld}
</head>
<body>
<a class="skip-link" href="#main" data-i18n="a11y.skip">Skip to content</a>
{sprite}
""".format(title=esc(title), desc=esc(description), site=SITE, canon=canonical,
           p=prefix, ld=extra_ld, sprite=SPRITE, ogimg=og_image)


# The nav entries that open onto more than one page. Both the desktop
# dropdowns and the drawer groups are generated from these, so a page added
# here shows up in both without touching the markup.
#
# Every entry carries a line of its own, because a label alone was making
# people guess: "Database" and "The game" both sound like they might hold the
# element table. The line says what is actually behind the link.
#
#   (page, label key, label, blurb key, blurb)
NEW_PAGES = [
    ("guide.html", "nav.route", "Levelling route",
     "navd.route", "Where to grind at every level"),
    ("mechanics.html", "nav.mech", "How it works",
     "navd.mech", "Stats, elements, refining, commands"),
    ("quiz.html", "nav.quiz", "Class test",
     "navd.quiz", "Six questions, one class to try"),
]
DB_PAGES = [
    ("database.html", "nav.items", "Items and cards",
     "navd.items", "Every drop, card and set bonus"),
    ("mvps.html", "nav.mvps", "MVPs and altars",
     "navd.mvps", "What to hand in, and what drops"),
    ("quests.html", "nav.quests", "Quests",
     "navd.quests", "Walkthroughs, with spoilers gated"),
]
GAME_PAGES = [
    ("index.html#server", "nav.server", "The server",
     "navd.server", "What makes this one different"),
    ("endgame.html", "nav.endgame", "End game",
     "navd.endgame", "Champions, raids, reputation"),
    ("index.html#faq", "nav.faq", "FAQ",
     "navd.faq", "The short answers"),
]
DROPS = [("nav.guide", "Start here", NEW_PAGES),
         ("nav.database", "Database", DB_PAGES),
         ("nav.game", "The game", GAME_PAGES)]


def nav_drop(prefix, active, key, label, pages):
    inside = any(page == active for page, _k, _l, _bk, _b in pages)
    items = "".join(
        '''
          <a href="{p}{page}" role="menuitem"{cur}>
            <b data-i18n="{k}">{l}</b>
            <span data-i18n="{bk}">{b}</span>
          </a>'''
        .format(p=prefix, page=page, k=k, l=l, bk=bk, b=b,
                cur=' aria-current="page"' if page == active else "")
        for page, k, l, bk, b in pages)
    return """      <div class="nav-drop">
        <button class="nav-drop-btn{open}" type="button" aria-expanded="false" aria-haspopup="true" data-i18n="{key}">{label}</button>
        <div class="nav-drop-menu" role="menu">{items}
        </div>
      </div>""".format(open=" -on" if inside else "", key=key, label=label,
                       items=items)


def nav_desktop(prefix, active):
    drops = {key: nav_drop(prefix, active, key, label, pages)
             for key, label, pages in DROPS}

    return """{new}
      <a href="{p}classes.html"{c_classes} data-i18n="nav.classes">Classes</a>
{db}
{game}
      <a href="https://wiki.nightmareofragnarok.com/" target="_blank" rel="noopener" data-i18n="nav.wiki">Wiki</a>
      <a href="{p}download.html"{c_dl} data-i18n="nav.download">Download</a>""".format(
        p=prefix, game=drops["nav.game"], new=drops["nav.guide"],
        db=drops["nav.database"],
        c_classes=' aria-current="page"' if active == "classes.html" else "",
        c_dl=' aria-current="page"' if active == "download.html" else "")


def drawer_group(prefix, active, key, label, pages):
    subs = "".join(
        '''
      <a class="-sub" href="{p}{page}"{cur}>
        <b data-i18n="{k}">{l}</b>
        <span data-i18n="{bk}">{b}</span>
      </a>'''
        .format(p=prefix, page=page, k=k, l=l, bk=bk, b=b,
                cur=' aria-current="page"' if page == active else "")
        for page, k, l, bk, b in pages)
    return ('      <span class="drawer-group" data-i18n="%s">%s</span>%s'
            % (key, label, subs))


def nav_drawer(prefix, active=""):
    groups = {key: drawer_group(prefix, active, key, label, pages)
              for key, label, pages in DROPS}
    return """{new}
      <a href="{p}classes.html"{c_classes} data-i18n="nav.classes">Classes</a>
{db}
{game}
      <a href="https://wiki.nightmareofragnarok.com/" target="_blank" rel="noopener" data-i18n="nav.wiki">Wiki</a>
      <a href="{p}download.html"{c_dl} data-i18n="nav.download">Download</a>""".format(
        p=prefix, game=groups["nav.game"], new=groups["nav.guide"],
        db=groups["nav.database"],
        c_classes=' aria-current="page"' if active == "classes.html" else "",
        c_dl=' aria-current="page"' if active == "download.html" else "")


def header(prefix, active):
    return """<header class="site-header" id="siteHeader">
  <div class="shell header-inner">
    <a class="brand" href="{p}index.html" aria-label="Nightmare RO, home">
      <img src="{p}assets/img/logo.webp" alt="Nightmare RO" width="180" height="38" fetchpriority="high">
    </a>
    <nav class="nav" aria-label="Main">
{navmain}
    </nav>
    <div class="header-tools">
      <button class="icon-btn" id="themeToggle" type="button" aria-label="Switch theme" title="Switch theme">
        <svg class="i-sun" aria-hidden="true"><use href="#i-sun"></use></svg>
        <svg class="i-moon" aria-hidden="true"><use href="#i-moon"></use></svg>
      </button>
      <div class="lang">
        <button class="lang-btn" id="langBtn" type="button" aria-haspopup="true" aria-expanded="false" aria-label="Change language">
          <svg aria-hidden="true"><use href="#i-globe"></use></svg>
          <span class="lang-code" id="langCode">EN</span>
        </button>
        <div class="lang-menu" id="langMenu" role="menu" aria-labelledby="langBtn"></div>
      </div>
      <a class="btn -primary -sm header-cta" href="{reg}" target="_blank" rel="noopener" data-i18n="cta.register">Create account</a>
      <button class="icon-btn burger" id="burger" type="button" aria-label="Open menu" aria-expanded="false">
        <svg aria-hidden="true"><use href="#i-menu"></use></svg>
      </button>
    </div>
  </div>
</header>

<div class="drawer" id="drawer" role="dialog" aria-modal="true" aria-label="Menu">
  <div class="shell">
    <div class="drawer-top">
      <img src="{p}assets/img/logo.webp" alt="Nightmare RO" width="150" height="32">
      <button class="icon-btn" id="drawerClose" type="button" aria-label="Close menu">
        <svg aria-hidden="true"><use href="#i-close"></use></svg>
      </button>
    </div>
    <nav aria-label="Mobile">
{navdrawer}
    </nav>
    <div class="drawer-actions">
      <a class="btn -primary -block" href="{reg}" target="_blank" rel="noopener" data-i18n="cta.register">Create account</a>
      <a class="btn -ghost -block" href="{dc}" target="_blank" rel="noopener">
        <svg aria-hidden="true"><use href="#i-discord"></use></svg><span data-i18n="cta.discord">Join the Discord</span>
      </a>
    </div>
  </div>
</div>
""".format(p=prefix, reg=REGISTER, dc=DISCORD, wiki=WIKI,
           navmain=nav_desktop(prefix, active),
           navdrawer=nav_drawer(prefix, active))


def footer(prefix):
    return """<footer class="site-footer">
  <div class="shell">
    <div class="footer-grid">
      <div>
        <img src="{p}assets/img/logo.webp" alt="Nightmare RO" width="170" height="36" loading="lazy">
        <p class="dim" style="margin-top:1rem;max-width:34ch" data-i18n="footer.blurb">A fully custom private server. Rebuilt, rebalanced and still being worked on.</p>
      </div>
      <div>
        <h4 data-i18n="footer.play">Play</h4>
        <ul>
          <li><a href="{reg}" target="_blank" rel="noopener" data-i18n="cta.register">Create account</a></li>
          <li><a href="{p}download.html" data-i18n="nav.download">Download</a></li>
          <li><a href="{p}classes.html" data-i18n="nav.classes">Classes</a></li>
          <li><a href="{p}quiz.html" data-i18n="nav.quiz">Class test</a></li>
          <li><a href="{p}database.html" data-i18n="nav.database">Database</a></li>
          <li><a href="{p}index.html#faq" data-i18n="nav.faq">FAQ</a></li>
        </ul>
      </div>
      <div>
        <h4 data-i18n="footer.community">Community</h4>
        <ul>
          <li><a href="{dc}" target="_blank" rel="noopener">Discord</a></li>
          <li><a href="https://wiki.nightmareofragnarok.com/" target="_blank" rel="noopener" data-i18n="footer.wiki">Player wiki</a></li>
          <li><a href="https://nightmareofragnarok.com/" target="_blank" rel="noopener" data-i18n="footer.panel">Control panel</a></li>
        </ul>
      </div>
      <div>
        <h4 data-i18n="footer.references">References</h4>
        <ul>
          <li><a href="https://docs.google.com/spreadsheets/d/e/2PACX-1vT3yuB3St__9v202ZUU9pUZm4PX88tph379Dr2eMR3TFNfZ0GUVD0tvuBl99Ma8GHp5e2pLzLG6Bmds/pubhtml" target="_blank" rel="noopener" data-i18n="footer.gear">Gear reference</a></li>
          <li><a href="https://docs.google.com/spreadsheets/d/e/2PACX-1vRaVCw9eEP3D-VlpBCryCcXy84FkDTm2RU-whdMIAZ8HuYhRvlsQrKqBiUUQlcLHq6gUqq6PXeUKB_5/pubhtml" target="_blank" rel="noopener" data-i18n="footer.cards">Card reference</a></li>
          <li><a href="https://docs.google.com/document/d/e/2PACX-1vSlu9yEhoRVn5ob2yCJ8f_lOEQLq476hibjolBnnpDko-VXRWiB88o7aumdASXs0WwC0a1aTgH2QcjP/pub" target="_blank" rel="noopener" data-i18n="footer.overview">Full server overview</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <span data-i18n="footer.legal">Nightmare RO is a free, non-commercial fan project. Not affiliated with any commercial game publisher.</span>
      <span>&copy; <span id="year">2026</span> Nightmare RO</span>
    </div>
  </div>
</footer>

<script src="{p}assets/js/i18n.js" defer></script>
<script src="{p}assets/js/main.js" defer></script>
</body>
</html>
""".format(p=prefix, reg=REGISTER, dc=DISCORD)


# --------------------------------------------------------------------------
# Build the flat class registry
# --------------------------------------------------------------------------

def build_registry():
    reg = {}
    order = []

    for first, branches in TREE:
        reg[first] = {"name": first, "tier": 1, "family": first,
                      "parent": None, "children": []}
        order.append(first)

        for second, thirds in branches:
            if second:
                reg[second] = {"name": second, "tier": 2, "family": first,
                               "parent": first, "children": list(thirds)}
                reg[first]["children"].append(second)
                order.append(second)
                parent = second
            else:
                reg[first]["children"].extend(thirds)
                parent = first

            for third in thirds:
                reg[third] = {"name": third, "tier": 3, "family": first,
                              "parent": parent, "children": []}
                order.append(third)

    for i, name in enumerate(order):
        reg[name]["slug"] = slugify(name)
        reg[name]["prev"] = order[i - 1] if i else None
        reg[name]["next"] = order[i + 1] if i + 1 < len(order) else None
        reg[name]["index"] = i

    return reg, order


# --------------------------------------------------------------------------
# Class page
# --------------------------------------------------------------------------

def portrait_block(slug, name):
    sexes = has_art(slug)
    if not sexes:
        return """      <div class="portrait">
        <div class="portrait-empty">
          <svg aria-hidden="true"><use href="#i-image"></use></svg>
          <span data-i18n="cls.noArt">Artwork for this class is on the way.</span>
        </div>
      </div>"""

    pair = PAIRED.get(name)
    if pair and len(sexes) > 1:
        figures = "".join("""
        <figure>
          <img src="../assets/img/classes/{s}-{x}.webp" alt="{label}"{dim} loading="eager" decoding="async">
          <figcaption>{label}</figcaption>
        </figure>""".format(s=slug, x=x, label=esc(label),
                            dim=art_dims("%s-%s" % (slug, x)))
            for x, label in (("male", pair[0]), ("female", pair[1])))
        return '      <div class="portrait -pair">%s\n      </div>' % figures

    first = sexes[0]
    toggle = ""
    if len(sexes) > 1:
        buttons = "".join(
            '<button type="button" data-src="../assets/img/classes/{s}-{x}.webp" '
            'data-alt="{n} {x}" aria-pressed="{p}" data-i18n="cls.{x}">{L}</button>'.format(
                s=slug, x=x, n=esc(name), p="true" if x == first else "false",
                L=x.capitalize())
            for x in sexes)
        toggle = '\n        <div class="sex-toggle" role="group" aria-label="Character art">%s</div>' % buttons

    return """      <div class="portrait">{toggle}
        <img src="../assets/img/classes/{slug}-{first}.webp" alt="{name} character art"{dim} loading="eager" decoding="async">
      </div>""".format(toggle=toggle, slug=slug, first=first, name=esc(name),
                       dim=art_dims("%s-%s" % (slug, first)))


def rich(text, mechanics):
    """Escape, colour the statuses, then mark the class mechanics."""
    return mark_mechanics(colorize(esc(text)), mechanics)


def skill_anchor(name):
    return "s-" + slugify(name)


def skill_card(skill, mechanics, by_name):
    fam = type_family(skill["type"]) if skill["type"] else "other"
    bits = ['          <li class="skill-card sk-%s" id="%s">'
            % (fam, skill_anchor(skill["name"]))]

    badges = ""
    if skill["type"]:
        badges += '<i class="sk-type">%s</i>' % esc(skill["type"])
    if skill["max"] and skill["max"] not in ("0", "1", "-"):
        badges += '<i class="sk-lv">Lv %s</i>' % esc(skill["max"])
    bits.append('            <div class="sk-top"><strong>%s</strong>%s</div>'
                % (esc(skill["name"]), badges))

    if skill["short"]:
        bits.append('            <p class="sk-short">%s</p>'
                    % rich(skill["short"], mechanics))

    for para in skill["body"]:
        bits.append('            <p class="sk-body">%s</p>' % rich(para, mechanics))

    if skill["options"]:
        items = "".join(
            "<li><b>%s</b>%s</li>" % (rich(o["label"], mechanics),
                                      rich(o["text"], mechanics))
            for o in skill["options"])
        bits.append('            <ul class="sk-options">%s</ul>' % items)

    if skill["riders"]:
        items = "".join("<li>%s</li>" % rich(r, mechanics) for r in skill["riders"])
        bits.append('            <ul class="sk-riders">%s</ul>' % items)

    if skill["needs"]:
        links = "".join('<a href="#%s">%s</a>' % (skill_anchor(n), esc(n))
                        for n in skill["needs"] if n in by_name)
        if links:
            bits.append('            <p class="sk-needs">'
                        '<span data-i18n="cls.needs">Works with</span>%s</p>' % links)

    bits.append("          </li>")
    return "\n".join(bits)


def skills_section(tree):
    """The whole skills block: legends first, then one grid per branch."""
    skills = tree["skills"]
    if not skills:
        return ""

    mechanics = tree["mechanics"]
    by_name = set(s["name"] for s in skills)

    # Only chip the statuses this class actually uses.
    page_text = esc(" ".join(tree["intro"]) + " " + " ".join(
        s["name"] + " " + s["short"] + " " + " ".join(s["body"] + s["riders"] +
        [o["label"] + " " + o["text"] for o in s["options"]]) for s in skills))
    chips = families_in(page_text)

    legend = ""
    if chips:
        legend = ('      <div class="kw-legend" style="margin-bottom:0.75rem">%s'
                  '<a href="../classes.html#codex" data-i18n="cls.legendMore">'
                  'What these do</a></div>\n' %
                  "".join('<span class="kw-%s">%s</span>' % (k, l)
                          for k, l, _t, _d in chips))

    strip = ""
    if mechanics:
        strip = ('      <div class="mech-strip">'
                 '<em data-i18n="cls.mechanics">This class runs on</em>%s</div>\n'
                 % "".join("<span>%s</span>" % esc(m) for m in mechanics))

    used = []
    for key, label in TYPE_KEY:
        if any(type_family(s["type"]) == key for s in skills if s["type"]):
            used.append('<span class="sk-%s" data-i18n="cls.t.%s">%s</span>'
                        % (key, key, label))
    key_row = ""
    if len(used) > 1:
        key_row = '      <div class="type-key">%s</div>\n' % "".join(used)

    blocks = []
    for group in tree["groups"]:
        cards = "\n".join(skill_card(s, mechanics, by_name) for s in group["skills"])
        # the count is only worth showing when there is more than one, which
        # also keeps every language out of singular and plural trouble
        count = ('<span>%d <span data-i18n="cls.skillWord">skills</span></span>'
                 % len(group["skills"])) if len(group["skills"]) > 1 else ""
        blocks.append("""      <div class="skill-branch">
        <h3 class="branch-title">{label}{count}</h3>
        <ul class="skill-grid">
{cards}
        </ul>
      </div>""".format(label=esc(group["label"]), count=count, cards=cards))

    return """
  <section class="section-pad-sm" id="skills">
    <div class="shell">
      <div class="section-head">
        <p class="eyebrow" data-i18n="cls.skillsEyebrow">Skill list</p>
        <h2 data-i18n="cls.skillsTitle">Skills</h2>
        <p class="muted" data-i18n="cls.skillsNote">Grouped the way the tree is grouped. Names, types and level caps come from the player wiki, so they match what you see in game.</p>
      </div>
{strip}{legend}{key}
{blocks}
    </div>
  </section>
""".format(strip=strip, legend=legend, key=key_row, blocks="\n".join(blocks))


def path_map(reg, name):
    info = reg[name]
    chain = []
    node = name
    while node:
        chain.append(node)
        node = reg[node]["parent"]
    chain.reverse()

    parts = []
    for i, step in enumerate(chain):
        if i:
            parts.append('<span class="arrow" aria-hidden="true">&rsaquo;</span>')
        if step == name:
            parts.append('<span class="current">%s</span>' % esc(step))
        else:
            parts.append('<a href="%s.html">%s</a>' % (reg[step]["slug"], esc(step)))

    for i, kid in enumerate(info["children"]):
        parts.append('<span class="arrow" aria-hidden="true">%s</span>'
                     % ("&rsaquo;" if i == 0 else "or"))
        parts.append('<a href="%s.html">%s</a>' % (reg[kid]["slug"], esc(kid)))

    return '<div class="path-map">%s</div>' % "".join(parts)


DISCORD_VIDEOS = "https://discord.gg/gHgFtmvudD"


def load_videos():
    """Community videos, keyed by class slug. See tools/data/class-videos.json."""
    path = os.path.join(ROOT, "tools", "data", "class-videos.json")
    try:
        return json.load(io.open(path, encoding="utf-8")).get("videos", {})
    except (IOError, ValueError):
        return {}


CLASS_VIDEOS = load_videos()


def videos_section(slug):
    """Players record their fights and post them in Discord. Each card is a
    thumbnail and a play button rather than an embed, because 5 embedded
    players would cost more than the rest of the page put together. The iframe
    is only created once someone actually clicks."""
    clips = CLASS_VIDEOS.get(slug, [])

    if not clips:
        body = """      <p class="vid-empty" data-i18n="cls.noVideos">No videos for this class yet. Record your gameplay and post it in the Discord.</p>
      <p><a class="btn -ghost" href="{dc}" target="_blank" rel="noopener" data-i18n="cta.discord">Join the Discord</a></p>""".format(dc=DISCORD_VIDEOS)
    else:
        cards = "".join("""
        <button class="vid-card" type="button" data-video="{vid}" aria-label="Play: {t}">
          <img src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="" width="480" height="360" loading="lazy" decoding="async">
          <span class="vid-play" aria-hidden="true"></span>
          <span class="vid-meta"><span class="vid-title">{t}</span><span class="vid-by">{by}</span></span>
        </button>""".format(vid=esc(c["id"]), t=esc(c["title"]), by=esc(c.get("by", "")))
            for c in clips)
        body = '      <div class="vid-grid">%s\n      </div>' % cards

    return """
  <section class="section-pad-sm" id="videos">
    <div class="shell">
      <div class="section-head">
        <p class="eyebrow" data-i18n="cls.videosEyebrow">From the players</p>
        <h2 data-i18n="cls.videosTitle">See it played</h2>
      </div>
{body}
    </div>
  </section>
""".format(body=body)


def class_page(reg, name, blocks):
    info = reg[name]
    slug = info["slug"]
    tree = build_skills(name, blocks, WIKI_SKILLS)
    intro = tree["intro"]

    tier = info["tier"]
    if info["family"] in ("Ninja", "Gunslinger"):
        levels = LEVEL_RANGE_SOLO.get(tier, LEVEL_RANGE[tier])
    else:
        levels = LEVEL_RANGE[tier]

    summary = intro[0] if intro else "%s is a playable class on Nightmare RO." % name
    desc = (summary[:157] + "...") if len(summary) > 160 else summary

    # Every community clip on the page gets a VideoObject, which is what puts
    # a class page in the video results rather than only the web results.
    clips = "".join("""    ,{{
      "@type": "VideoObject",
      "name": "{t}",
      "description": "{t}, played on Nightmare RO.",
      "thumbnailUrl": "https://i.ytimg.com/vi/{v}/hqdefault.jpg",
      "uploadDate": "2026-01-01",
      "embedUrl": "https://www.youtube-nocookie.com/embed/{v}"
    }}""".format(t=esc(c["title"].replace('"', "'")), v=esc(c["id"]))
        for c in CLASS_VIDEOS.get(slug, []))

    ld = """<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@graph": [
    {{
      "@type": "BreadcrumbList",
      "itemListElement": [
        {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "{site}/" }},
        {{ "@type": "ListItem", "position": 2, "name": "Classes", "item": "{site}/classes.html" }},
        {{ "@type": "ListItem", "position": 3, "name": "{name}", "item": "{site}/classes/{slug}.html" }}
      ]
    }},
    {{
      "@type": "Article",
      "headline": "{name} class guide",
      "about": "{name}",
      "inLanguage": "en",
      "isPartOf": {{ "@type": "WebSite", "name": "Nightmare RO", "url": "{site}/" }},
      "publisher": {{ "@type": "Organization", "name": "Nightmare RO" }},
      "description": "{desc}"
    }}
{clips}
  ]
}}
</script>""".format(site=SITE, name=esc(name), slug=slug,
                    desc=esc(desc.replace('"', "'")), clips=clips)

    title = "%s | Nightmare RO class guide" % name

    # The class artwork makes a far better share card than the site cover, and
    # it is what people are pasting into Discord anyway.
    sexes = has_art(slug)
    og = ("assets/img/classes/%s-%s.webp" % (slug, sexes[0])) if sexes \
        else "assets/social/og-cover.jpg"

    parts = [head("../", title, desc, "classes/%s.html" % slug, ld, og),
             header("../", "classes.html"),
             '<main id="main">']

    # ---- hero
    parts.append("""
  <section class="page-head">
    <div class="shell">
      <nav class="breadcrumb" aria-label="Breadcrumb"><ol>
        <li><a href="../index.html" data-i18n="nav.home">Home</a></li>
        <li><a href="../classes.html" data-i18n="nav.classes">Classes</a></li>
        <li>{name}</li>
      </ol></nav>
    </div>
  </section>

  <section>
    <div class="shell class-hero">
      <div class="stack">
        <p class="eyebrow" data-i18n="tier.{tier}">{tierlabel}</p>
        <h1>{name}</h1>
        <div class="tier-tags">
          <span class="tag -accent" data-i18n="tier.{tier}">{tierlabel}</span>
          <span class="tag">{levels}</span>
          <span class="tag">{family} line</span>
        </div>
        {intro}
      </div>
{portrait}
    </div>
  </section>
""".format(name=esc(name), tier=tier, tierlabel=TIER_LABEL[tier], levels=esc(levels),
           family=esc(info["family"]),
           intro="\n        ".join(
               '<p class="muted">%s</p>' % rich(p, tree["mechanics"])
               for p in intro),
           portrait=portrait_block(slug, name)))

    # ---- path
    parts.append("""
  <section class="section-pad-sm">
    <div class="shell stack">
      <p class="eyebrow" data-i18n="cls.path">Where it sits</p>
      {pmap}
    </div>
  </section>
""".format(pmap=path_map(reg, name)))

    # ---- skills
    parts.append(skills_section(tree))

    # ---- community videos
    parts.append(videos_section(info["slug"]))

    # ---- pager
    prev, nxt = info["prev"], info["next"]
    pager = []
    if prev:
        pager.append('        <a href="{s}.html"><small data-i18n="cls.prev">Previous class</small><strong>{n}</strong></a>'
                     .format(s=reg[prev]["slug"], n=esc(prev)))
    if nxt:
        pager.append('        <a class="-next" href="{s}.html"><small data-i18n="cls.next">Next class</small><strong>{n}</strong></a>'
                     .format(s=reg[nxt]["slug"], n=esc(nxt)))

    parts.append("""
  <section class="section-pad-sm">
    <div class="shell">
      <div class="pager">
{pager}
      </div>
      <div class="cta-band mt-xl">
        <div class="inner">
          <h2 data-i18n="band.title">Come find out what changed</h2>
          <p class="lede text-center" data-i18n="band.lede">Make an account, grab the client, and come and see what changed.</p>
          <div class="hero-actions">
            <a class="btn -primary -lg" href="{reg}" target="_blank" rel="noopener" data-i18n="cta.registerFree">Create a free account</a>
            <a class="btn -ghost -lg" href="{wiki}" target="_blank" rel="noopener">
              <svg aria-hidden="true"><use href="#i-book"></use></svg><span data-i18n="cta.wiki">Open the wiki</span>
            </a>
            <a class="btn -ghost -lg" href="../classes.html" data-i18n="cta.allClasses">See the revamped classes</a>
          </div>
        </div>
      </div>
    </div>
  </section>

</main>
""".format(pager="\n".join(pager), reg=REGISTER, wiki=WIKI))

    parts.append(footer("../"))
    return "".join(parts)


# --------------------------------------------------------------------------
# Classes index
# --------------------------------------------------------------------------

def index_card(reg, name):
    info = reg[name]
    slug = info["slug"]
    sexes = has_art(slug)
    pair = PAIRED.get(name)
    extra = ""

    if pair and len(sexes) > 1:
        # Both counterparts on the card, side by side.
        extra = " -pair"
        art = "".join(
            '<img class="art -{k}" src="assets/img/classes/{s}-{x}-sm.webp" alt="{label}"{dim} '
            'loading="lazy" decoding="async">'.format(
                k=x[0], s=slug, x=x, label=esc(label),
                dim=art_dims("%s-%s-sm" % (slug, x)))
            for x, label in (("male", pair[0]), ("female", pair[1])))
    elif sexes:
        art = ('<img class="art" src="assets/img/classes/{s}-{x}-sm.webp" alt="{n}"{dim} '
               'loading="lazy" decoding="async">'
               .format(s=slug, x=sexes[0], n=esc(name),
                       dim=art_dims("%s-%s-sm" % (slug, sexes[0]))))
    else:
        art = '<span class="art-fallback" aria-hidden="true">%s</span>' % esc(name[0])

    return """          <a class="class-card{extra}" href="classes/{slug}.html" data-class data-tier="{tier}" data-search="{search}">
            {art}
            <span class="meta"><em data-i18n="tier.{tier}">{tierlabel}</em><strong>{name}</strong></span>
          </a>""".format(slug=slug, tier=info["tier"], art=art, name=esc(name),
                         extra=extra, tierlabel=TIER_LABEL[info["tier"]],
                         search=esc((name + " " + info["family"]).lower()))


def classes_index(reg):
    ld = """<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "{site}/" }},
    {{ "@type": "ListItem", "position": 2, "name": "Classes", "item": "{site}/classes.html" }}
  ]
}}
</script>""".format(site=SITE)

    parts = [head("", "Revamped Classes | Nightmare RO",
                  "Every playable class on Nightmare RO, revamped. Nine starting classes, fourteen second tier and thirty two third tier classes, each with a fully rewritten skill set.",
                  "classes.html", ld),
             header("", "classes.html"),
             """<main id="main">
  <section class="page-head">
    <div class="shell">
      <nav class="breadcrumb" aria-label="Breadcrumb"><ol>
        <li><a href="index.html" data-i18n="nav.home">Home</a></li>
        <li data-i18n="nav.classes">Classes</li>
      </ol></nav>
      <div class="section-head">
        <p class="eyebrow" data-i18n="idx.eyebrow">Revamped classes</p>
        <h1 data-i18n="idx.title">Pick something and see how little you remember</h1>
        <p class="lede" data-i18n="idx.lede">Every skill tree here was written from a blank page. Nine starting classes, fourteen second tier classes, and thirty two third tier classes, each branching two ways from its parent.</p>
      </div>
    </div>
  </section>

  <section class="section-pad-sm">
    <div class="shell">
      <p class="note" style="margin-bottom:var(--gap-md)">
        <span data-i18n="idx.quizNudge">That is a lot to read through. If you are not sure where to start, the class test asks thirteen questions and picks one for you.</span>
        <a href="quiz.html" style="color:var(--accent-soft);text-decoration:underline;text-underline-offset:3px" data-i18n="idx.quizLink">Take the test</a>
      </p>
      <div class="filter-bar">
        <button class="chip" type="button" data-tier="all" aria-pressed="true" data-i18n="idx.all">All</button>
        <button class="chip" type="button" data-tier="1" aria-pressed="false" data-i18n="tier.1">First tier</button>
        <button class="chip" type="button" data-tier="2" aria-pressed="false" data-i18n="tier.2">Second tier</button>
        <button class="chip" type="button" data-tier="3" aria-pressed="false" data-i18n="tier.3">Third tier</button>
        <div class="search-field">
          <svg aria-hidden="true"><use href="#i-search"></use></svg>
          <label class="visually-hidden" for="classSearch" data-i18n="idx.searchLabel">Search classes</label>
          <input id="classSearch" type="search" placeholder="Search classes" autocomplete="off"
                 data-i18n-attr="placeholder:idx.search">
        </div>
      </div>

      <div id="classIndex">"""]

    for family, branches in TREE:
        names = [family]
        for second, thirds in branches:
            if second:
                names.append(second)
            names.extend(thirds)

        cards = "\n".join(index_card(reg, n) for n in names)
        parts.append("""
        <div class="branch">
          <div class="branch-head">
            <h2>{family}</h2>
            <span>{count} classes</span>
          </div>
          <div class="class-grid">
{cards}
          </div>
        </div>""".format(family=esc(family), count=len(names), cards=cards))

    codex_cards = "\n".join(
        """        <li class="kw-{key}">
          <i class="swatch" aria-hidden="true"></i>
          <div>
            <b>{label}</b>
            <span data-i18n="codex.{key}">{desc}</span>
            <em>{terms}</em>
          </div>
        </li>""".format(key=key, label=esc(label), desc=esc(desc),
                        # length first, then alphabetical, so the build is
                        # reproducible when two terms are the same length
                        terms=esc(", ".join(sorted(set(terms), key=lambda w: (-len(w), w))[:3])))
        for key, label, terms, desc in STATUS)

    parts.append("""
      </div>
      <p class="empty-state" id="classEmpty" hidden data-i18n="idx.empty">Nothing matched that search.</p>
    </div>
  </section>

  <section class="section-pad-sm" id="codex">
    <div class="shell">
      <div class="section-head">
        <p class="eyebrow" data-i18n="codex.eyebrow">Status codex</p>
        <h2 data-i18n="codex.title">The colours you will see in every skill</h2>
        <p class="lede" data-i18n="codex.lede">Combat here runs on status effects. Durations are short, effects are strong, and most skills read the target before deciding what to do. Each family gets a colour, used everywhere on this site.</p>
      </div>
      <ul class="codex">
{codex}
      </ul>
    </div>
  </section>
""".format(codex=codex_cards))

    parts.append("""

  <section class="section-pad-sm">
    <div class="shell">
      <div class="cta-band">
        <div class="inner">
          <h2 data-i18n="band.title">Come find out what changed</h2>
          <p class="lede text-center" data-i18n="band.lede">Make an account, grab the client, and come and see what changed.</p>
          <div class="hero-actions">
            <a class="btn -primary -lg" href="{reg}" target="_blank" rel="noopener" data-i18n="cta.registerFree">Create a free account</a>
            <a class="btn -ghost -lg" href="{wiki}" target="_blank" rel="noopener">
              <svg aria-hidden="true"><use href="#i-book"></use></svg><span data-i18n="cta.wiki">Open the wiki</span>
            </a>
            <a class="btn -ghost -lg" href="download.html" data-i18n="cta.download">Download</a>
          </div>
        </div>
      </div>
    </div>
  </section>
</main>
""".format(reg=REGISTER, wiki=WIKI))

    parts.append(footer(""))
    return "".join(parts)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Class brief, consumed by the personality test
# --------------------------------------------------------------------------

def write_brief(reg, order, data):
    """A small JSON with just enough per class for quiz.html to draw a result
    card: one line of flavour, a handful of skills, and the artwork path."""
    out = []
    for name in order:
        info = reg[name]
        tree = build_skills(name, data.get(name, []), WIKI_SKILLS)
        intro, skills = tree["intro"], tree["skills"]
        slug = info["slug"]
        sexes = has_art(slug)

        summary = intro[0] if intro else ""
        # keep it to two sentences so the card stays readable
        bits = re.split(r"(?<=\.)\s+", summary)
        summary = " ".join(bits[:2]).strip()

        picked = []
        for sk in skills:
            # the wiki one liner if there is one, otherwise the document's
            # first sentence
            text = sk["short"] or re.split(r"(?<=\.)\s+",
                                           " ".join(sk["body"]).strip())[0]
            if not text:
                continue
            picked.append({"name": sk["name"], "text": text})
            if len(picked) == 5:
                break

        out.append({
            "slug": slug,
            "name": name,
            "tier": info["tier"],
            "family": info["family"],
            "parent": info["parent"],
            "summary": summary,
            "skills": picked,
            "art": ("assets/img/classes/%s-%s.webp" % (slug, sexes[0])) if sexes else None,
        })

    path = os.path.join(ROOT, "assets", "data", "classes-brief.json")
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        json.dumps({"count": len(out), "classes": out},
                   ensure_ascii=False, separators=(",", ":")))
    print("assets/data/classes-brief.json: %d classes (%.0f KB)"
          % (len(out), os.path.getsize(path) / 1024.0))


def main():
    data = json.load(io.open(DATA, encoding="utf-8"))
    reg, order = build_registry()

    missing_data = [n for n in order if n not in data]
    if missing_data:
        print("No document section for: %s" % ", ".join(missing_data))

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    for name in order:
        html = class_page(reg, name, data.get(name, []))
        path = os.path.join(OUT_DIR, reg[name]["slug"] + ".html")
        io.open(path, "w", encoding="utf-8", newline="\n").write(html)

    io.open(os.path.join(ROOT, "classes.html"), "w", encoding="utf-8",
            newline="\n").write(classes_index(reg))

    write_brief(reg, order, data)

    no_art = [n for n in order if not has_art(reg[n]["slug"])]
    print("Wrote %d class pages plus classes.html" % len(order))
    print("Classes still without artwork (%d):" % len(no_art))
    for n in no_art:
        print("  - %s  ->  %s-male.png / %s-female.png" %
              (n, reg[n]["slug"], reg[n]["slug"]))

    io.open(os.path.join(ROOT, "tools", "missing-art.txt"), "w",
            encoding="utf-8", newline="\n").write("\n".join(no_art))


if __name__ == "__main__":
    main()
