# Nightmare RO website

Static site for the Nightmare RO server. No build step, no framework, no
dependencies. Plain HTML, one stylesheet, two small scripts. Drop it on any
static host and it works.

---

## Contents

```
.
├── index.html               landing page
├── guide.html               new player guide, still a placeholder
├── classes.html             class hub, filter + search over all 55
├── quiz.html                class personality test
├── database.html            items and cards
├── mvps.html                boss altars, summon lists and drops
├── quests.html              spoiler quest walkthroughs
├── download.html            client download and install help
├── classes/                 55 generated class pages
├── assets/
│   ├── css/style.css        the whole design system
│   ├── js/main.js           theme, menus, countdown, filters
│   ├── js/i18n.js           language switcher
│   ├── i18n/                pt, fr, it, de, ja  (English lives in the HTML)
│   └── img/
│       ├── classes/         character art, .webp, two sizes each
│       ├── bg/              hero and secondary backgrounds
│       ├── hero-a/-b.webp   the two figures in the landing page hero
│       ├── logo.webp/.png   logo
│       ├── icon-*.png       favicons and app icons
│       └── og-cover.jpg     social share card
├── tools/                   regeneration scripts (harmless if uploaded,
│                            nothing links to them)
├── robots.txt
├── sitemap.xml
├── site.webmanifest
└── _headers                 Cloudflare Pages cache and security headers
```

---

## Before it goes live

Two things need a real value. Everything else is ready.

### 1. The domain

Every canonical URL, Open Graph tag and sitemap entry points at the current
home, `https://nightmarero.pages.dev`. These have to be absolute and they have
to resolve: Discord, Slack and Google fetch the share image from that exact
address, so if it points at a domain that is not live yet the preview comes up
blank.

When the real domain is ready, swap it in and rebuild:

```bash
grep -rl "nightmarero.pages.dev" . --exclude-dir=.git | xargs sed -i 's|https://nightmarero.pages.dev|https://YOUR-DOMAIN|g'
python tools/build_classes.py && python tools/build_sitemap.py
```

The `grep` covers `tools/build_classes.py` and `tools/build_sitemap.py` too, so
the `SITE` constant in both scripts moves with everything else.

### 2. The client download link

`download.html` has one primary download button. It currently points at the
control panel as a placeholder. Search the file for the comment that starts
`Twilight: replace the href below` and swap in the real link.

To add mirrors, duplicate that button:

```html
<a class="btn -ghost -lg" href="MIRROR-URL" target="_blank" rel="noopener">
  <svg aria-hidden="true"><use href="#i-download"></use></svg>
  <span>Mirror: Mega</span>
</a>
```

That is all that is strictly outstanding. All 55 classes have artwork, so
nothing on the site falls back to a placeholder.

---

## Deploying to Cloudflare Pages

1. Push this folder to a GitHub repository.
2. In the Cloudflare dashboard: **Workers & Pages → Create → Pages → Connect to Git**.
3. Pick the repo. Leave the build settings empty:
   - Framework preset: **None**
   - Build command: *(blank)*
   - Build output directory: `/`
4. Deploy, then add the custom domain under **Custom domains**.

`_headers` is picked up automatically and sets the cache and security headers.

---

## Regenerating the class pages

The 55 class pages and `classes.html` are generated from two sources:

- `tools/classes.json`, the text of the Class Overviews document
- `tools/data/wiki-classes.json`, the skill tables off the player wiki

```bash
python tools/build_classes.py
python tools/build_sitemap.py
```

`build_classes.py` also prints which classes are still missing artwork and
writes that list to `tools/missing-art.txt`.

### How a skill list gets built

The document is prose. It names every skill and describes it well, but it runs
four different kinds of line together and never says which is which:

```
Void Infusion: Converts all magic damage dealt...      a skill
Ghost: The user's Magic Pierce is reduced to 0         an option of it
Phantasmal Crush: Invokes forbidden magic...           a skill
If Void Infusion: Ghost is active, cooldown halved     a rider on it
```

The wiki carries the part the document does not: which branch a skill sits in,
whether it is physical or magical or supportive, and its level cap. So the
wiki skill tables are treated as the authority on what counts as a skill.
Anything in the document that is not on that list gets folded into the entry
above it, as an option or as a conditional rider. That work lives in
`tools/skills.py`.

On top of that the build works out two more things per class:

- **Mechanics.** Resources, stances and states that are referred to over and
  over but are not skills: Void Spheres, Axe Stance, Extort, Rhythm Stacks.
  Found by head noun, then required to turn up in two different skills or in
  the class introduction. They get listed above the skill grid and marked
  inline in the accent colour with a dotted underline, so they never look like
  a status effect.
