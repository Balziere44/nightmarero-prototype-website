#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds the two reference pages that explain how the server actually works.

    python tools/build_mechanics.py

mechanics.html is the rules of combat: the experience curve, what each stat
does and what it gives you at every tenth and twenty fifth point, the crit,
cast and attack speed formulas, the element table, the status effects, the
potion ladder, the refine ladder, warps and commands.

endgame.html is everything that waits after the levelling route: champions,
summoned bosses, the Roaming Archaeologist, guilds and raids, the Nightmare
dungeons with their Depth, Resistance and Agony, the Challenge dungeons, and
the three reputation lines.

Everything on both pages comes from the Server Overview document the server
owner keeps, plus the stat breakpoint and element table posts in the Discord
server information channel.

Page copy is English, like the class pages and the item database. The
headings, ledes and labels carry data-i18n keys, so the chrome is translated
and the reference text is not, which is the same rule the rest of the site
follows.
"""

import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_classes import esc, head, header, footer, SITE, REGISTER
from status_codex import STATUS, colorize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --------------------------------------------------------------------------
# Small markup helpers
# --------------------------------------------------------------------------

def rows(pairs):
    """The definition list the home page uses for the server spec."""
    return '<dl class="rows">%s</dl>' % "".join(
        '<div class="row"><dt>%s</dt><dd>%s</dd></div>' % (esc(term), body)
        for term, body in pairs)


def table(heads, body_rows, cls="mvp-table"):
    head_html = "".join("<th>%s</th>" % esc(h) for h in heads)
    body = "".join(
        "<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in row)
        for row in body_rows)
    return ('<div class="table-wrap"><table class="%s">'
            "<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>"
            % (cls, head_html, body))


def bullets(lines):
    return '<ul class="guide-notes">%s</ul>' % "".join(
        "<li>%s</li>" % line for line in lines)


def note(key, text):
    return '<p class="note" data-i18n="%s">%s</p>' % (key, esc(text))


def section(anchor, key, title, lede_key, lede, body):
    return """
  <section class="section-pad-sm mech-sec" id="{anchor}">
    <div class="shell">
      <h2 class="mech-title" data-i18n="{key}">{title}</h2>
      <p class="lede" data-i18n="{lk}">{lede}</p>
{body}
    </div>
  </section>
""".format(anchor=anchor, key=key, title=esc(title), lk=lede_key,
           lede=esc(lede), body=body)


def jumps(items):
    return """      <nav class="q-jumps" aria-label="Jump to a section">
        <span class="q-jumps-label" data-i18n="q.jump">Jump to</span>
%s
      </nav>
""" % "\n".join('        <a class="q-jump" href="#%s" data-i18n="%s">%s</a>'
                % (anchor, key, esc(label)) for anchor, key, label in items)


def page_top(eyebrow_key, eyebrow, title_key, title, lede_key, lede, crumb_key,
             crumb):
    return """<main id="main">
  <section class="page-head">
    <div class="shell">
      <nav class="breadcrumb" aria-label="Breadcrumb"><ol>
        <li><a href="index.html" data-i18n="nav.home">Home</a></li>
        <li data-i18n="{ck}">{crumb}</li>
      </ol></nav>
      <div class="section-head">
        <p class="eyebrow" data-i18n="{ek}">{eyebrow}</p>
        <h1 data-i18n="{tk}">{title}</h1>
        <p class="lede" data-i18n="{lk}">{lede}</p>
      </div>
    </div>
  </section>
""".format(ck=crumb_key, crumb=esc(crumb), ek=eyebrow_key, eyebrow=esc(eyebrow),
           tk=title_key, title=esc(title), lk=lede_key, lede=esc(lede))


def page_end(links):
    """The closing call to action. links is a list of (href, key, label)."""
    buttons = "".join(
        '\n            <a class="btn -ghost -lg" href="%s" data-i18n="%s">%s</a>'
        % (href, key, esc(label)) for href, key, label in links)
    return """
  <section class="section-pad-sm">
    <div class="shell">
      <div class="cta-band">
        <div class="inner">
          <h2 data-i18n="band.title">Come find out what changed</h2>
          <p class="lede text-center" data-i18n="band.lede">Make an account, grab the client, and come and see what changed.</p>
          <div class="hero-actions">
            <a class="btn -primary -lg" href="{reg}" target="_blank" rel="noopener" data-i18n="cta.registerFree">Create a free account</a>{buttons}
          </div>
        </div>
      </div>
    </div>
  </section>
