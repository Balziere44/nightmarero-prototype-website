#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Downloads every tab of the published Gear and Card reference sheets into
tools/data/*.csv.

    python tools/fetch_sheets.py
    python tools/build_database.py

Only run this when Twilight has changed the sheets. The CSVs are committed,
so a normal rebuild does not need network access.

Empty tabs are skipped. Both Shadow tabs have content now.
"""

import io
import os
import re
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", "data")

DOCS = {
    "gear": "2PACX-1vT3yuB3St__9v202ZUU9pUZm4PX88tph379Dr2eMR3TFNfZ0GUVD0tvuBl99Ma8GHp5e2pLzLG6Bmds",
    "card": "2PACX-1vRaVCw9eEP3D-VlpBCryCcXy84FkDTm2RU-whdMIAZ8HuYhRvlsQrKqBiUUQlcLHq6gUqq6PXeUKB_5",
}

BASE = "https://docs.google.com/spreadsheets/d/e/%s"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)

    for doc, key in DOCS.items():
        page = get((BASE % key) + "/pubhtml")
        names = re.findall(r'name: ?"([^"]+)"', page)

        seen, gids = set(), []
        for g in re.findall(r"gid=(\d+)", page):
            if g not in seen:
                seen.add(g)
                gids.append(g)

        print("\n%s: %d tabs" % (doc, len(gids)))
        for i, gid in enumerate(gids):
            name = names[i] if i < len(names) else gid
            csv = get((BASE % key) + "/pub?gid=%s&single=true&output=csv" % gid)
            if not csv.strip():
                print("  %-24s empty, skipped" % name)
                continue
            safe = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            path = os.path.join(OUT, "%s__%s.csv" % (doc, safe))
            io.open(path, "w", encoding="utf-8", newline="\n").write(csv)
            print("  %-24s %6d bytes" % (name, len(csv)))

    print("\nNow run: python tools/build_database.py")


if __name__ == "__main__":
    main()
