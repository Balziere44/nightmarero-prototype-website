#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pulls the per skill pages off the player wiki into tools/data/wiki-skills.json.

    python tools/fetch_wiki_skills.py

fetch_wiki.py reads the class pages, which give a skill its name, its branch,
its type and its level cap. That was everything the wiki had when it was
written. Since then every skill has been given a page of its own, and those
pages carry the part that was missing: the full description, what the skill
targets, what it needs learnt first, and a table of what each level of it
actually does.

Only this script needs the network. The JSON it writes is committed, so
build_classes.py works offline.

A table is only kept if every row has as many cells as the header. Some pages
were typed by hand and their rows do not line up; half a row of numbers is
worse than none, so those are dropped and reported at the end.
"""

import io
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

API = "https://wiki.nightmareofragnarok.com/w/api.php"
OUT = os.path.join(ROOT, "tools", "data", "wiki-skills.json")
UA = "NightmareRO-site-build/1.0 (static site generator)"
BATCH = 40


def get(params):
    params = dict(params)
    params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))


def fetch(titles):
    """Wikitext for up to BATCH titles at once."""
    out = {}
    data = get({"action": "query", "prop": "revisions", "rvprop": "content",
                "rvslots": "main", "titles": "|".join(titles)})
    for page in data.get("query", {}).get("pages", {}).values():
        if "missing" in page:
            continue
        try:
            out[page["title"]] = page["revisions"][0]["slots"]["main"]["*"]
        except (KeyError, IndexError):
            pass
    return out


LINK_RE = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]|]*)\]\]")
TAG_RE = re.compile(r"<[^>]+>")


def clean(cell):
    """Wikitext to plain text. Same rules as fetch_wiki.py."""
    text = LINK_RE.sub(r"\1", cell)
    text = text.replace("'''", "").replace("''", "")
    text = TAG_RE.sub(" ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("—", ", ").replace("–", " to ")
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"\s+([,.;:!?])", r"\1", text)


def infobox(text):
    """The {{SkillInfobox}} at the top, as a dict.

    Written by hand on 586 pages, so a few are missing their closing braces
    and run one field into the next. Anything with a newline inside it after
    the split is a field that ate its neighbour, and gets dropped."""
    start = text.find("{{")
    if start < 0:
        return {}
    depth, i = 0, start
    while i < len(text):
        if text[i:i + 2] == "{{":
            depth += 1
            i += 2
        elif text[i:i + 2] == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                break
        else:
            i += 1
    body = text[start + 2:i - 2]
    out = {}
    for part in body.split("\n|"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip().lstrip("|").lower()
        value = clean(value)
        if key and value and "{" not in value:
            out[key] = value
    return out


HEAD_RE = re.compile(r"^\s*(={2,4})\s*(.+?)\s*\1\s*$")


def section(text, name):
    """The body of a == heading == section, without its sub headings."""
    lines = text.split("\n")
    out, taking = [], False
    for line in lines:
        m = HEAD_RE.match(line)
        if m:
            taking = clean(m.group(2)).lower() == name and len(m.group(1)) == 2
            continue
        if taking:
            out.append(line)
    return "\n".join(out)


def description(text):
    """The prose under == Description ==, as paragraphs."""
    body = section(text, "description")
    body = re.sub(r"\{\{[^{}]*\}\}", "", body)
    paras = []
    for chunk in re.split(r"\n\s*\n", body):
        chunk = clean(chunk)
        if chunk and not chunk.startswith(("[[Category", "{|", "|")):
            paras.append(chunk)
    return paras


def cells(line):
    """The cells on one wikitable row or header line.

    A row can be written as one line of `||` separated cells or as one line
    per cell, and headers use `!!` for the same job. Inside a cell, a single
    pipe separates the styling from the content, which is why the links are
    resolved to plain text first: `[[Status Effects#Bleed|Bleed]]` carries a
    pipe of its own and would otherwise be cut in half.

    Some rows on the wiki are typed with a stray pipe in them. Reading the
    part after the first pipe is what the wiki itself does, so this lands on
    the same values a reader sees."""
    line = LINK_RE.sub(r"\1", line)
    line = line[1:].replace("!!", "||")
    out = []
    for part in line.split("||"):
        if "|" in part:
            part = part.split("|", 1)[1]
        out.append(clean(part))
    return out


def level_table(text):
    """The == Skill Levels == table as (headers, rows), or None."""
    body = section(text, "skill levels")
    if "{|" not in body:
        return None

    lines = body.split("\n")
    headers, rows, row = [], [], None
    started = False
    for line in lines:
        line = line.strip()
        if line.startswith("{|"):
            started = True
            continue
        if not started or line.startswith(("|+", "|-")):
            if line.startswith("|-") and row:
                rows.append(row)
                row = None
            if line.startswith("|-"):
                row = []
            continue
        if line.startswith("|}"):
            break
        if line.startswith("!"):
            headers.extend(c for c in cells(line) if c)
            row = None
            continue
        if line.startswith("|") and row is not None:
            row.extend(cells(line))
    if row:
        rows.append(row)

    rows = [r for r in rows if any(c for c in r)]
    if len(headers) < 2 or not rows:
        return None
    if any(len(r) != len(headers) for r in rows):
        return None
    return {"headers": headers, "rows": rows}


def main():
    urllib.parse  # noqa, imported through urllib.request

    classes = json.load(io.open(os.path.join(ROOT, "tools", "data",
                                             "wiki-classes.json"),
                                encoding="utf-8"))
    names = []
    for _cls, groups in sorted(classes.items()):
        for group in groups:
            for skill in group["skills"]:
                if skill["name"] not in names:
                    names.append(skill["name"])

    pages = {}
    for i in range(0, len(names), BATCH):
        pages.update(fetch(names[i:i + BATCH]))
        time.sleep(0.2)

    out, ragged, tableless = {}, [], []
    for name in names:
        text = pages.get(name)
        if text is None:
            continue
        entry = {}
        box = infobox(text)
        for key in ("type", "target", "requires", "skillform", "maxlevel"):
            if box.get(key):
                entry[key] = box[key]
        paras = description(text)
        if paras:
            entry["desc"] = paras
        table = level_table(text)
        if table:
            entry["levels"] = table
        elif "Skill Levels" in text:
            (ragged if "{|" in section(text, "skill levels")
             else tableless).append(name)
        if entry:
            out[name] = entry

    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))

    withtab = sum(1 for e in out.values() if "levels" in e)
    print("tools/data/wiki-skills.json: %d of %d skills, %d with a level "
          "table (%.0f KB)"
          % (len(out), len(names), withtab, os.path.getsize(OUT) / 1024.0))
    if tableless:
        print("No table yet (%d): %s" % (len(tableless), ", ".join(tableless)))
    if ragged:
        print("Table rows do not line up (%d): %s"
              % (len(ragged), ", ".join(ragged)))


if __name__ == "__main__":
    import urllib.parse  # noqa
    sys.exit(main())