</main>
""".format(reg=REGISTER, buttons=buttons)


def breadcrumb_ld(name, page):
    return """<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "{site}/" }},
    {{ "@type": "ListItem", "position": 2, "name": "{name}", "item": "{site}/{page}" }}
  ]
}}
</script>""".format(site=SITE, name=name, page=page)


# ==========================================================================
# mechanics.html
# ==========================================================================

# Every stat, what it already did, and what each breakpoint adds. A weapon
# label of None means the pair applies whatever you are holding.
STATS = [
    ("Str", "Strength", "Physical attack with melee weapons, and carry weight.",
     [("Melee weapon",
       [("Every 10", "Weapon attack +5%"), ("Every 25", "Melee damage +3%")]),
      ("Bow, instrument, whip or gun",
       [("Every 10", "Defence pierce +3%"), ("Every 25", "Max HP +3%")])]),
    ("Agi", "Agility", "Flee and attack speed.",
     [(None,
       [("Every 10", "Perfect dodge +1"),
        ("Every 25", "All skill cooldowns -5%")])]),
    ("Vit", "Vitality", "Max HP, HP regeneration and carry weight.",
     [(None,
       [("Every 10", "Status damage taken -2%"),
        ("Every 25", "Potion cooldown -0.5s")])]),
    ("Int", "Intelligence", "Magic attack, max SP and SP regeneration.",
     [("Staff, mace, dagger, instrument or whip",
       [("Every 10", "Weapon magic attack +5%"),
        ("Every 25", "Magic damage +3%")]),
      ("Any other weapon",
       [("Every 10", "Fixed cast time -0.1s"),
        ("Every 25", "SP consumption -10%")])]),
    ("Dex", "Dexterity",
     "Physical attack with ranged weapons, hit rate, and cast time.",
     [("Bow, instrument, whip or gun",
       [("Every 10", "Weapon attack +5%"), ("Every 25", "Ranged damage +3%")]),
      ("Any other weapon",
       [("Every 10", "Defence pierce +3%"),
        ("Every 25", "Movement speed +3%")])]),
    ("Luk", "Luck", "Critical rate and perfect dodge.",
     [(None,
       [("Every 10", "Outgoing status duration +3%"),
        ("Every 25", "5% chance to resist most negative statuses")])]),
]

# The element table, read off the chart the server owner posts. Each cell is
# either None for no change, or (direction, "a/b/c/d") where the four numbers
# are the four levels of the defender's element and direction is up for more
# damage dealt, down for less.
ELEMENTS = ["Neutral", "Fire", "Water", "Wind", "Earth", "Poison", "Undead",
            "Ghost", "Dark", "Holy"]

_U, _D = "up", "down"
ELEMENT_TABLE = {
    "Neutral": {"Ghost": (_D, "10/20/30/50"), "Holy": (_D, "10/25/50/75")},
    "Fire": {"Fire": (_D, "15/25/50/75"), "Water": (_D, "0/10/25/50"),
             "Earth": (_U, "10/25/35/50"), "Undead": (_U, "10/25/35/50"),
             "Holy": (_D, "10/25/50/75")},
    "Water": {"Fire": (_U, "10/25/35/50"), "Water": (_D, "15/25/50/75"),
              "Wind": (_D, "0/10/25/50"), "Holy": (_D, "10/25/50/75")},
    "Wind": {"Water": (_U, "10/25/35/50"), "Wind": (_D, "15/25/50/75"),
             "Earth": (_D, "0/10/25/50"), "Holy": (_D, "10/25/50/75")},
    "Earth": {"Fire": (_D, "0/10/25/50"), "Wind": (_U, "10/25/35/50"),
              "Earth": (_D, "15/25/50/75"), "Holy": (_D, "10/25/50/75")},
    "Poison": {"Fire": (_U, "5/10/15/20"), "Water": (_U, "5/10/15/20"),
               "Wind": (_U, "5/10/15/20"), "Earth": (_U, "5/10/15/20"),
               "Poison": (_D, "15/25/50/75"), "Undead": (_D, "0/10/25/50"),
               "Holy": (_D, "10/25/50/75")},
    "Undead": {"Neutral": (_U, "5/10/15/20"), "Fire": (_D, "0/10/25/50"),
               "Poison": (_U, "5/10/15/20"), "Undead": (_D, "15/25/50/75"),
               "Ghost": (_D, "0/10/25/50"), "Dark": (_U, "5/10/15/20"),
               "Holy": (_D, "10/25/50/75")},
    "Ghost": {"Undead": (_U, "10/25/35/50"), "Ghost": (_U, "5/10/15/20"),
              "Holy": (_D, "10/25/50/75")},
    "Dark": {"Undead": (_D, "0/10/25/50"), "Dark": (_D, "15/25/50/75"),
             "Holy": (_U, "10/25/35/50")},
    "Holy": {"Neutral": (_U, "5/10/15/20"), "Fire": (_U, "5/10/15/20"),
             "Water": (_U, "5/10/15/20"), "Wind": (_U, "5/10/15/20"),
             "Earth": (_U, "5/10/15/20"), "Poison": (_U, "5/10/15/20"),
             "Undead": (_U, "10/25/35/50"), "Ghost": (_U, "10/25/35/50"),
             "Dark": (_U, "10/25/35/50"), "Holy": (_D, "10/25/50/75")},
}

NOVICE = [
    ("Basic Skill", "Explains the common status effects as you meet them."),
    ("Sense", "Prints everything about a monster into the chat window. This "
              "is the whole reason the old monster info command is gone."),
    ("Mobile Storage", "Your cart, once you have bought a licence."),
    ("Vending", "Opens a shop out of that cart. Needs the same licence."),
    ("Teleport", "Random spot on the map, or back to your save point. Long "
                 "cooldown."),
    ("Area Loot", "Picks up everything within four cells, and respects loot "
                  "priority."),
]

NOVICE_QUEST = [
    ("Resurrection", "Revives a downed player and spends one Holy Water out "
                     "of their inventory. You get three every time you "
                     "respawn or talk to a Kafra."),
    ("Warp Portal", "Memo a spot, open a portal to it, spend a Blue Gemstone."),
    ("High Jump", "Jumps to where you point, through anything in the way."),
]

COMMANDS = [
    ("@showexp", "Prints experience gained and lost into the chat log."),
    ("@showzeny", "The same for zeny."),
    ("@whereis", "Where a named monster spawns. The in game navigation "
                 "window does the same job."),
    ("@refresh", "Redraws the screen when your position goes out of sync."),
    ("@noks", "Stops other players touching what you are fighting. It works "
              "on bosses here, which is unusual."),
    ("@autotrade", "Closes the client without closing your shop, so you can "
                   "vend while logged out."),
    ("@prep", "Toggles the safety catch on the Sniper preparation mechanic. "
              "Nothing to anyone else."),
    ("@casttime", "Your current fixed and variable cast reduction, buffs and "
                  "gear included."),
    ("@autoswap", "Registers weapons to swap to. Cast a skill your current "
                  "weapon cannot use and the game finds one that can and "
                  "equips it."),
]

GONE = [
    ("@whodrops", "Its answers were incomplete and wrong."),
    ("@mobinfo", "The Sense skill replaced it."),
    ("@iteminfo", "Too much leftover junk in the files for it to be useful."),
    ("@autoloot", "Pick your own items up."),
]

EXP_GAP = [
    ("15 or more levels above the monster", "Nothing at all"),
    ("10 levels above", "Half"),
    ("6 levels above", "90%"),
    ("Up to 5 levels above", "Full experience"),
    ("3 to 10 levels below", "5% more, rising to 40% more at ten"),
    ("10 to 15 levels below", "Tapering back down, 15% more at fifteen"),
    ("16 or more levels below", "90% less"),
]

REFINE_WEAPON = [
    ("+0 to +3", "Phracon or better", "+2 attack and magic attack each"),
    ("+4 to +6", "Emveretarcon or better", "+4 each"),
    ("+7 to +9", "Oridecon or better", "+6 each"),
    ("+10", "Enriched Oridecon", "+10, for +46 in total"),
]

REFINE_ARMOUR = [
    ("+0 to +3", "Iron or better", "+1 defence each"),
    ("+4 to +6", "Steel or better", "+2 each"),
    ("+7 to +9", "Elunium or better", "+3 each"),
    ("+10", "Enriched Elunium", "+5, for +23 in total"),
]

ORES = [
    ("Boss level 1 to 50", "Phracon and Iron"),
    ("51 to 100", "Emveretarcon and Steel"),
    ("101 to 150", "Oridecon and Elunium"),
    ("Over 150", "Enriched Oridecon and Enriched Elunium"),
]


# --------------------------------------------------------------------------
# The two reference tabs of the gear sheet
#
# Both are laid out for a human reading a spreadsheet, not for a program:
# blocks of slot columns sitting side by side with blank rows between them.
# These two readers turn that back into a list, so the page follows the sheet
# whenever Twilight touches it.
# --------------------------------------------------------------------------

DATA = os.path.join(ROOT, "tools", "data")


def _grid(name):
    with io.open(os.path.join(DATA, name), encoding="utf-8", newline="") as fh:
        return [[c.strip() for c in row] for row in csv.reader(fh)]


def random_options():
    """[(title, [(slot, [options])], note)] in the order the sheet has them.

    Three things in the columns are not options: the second slot header that
    only two handed weapons get, and two sentences the sheet leaves in the
    cells as footnotes. They come back out as a slot of their own and as the
    block's note.
    """
    rows = _grid("gear__random-option-tables.csv")

    def at(r, c):
        return rows[r][c] if r < len(rows) and c < len(rows[r]) else ""

    blocks = []
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            if cell != "Slot 1":
                continue
            cols = []
            k = j
            while at(i, k).startswith("Slot "):
                cols.append((at(i, k), k))
                k += 1

            end = i + 1
            while end < len(rows) and any(at(end, x) for x in range(j, j + 4)):
                end += 1

            slots, note_lines = [], []
            for label, col in cols:
                values = []
                for r in range(i + 1, end):
                    value = at(r, col)
                    if not value:
                        continue
                    if "Level Tier above" in value or value.startswith("This tier"):
                        note_lines.append(value)
                    elif value.startswith("Slot "):
                        slots.append((label, values))
                        label, values = value, []
                    else:
                        values.append(value)
                if values:
                    slots.append((label, values))
            blocks.append((at(i - 2, j), slots, " ".join(note_lines)))
    return blocks


# Four slips in the enchant tab that would read as real values on the page.
# Fixed here rather than in the CSV, so re-fetching the sheet does not quietly
# put them back.
ENCHANT_TYPOS = [
    ("Str +1, Stk +3%", "Str +1, Atk +3%"),
    ("Nigthmares", "Nightmares"),
    ("Damage Takenb from", "Damage Taken from"),
    ("Int +5,. Matk", "Int +5, Matk"),
]


def shadow_enchants():
    """[(stat, [(name, effect)])], one entry per stat the sheet groups by."""
    groups = []
    for row in _grid("gear__shadow-enchants.csv"):
        name = row[0] if row else ""
        effect = row[1] if len(row) > 1 else ""
        if not name:
            continue
        if name.endswith("Enchants"):
            groups.append((name[:-len(" Enchants")], []))
        elif groups and effect:
            for wrong, right in ENCHANT_TYPOS:
                effect = effect.replace(wrong, right)
            groups[-1][1].append((name, effect))
    return groups

MECH_JUMPS = [
    ("levels", "m.jLevels", "Levels and experience"),
    ("stats", "m.jStats", "Stats and breakpoints"),
    ("combat", "m.jCombat", "Combat maths"),
    ("elements", "m.jElements", "Element table"),
    ("status", "m.jStatus", "Status effects"),
    ("potions", "m.jPotions", "Potions and catalysts"),
    ("novice", "m.jNovice", "Skills everyone has"),
    ("refine", "m.jRefine", "Refining"),
    ("options", "m.jOptions", "Random options"),
    ("warps", "m.jWarps", "Warps"),
    ("commands", "m.jCommands", "Commands"),
]


def slug_el(name):
    return name.lower()


def stat_card(short, name, does, groups):
    blocks = []
    for label, pairs in groups:
        head_html = ('<h4 class="st-when">%s</h4>' % esc(label)) if label else ""
        items = "".join(
            '<li><span class="st-step">%s</span><span>%s</span></li>'
            % (esc(step), esc(gain)) for step, gain in pairs)
        blocks.append('%s<ul class="st-list">%s</ul>' % (head_html, items))

    return """        <article class="st-card">
          <div class="st-head">
            <span class="st-abbr">{short}</span>
            <h3>{name}</h3>
          </div>
          <p class="st-does">{does}</p>
{blocks}
        </article>""".format(short=esc(short), name=esc(name), does=esc(does),
                             blocks="\n".join("          " + b for b in blocks))


def element_table():
    head_cells = "".join(
        '<th class="el-h el-%s"><span>%s</span></th>' % (slug_el(e), esc(e))
        for e in ELEMENTS)

    body = []
    for attacker in ELEMENTS:
        cells = ['<th class="el-h el-%s el-row"><span>%s</span></th>'
                 % (slug_el(attacker), esc(attacker))]
        for defender in ELEMENTS:
            cell = ELEMENT_TABLE.get(attacker, {}).get(defender)
            if cell is None:
                cells.append('<td class="el-c"><span class="el-none">'
                             "&middot;</span></td>")
            else:
                direction, value = cell
                cells.append('<td class="el-c"><span class="el-v -%s">%s</span></td>'
                             % (direction, value))
        body.append("<tr>%s</tr>" % "".join(cells))

    return """      <div class="el-legend">
        <span class="el-v -up">10/25/35/50</span>
        <span class="el-legend-t" data-i18n="m.elUp">you deal that much more</span>
        <span class="el-v -down">10/25/35/50</span>
        <span class="el-legend-t" data-i18n="m.elDown">you deal that much less</span>
      </div>
      <div class="table-wrap">
        <table class="el-table">
          <thead><tr><th class="el-corner"><span data-i18n="m.elAxis">Attacker down, defender across</span></th>{heads}</tr></thead>
          <tbody>{body}</tbody>
        </table>
      </div>
