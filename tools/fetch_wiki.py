#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pulls the skill tables off the player wiki and writes tools/data/wiki-classes.json.

The wiki is the only place that says, per skill, which branch of the tree it
belongs to, whether it is physical, magical, supportive or passive, and how
many levels it has. The Class Overviews document has none of that. So the
build reads both: prose from the document, structure from here.

    python tools/fetch_wiki.py

Only this script needs the network. The JSON it writes is committed, so
build_classes.py works offline.
"""

import io
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://wiki.nightmareofragnarok.com/w/api.php"
OUT = os.path.join(ROOT, "tools", "data", "wiki-classes.json")
UA = "NightmareRO-site-build/1.0 (static site generator)"

# Page titles on the wiki, where they differ from the name we use.
TITLES = {
    "Bard and Dancer": "Bard/Dancer",
}

CLASSES = [
    "Swordsman", "Knight", "Lord Knight", "Rune Knight", "Crusader", "Paladin",
    "Royal Guard", "Merchant", "Blacksmith", "Mastersmith", "Mechanic",
    "Alchemist", "Biochemist", "Geneticist", "Thief", "Assassin",
    "Assassin Cross", "Guillotine Cross", "Rogue", "Stalker", "Shadow Chaser",
    "Mage", "Wizard", "High Wizard", "Warlock", "Sage", "Scholar", "Sorcerer",
    "Archer", "Hunter", "Sniper", "Ranger", "Bard and Dancer", "Clown/Gypsy",
    "Minstrel/Wanderer", "Acolyte", "Priest", "High Priest", "Arch Bishop",
    "Monk", "Champion", "Sura", "Taekwon", "Star Gladiator", "Star Emperor",
    "Sky Emperor", "Soul Linker", "Soul Reaper", "Soul Ascetic", "Ninja",
    "Kagemusha", "Maboroshi", "Gunslinger", "Rebel", "Night Watch",
]


def get(params):
    params = dict(params)
    params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=45).read().decode("utf-8"))


def wikitext(title):
    data = get({"action": "query", "prop": "revisions", "rvprop": "content",
                "rvslots": "main", "titles": title})
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if "missing" in page:
            return None
        try:
            return page["revisions"][0]["slots"]["main"]["*"]
        except (KeyError, IndexError):
            return None
    return None


LINK_RE = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]|]*)\]\]")
TAG_RE = re.compile(r"<[^>]+>")
TPL_RE = re.compile(r"\{\{[^{}]*\}\}")


def clean(cell):
    """Wikitext cell to plain text."""
    text = cell
    for _ in range(3):
        text = TPL_RE.sub("", text)
    text = LINK_RE.sub(r"\1", text)
    text = text.replace("'''", "").replace("''", "")
    text = TAG_RE.sub(" ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    # the wiki uses an em dash in a few short descriptions; we never do
    text = text.replace("—", ", ").replace("–", " to ")
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = re.sub(r"\s+", " ", text).strip()
    # a dash that became a comma leaves a space in front of it
    return re.sub(r"\s+([,.;:!?])", r"\1", text)


HEAD_RE = re.compile(r"^\s*(={2,4})\s*(.+?)\s*\1\s*$")

# A placeholder row the wiki template ships with. Not real data.
PLACEHOLDER = re.compile(r"^(skill|item|name|example)\s*(name)?$", re.I)


def parse_tables(text):
    """Walks the page, tracking the current heading, and reads every
    wikitable whose header row starts with a Skill column."""
    groups = []
    heading = None
    in_skills = False
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        m = HEAD_RE.match(line)
        if m:
            level, label = len(m.group(1)), clean(m.group(2))
            if level == 2:
                in_skills = label.lower() == "skills"
                heading = None
            elif in_skills:
                heading = label
            i += 1
            continue

        if in_skills and line.strip().startswith("{|"):
            rows, i = read_table(lines, i)
            if rows:
                skills = []
                for cells in rows:
                    name = clean(cells[0]) if cells else ""
                    if not name or PLACEHOLDER.match(name):
                        continue
                    skills.append({
                        "name": name,
                        "type": clean(cells[1]) if len(cells) > 1 else "",
                        "max": clean(cells[2]) if len(cells) > 2 else "",
                        "desc": clean(cells[3]) if len(cells) > 3 else "",
                    })
                if skills:
                    groups.append({"group": heading or "Skills", "skills": skills})
            continue

        i += 1

    return groups


def read_table(lines, i):
    """Reads one wikitable starting at lines[i], returns (data rows, next i).
    The header row is dropped."""
    rows = []
    current = None
    i += 1
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|}"):
            i += 1
            break
        if line.startswith("|-"):
            if current:
                rows.append(current)
            current = []
        elif line.startswith("!"):
            current = None            # header row, skip it
        elif line.startswith("|") and current is not None:
            body = line[1:]
            if body.startswith("|"):  # "||" inline separator
                body = body[1:]
            current.extend(p for p in body.split("||"))
        elif current and current and not line.startswith(("|", "!", "{|")):
            # continuation of the previous cell
            if line:
                current[-1] += " " + line
        i += 1
    if current:
        rows.append(current)
    return rows, i


def main():
    urllib.parse  # noqa, imported through urllib.request
    out = {}
    missing = []

    for name in CLASSES:
        title = TITLES.get(name, name.replace(" ", "_"))
        text = wikitext(title)
        if text is None:
            missing.append(name)
            continue
        groups = parse_tables(text)
        if groups:
            out[name] = groups
        else:
            missing.append(name + " (no skill table)")
        time.sleep(0.25)

    if not os.path.isdir(os.path.dirname(OUT)):
        os.makedirs(os.path.dirname(OUT))
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))

    total = sum(len(g["skills"]) for gs in out.values() for g in gs)
    print("tools/data/wiki-classes.json: %d classes, %d skills (%.0f KB)"
          % (len(out), total, os.path.getsize(OUT) / 1024.0))
    if missing:
        print("No wiki data for: %s" % ", ".join(missing))


if __name__ == "__main__":
    import urllib.parse  # noqa
    main()
