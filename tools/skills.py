#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turns a class section of the Class Overviews document into a structured skill
tree, using the player wiki for the parts the document does not carry.

The document is prose. It gives every skill a name and a good description, but
it says nothing about which branch a skill belongs to, whether it is physical
or magical, or how many levels it has. It also runs several different kinds of
line together:

    Void Infusion: Converts all magic damage dealt...      <- a skill
    Ghost: The user's Magic Pierce is reduced to 0         <- an option of it
    Phantasmal Crush: Invokes forbidden magic...           <- a skill
    If Void Infusion: Ghost is active, cooldown is halved  <- a rider on it

The old parser read all four of those as separate skills, so class pages ended
up with entries called "Ghost" and "If Void Infusion". This module tells them
apart. The wiki skill tables are the authority on what counts as a real skill:
anything in the document that is not on that list gets folded into the skill
above it, either as an option or as a conditional rider.

    from skills import load_wiki, build
    tree = build("Warlock", blocks, load_wiki())
"""

import difflib
import io
import json
import os
import re

from status_codex import STATUS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI_FILE = os.path.join(ROOT, "tools", "data", "wiki-classes.json")


def load_wiki():
    try:
        return json.load(io.open(WIKI_FILE, encoding="utf-8"))
    except (IOError, ValueError):
        return {}


# --------------------------------------------------------------------------
# Text tidying, shared with build_classes
# --------------------------------------------------------------------------

QUOTES = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": " to ", "—": ", ", "…": "...", " ": " ",
    "�": "'",
}


def tidy(text):
    for bad, good in QUOTES.items():
        text = text.replace(bad, good)
    return re.sub(r"\s+", " ", text).strip()


def norm(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


# --------------------------------------------------------------------------
# Skill types
#
# The wiki uses about seventy different type labels, from "Physical" to
# "Grenade Launcher" to "Nature Ritual". We keep the label as written, because
# it is genuinely useful, and map it onto one of eight colour families so the
# page reads at a glance.
# --------------------------------------------------------------------------

TYPE_FAMILIES = [
    ("stance", ("stance",)),
    ("summon", ("summon", "trap", "drone", "madogear", "fauna", "flora",
                "talisman", "possession", "spirit", "homunculus")),
    ("passive", ("passive", "enchant", "mastery", "alignment", "informational")),
    ("magic", ("magical", "magic", "arcane", "elemental", "celestial",
               "nature ritual", "ritual", "miracle")),
    ("support", ("supportive", "support", "buff", "heal", "recovery", "aura",
                 "grace", "enhancement", "stimulant", "song", "dance",
                 "performance", "rhythm", "defensive")),
    ("debuff", ("debuff", "toxin", "curse", "chemical", "judgement",
                "authority", "mark")),
    ("utility", ("utility", "crafting", "command", "movement", "combo",
                 "opener")),
    ("physical", ("physical", "melee", "ranged", "offensive", "attack",
                  "blade", "dagger", "katar", "sword", "spear", "axe",
                  "hammer", "bow", "throwing", "revolver", "rifle", "shotgun",
                  "gatling", "grenade", "gun", "finisher", "strike", "kick",
                  "ninja art", "shade")),
]

DEFAULT_TYPE = "other"


def type_family(label):
    low = label.lower()
    for key, words in TYPE_FAMILIES:
        for word in words:
            if word in low:
                return key
    return DEFAULT_TYPE


# --------------------------------------------------------------------------
# Class mechanics
#
# Resources, stances and states a class builds its rotation around. They are
# not skills, so they never get their own entry, but they are referred to over
# and over inside skill text. Detected by head noun, then required to show up
# in at least two different skills so a one-off phrase does not qualify.
# --------------------------------------------------------------------------

MECH_HEADS = (
    "stance", "stances", "sphere", "spheres", "stack", "stacks",
    "marker", "markers", "enchant", "enchants", "art", "arts",
    "stigmata", "affinity", "affinities", "infusion", "rhythm",
    "grenade", "grenades", "stone", "stones", "discipline", "aura",
    "overdrive", "madogear", "homunculus", "extort", "blades", "fists",
    "talisman", "talismans", "veil", "seal", "seals", "charge", "charges",
    "coin", "coins", "blessing", "protection", "heat", "state", "barrier",
    "providence", "elemental", "trance",
)

# Words that start a sentence or a clause and get swept up by the capital
# letter run. Stripped off the front of a candidate.
LEAD_STOP = {
    "during", "while", "if", "the", "this", "a", "an", "each", "every",
    "when", "upon", "after", "before", "at", "consumes", "deals", "grants",
    "increases", "reduces", "creates", "summons", "calls", "gains", "gain",
    "generates", "has", "for", "in", "on", "to", "of", "and", "or", "with",
    "any", "all", "both", "only", "otherwise", "additionally", "also",
    "immediately", "passively", "using", "use", "uses", "activating",
    "orders", "order", "requires", "require", "returns", "targeting",
    "enables", "enable", "boosts", "boost", "provides", "provide",
    "allows", "allow", "improves", "improve", "empowers", "empower",
    "consuming", "applies", "inflicts", "removes", "restores", "converts",
    "adds", "their", "its", "user", "users", "target", "targets", "enemy",
    "enemies", "ally", "allies", "skill", "skills",
}

# Things the head-noun rule lets through that are not really mechanics.
MECH_DENY = {
    "fixed cast time", "variable cast time", "cast time", "cooldown",
    "skill level", "base level", "job level", "max level", "attack state",
    "current state", "elemental", "elemental property",
}

CAP_RUN = re.compile(r"\b[A-Z][A-Za-z']*(?:\s+(?:of\s+)?[A-Z][A-Za-z']*){0,3}\b")

STATUS_TERMS = set()
for _key, _label, _terms, _desc in STATUS:
    for _t in _terms:
        STATUS_TERMS.add(_t.lower())


def candidates(text):
    """Capitalised phrases in a body of text, with leading filler removed."""
    out = set()
    for run in CAP_RUN.findall(text):
        words = run.split()
        while words and words[0].lower() in LEAD_STOP:
            words.pop(0)
        while words and words[-1].lower() in LEAD_STOP:
            words.pop()
        if not words:
            continue
        phrase = " ".join(words)
        if phrase.lower() in MECH_DENY or phrase.lower() in STATUS_TERMS:
            continue
        if words[-1].lower() in MECH_HEADS:
            out.add(phrase)
    return out


TAG_SPLIT = re.compile(r"(<[^>]+>)")


def mark_mechanics(html, mechanics):
    """Marks class mechanics inside already escaped and colourised text.
    Splits on tags first so nothing lands inside an attribute."""
    if not mechanics:
        return html
    # The text switches between "a Void Sphere" and "five Void Spheres", so
    # match both forms of every mechanic.
    forms = set()
    for m in mechanics:
        forms.add(m)
        forms.add(m[:-1] if m.endswith("s") else m + "s")
    pattern = re.compile(r"\b(%s)\b" % "|".join(
        re.escape(m) for m in sorted(forms, key=lambda w: (-len(w), w))))
    out = []
    for part in TAG_SPLIT.split(html):
        if part.startswith("<"):
            out.append(part)
        else:
            out.append(pattern.sub(r'<b class="mech">\1</b>', part))
    return "".join(out)


def find_mechanics(skills, intro_text):
    """A mechanic has to appear in two different skills, or in one skill and
    in the class introduction. Skill names are excluded: a skill that another
    skill needs is a dependency, which the page shows differently."""
    names = {norm(s["name"]) for s in skills}
    seen = {}
    for s in skills:
        text = " ".join([s["short"]] + s["body"] + s["riders"] +
                        [o["text"] for o in s["options"]])
        for phrase in candidates(text):
            if norm(phrase) in names:
                continue
            seen.setdefault(phrase, set()).add(s["name"])

    intro_caps = candidates(intro_text)
    out = []
    for phrase, users in seen.items():
        if len(users) >= 2 or phrase in intro_caps:
            out.append(phrase)

    # Once a bare head noun has qualified, every named variant of it counts
    # too. Taekwon says "Stance" all over the place but names each one only
    # once, and the four stances are the whole point of the class.
    heads = {p.lower() for p in out if " " not in p}
    if heads:
        for phrase in seen:
            if phrase in out:
                continue
            if phrase.split()[-1].lower() in heads:
                out.append(phrase)

    # Drop a phrase that is only ever seen inside a longer one, so we list
    # "Void Spheres" and not "Void Spheres" plus "Void Sphere" plus "Spheres".
    # A bare head noun that already lives inside a skill name is just that
    # skill being talked about. Lord Knight says "Stance" constantly, but the
    # stances are Vanguard Stance and Warden Stance, both real skills.
    name_words = set()
    for s in skills:
        for word in s["name"].split():
            name_words.add(re.sub(r"[^a-z]", "", word.lower()))
    out = [p for p in out
           if " " in p or re.sub(r"[^a-z]", "", p.lower()) not in name_words]

    out.sort(key=lambda p: (-len(p), p))
    kept = []
    for phrase in out:
        if any(phrase.lower() in k.lower() and phrase.lower() != k.lower()
               for k in kept):
            continue
        # singular of a plural we already kept, and the other way round
        if any(norm(phrase) == norm(k).rstrip("s") or
               norm(phrase).rstrip("s") == norm(k) for k in kept):
            continue
        kept.append(phrase)
    kept.sort()
    return kept


# --------------------------------------------------------------------------
# Document parsing
# --------------------------------------------------------------------------

ENTRY_RE = re.compile(r"^([A-Z][^:]{1,60}):\s*(.*)$")
MARKER_RE = re.compile(r"(following skills|^skills:|skill points to spend)", re.I)

# Lines that are conditional riders on the skill above rather than skills.
RIDER_RE = re.compile(
    r"^(If|While|When|During|Whenever|Upon|Otherwise|Additionally|Note)\b|"
    r"\bBonus$", re.I)

# "Dagger Skill.", "Revolver Skill:", "Toxin Skill.", "Blade Enchant.",
# "Passive.", "Quest Skill." and friends, written at the head of the body.
LEAD_TAG_RE = re.compile(
    r'^((?:"?[A-Z][A-Za-z/\'-]*"?(?:\s+[A-Z][A-Za-z/\'-]*){0,3})\s+'
    r'(?:Skill|Skills|Enchant|Art|Arts)|Passive)\s*[.:]\s+')


def split_entries(blocks):
    """Splits a class body into intro paragraphs and raw name/body entries.
    No judgement yet about what is a skill and what is not."""
    texts = [t for t in (tidy(b["x"]) for b in blocks) if t]

    start = None
    for i, t in enumerate(texts):
        if t.endswith(":") and MARKER_RE.search(t):
            start = i + 1
            break
    if start is None:
        for i, t in enumerate(texts):
            m = ENTRY_RE.match(t)
            if m and len(m.group(2)) > 40:
                start = i
                break
    if start is None:
        start = len(texts)

    intro = [t for t in texts[:start] if not (t.endswith(":") and MARKER_RE.search(t))]

    entries = []
    for t in texts[start:]:
        m = ENTRY_RE.match(t)
        if m:
            name, rest = m.group(1).strip(), m.group(2).strip()
            # "Command: Attack!" and "Shuriken:" are headings, not pairs
            if not rest or (len(rest) < 32 and not rest.endswith(".")):
                entries.append({"name": t.rstrip(":").strip(), "body": []})
            else:
                entries.append({"name": name, "body": [rest]})
        elif entries:
            entries[-1]["body"].append(t)
        else:
            intro.append(t)

    return intro, entries


# --------------------------------------------------------------------------
# Matching document entries against the wiki skill list
# --------------------------------------------------------------------------

def wiki_index(groups):
    index = {}
    order = []
    for gi, group in enumerate(groups):
        for si, skill in enumerate(group["skills"]):
            key = norm(skill["name"])
            index[key] = {
                "name": skill["name"],
                "type": skill["type"],
                "max": skill["max"],
                "short": skill["desc"],
                "group": group["group"],
                "gi": gi,
                "si": si,
            }
            order.append(key)
    return index, order


def resolve(entry, index):
    """Finds the wiki row for a document entry, or None if the entry is not a
    skill in its own right."""
    key = norm(entry["name"])
    if key in index:
        return index[key]

    # "Tarot Card" + body "The Magician: Bestows..." is really the skill
    # "Tarot Card: The Magician".
    if entry["body"]:
        head = entry["body"][0].split(":", 1)
        if len(head) == 2 and len(head[0]) < 40:
            joined = norm(entry["name"] + head[0])
            if joined in index:
                hit = dict(index[joined])
                hit["strip_head"] = head[0].strip()
                return hit

    if RIDER_RE.search(entry["name"]):
        return None

    # The document predates a few wiki renames: Seismic Tremor became Seismic
    # Tremors, Falcon Mastery became Falconry Mastery, and so on.
    close = difflib.get_close_matches(key, list(index), n=1, cutoff=0.82)
    if close:
        return index[close[0]]
    return None


OPTION_RE = re.compile(r"^(Level\s+\d+|[A-Z][A-Za-z'/ ]{1,28})$")


def attach(parent, entry):
    """Folds a non-skill entry into the skill above it."""
    body = " ".join(entry["body"]).strip()
    name = entry["name"]

    # A short option written on one line, "Dark: The user's SP Regen is
    # halved", arrives here with the whole line as the name.
    if not body and ": " in name:
        label, rest = name.split(": ", 1)
        if len(label) <= 30 and not RIDER_RE.search(label):
            name, body = label, rest

    if RIDER_RE.search(name):
        text = ("%s: %s" % (name, body)) if body else name
        # "Toxic Blades Bonus: Treated as Poison Damage" reads fine as is
        parent["riders"].append(re.sub(r"\s+", " ", text).strip())
    elif OPTION_RE.match(name):
        parent["options"].append({"label": name, "text": body})
    elif body:
        parent["riders"].append("%s: %s" % (name, body))
    else:
        parent["options"].append({"label": name, "text": ""})


# Riders that the document writes as their own paragraph under the skill.
INLINE_RIDER_RE = re.compile(r"^(If|While|Whenever)\s+[A-Z]")


def clean_body(paragraphs):
    """Splits a skill body into plain paragraphs and conditional riders, and
    strips the "Dagger Skill." style tag off the front."""
    body, riders, tag = [], [], ""
    for i, para in enumerate(paragraphs):
        text = para.strip()
        if i == 0:
            m = LEAD_TAG_RE.match(text)
            if m:
                tag = m.group(1).strip()
                text = text[m.end():].strip()
        if not text:
            continue
        if INLINE_RIDER_RE.match(text) and (body or riders):
            riders.append(text)
        else:
            body.append(text)
    return body, riders, tag


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

# An entry the wiki skill tables do not list is, by definition, not a skill.
# In practice it is always a class mechanic the document explains inline, like
# High Wizard's Affinities.
GROUP_FALLBACK = "Mechanics"


def build(class_name, blocks, wiki):
    intro, entries = split_entries(blocks)
    groups = wiki.get(class_name, [])
    index, _order = wiki_index(groups)

    skills = []
    for entry in entries:
        hit = resolve(entry, index)
        if hit is None and skills:
            attach(skills[-1], entry)
            continue

        paragraphs = list(entry["body"])
        if hit and hit.get("strip_head"):
            # drop the "The Magician:" prefix, it is in the name now
            head = hit["strip_head"]
            if paragraphs and paragraphs[0].startswith(head):
                paragraphs[0] = paragraphs[0][len(head):].lstrip(": ").strip()

        body, riders, tag = clean_body(paragraphs)
        name = hit["name"] if hit else entry["name"]
        fallback = tag or GROUP_FALLBACK

        skills.append({
            "name": name,
            "type": (hit["type"] if hit else "") or tag or "",
            "max": hit["max"] if hit else "",
            "short": hit["short"] if hit else "",
            "group": hit["group"] if hit else fallback,
            "gi": hit["gi"] if hit else 99,
            "si": hit["si"] if hit else len(skills),
            "body": body,
            "riders": riders,
            "options": [],
            "needs": [],
        })

    for s in skills:
        if s["group"] == GROUP_FALLBACK and not s["type"]:
            s["type"] = "Mechanic"

    # ---- dependencies: a skill that names another skill of the same class
    by_name = {}
    for s in skills:
        by_name[s["name"].lower()] = s["name"]
    # longest first so "Void Infusion" wins over "Void"
    ordered = sorted(by_name, key=len, reverse=True)

    for s in skills:
        # Option labels are left out on purpose. An Axe Stance table that
        # lists "Counter Kick: Inflicts Vulnerable" is describing what the
        # stance does to those kicks, not depending on them.
        text = " ".join([s["short"]] + s["body"] + s["riders"] +
                        [o["text"] for o in s["options"]])
        low = text.lower()
        found = []
        for other in ordered:
            if other == s["name"].lower() or len(other) < 5:
                continue
            if re.search(r"\b%s\b" % re.escape(other), low):
                if not any(other in f for f in found):
                    found.append(other)
        s["needs"] = [by_name[f] for f in found][:3]

    mechanics = find_mechanics(skills, " ".join(intro))

    # ---- lay the skills back out in wiki order, one bucket per branch
    buckets = []
    seen = {}
    for s in sorted(skills, key=lambda s: (s["gi"], s["si"])):
        label = s["group"]
        if label not in seen:
            seen[label] = {"label": label, "skills": []}
            buckets.append(seen[label])
        seen[label]["skills"].append(s)

    return {
        "intro": intro,
        "groups": buckets,
        "skills": skills,
        "mechanics": mechanics,
    }