- **Dependencies.** A skill whose text names another skill of the same class
  gets a "Works with" link to it. Option labels are excluded on purpose: an
  Axe Stance table listing "Counter Kick: Inflicts Vulnerable" is saying what
  the stance does to that kick, not depending on it.

Skill types are coloured by family. The wiki uses about seventy type labels;
`TYPE_FAMILIES` in `tools/skills.py` folds them onto eight `--sk-*` colours,
which are separate from the status codex so the two never compete on a card.

To refresh the wiki side:

```bash
python tools/fetch_wiki.py
```

That is the only script besides `fetch_sheets.py` that touches the network.
The JSON it writes is committed, so `build_classes.py` runs offline.

If the wiki adds a skill the document has not caught up with, it simply does
not appear. If the document has one the wiki has not listed, it still appears,
under a "Mechanics" heading, without a type or level. Renames between the two
are matched by similarity, which is how "Seismic Tremor" in the document finds
"Seismic Tremors" on the wiki.

### When the class document changes

`tools/extract.py` turns a saved copy of the published Google Doc into
`classes.json`:

```bash
python tools/extract.py "Class Overviews.html" tools/classes.json
```

Then re-run `build_classes.py`.

### Adding class artwork

Every class page looks for these two files and uses whichever exist:

```
assets/img/classes/<slug>-male.webp      up to 760px tall,  full size
assets/img/classes/<slug>-male-sm.webp   up to 420px tall,  card size
assets/img/classes/<slug>-female.webp
assets/img/classes/<slug>-female-sm.webp
```

The slug is the class name lowercased with non-letters turned into hyphens:
`Shadow Chaser` becomes `shadow-chaser`, `Clown/Gypsy` becomes `clown-gypsy`,
`Bard and Dancer` becomes `bard-dancer`.

Drop new PNGs named `<Class Name> Male.png` / `<Class Name> Female.png` into a
folder and run `tools/prepare_art.py` to crop, resize and convert them:

```bash
python tools/prepare_art.py "path/to/new/art"
```

Then re-run `build_classes.py` so the pages pick them up. Nothing else changes.

`prepare_art.py` also writes `tools/art-sizes.json`, the real pixel size of
every file. `build_classes.py` reads it to put `width` and `height` on each
image so the layout does not jump while the art loads. It is generated, so
there is nothing to edit by hand.

### Classes that show two characters

Bard and Dancer, Clown/Gypsy and Minstrel/Wanderer are two jobs sharing one
page, not two genders of one job. They skip the male/female toggle and show
both characters side by side, each with its own name underneath.

The mapping lives in `PAIRED` near the top of `tools/build_classes.py`:

```python
PAIRED = {
    "Bard and Dancer": ("Bard", "Dancer"),      # male art, female art
    "Clown/Gypsy": ("Clown", "Gypsy"),
    "Minstrel/Wanderer": ("Minstrel", "Wanderer"),
}
```

The artwork still uses the `-male` and `-female` filenames, since that is
which slot each job occupies. On the card these get the `-pair` class, which
lays them out as a band rather than one full height figure.

---

## Languages

Six languages: English, Portuguese, French, Italian, German, Japanese.

English is written directly into the HTML, so crawlers and anyone with
JavaScript disabled always get real content. The other five live in
`assets/i18n/*.js` and swap the text in at runtime. The choice is remembered in
`localStorage` and the browser language is used on a first visit.

To change a string, find its key:

```html
<h3 data-i18n="feat.t4">Bosses you summon</h3>
```

Edit the English in the HTML, then edit `'feat.t4'` in each locale file. A key
that is missing from a locale falls back to English rather than breaking.

Strings may contain inline `<strong>` and `<b class="kw kw-burn">` markup, and
it survives a language change. Keep the tags balanced: the value is written
straight into the element.

Skill names and skill descriptions on the class pages stay in English on
purpose, because that is how they appear in game.

### Check the locale files after editing them

Each locale file is one JavaScript object literal, so a missing comma or a bare
apostrophe inside a value (`l'arbre`) makes the browser throw on the whole file.
Nothing looks broken: the page just stays in English while the switcher still
shows the flag you picked. Use a typographic apostrophe (`l’arbre`) in French
and Italian, and run the checker before committing:

```bash
python tools/check_i18n.py
```

It parses every locale the way a browser would and reports malformed lines,
duplicate keys, and keys the pages ask for that a locale does not have. It
exits non zero when something is wrong.

---

## The item database

`database.html` searches every weapon, armour piece and card on the server.
It loads `assets/data/items.json` once and filters in memory, painting results
in chunks of 60 so a 1200 entry list never stalls the page.

The data comes from Twilight's two published reference sheets. Refresh it in
two steps:

