# -*- coding: utf-8 -*-
"""
The status effect codex, in one place.

build_classes.py uses it to colour skill text on the class pages, and
build_database.py ships the term list inside items.json so the database can
colour item effects the same way. Adding a family here means adding a
matching --kw-<key> pair to both theme blocks in style.css.
"""

import re

# (key, display label, terms matched in text, what the status does)
STATUS = [
    ("bleed", "Bleeding", ["Internal Bleeding", "Bleeding", "Bleed"],
     "Damage every second, scaled off the applier's Strength and level. "
     "Internal Bleeding works the same but scales off Dexterity."),
    ("burn", "Burning", ["Severe Burning", "Burning"],
     "Damage every second, scaled off Intelligence. "
     "Severe Burning scales off Vitality instead."),
    ("poison", "Poison", ["Deadly Poison", "Poison"],
     "Damage every second, scaled off Agility. "
     "Deadly Poison scales off Luck instead."),
    ("blind", "Blind", ["Blinded", "Blind"],
     "Cuts the target's Hit and Flee by a flat 30, and shrinks how much of "
     "the screen a player can see."),
    ("vuln", "Vulnerable", ["Vulnerable"],
     "Strips 40% of the target's hard and soft defence. No attack bonus, "
     "unlike the Provoke you remember."),
    ("breach", "Breach", ["Breached", "Breach"],
     "The same idea aimed at magic defence instead. It is how a caster gets "
     "through a high MDef enemy, and Breach Potency raises what it strips."),
    ("frozen", "Frozen", ["Frozen", "Freeze", "Chill", "Cold"],
     "Cancels casting and locks the target until it takes damage. Chill slows "
     "movement and attack speed, Cold is the follow up during the resist window."),
    ("stun", "Stun", ["Stunned", "Stun", "Staggered", "Stagger"],
     "Cancels casting and stops the target acting. Monsters resist for 30 "
     "seconds afterwards and take Stagger instead."),
    ("sleep", "Sleep", ["Sleeping", "Sleep", "Dazed"],
     "Cancels casting and stops the target acting until it takes damage. "
     "Monsters take Dazed during the resist window."),
    ("slow", "Slow", ["Slowcast", "Slowed", "Slow", "Atrophy", "Immobilized", "Immobilize"],
     "Movement speed down. Atrophy hits attack speed instead, and Slowcast "
     "stretches fixed cast time."),
]

# term -> family key
TERM_CLASS = {}
for _key, _label, _terms, _desc in STATUS:
    for _t in _terms:
        TERM_CLASS[_t] = _key

# Matching is case sensitive on purpose, so an ordinary lowercase "cold" or
# "slow" in a sentence is left alone. Longer terms win, so "Internal Bleeding"
# is matched before "Bleeding".
PATTERN = r"\b(%s)\b" % "|".join(
    sorted((re.escape(t) for t in TERM_CLASS), key=len, reverse=True))
STATUS_RE = re.compile(PATTERN)


def colorize(text):
    """Wraps status names so they pick up their codex colour."""
    return STATUS_RE.sub(
        lambda m: '<b class="kw kw-%s">%s</b>' % (TERM_CLASS[m.group(1)], m.group(1)),
        text)


def families_in(text):
    """Which status families a piece of text mentions, in codex order."""
    found = set(TERM_CLASS[m] for m in STATUS_RE.findall(text))
    return [s for s in STATUS if s[0] in found]
