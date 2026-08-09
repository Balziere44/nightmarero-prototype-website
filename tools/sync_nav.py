#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rewrites the nav and the drawer of the hand written pages.

    python tools/sync_nav.py

index.html, database.html, quiz.html and download.html are edited by hand, so
they carry their own copy of the header and the footer. The generated pages
get theirs from build_classes.header() and footer(). This script pastes both
back into the four copies, so changing NEW_PAGES, DB_PAGES, the nav layout or
a reference link only ever needs doing once.

Run it after any change to either, then rebuild the generated pages.
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from build_classes import nav_desktop, nav_drawer, footer

# page -> the value header() would get as its active page
PAGES = [
    ("index.html", ""),
    ("database.html", "database.html"),
    ("quiz.html", "quiz.html"),
    ("download.html", "download.html"),
]

MAIN = re.compile(r'(<nav class="nav" aria-label="Main">\n).*?(\n    </nav>)', re.S)
DRAWER = re.compile(r'(<nav aria-label="Mobile">\n).*?(\n    </nav>)', re.S)
# The footer carries the reference links, which change more often than the
# nav does, so it gets pasted back the same way.
FOOT = re.compile(r'<footer class="site-footer">.*?</footer>\n', re.S)


def main():
    for page, active in PAGES:
        path = os.path.join(ROOT, page)
        text = io.open(path, encoding="utf-8").read()
        before = text

        text, hit_main = MAIN.subn(
            lambda m: m.group(1) + nav_desktop("", active) + m.group(2),
            text, count=1)
        text, hit_drawer = DRAWER.subn(
            lambda m: m.group(1) + nav_drawer("") + m.group(2), text, count=1)

        text, hit_foot = FOOT.subn(
            lambda m: footer("").split("</footer>")[0] + "</footer>\n",
            text, count=1)

        if not (hit_main and hit_drawer and hit_foot):
            print("%s: could not find the chrome (main=%d, drawer=%d, foot=%d)"
                  % (page, hit_main, hit_drawer, hit_foot))
            continue

        io.open(path, "w", encoding="utf-8", newline="\n").write(text)
        print("%s: %s" % (page, "updated" if text != before else "already current"))


if __name__ == "__main__":
    sys.exit(main())