```bash
python tools/fetch_sheets.py     # re-download tools/data/*.csv from Google
python tools/build_database.py   # rebuild assets/data/items.json
```

`fetch_sheets.py` is the only script that needs the network. The CSVs are
committed, so anyone can rebuild the JSON offline.

Three things to know about the source data:

- **Shadow gear is laid out as sets, not as a table.** A tier heading, a set
  name on its own row, then its Armor, Gloves, Shoes and Pendant, then one or
  two set bonus rows that apply to all four. `parse_shadow()` reads that shape
  and gives each piece its own slot (`shadow-armor` and so on), because shadow
  gear equips in a second window and is worn alongside ordinary gear rather
  than instead of it. The tail of the tab repeats an unfinished set over and
  over, so a set name already seen in the same tier is skipped.
- **Shadow Enchants is still an empty tab**, so none of it is in the database
  yet. It will appear once Twilight fills it in and the two commands above are
  re-run.
- **The sheets mark champion drops with a green cell fill.** Colour does not
  survive the CSV export, so that distinction is not in the database. If it
  matters later, the champion names would need their own column.

The drop rate rules on `database.html` are not in any sheet. They come from
Twilight directly and are written into the page: trash loot at 100%, gear off
ordinary mobs at 1 to 5%, gear off Champions and MVPs at 10 to 50%, cards at
1% and 5%, and no level based penalty.

Category names differ slightly between the two gear docs (`GATLINGS` versus
`GATLING GUNS`). `CATEGORY_ALIASES` in `build_database.py` folds those
together so the filter does not list near-duplicates.

## MVP altars

`mvps.html` lists every summonable boss: the map its altar is on, the two item
lists that open it, its drops, and the card it leaves behind.

```bash
python tools/fetch_mvps.py       # the CSV tabs
python tools/fetch_mvp_art.py    # the pictures, with their anchor cells
python tools/build_mvps.py
```

The source sheet is a two column visual grid rather than a table, so
`build_mvps.py` reads it as a grid: it finds cells starting with `MVP:`, works
out which half of the page they are on, and takes everything under them until
the next boss on that side.

Three things about the source are worth knowing:

- **The pictures are floating images**, so the CSV export cannot see them.
  `fetch_mvp_art.py` downloads the workbook as xlsx instead, where every
  drawing carries the row and column it is anchored to, and writes those
  coordinates to `tools/data/mvp-art.json`. That is how each minimap and each
  drop table screenshot ends up filed under the right boss.
- **The drop tables only exist as screenshots.** They are transcribed by hand
  into `tools/data/mvp-drops.json` so the page can show real, searchable text.
  The screenshot stays in the card as well, so the transcription can be
  checked against it. 31 of the 43 bosses have one; the rest are blank in the
  sheet.
- **Champion items are marked by cell colour**, which the CSV export loses.
  The build recognises them by name instead, against the champion drop tab,
  and marks them gold. `ITEM_ALIASES` in `build_mvps.py` covers the handful of
  names that are spelled differently on the two tabs.

Two things live in the item database rather than only here, so one search
covers them: MVP cards under an `MVP Card` category, and relic gear under
`Relic Gear`.

Relic gear only exists in the sheet as tooltip screenshots. Those are
transcribed into `tools/data/relic-gear.json`, and the screenshots are
deliberately not shipped: the page renders the transcription instead, and
`fetch_mvp_art.py` skips that tab. `build_database.py` reads the same file, so
adding an entry there puts it on both the MVP page and in the database.

## Quests

`quests.html` collects the quests that have no NPC pointing at them. Everything
sits behind a reveal button, and the choice is remembered in `localStorage`,
because a fair number of players would rather work these out themselves.

```bash
python tools/build_quests.py
```

Each quest is one tab in the sheet: a column of steps with screenshots dropped
between them. Screenshots are attached to the step above them, using the same
anchor rows as the MVP page. The jump buttons at the top are generated from
`QUESTS`, so adding a quest there adds its button too.

The Endless Desert route table is a special case. The sheet marks the layer of
every moc_fild map with a cell colour, and the CSV export drops colour, so the
column of "Layer 1" to "Layer 5" labels next to the table is a legend rather
than a label for the row it lines up with. `DESERT_LAYERS` in
`build_quests.py` holds the map to layer mapping read out of the xlsx fills,
and `desert_table()` renders the legend properly and colours each map by its
own layer.

The sheet is written in Portuguese. `tools/data/quest-text.json` holds the
English for each line, keyed by the original, and anything without a
translation falls through unchanged, so a new line shows up untranslated
rather than disappearing. `TABLES` in `build_quests.py` marks the two tabs
that hold a reference table instead of a step list.