""".format(heads=head_cells, body="".join(body))


def status_cards():
    """The same codex cards the class index carries, down to the i18n keys, so
    the descriptions are already translated."""
    return '      <ul class="codex">%s</ul>\n' % "".join(
        """
        <li class="kw-{key}">
          <i class="swatch" aria-hidden="true"></i>
          <div>
            <b>{label}</b>
            <span data-i18n="codex.{key}">{desc}</span>
            <em>{terms}</em>
          </div>
        </li>""".format(
            key=key, label=esc(label), desc=esc(desc),
            terms=esc(", ".join(sorted(set(terms),
                                       key=lambda w: (-len(w), w))[:3])))
        for key, label, terms, desc in STATUS)



# The random option blocks group into three families that people shop for
# separately: what you swing, what you wear, and the rest.
RO_FAMILIES = [
    ("m.roWeapons", "Weapons", ("Physical Weapons", "Magical Weapons",
                                "Hybrid Weapons")),
    ("m.roWorn", "Armour, shields and shoes", ("Armor / Shields", "Shoes")),
    ("m.roRest", "Garments and accessories", ("Garments", "Accessories")),
]


def option_cards(blocks):
    out = []
    for key, label, prefixes in RO_FAMILIES:
        out.append('      <h3 class="mech-sub" data-i18n="%s">%s</h3>\n'
                   % (key, esc(label)))
        cards = []
        ordered = [b for prefix in prefixes for b in blocks
                   if b[0].startswith(prefix)]
        for title, slots, note_text in ordered:
            cols = "".join(
                """
            <div class="ro-slot">
              <b>%s</b>
              <ul>%s</ul>
            </div>""" % (esc(slot),
                         "".join("<li>%s</li>" % esc(v) for v in values))
                for slot, values in slots)
            cards.append("""
        <article class="ro-card">
          <h4>%s</h4>
          <div class="ro-slots">%s
          </div>%s
        </article>""" % (esc(title), cols,
                         '\n          <p class="ro-note">%s</p>' % esc(note_text)
                         if note_text else ""))
        out.append('      <div class="ro-grid">%s\n      </div>\n'
                   % "".join(cards))
    return "".join(out)


def enchant_cards(groups):
    return '      <div class="ench-grid">%s\n      </div>\n' % "".join(
        """
        <article class="ench-card">
          <h4>%s</h4>
          <dl>%s</dl>
        </article>""" % (esc(stat), "".join(
            "<dt>%s</dt><dd>%s</dd>" % (esc(name), colorize(esc(effect)))
            for name, effect in lines))
        for stat, lines in groups)

def build_mechanics():
    body = []

    body.append(section(
        "levels", "m.lvTitle", "Levels and experience",
        "m.lvLede",
        "The tables were rewritten from scratch, so nobody can quote you a "
        "rate. What follows is the shape of the curve instead.",
        rows([
            ("Max level",
             "<strong>150 base, 50 job.</strong> Jobs come in three tiers: "
             "first job carries you from 1 to 50, second from 51 to 99, third "
             "from 100 to 150. Each tier has its own fifty job levels, so "
             "fifty skill points to spend before you move on."),
            ("Ninja and Gunslinger",
             "The exceptions. They stay on their first job until 99 and then "
             "go straight to their final one. They still collect both sets of "
             "fifty skill points."),
            ("Per kill",
             "About <strong>5% of a level at base 50</strong>, "
             "<strong>1% at 100</strong>, <strong>0.1% at 149</strong>. "
             "Monsters here take much longer to kill than you are used to, so "
             "read those numbers with that in mind."),
            ("Parties",
             "<strong>Five players.</strong> Experience only splits evenly if "
             "the lowest and highest member are within 15 levels of each other."),
        ])
        + '<h3 class="mech-sub" data-i18n="m.lvGapTitle">What the level gap costs you</h3>'
        + table(["Your level against the monster", "Experience"],
                [[esc(a), esc(b)] for a, b in EXP_GAP])
        + note("m.lvGapNote",
               "So the sweet spot is monsters a few levels above you, not "
               "below. Fighting something ten levels higher pays 40% more, "
               "and grinding something fifteen levels lower pays nothing.")))

    body.append(section(
        "stats", "m.stTitle", "Stats and breakpoints",
        "m.stLede",
        "Each stat still does what you expect, and then gives you something "
        "extra at every tenth and every twenty fifth point. Several of those "
        "bonuses depend on what you are holding.",
        '      <div class="st-grid">\n%s\n      </div>\n'
        % "\n".join(stat_card(*s) for s in STATS)
        + note("m.stNote",
               "Bonus stats count. If you have 77 Strength and 23 from gear "
               "and buffs, the game reads 100 for every breakpoint above. The "
               "Luck resistance roll does not cover statuses you inflict on "
               "yourself, item or homunculus cooldowns, Threefold Arrow or "
               "Quick Draw charges, Convex Mirrors, or Death Sentence.")))

    body.append(section(
        "combat", "m.cbTitle", "Combat maths",
        "m.cbLede",
        "Most formulas match renewal. These are the ones that do not, and "
        "they are the ones that decide how a build feels.",
        rows([
            ("Critical hits",
             "<strong>Every physical skill and attack can crit.</strong> Rate "
             "is still 1 + (Luk / 3) + (base level / 100). The damage bonus "
             "dropped from 40% to 20%, crits no longer skip flee or defence, "
             "and monsters have no crit shield, so their Luck does not reduce "
             "your rate."),
            ("Cast time",
             "Split into fixed and variable. Variable reduction is "
             "<strong>sqrt((Dex &times; 2) / 600) &times; 100</strong>, which "
             "means 300 Dex for a full 100%, which nobody reaches. Reduction "
             "from gear adds to reduction from stats instead of multiplying, "
             "so 40% from stats and 60% from gear leaves nothing. Fixed cast "
             "only bends to gear and to the Intelligence breakpoints."),
            ("Attack speed",
             "<strong>ASPD = base ASPD + (Agi / 5)</strong>, where the base "
             "comes from your class and weapon type. There is a soft cap at "
             "185 that gear and buffs can push through, and a hard cap at 190 "
             "that nothing can."),
            ("Status resistance",
             "Outside the Luck breakpoints, <strong>no stat resists "
             "anything</strong>. Two thousand Vitality still gets stunned. "
             "Gear is the only other answer."),
            ("Elements and cards",
             "Weapon element applies to your <strong>whole attack</strong>, "
             "not just the weapon part of it. Damage bonuses against a race, "
             "element or size work the same way."),
            ("Movement and regen",
             "Base movement went from 150ms per cell to <strong>120ms</strong>. "
             "HP and SP regeneration are five times what you remember."),
        ])))

    body.append(section(
        "elements", "m.elTitle", "Element table",
        "m.elLede",
        "This table has moved a long way from the one you know, and Undead in "
        "particular is now worth carrying. Read your attack element down the "
        "left, your target across the top. The four numbers are the four "
        "levels of the target's element.",
        element_table()
        + note("m.elNote",
               "Holy beats everything and is beaten by nothing except itself, "
               "which is why holy monsters are the wall they are. Poison is a "
               "small edge against most things and a wall against Undead. "
               "Neutral has no answer to Ghost.")))

    body.append(section(
        "status", "m.sfTitle", "Status effects",
        "m.sfLede",
        "Statuses are a pillar of combat here rather than a nuisance. Most "
        "last five seconds or less and hit far harder than they used to, and "
        "a lot of skills change behaviour depending on what is already on the "
        "target.",
        status_cards()
        + note("m.sfNote",
               "Two rules follow from that. No stat gives you any resistance, "
               "so the only defences are the Luck breakpoints and gear. And "
               "champions and bosses have no immunity at all, so everything "
               "you carry works on them.")))

    body.append(section(
        "potions", "m.poTitle", "Potions and catalysts",
        "m.poLede",
        "Your potion is a piece of equipment, not a stack of items. It is "
        "never consumed, it sits on a ten second cooldown, and you upgrade it "
        "as you go.",
        rows([
            ("Healing",
             "<strong>Red, then Orange, Yellow, White.</strong> Around level "
             "30 the Red one stops keeping up. Gather the herbs and materials "
             "and commission the upgrade from the Alchemists in Aldebaran, or "
             "from any starting town tool shop for the Red one."),
            ("SP", "<strong>Grape Juice, then Blue Potion.</strong>"),
            ("Attack speed",
             "<strong>Concentration, Awakening, Berserk.</strong> Every class "
             "restriction on these has been removed."),
            ("Status", "A Green Potion, for when the pressure gets silly."),
            ("Catalysts",
             "Most class consumables are gone. The ones that stayed became "
             "catalysts that are <strong>not used up</strong>: endow stones, "
             "arrows, maintenance kits, poisons and the rest. Short quests or "
             "crafting get you them."),
        ])
        + '<p class="mech-link"><a class="btn -ghost" href="quests.html#potions" data-i18n="m.poLink">The potion crafting recipes</a></p>'))

    body.append(section(
        "novice", "m.nvTitle", "Skills everyone has",
        "m.nvLede",
        "The novice stage is skipped, since the tutorial hands you your first "
        "job at level 1. The novice skills stayed, and several of them matter "
        "for the whole game.",
        table(["Skill", "What it does"],
              [["<b>%s</b>" % esc(n), esc(d)] for n, d in NOVICE])
        + '<h3 class="mech-sub" data-i18n="m.nvQuestTitle">The three you have to earn</h3>'
        + table(["Skill", "What it does"],
                [["<b>%s</b>" % esc(n), esc(d)] for n, d in NOVICE_QUEST])
        + note("m.nvNote",
               "All three need a quest to learn and more quests to raise past "
               "level 1. Where each one starts is written in its skill "
               "description, in your skill tree.")))

    body.append(section(
        "refine", "m.rfTitle", "Refining",
        "m.rfLede",
        "The one part of this server that is kinder than the game you "
        "remember. Gear never breaks and never drops a level. The only thing "
        "at risk is your wallet.",
        rows([
            ("The odds",
             "Maximum is <strong>+10</strong>, and success is "
             "<strong>100% minus 10% per current refine</strong>. So +0 to +1 "
             "always works, +4 to +5 is a coin flip and a bit, and +9 to +10 "
             "is one in ten."),
            ("One weapon level",
             "Every weapon in the game refines with the same ores. Armour, "
             "shields, garments, shoes and headgear share one ladder too."),
            ("Where the ores come from",
             "Mostly from killing bosses, banded by the boss's own level."),
        ])
        + '<h3 class="mech-sub" data-i18n="m.rfWeapon">Weapons</h3>'
        + table(["Refine", "Ore", "Per step"],
                [[esc(a), esc(b), esc(c)] for a, b, c in REFINE_WEAPON])
        + '<h3 class="mech-sub" data-i18n="m.rfArmour">Armour</h3>'
        + table(["Refine", "Ore", "Per step"],
                [[esc(a), esc(b), esc(c)] for a, b, c in REFINE_ARMOUR])
        + '<h3 class="mech-sub" data-i18n="m.rfOres">Which boss drops what</h3>'
        + table(["Boss", "Drops"], [[esc(a), esc(b)] for a, b in ORES])))

    body.append(section(
        "options", "m.roTitle", "Random options",
        "m.roLede",
        "Almost everything that drops rolls its own extra stats on top of the "
        "ones printed on it. Which stats it can roll depends on what the "
        "piece is and what level bracket it came from, and the tables below "
        "are the whole of it.",
        rows([
            ("What does not roll",
             "<strong>Headgears</strong>, except in special cases. "
             "<strong>Costumes</strong>, which are appearance only. And the "
             "non standard weapons: shuriken, kunai, huuma, gatling guns and "
             "grenade launchers."),
            ("Slots",
             "A piece rolls one option per slot on its table. Weapons get "
             "fewer slots as their level bracket climbs, so a two slot weapon "
             "at 150 rolls less than a four slot weapon at 30 and each roll "
             "is worth much more. <strong>Two handed weapons</strong> get a "
             "fourth slot the one handed ones do not."),
            ("Boss gear",
             "Gear that drops from a boss rolls on the tier above the one its "
             "level requirement would suggest, and the top bracket has a tier "
             "that <strong>only boss gear can reach</strong>."),
            ("No options at all",
             "Anything handed over by the Roaming Archaeologist, relic gear "
             "included, comes with <strong>no random options</strong>. That "
             "is the price of a guaranteed drop."),
            ("Rerolling",
             "Reroll Scrolls come out of the reward chests in the challenge "
             "dungeons, which is the only way to change a roll you do not "
             "want."),
        ])
        + option_cards(random_options())
        + note("m.roNote",
               "[Size] and [Element] are placeholders: the roll picks one and "
               "prints it. A range like +1~5% means the roll lands somewhere "
               "in it, so two copies of the same item are rarely worth the "
               "same.")))

    body.append(section(
        "warps", "m.wpTitle", "Warps",
        "m.wpLede",
        "The Kafra teleport service works, with one condition attached.",
        bullets([
            "You cannot warp to a town until you have <b>walked there once</b> "
            "and spoken to its Kafra.",
            "<b>Prontera, Izlude, Morroc, Geffen, Payon and Alberta</b> are "
            "open from your first login, and warping between those six is free.",
            "Everything else costs zeny once you have unlocked it.",
            "Unlocks are <b>account wide</b>, so your second character starts "
            "with everything the first one opened.",
        ])))

    body.append(section(
        "commands", "m.cmTitle", "Commands",
        "m.cmLede", "The short list of what @ commands do here.",
        table(["Command", "What it does"],
              [['<code class="cmd">%s</code>' % esc(c), esc(d)]
               for c, d in COMMANDS])
        + '<h3 class="mech-sub" data-i18n="m.cmGone">Gone on purpose</h3>'
        + table(["Command", "Why"],
                [['<code class="cmd">%s</code>' % esc(c), esc(d)]
                 for c, d in GONE])))

    parts = [
        head("", "How the server works | Nightmare RO",
             "How combat works on Nightmare RO: the experience curve, every "
             "stat breakpoint, the crit and cast formulas, the rewritten "
             "element table, refining and commands.",
             "mechanics.html", breadcrumb_ld("How it works", "mechanics.html")),
        header("", "mechanics.html"),
        page_top("m.eyebrow", "The rules", "m.title",
                 "How the server actually works", "m.lede",
                 "Everything below is different enough from the game you "
                 "remember that guessing will cost you levels. It is worth "
                 "twenty minutes before you pick a build.",
                 "nav.mech", "How it works"),
        '  <section class="section-pad-sm"><div class="shell">\n',
        jumps(MECH_JUMPS),
        "  </div></section>\n",
        "".join(body),
        page_end([("guide.html", "nav.route", "Levelling route"),
                  ("endgame.html", "nav.endgame", "End game"),
                  ("classes.html", "nav.classes", "Classes")]),
        footer(""),
    ]

    out = os.path.join(ROOT, "mechanics.html")
    io.open(out, "w", encoding="utf-8", newline="\n").write("".join(parts))
    print("mechanics.html: %d sections, %d stats, %d element rows (%.0f KB)"
          % (len(MECH_JUMPS), len(STATS), len(ELEMENTS),
             os.path.getsize(out) / 1024.0))


# ==========================================================================
# endgame.html
# ==========================================================================

END_JUMPS = [
    ("champions", "e.jChampions", "Champions"),
    ("bosses", "e.jBosses", "Bosses and altars"),
    ("archaeologist", "e.jArch", "The Archaeologist"),
    ("guilds", "e.jGuilds", "Guilds and raids"),
    ("nightmare", "e.jNightmare", "Nightmare dungeons"),
    ("shadow", "e.jShadow", "Shadow enchants"),
    ("challenge", "e.jChallenge", "Challenge dungeons"),
    ("reputation", "e.jRep", "Reputation"),
]


def build_endgame():
    body = []

    body.append(section(
        "champions", "e.chTitle", "Champions",
        "e.chLede",
        "Some maps carry a single monster that is far stronger than anything "
        "around it. It is the reason to keep coming back to a field after you "
        "have outgrown the levels.",
        bullets([
            "One champion per map at a time, and it <b>respawns the instant "
            "you kill it</b>.",
            "They drop what the map drops, at hugely better rates, and hand "
            "over a chunk of bonus experience on top.",
            "They are the <b>only source of Relics</b>, which is what opens "
            "the boss altar for that region.",
            "You can spot one by its <b>green aura</b>, and pin down exactly "
            "where it is with a Convex Mirror from any tool dealer.",
        ])))

    body.append(section(
        "bosses", "e.boTitle", "Bosses and altars",
        "e.boLede",
        "Bosses work nothing like the ones you have chased before. None of "
        "them spawn on their own. A player brings the Relics to the Ancient "
        "Altar in that region, and the boss walks in.",
        rows([
            ("Nobody can steal it",
             "Loot priority on everything the boss drops goes to "
             "<strong>whoever summoned it</strong>, even if that player is "
             "lying dead when it falls. If they have left, it falls back to "
             "the old rules of most damage first. The no kill steal command "
             "works on bosses here too."),
            ("How hard",
             "Tuned for <strong>one to three players at the boss's own "
             "level</strong>, which is usually about five above the map it "
             "sits on."),
            ("What they pay",
             "Unique gear at very high rates, <strong>typically 35%</strong>. "
             "This is the main way gear progresses here."),
            ("No cooldown",
             "Summon as often as you can afford the items. The only rule is "
             "that a second boss cannot be summoned while the first is still "
             "alive."),
            ("No tricks",
             "Champions and bosses cannot see through hiding or cloaking, and "
             "have <strong>no status immunity</strong> whatsoever."),
        ])
        + '<p class="mech-link"><a class="btn -ghost" href="mvps.html" data-i18n="nav.mvps">MVPs and altars</a></p>'))

    body.append(section(
        "archaeologist", "e.arTitle", "The Roaming Archaeologist",
        "e.arLede",
        "The world is large and tracking down which champion drops which "
        "Relic would be miserable. So there is an NPC who does it for you. "
        "You will find her at dungeon entrances, and on any field that has an "
        "altar.",
        bullets([
            "If she is standing on a field, <b>that field has an altar</b>. "
            "Ask and she will tell you either way.",
            "She names the Relics the region's altar wants and where the "
            "champions that drop them live.",
            "She trades Relics for <b>any gear that region's boss drops</b>, "
            "without random options. That is your safety net when a boss will "
            "not cooperate.",
            "She also trades Relics for <b>Relic equipment</b>, which cannot "
            "be found anywhere else and carries effects nothing at its level "
            "can match.",
            "MVP Trophies buy a card album holding one random MVP card from "
            "the same level bracket.",
            "Listen to her small talk. She explores for a living, and she "
            "gossips about what she has found.",
        ])))

    body.append(section(
        "guilds", "e.guTitle", "Guilds and raids",
        "e.guLede",
        "A guild costs nothing to start. Press Alt and G. There is no "
        "Emperium involved. What is new is that the guild itself levels.",
        rows([
            ("Guild levels",
             "Guilds start at level 0 and earn experience toward levels and "
             "skill points. The leader spends those on more member slots, on "
             "guild storage, and on <strong>permanent stat bonuses for every "
             "member</strong>."),
            ("Tax",
             "The leader sets a rate between 0 and 99%, and that slice of "
             "every member's base experience goes to the guild instead."),
            ("Guild quests",
             "Unlocked by the Steel Wings Favor skill, once a week, handed "
             "out at the Steel Wings Headquarters in <strong>Luina, west of "
             "Aldebaran</strong>. Better rewards at higher Favor."),
            ("Guild raids",
             "High end instances for five players that pay large amounts of "
             "guild experience, and where everything inside can drop "
             "commendations. No cooldown, but each run needs a Raid Pass that "
             "only leaders can buy. Passes are not tradeable, but guild "
             "storage will move them, so a guild can share a stack."),
        ])))

    body.append(section(
        "nightmare", "e.nmTitle", "Nightmare dungeons",
        "e.nmLede",
        "The dungeons the server is named after. They look like ordinary "
        "dungeons and they are not, because of three stats that only exist "
        "inside them.",
        rows([
            ("Depth",
             "Each one has three levels. Every step down looks the same and "
             "is not: monsters gain huge stats and <strong>new skills</strong>, "
             "and drop better. The dungeon's own champion only appears on the "
             "lowest floor, and killing it is how you reach the boss room."),
            ("Resistance",
             "The deeper floors give monsters Resistance, and each point cuts "
             "<strong>all</strong> damage you deal by 1%, physical, magical, "
             "misc and status alike. Resistance Pierce is the counter, point "
             "for point. Forty Resistance against twenty Pierce leaves twenty."),
            ("Agony",
             "High level floors drain <strong>1% of your max HP every five "
             "seconds per level of Agony</strong>. The level is posted before "
             "you walk in. Agony Resistance subtracts from it point for point."),
            ("Shadow Gear",
             "The answer to both, and it only comes from these dungeons. It "
             "equips in the costume tab, so it sits <strong>alongside your "
             "real build</strong> rather than replacing any of it. Outside a "
             "Nightmare dungeon it is a small stat bump. Inside, it carries "
             "your Resistance Pierce and Agony Resistance, gets much stronger "
             "at higher tiers, and takes enchants to shape it how you need."),
            ("The boss",
             "Instanced, up to five players, and entry costs items found in "
             "the dungeon. Rewards come as chests: enchanting materials, "
             "refine ores, convex mirrors and supplies rather than unique "
             "gear. They also drop <strong>Nightmare Echoes</strong>, which "
             "spend at the Steel Wings Headquarters in Luina."),
        ])
        + '<p class="mech-link"><a class="btn -ghost" href="database.html" data-i18n="e.nmLink">Every piece of Shadow Gear</a></p>'))

    body.append(section(
        "shadow", "e.shTitle", "Shadow enchants",
        "e.shLede",
        "Every piece of Shadow Gear takes an enchant, and the enchant is "
        "where the set stops being a stat stick and starts being a build. "
        "Each one is tied to a stat, comes in ranks, and like the gear "
        "itself it only does anything inside a Nightmare dungeon.",
        enchant_cards(shadow_enchants())
        + note("e.shNote",
               "Four ranks on the plain stat line, three on each of the "
               "others. The higher the rank the rarer the roll, so a set is "
               "usually a mix rather than four of the same.")))

    body.append(section(
        "challenge", "e.clTitle", "Challenge dungeons",
        "e.clLede",
        "The ceiling. Monsters above level 150, harder than anything else at "
        "the same level, and mostly hidden behind something before you can "
        "even get in.",
        bullets([
            "Everything inside drops <b>Ore Boxes and Herb Boxes</b>, which "
            "is a lot of crafting material.",
            "Each dungeon has its own gear, dropped at a low rate by every "
            "monster in it and <b>hidden from Sense</b>, so you will not see "
            "it coming.",
            "Everything can also drop an <b>Emblem of Valor</b>, and you need "
            "those to fight the dungeon's MVP.",
            "Those MVPs expect three to five players. Their reward chests do "
            "carry gear: <b>one guaranteed piece</b> from that dungeon, plus "
            "ores, convex mirrors, reroll scrolls for random options, and "
            "<b>Arcane Dust</b> to spend in Luina.",
            "Entrances are obscured, gated behind quests, or need special "
            "materials every single time. Expect to do detective work.",
        ])))

    body.append(section(
        "reputation", "e.rpTitle", "Reputation",
        "e.rpLede",
        "Three factions keep score of what you do, and two of them are at war "
        "with each other.",
        rows([
            ("Steel Wings",
             "The order the crown set up to deal with the mess in Midgard, "
             "and the one that matters to everybody. You earn it by taking "
             "their missions, above all the ones researching the Nightmare "
             "dungeons, and it buys faction shops, discounts and further "
             "quests. <strong>You cannot realistically lose it.</strong>"),
            ("Rachel and Veins",
             "Arunafeltz is in civil war and the two cities want opposite "
             "things. Both are shut to you until you earn your way in. "
             "Reputation buys shops, discounts, freedom of movement, and "
             "soldiers who stop attacking you. It also buys a "
             "<strong>blessing</strong>: more damage dealt and less taken in "
             "any dungeon that faction controls, scaling with how much they "
             "like you."),
            ("The warzone",
             "The land between the two cities is a battlefield, and both "
             "sides will cut down a stray adventurer. Killing one side is the "
             "fastest way to earn the other, and the fastest way into the "
             "negative with the one you killed. Go far enough negative and "
             "they start sending assassins after you, more often and stronger "
             "the lower you sink."),
            ("Neither side",
             "You can hold both cities at positive at once, or ignore the war "
             "altogether. Neither is easy. And if you have burned every "
             "bridge, an underground <strong>black market</strong> sells "
             "almost everything the factions monopolise, for a price."),
        ])))

    parts = [
        head("", "The end game | Nightmare RO",
             "What waits after the levelling route on Nightmare RO: "
             "champions, summoned bosses, guild raids, the Nightmare dungeons "
             "and their Agony, and three reputation lines.",
             "endgame.html", breadcrumb_ld("End game", "endgame.html")),
        header("", "endgame.html"),
        page_top("e.eyebrow", "After the route", "e.title",
                 "What the levels were for", "e.lede",
                 "Getting to 150 is the tutorial for this part. Bosses you "
                 "summon yourself, dungeons that drain your health for "
                 "standing in them, and two cities at war who both want to "
                 "know whose side you are on.",
                 "nav.endgame", "End game"),
        '  <section class="section-pad-sm"><div class="shell">\n',
        jumps(END_JUMPS),
        "  </div></section>\n",
        "".join(body),
        page_end([("mvps.html", "nav.mvps", "MVPs and altars"),
                  ("mechanics.html", "nav.mech", "How it works"),
                  ("quests.html", "nav.quests", "Quests")]),
        footer(""),
    ]

    out = os.path.join(ROOT, "endgame.html")
    io.open(out, "w", encoding="utf-8", newline="\n").write("".join(parts))
    print("endgame.html: %d sections (%.0f KB)"
          % (len(END_JUMPS), os.path.getsize(out) / 1024.0))


if __name__ == "__main__":
    build_mechanics()
    build_endgame()
