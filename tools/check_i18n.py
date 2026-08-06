#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Checks the locale files before they ship.

English lives in the HTML, the other five languages are plain script files that
call NM_I18N_REGISTER with one object literal. A single missing comma or a bare
apostrophe inside a value makes the browser throw on the whole file, and the
page silently stays in English, which is exactly how the last regression got
out. This reads every locale file the same way a parser would and reports:

  * lines that are not a well formed  'key': 'value',  pair
  * duplicate keys inside one file
  * keys asked for by the pages but missing from a locale
  * keys a locale carries that no page ever asks for

    python tools/check_i18n.py

Exits non zero when anything is wrong, so it can gate a commit.
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
I18N = os.path.join(ROOT, "assets", "i18n")
LOCALES = ("pt", "fr", "it", "de", "ja")

BS = chr(92)
# a value may carry escaped quotes, nothing else may end the string early
STR = "'(?:[^'" + BS + BS + "]|" + BS + BS + ".)*'"
PAIR = re.compile("^  (" + STR + "): (" + STR + "),$")

I18N_ATTR = re.compile(r'data-i18n="([^"]+)"')
I18N_ATTR_PAIRS = re.compile(r'data-i18n-attr="([^"]+)"')

# the database and quiz build their labels at runtime. Keys are passed around
# as plain strings, t('db.lv', 'Lv') or flash(btn, 'db.copied', 'Copied'), so
# any dotted literal in a script counts as a lookup. Some are only a prefix,
# t('db.s.' + slot, ...), which stands for a whole family of keys.
RUNTIME = re.compile(r"'([a-z][A-Za-z0-9]*(?:\.[A-Za-z0-9_]+)+)'")
RUNTIME_FAMILY = re.compile(r"'([A-Za-z0-9._]*\.)'\s*\+")

# i18n.js only mentions data-i18n in its own documentation
SKIP_FILES = ("assets/js/i18n.js",)


def page_keys(namespaces):
    """Every key the built pages actually look up, plus the key prefixes that
    are completed at runtime."""
    keys, families = set(), set()
    for base, dirs, files in os.walk(ROOT):
        if any(part in base for part in (".git", "node_modules", "tools")):
            continue
        for name in files:
            if not name.endswith((".html", ".js")):
                continue
            path = os.path.join(base, name)
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            if rel in SKIP_FILES:
                continue
            text = io.open(path, encoding="utf-8", errors="replace").read()
            keys.update(I18N_ATTR.findall(text))
            for chunk in I18N_ATTR_PAIRS.findall(text):
                for pair in chunk.split(","):
                    bits = pair.split(":")
                    if len(bits) > 1:
                        keys.add(bits[1].strip())
            if name.endswith(".js"):
                # a dotted literal could just as well be a host name, so only
                # trust the namespaces the locale files already use
                for key in RUNTIME.findall(text):
                    if key.split(".")[0] in namespaces:
                        keys.add(key)
                families.update(RUNTIME_FAMILY.findall(text))
    return keys, families


def read_locale(code, problems):
    path = os.path.join(I18N, code + ".js")
    lines = io.open(path, encoding="utf-8").read().split("\n")
    table, seen = {}, set()

    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if (not stripped or stripped.startswith("/*") or
                stripped.startswith("window.") or stripped in ("});", "}")):
            continue
        found = PAIR.match(line.rstrip())
        if not found:
            problems.append("%s.js:%d  not a valid key value pair: %s"
                            % (code, number, stripped[:80]))
            continue
        key = found.group(1)[1:-1]
        if key in seen:
            problems.append("%s.js:%d  duplicate key %s" % (code, number, key))
        seen.add(key)
        table[key] = found.group(2)[1:-1]

    return table


def main():
    problems = []
    tables = {}

    for code in LOCALES:
        tables[code] = read_locale(code, problems)

    namespaces = set(k.split(".")[0] for t in tables.values() for k in t)
    wanted, families = page_keys(namespaces)

    def used(key):
        return key in wanted or any(key.startswith(f) for f in families)

    spare = []
    for code in LOCALES:
        table = tables[code]
        for key in sorted(wanted - set(table)):
            problems.append("%s.js  missing key %s" % (code, key))
        for key in sorted(k for k in table if not used(k)):
            spare.append("%s.js  spare key %s" % (code, key))

    print("pages ask for %d keys" % len(wanted))
    for code in LOCALES:
        print("  %-3s %d keys" % (code, len(tables[code])))

    # a translated string no page uses right now is harmless, so say it and
    # carry on
    for line in spare:
        print("  note: " + line)

    if problems:
        print("\n%d problem(s):" % len(problems))
        for line in problems:
            print("  " + line)
        return 1

    print("\nall locales parse and cover every key")
    return 0


if __name__ == "__main__":
    sys.exit(main())