The potion recipes come from a player made wiki rather than from Twilight, and
are labelled as such on the page along with the date they were last touched.

## The new player guide

`guide.html` is the page for people who have never played here. It carries the
levelling route, one card per level band.

```bash
python tools/build_database.py    # the guide reads assets/data/items.json
python tools/build_guide.py
```

The route lives in `LEVELS` in `tools/build_guide.py`: level band, place, what
to collect, which monsters the stop is about, which altars sit on those maps,
and who gets the most out of it. Everything else is looked up rather than
typed:

- **cards** are matched on the monster name, because a card is named after the
  monster that drops it
- **gear** is matched against its own drop list
- **altars** link straight to the boss on `mvps.html`

So the guide cannot drift from the database. Rebuild after a sheet change and
every card and stat on the page is current. A typo in a monster name quietly
drops its card, so the build prints any stop whose monsters matched nothing.

Monster lists only claim what the sheets tie to a map: a monster named by an
altar, by the champion tab, or by the route itself. They are not full spawn
lists, and the page says so.

`GUIDES` is the older free form section, kept for prose guides. An entry is a
title, a credit, a blurb, an intro and a list of blocks, where a block is a
numbered route (`steps`), a fork with a card per branch (`split`), or a plain
list (`notes`). Credit the author in the `credit` field; it renders under the
title.

---

## The class personality test

`quiz.html` asks nine scenarios set in Midgard, scores six traits, and uses
the top two to pick one of fifteen archetypes. Every unordered pair of traits
has exactly one archetype, so there is no combination that falls through.

Everything lives in `assets/js/quiz.js`:

- `TRAITS` the six axes
- `QUESTIONS` the scenarios and what each answer scores
- `ARCHETYPES` fifteen entries keyed by `pair`, each naming a class and a
  runner up
- `OLD_CLASSES` the class the player used to main, which only changes the
  wording of the result, never the maths

The result card reads `assets/data/classes-brief.json`, generated by
`build_classes.py` alongside the class pages. "Save as image" composes a
1200x630 PNG on a canvas with the logo, the archetype and the class art.

Questions and archetypes are English only, the same call made for skill names
elsewhere. The page chrome around them is translated.

## The launch countdown

The hero counts down to launch and then swaps itself for a "servers are live"
badge. The moment is defined once, at the top of the countdown section in
`assets/js/main.js`:

```js
var LAUNCH = Date.UTC(2026, 7, 7, 23, 0, 0);  // 7 Aug 2026, 20:00 Brasilia
var LAUNCH_OFFSET_MIN = -180;                 // Brasilia, minutes from UTC
```

Months are zero based, so `7` is August, and the hour is **UTC**, not local.
If the date moves, change those two lines and then update the text in three
places: `cd.when` and `hero.badge` in each locale file plus the English in
`index.html`, `faq.a8`, and the `datePublished` field in the JSON-LD block.

Visitors outside Brazil also get the launch time in their own zone,
formatted by `Intl.DateTimeFormat` and re-rendered whenever the language
changes. That line stays hidden for anyone already on UTC-3.

## The status codex

Combat runs on status effects, so each family has a colour that is used
everywhere: inline in skill text, on the chips above each skill list, and on
the reference cards at the bottom of `classes.html` (anchor `#codex`).

The colours live in one place, `:root` in `style.css`, as `--kw-bleed`,
`--kw-burn` and so on, with darker values under `html[data-theme="light"]`.

The terms themselves are defined in the `STATUS` list in
`tools/status_codex.py`. Matching is case sensitive, so an ordinary lowercase
"cold" or "slow" in a sentence is left alone. To add a status, add a row there
with a new key, add `--kw-<key>` to both theme blocks in `style.css`, and
re-run the build.

Each class page shows chips only for the statuses that class actually
mentions, so a Crusader page shows Bleeding, Blind and Vulnerable and nothing
else.

## Naming

The site deliberately never uses the name of the game this server is based on,
or its publisher. Search visibility is carried by "private RO server", "custom
RO server", "PvE MMORPG server" and similar phrasing instead. Worth keeping in
mind when writing new copy.

The only exception is the control panel domain in the account and download
links, which is what it is.

---

## Design notes

- Theme: red and black, eclipse and broken glass. Light mode is a bone-white
  variant of the same palette.
- Type: Outfit for headings, Inter for body, JetBrains Mono for labels, all
  from Google Fonts. Noto Sans JP loads only when Japanese is selected.
- All colours, spacing and type sizes are CSS custom properties at the top of
  `style.css`. Change them there and the whole site follows.
- Motion respects `prefers-reduced-motion`.

## Licence

Site code is free to reuse for the server. Character art, backgrounds and the
logo belong to their creators.
