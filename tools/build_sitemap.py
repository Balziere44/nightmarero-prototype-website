#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Writes sitemap.xml from whatever HTML files are in the project."""

import io
import os
import glob
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://nightmarero.pages.dev"
TODAY = datetime.date.today().isoformat()

PRIORITY = {"index.html": ("1.0", "weekly"),
            "classes.html": ("0.9", "weekly"),
            "download.html": ("0.9", "monthly"),
            "database.html": ("0.8", "weekly"),
            "mvps.html": ("0.8", "weekly"),
            "quests.html": ("0.8", "monthly")}


def main():
    pages = [os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "*.html"))]
    pages.sort(key=lambda p: (p != "index.html", p))

    urls = []
    for page in pages:
        prio, freq = PRIORITY.get(page, ("0.7", "monthly"))
        loc = SITE + "/" + ("" if page == "index.html" else page)
        urls.append((loc, prio, freq))

    for p in sorted(glob.glob(os.path.join(ROOT, "classes", "*.html"))):
        urls.append((SITE + "/classes/" + os.path.basename(p), "0.6", "monthly"))

    body = "\n".join(
        '  <url>\n'
        '    <loc>{loc}</loc>\n'
        '    <lastmod>{mod}</lastmod>\n'
        '    <changefreq>{freq}</changefreq>\n'
        '    <priority>{prio}</priority>\n'
        '  </url>'.format(loc=loc, mod=TODAY, freq=freq, prio=prio)
        for loc, prio, freq in urls)

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + body + "\n</urlset>\n")

    io.open(os.path.join(ROOT, "sitemap.xml"), "w",
            encoding="utf-8", newline="\n").write(xml)
    print("sitemap.xml written with %d urls" % len(urls))


if __name__ == "__main__":
    main()
