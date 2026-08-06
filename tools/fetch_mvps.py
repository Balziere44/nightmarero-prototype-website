#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Downloads the MVP and quest reference sheets as CSV into tools/data/.

Two spreadsheets feed the MVP and quest pages:

  mvp   summon items, altar locations, Nightmare dungeon bosses, MVP cards
        and relic gear
  quest the per-quest walkthroughs, one tab each

    python tools/fetch_mvps.py

Only this script needs the network. The CSVs are committed so
build_mvps.py and build_quests.py work offline.
"""

import io
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", "data")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NightmareRO-site-build/1.0"

MVP_SHEET = "1ojSow2JMglSDcvXii3Sppoa9Nx9mWAcVtC3c_OzApzk"
QUEST_SHEET = "1Nr10_X30Okn5MgPTZVSpoSGuy50g7VdRvyOm1p9IRSk"

# (output file stem, spreadsheet id, gid)
TABS = [
    ("mvp-summon-items", MVP_SHEET, "1375148529"),
    ("mvp-locations", MVP_SHEET, "205823077"),
    ("mvp-nightmare", MVP_SHEET, "1824768857"),
    ("mvp-cards", MVP_SHEET, "1831781680"),
    ("mvp-relic-gears", MVP_SHEET, "877761147"),
    ("mvp-spoiler-quest", MVP_SHEET, "927236412"),

    ("quest-index", QUEST_SHEET, "1646101137"),
    ("quest-relic-gear-options", QUEST_SHEET, "1861244107"),
    ("quest-amatsu", QUEST_SHEET, "1257873792"),
    ("quest-true-hero-shadow-gloves", QUEST_SHEET, "488668968"),
    ("quest-fallen-hero", QUEST_SHEET, "1994544935"),
    ("quest-niflheim-challenge", QUEST_SHEET, "658849052"),
    ("quest-kiel-challenge", QUEST_SHEET, "1952083904"),
    ("quest-thor-challenge", QUEST_SHEET, "1597208723"),
    ("quest-black-ops", QUEST_SHEET, "370565337"),
    ("quest-celine-kimi", QUEST_SHEET, "1141716589"),
    ("quest-endless-desert", QUEST_SHEET, "1906486285"),
    ("quest-lighthalzen-entrance", QUEST_SHEET, "1868481926"),
]

URL = ("https://docs.google.com/spreadsheets/d/%s/export"
       "?format=csv&gid=%s")


def fetch(sheet_id, gid):
    req = urllib.request.Request(URL % (sheet_id, gid),
                                 headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8-sig")


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)

    failed = []
    for stem, sheet_id, gid in TABS:
        try:
            text = fetch(sheet_id, gid)
        except Exception as exc:                      # noqa: BLE001
            failed.append("%s (%s)" % (stem, exc))
            continue
        path = os.path.join(OUT, stem + ".csv")
        io.open(path, "w", encoding="utf-8", newline="\n").write(text)
        print("%-32s %6.1f KB" % (stem + ".csv", len(text) / 1024.0))
        time.sleep(0.4)

    if failed:
        print("Could not download: %s" % ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
