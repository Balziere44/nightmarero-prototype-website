#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stamps every page with the build it belongs to, so nobody is ever looking at a
cached copy of the site.

    python tools/stamp_build.py        # after any change, before committing
    python tools/stamp_build.py --check  # fail if a stamp is out of date

`_headers` already tells Cloudflare and the browser to revalidate everything on
every visit, which is what a Ctrl+Shift+R does. That only governs copies fetched
from now on: a reader who was here yesterday still holds items.json under the
old rule that let it sit for a day, and no header we send today can reach into
that. A changed URL can. So each page carries a build id and asks for its
stylesheet, its scripts and its data with `?v=<id>` on the end, which is an
address the old cache has never seen and therefore cannot answer from.

The id is a hash of everything it stamps, so it changes when the site changes
and not otherwise. The JSON files are hashed into it too, even though the pages
do not name them directly: the scripts read the id off <html data-build> and put
it on their own fetches, so a rebuilt database is a new URL as well.
"""

import hashlib
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Everything a page pulls in that is ours and can change. Artwork is left out:
# it is served under a name of its own and replaced by adding a file, never by
# overwriting one.
HASHED = (
    "assets/css",
    "assets/js",
    "assets/i18n",
    "assets/data",
    "assets/quiz",
)

# href="assets/css/style.css" and src="../assets/js/main.js", with or without a
# stamp already on them. The data folder is in here for one line: database.html
# preloads items.json, and a preload that asks for a different address than the
# script does is a 1.2 MB file downloaded twice.
REF = re.compile(
    r'((?:src|href)=")((?:\.\./)?assets/(?:css|js|data)/[A-Za-z0-9_.-]+)'
    r'(?:\?v=[A-Za-z0-9]+)?(")')
HTML_TAG = re.compile(r'(<html\b[^>]*?)(?:\s+data-build="[A-Za-z0-9]*")?(\s*>)')


def pages():
    for name in sorted(os.listdir(ROOT)):
        if name.endswith(".html"):
            yield os.path.join(ROOT, name)
    sub = os.path.join(ROOT, "classes")
    if os.path.isdir(sub):
        for name in sorted(os.listdir(sub)):
            if name.endswith(".html"):
                yield os.path.join(sub, name)


def build_id():
    """One short hash over every file the pages can end up asking for."""
    digest = hashlib.sha1()
    for folder in HASHED:
        path = os.path.join(ROOT, folder)
        if not os.path.isdir(path):
            continue
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            if os.path.isfile(full):
                digest.update(name.encode("utf-8"))
                digest.update(io.open(full, "rb").read())
    return digest.hexdigest()[:10]


def stamp(text, ident):
    text = REF.sub(lambda m: "%s%s?v=%s%s"
                   % (m.group(1), m.group(2), ident, m.group(3)), text)
    return HTML_TAG.sub(lambda m: '%s data-build="%s"%s'
                        % (m.group(1), ident, m.group(2)), text, count=1)


def main():
    check = "--check" in sys.argv
    ident = build_id()
    stale, written = [], 0

    for path in pages():
        text = io.open(path, encoding="utf-8").read()
        fixed = stamp(text, ident)
        if fixed == text:
            continue
        stale.append(os.path.relpath(path, ROOT).replace("\\", "/"))
        if not check:
            io.open(path, "w", encoding="utf-8", newline="\n").write(fixed)
            written += 1

    if check:
        if stale:
            print("build %s: %d páginas desatualizadas: %s"
                  % (ident, len(stale), ", ".join(stale[:6])))
            return 1
        print("build %s: todas as páginas carimbadas" % ident)
        return 0

    print("build %s -> %d páginas carimbadas (de %d)"
          % (ident, written, len(list(pages()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
