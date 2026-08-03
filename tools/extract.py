#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turns a saved copy of the published Class Overviews document into classes.json.

    python tools/extract.py "Class Overviews.html" tools/classes.json

Save the published Google Doc from the browser (Ctrl+S, "Webpage, complete" or
"Webpage, HTML only"), point this at the .html file, then run
tools/build_classes.py to rebuild the pages.

Each class heading in the document becomes a key. The value is the list of
paragraphs and list items under it, in order, which build_classes.py splits
into the intro and the skill list.
"""

import io
import re
import sys
import html
import json


def clean(fragment):
    text = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def main():
    if len(sys.argv) < 3:
        sys.exit("Usage: python tools/extract.py <source.html> <out.json>")

    source, target = sys.argv[1], sys.argv[2]
    raw = io.open(source, encoding="utf-8", errors="replace").read()

    body = re.search(r"<body[^>]*>(.*)</body>", raw, re.S | re.I)
    if body:
        raw = body.group(1)
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.S | re.I)

    headings = list(re.finditer(r"<(h[1-6])[^>]*>(.*?)</\1>", raw, re.S | re.I))
    data = {}

    for i, heading in enumerate(headings):
        name = clean(heading.group(2))
        if not name or name.lower().startswith("table of contents"):
            continue

        end = headings[i + 1].start() if i + 1 < len(headings) else len(raw)
        blocks = []
        for block in re.finditer(r"<(p|li)\b[^>]*>(.*?)</\1>",
                                 raw[heading.end():end], re.S | re.I):
            text = clean(block.group(2))
            if text:
                blocks.append({"t": block.group(1).lower(), "x": text})

        data[name] = blocks

    io.open(target, "w", encoding="utf-8", newline="\n").write(
        json.dumps(data, ensure_ascii=False, indent=1))

    print("Wrote %s with %d sections" % (target, len(data)))
    for name, blocks in data.items():
        print("  %-22s %3d blocks" % (name, len(blocks)))


if __name__ == "__main__":
    main()
