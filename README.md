# Nightmare RO website

Static site for the Nightmare RO server. No build step, no framework, no
dependencies. Plain HTML, one stylesheet, two small scripts. Drop it on any
static host and it works.

---

## Contents

```
.
├── index.html               landing page
├── guide.html               new player guide, route and where to hunt
├── mechanics.html           how combat works: stats, elements, formulas
├── endgame.html             champions, bosses, nightmare and challenge
├── classes.html             class hub, filter + search over all 55
├── quiz.html                class personality test
├── database.html            items and cards
├── mvps.html                boss altars, summon lists and drops
├── quests.html              spoiler quest walkthroughs
├── download.html            client download and install help
├── loading-screens.html     the class loading screens, browsable and free
├── classes/                 55 generated class pages
├── assets/
│   ├── css/style.css        the whole design system
│   ├── js/main.js           theme, menus, site search, filters
│   ├── js/i18n.js           language switcher
│   ├── i18n/                pt, fr, it, de, ja  (English lives in the HTML)
│   ├── data/                items.json and search.json, both generated
│   └── img/
│       ├── classes/         character art, .webp, two sizes each
│       ├── loadings/        loading screens, full size + thumbs/
│       ├── mvp/             sheet screenshots for the boss and quest pages
│       ├── relic/           per relic piece: its minimap and its cost strip
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

`download.html` has two download buttons in the hero. The primary one points
at the release build on MediaFire, the ghost one at the older Google Drive
copy, kept as a mirror. Both are plain hrefs in the markup, above a comment
that says so.

To add another mirror, duplicate the ghost button:

```html
<a class="btn -ghost -lg" href="MIRROR-URL" target="_blank" rel="noopener">
  <svg aria-hidden="true"><use href="#i-download"></use></svg>
  <span>Mirror on Mega</span>
</a>
```

A label that names the host wants a key in the five locale files, the way
`dl.mirror` has one. A label that is just a host name does not need one.

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

### Nobody reads a cached copy of this site

Run this before committing, whenever anything under `assets/` changed:

```bash
python tools/stamp_build.py          # stamp every page with the new build
python tools/stamp_build.py --check  # exit 1 if a page is out of date
```

Two halves, and both are needed.

`_headers` sends `Cache-Control: no-cache, must-revalidate` on **everything**.
That does not mean "do not store", it means "store it, but never serve it
without asking us first", which is what a Ctrl+Shift+R does by hand. An
unchanged file answers 304 with no body, so the cost is one conditional request
per file rather than a download. There are no exceptions, artwork included:
Pages merges every matching rule instead of letting the most specific one win,
so a second block naming `Cache-Control` would put two contradictory values in
one header and let the browser choose.

That only governs copies fetched from now on. A reader who was here before it
landed still holds files under the old rules — the item database was allowed to
sit for a day — and no header can reach into a cache that is not asking.
`stamp_build.py` can: it hashes everything under `assets/css`, `js`, `i18n`,
`data` and `quiz` into one short build id, writes it onto every page as
`<html data-build>`, and rewrites each stylesheet, script and preload to
`?v=<id>`. An address the old cache has never seen cannot be answered from it.

The scripts fetch their own JSON through `window.NM_FRESH()`, defined in
`i18n.js` (the first script on every page) off that same attribute, so
`items.json`, `search.json`, the locale files and the quiz packs are on the
stamp too. `database.html` preloads `items.json`, and that preload is stamped
as well — a preload asking for a different address than the script does would
download 1.2 MB twice.

The id is a hash, not a clock, so a rebuild that changes nothing changes no
URLs.

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
in chunks of 60 so a long list never stalls the page.

**The page opens with nothing listed.** Painting all 3638 entries on arrival
gave the results column a scrollbar of its own and made the filters below the
fold unreachable: the wheel scrolled the results instead of the page. So the
grid stays empty until something is asked for — a word in any of the three
boxes, a select, a level, or one of the kind chips — and *Show everything* is a
button for when browsing the lot is the point. `?drops=` and `?item=` both fill
a filter in, so a link from the site search still lands on results.

Three sources feed it, in order of how much they are trusted. The game client
first, because it is the game (see below). Then Twilight's two published
reference sheets, which are the only thing that says where an item drops. Then
`relic-gear.json` and `tooltip-items.json`, both typed out of screenshots by
hand.

Nothing is listed unless one of those four says the item is on **this** server.
That rule cost the database 733 entries once and is the reason the section
below exists.

```bash
python tools/fetch_sheets.py        # re-download tools/data/*.csv from Google
python tools/fetch_client_items.py  # re-read the installed game client
python tools/build_database.py      # rebuild assets/data/items.json
```

`fetch_sheets.py` is the only script that needs the network and
`fetch_client_items.py` the only one that needs the game installed. Both commit
what they produce, so anyone can rebuild the JSON with neither.

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

### The game client outranks every sheet

The reference sheets are typed by hand and lag behind patches. The client is
not: `SystemEN/LuaFiles514/itemInfo.lua` inside the game folder is the exact
text the item description window shows in game, and the patcher rewrites it on
every patch. So that file has the last word, and a screenshot of a tooltip is
only a photograph of it.

```bash
python tools/fetch_client_items.py "E:/NightmareRO (Release)"
python tools/build_database.py
```

#### but it is not a list of the items this server has

That file is llchrisll's ROenglishRE, a community translation of the **whole**
official item database, and it ships the same 19,315 entries to every server
that installs it. Siege White Potion, Enriched White PotionZ, the 11th
Anniversary Coin, three flavours of Light White Potion: all present in the file,
none of them in this game. Reading it as an item list put 733 items that do not
exist on the site, and a player noticed by screenshotting the real White Potion
next to them.

Twilight edits that file in place for his own content, so the only entries
`fetch_client_items.py` will publish are the ones he changed. Every entry is
diffed against the exact release the client was built from:

| origin | meaning | count |
| --- | --- | --- |
| `custom` | an id the translation never had | 1536 |
| `edited` | name, description or slot count rewritten | 2173 |
| `vanilla` | byte for byte the translation, so no evidence | 17142 |

The base comes from the `-- Last updated: 20210313` stamp in the client file's
own header, pinned by commit in `BASE_PINS`, downloaded once into
`tools/cache/` (gitignored, 15 MB). **If a patch ever moves the client to a
release with no pin, the script stops instead of guessing**, because guessing
is what put the 733 there. Add the new commit from
[the upstream history](https://github.com/llchrisll/ROenglishRE/commits/master)
and re-run.

The gate proves itself in both directions: all 131 items transcribed off the
guild's screenshots come back `custom` or `edited`, and all 11 items the player
reported come back `vanilla`.

An untouched entry is **not** a claim that the item is missing. Jellopy is
untouched and obviously real. It only means nothing readable says it is here, so
it stays out until a sheet, a screenshot or an answer in the Discord says
otherwise — an item named in `who-drops.json` is imported however its tooltip
reads, which is how Sunglasses stays in.

#### what it does with what is left

`fetch_client_items.py` writes `tools/data/client-items.json`. It needs the
client installed, which is why its output is committed: everyone else rebuilds
from the JSON. It does two things:

- **Corrects what the site already lists.** 1449 of them. The stats and the
  effects come from the client, and the one thing a tooltip never says is kept
  from the sheet: where the item drops. Card slot counts, affixes, categories
  and `Found on <map>` lines survive too. 207 rows are left alone because their
  client entry is untouched translation text, which would be a downgrade.
- **Adds what is in the game and on no sheet at all.** 2156 entries, including
  whole families the sheets never mention. They carry no location, so they land
  under *Location unknown* in the source filter.

Three things stop it from doing damage:

- **A display name is not unique in the client.** Mysteltainn is a sword and a
  card, RO ships three different Falchions, and the renewal version of a weapon
  keeps the old one's name. An entry is only used when its `Type:` line agrees
  with the category the site has the item under *and* every remaining candidate
  reads the same. The 14 that stay ambiguous are printed and left with the
  sheet.
- **A tooltip that parses down to nothing is a bug in the reader, not an item
  without effects.** `build_database.py` refuses to replace a filled effect
  list with an empty one and names whatever it skipped.

The client's own markup has to come off on the way in. `^FF0000` colour codes go
(the site colours the same words itself from the status codex), including the
three cards written `^00000` with a digit missing, which used to print as
`Water^00000` on the page. `<NAVI>Mayomayo<INFO>malangdo,213,167,...</INFO>
</NAVI>` is a link the client turns into a clickable walk-there name, so it
becomes `Mayomayo (malangdo 213,167)`. `<None>` becomes `None`. A line that is
still Korean is dropped rather than printed at an English reader, and the file
is read as `cp949`, which is the codepage the client itself uses.

The reader has to tell an effect from flavour text, since the client separates
its blocks with a rule of underscores and labels almost nothing. Flavour is the
block that hands out no numbers, does not open like an effect (`Enables`,
`Add`, `If`, ...) and is written as finished sentences; everything doubtful
stays an effect, because an extra line on a card is a blemish and a lost effect
is a lie. Headings are folded into the lines under them, so `For each Refine:`
and `Combo: Novice Hat + Breastplate` never end up as bullets on their own.

`tools/data/tooltip-items.json` is still there and still read first, before the
client overwrites it. It is the transcription of the screenshots the guild took,
it is what named the 78 items nobody had listed, and it is what the build falls
back on for anything the client reader cannot resolve. Every name in it has been
checked against the client. Two were wrong and were corrected there: the game
really does call one bow `True Faith Bow Bow`, and `Nightfall's Flame of the
Apostle` was `Nightfall's Flame` wearing a random option suffix in the title
bar.


### Who drops it

This is the question players actually ask, and the game gives them nothing to
ask it with: there is no working `@whodrops`, the client never says where
anything comes from, the wiki has no monster pages and the control panel has no
item database. So the site answers it three ways.

- **From the sheets.** The gear docs have a *Drops From* column, and that is
  where 639 of the answers come from. `database.html` now has a **Dropped by**
  filter over that column, and `?drops=Poporing` opens the page already
  filtered, which is what the site search links to.
- **Backwards, out of the same column.** `drops_rows()` in `build_search.py`
  turns every distinct name in it into a search row, so typing a monster into
  the header search offers *Poporing, 2 drops* and one click lists them. A card
  is named after the monster that drops it, so the filter matches a card by its
  own name too.
- **From the Discord, for everything else.** No sheet covers loot and
  materials. `tools/data/who-drops.json` holds what people answered in
  `#item-finder`, each line credited to whoever said it, and those items are
  labelled *Answered on Discord* in the source filter rather than being passed
  off as documented. `_wanted` in that file is the list nobody has answered
  yet, which is what to ask Twilight for.

### Loot and materials

The database used to be gear and cards only, and a player said so in
`#item-finder`: *"it doesn't work for etc/use items."* Everything the owner
wrote an entry for is in now, under a third filter chip: loot, relic and quest
materials, herbs, crafting, forging and refining ingredients, catalysts,
trophies, valuables and artifacts, and the systems that are his own work and are
documented nowhere else — enchants and enchant scrolls, containers and coffers,
runes, homunculus embryos, stat boosters, salvagers, modifications, maintenance
kits and travel items. Costumes come in as gear, in a costume slot of their own.

The categories are the `Type:` line he writes, folded only where he spells the
same thing two ways, so the filter reads in the words the game and the Discord
already use.

Loot has no stats, so for those entries the description *is* the information
and the reader's flavour text becomes the entry body. An item somebody asked
about in `who-drops.json` is imported even when its tooltip is plain official
text with none of this server's vocabulary in it, which is how Sunglasses got
in.

### What a quest needs, and who drops that

`tools/data/recipes.json` holds the crafting ladders off the wiki's Potion
page. Two builders read it, which is the point of it being a file rather than a
constant:

- `build_quests.py` prints the tables on `quests.html#potions`, and every
  ingredient is now a link to that item in the database, which is where the
  answer to *and who drops that* lives.
- `build_database.py` uses it twice. A material a recipe asks for is **proof
  the item is in the game**, so it comes in past the provenance gate however
  its client entry reads -- without that, Scell, Nine Tail, Detrimindexta,
  Karvodailnirol and Golden Hair all vanished from the site, because they are
  plain official items the owner never had a reason to rewrite. And each
  material's own entry gains a `Used to craft: White Potion` line, so searching
  a potion by effect lists its whole shopping list.

Of the 27 materials the potion ladder asks for, 16 have a source and 11 do not.
The wiki names 12 of them, the Discord answered 4 more. The eleven still open
-- Golden Hair, Grave Dust, Blazing Stone, Broken Urn, Detrimindexta, Ancient
Tooth, Cultish Mask, Karvodailnirol, Scell, Nine Tail and the loot Poison Spore
-- are the list to take to Twilight.

Two more passes fill drops in from the client's own words, and both only ever
fill a blank, so a sheet row or an answer in the Discord always wins:

- **A chest that lists what it gives** is telling you where those items come
  from. That is 52 pieces of gear, the whole Nightmare and Abyss weapon and
  armour families, which are bought out of a chest and were sitting under
  *Location unknown* while the answer was written on the chest.
- **A description that names the monster it came off.** "A tail cut from a
  Green Pitaya" is an answer; "an idol carved in a shape reminiscent of a
  Chimera" is not, so `apply_flavour()` reads the shape of the sentence -- a
  taken-from verb, then the monster -- and a deny list throws out the
  resemblances. 20 materials, and it will not guess beyond them.

Both are labelled *The item's own description* in the source filter rather than
being passed off as a documented drop.

A card is named after its monster and that monster often drops loot of the same
name. The card Poison Spore and the mushroom Poison Spore are two items, and
both are listed; the recipe marks the mushroom.

### When the sheet and the game spell it differently

Every sheet row was checked against the client's display names. 21 of them are
spelled another way in game — `Peco Peco` is `Pecopeco`, `Worm Tail` is
`Wormtail`, `Iron Knuckles` is `Iron Knuckle`, `Desert Wofl` is a typo for
`Desert Wolf`. The game's spelling wins, in `GAME_SPELLING` in
`build_database.py` rather than in the CSVs, which are refetched: it is what the
player reads in the item window and types into the search, and ten of those
names were putting the same item on the site twice, once under each spelling.

Only unambiguous cases are listed. `Glacial Shield` has no client entry at all
and is left as the sheet has it rather than folded into the `Gaia Shield` it
merely resembles. Where the game itself carries the typo it is kept: the server
really does call one bow `True Faith Bow Bow`.

## The gear reference tabs

Two tabs of the gear sheet are reference tables rather than item lists, so
they do not belong in `items.json`. They are read straight off the CSV by
`tools/build_mechanics.py` and rendered as cards:

| Tab | Reader | Where it lands |
| --- | --- | --- |
| Random Option Tables | `random_options()` | `mechanics.html#options` |
| Shadow Enchants | `shadow_enchants()` | `endgame.html#shadow` |

Both tabs are laid out for a person reading a spreadsheet: blocks of slot
columns side by side with blank rows between them. The readers put that back
into a list, so a change to the sheet reaches the page with a re-fetch and a
rebuild and nothing else.

Two details worth knowing. The random option sheet leaves footnotes inside
option cells ("MVP Armors drop at one Level Tier above their Requirements"),
and the reader lifts those out as the block's note. And the enchant tab has
four typos that would read as real values, so `ENCHANT_TYPOS` fixes them at
read time rather than in the CSV, where a re-fetch would quietly undo it.

---

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
  drop table screenshot ends up filed under the right boss. It reads the tab
  names out of the workbook and matches `BOOKS` against them; the list used to
  be positional, which silently filed every picture after a newly added tab
  under the wrong quest. A tab that is not in `BOOKS` is named on stdout and
  skipped, so a new one announces itself. File names are the first ten
  characters of the picture's own sha1, because Google renumbers `xl/media`
  on every export and a name taken from it renames half the folder for
  nothing.
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
transcribed into `tools/data/relic-gear.json`, and the tooltips themselves are
deliberately not shipped: the page renders the transcription instead, and
`fetch_mvp_art.py` skips that tab. `build_database.py` reads the same file, so
adding an entry there puts it on both the MVP page and in the database.

## Where relic gear is found

Every piece sits on the tab under the name of the map it is found on, next to
a minimap and a strip of item icons showing what it costs. Those three things
are the answer to "where do I get this", so they are on the page, and they
come from three different places:

```bash
python tools/fetch_relic_art.py  # the minimap and the cost strip per piece
python tools/build_mvps.py
```

- **The map names are printed labels.** They are not cell text and not
  drawing text, so the CSV export is empty, the xlsx export has nothing, and
  even Google's own PDF export of that tab comes out with no text in it at
  all. They live in `relic-gear.json` under `map`, typed in by hand off the
  printed sheet, and every one was checked against the client's minimap
  textures before being written down. `prt_maze02` for Loki's Nail was read
  off the texture alone, because its label falls on a page break in the print
  and does not survive it.
- **The pictures are anchored, not named.** `cell` in `relic-gear.json` holds
  the `row,col` the minimap and the cost strip are pinned to, and
  `fetch_relic_art.py` matches on that, so each piece gets
  `assets/img/relic/<slug>-map.webp` and `<slug>-cost.webp` plus its size in
  `tools/data/relic-art.json`. Where the sheet drew two pieces against one
  screenshot, both slugs cite the same anchor and both get a copy. A piece
  whose anchors are missing is reported and skipped rather than guessed at.
- **The materials are not named anywhere.** The sheet shows an icon and a
  number and nothing else, so the cost strip is shown as the sheet drew it and
  the page says as much. Do not write material names into the JSON unless
  something on the server says what they are.

`build_database.py` also puts `Found on <map>` on each relic entry, so a
search for a map name in the database turns up the pieces that come from it.

### The database used to call that map a "drop"

`database.html` reused its ordinary "Drops from" field for relic gear too,
with the map code as the value. A player screenshotted the modal for **Black
Forest Boots** -- "DROPS FROM hu_fild02" -- and went looking for a monster on
that field that does not exist: Relic Gear is never a monster drop, it is
traded from the Roaming Archaeologist NPC for a Relic, and the map is where
her altar sits.

`database.js` now special-cases anything with `cat === 'Relic Gear'` (`117`
items, not just the `20` transcribed into `relic-gear.json`) with its own
"How to get it" heading, in both the modal and the Discord share text:

- The `20` with a transcribed map (`source === 'relic'`) read *"Quest reward
  from the Roaming Archaeologist, found on hu_fild02"*, linked to
  **`endgame.html#archaeologist`**, which explains who she is, and to a **"See
  the map"** link that jumps straight to that piece's own card on
  `mvps.html#r-<slug>` -- the minimap and cost strip, the actual answer to
  "where do I get this". `parse_relics()` writes that slug onto the item as
  `relicSlug`, computed with the same `slugify()` `build_mvps.py` uses for the
  card's `id="r-<slug>"`, so the two are guaranteed to agree without hand
  matching two lists.
- The other `97`, read out of the client with no location attached, read
  *"Quest reward from the Roaming Archaeologist. The location has not been
  written down yet"* -- the mechanism is still true even where the specific
  map is not, so it is still said, and nothing is invented for the part that
  is not known.

The Discord share text spells out full origin URLs rather than a relative
`href`, since Discord cannot follow those, and stays English no matter the
page's language, the same as every other line `shareText()` builds.

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

Two tabs do not behave, and both are handled in `build_quests.py`:

- **Abbey Sealed Chambers is screenshots and nothing else**, so its CSV comes
  back empty. `WRITTEN_STEPS` holds the five steps read off those screenshots,
  each with the row it is anchored to, which is how the pictures still land on
  the right step. If the tab ever gets real text, delete the entry and it goes
  back to being read like every other quest.
- **The Endless Desert walking directions were deleted from the sheet** on 14
  Aug 2026, leaving the Avatars and their maps behind. `DESERT_ROUTE` keeps
  those four lines and fills them back in, because the route still matches the
  maps that are still there. Delete it if the sheet ever says otherwise.

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
They live in `POTIONS` in `build_quests.py`: a label, the rows, and the list of
plants and monsters each material comes from, which is the part players
actually ask about. Re-read
[the wiki page](https://wiki.nightmareofragnarok.com/wiki/Potion) when it
changes; it is edited far more often than the sheets are. `POTION_RULES` holds
what is not an amount, including the one thing the wiki does not say: the
ladder is per character, which Twilight confirmed in Discord on 8 Aug 2026.

## The navigation

Four entries open onto more than one page: The game (the server spec on the
home page, the mechanics page and the end game page), New players (the
levelling route and the class test), Database (items, MVPs, quests) and
Download (the client, the loading screens). Both the desktop dropdowns and the
drawer groups come from `GAME_PAGES`, `NEW_PAGES`, `DB_PAGES` and `DL_PAGES` in
`tools/build_classes.py`.

The generated pages take their header from `header()`. `index.html`,
`database.html`, `quiz.html`, `download.html` and `loading-screens.html` are
hand written and carry their own copy, so after any nav change:

```bash
python tools/sync_nav.py       # paste the generated nav into the four copies
python tools/build_classes.py  # then rebuild everything else
```

`sync_nav.py` is safe to re-run; it reports which pages it actually changed.

---

## The loading screens

`loading-screens.html` shows every finished loading screen and hands out the
file. The artwork is from Ragnarok Online 3, edited in Photoshop by Balziere,
with the class text by Twilight, and the page says so in three places, so keep
that credit wherever the set is mentioned.

Two copies of each screen live in `assets/img/loadings/`: the original
1280 × 720 JPG, which is what the download link points at, and a 720px wide
thumbnail in `thumbs/` for the grid. Nothing on the page loads a full size
image until somebody opens the viewer.

The grid inside `<div class="ls-grid" id="lsGrid">` is generated. Adding the
next class is one line in `SCREENS` in `tools/build_loadings.py` — the slug
(which is also the file name and the class page it links to), the name printed
on the card, `trans` or `third`, and the file it comes from in the source
folder — then:

```bash
python tools/build_loadings.py "C:/path/to/Loading Screens"
```

That imports the originals, rewrites the thumbnails, rebuilds the cards and
updates the count next to the filter chips. Without the folder argument it
rebuilds thumbnails and markup from the files already in the repo. It needs
Pillow (`pip install Pillow`), same as `prepare_art.py`.

One thing it cannot fix for you: the FAQ answer on the page counts the finished
classes out loud ("seven transcendent classes and their seven third class
counterparts"). That sentence is `ls.a1`, in the page and in all five locale
files, and the script prints a reminder about it every run.

The viewer, the tier filters, the thumbnail rail and the cursor glow are
section 7b of `assets/js/main.js`. The grid is a set of plain links to the full
JPGs, so with the script blocked the page still works, it just opens the image
directly. The open screen is mirrored into the URL hash, so
`loading-screens.html#warlock` opens on the Warlock.

---

## The site search

A menu can only be six words wide, and the site is now a couple of thousand
things. So there is one box that searches all of them, opened by the button in
the header, by pressing <kbd>/</kbd>, or by <kbd>Ctrl</kbd> + <kbd>K</kbd>.

`tools/build_search.py` writes `assets/data/search.json`: one row per page,
section, class, skill, item, card, boss, quest, status family, field and
dungeon. Rows are arrays, not objects, because there are thousands of them:

```
[title, subtitle, url, group, extra search words]
```

It reads what the other builders already produced, including two of the built
pages, so **it runs last**:

```bash
python tools/build_mvps.py
python tools/build_quests.py
python tools/build_search.py
```

The panel itself is section 3d of `assets/js/main.js` and is built at runtime,
so no page carries markup for it. The file is fetched the first time somebody
reaches for the search and warmed as soon as a pointer touches the button.

Two things worth knowing before changing the ranking. Groups are weighted, so
a page outranks an item: "fire" is the name of a hundred cards and of one
section that explains what fire does. And each group is capped at seven hits,
so nine hundred cards cannot bury the one page. Both live at the top of that
section as `WEIGHT` and `PER_GROUP`.

Item and skill names are English everywhere on the site, but the search strips
accents before matching and the page rows carry Portuguese words as well, so
"refino", "poção" and "onde upar" all land somewhere sensible. Those words are
in `PAGES` in the build script.

---

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

The page opens with two shorter sections that sit above the route.

`WHERE` is the quick reference: every level band and the fields and dungeons
that fit it. Dungeon levels are the ones printed on the levelled world map the
server owner posted, because the levels baked into the client are wrong and
there is no patcher to correct them. Field levels are the tile numbers around
the town named. Each entry is `(place, level, "field" or "dungeon")`, and the
kind only decides which colour the left edge gets.

Above that, the page tells players to press `Ctrl` and `'` for the world map
and then `Tab` for the level numbers, and repeats the rule that decides where
they should be standing: at or a little above their own level, and never 15
levels apart in either direction, because 15 above the monster pays nothing
and 15 below costs 90%.

`JOBS` is where each job change starts, from the server owner's own list.
Third job changes are not in it.

`GUIDES` is the older free form section, kept for prose guides. An entry is a
title, a credit, a blurb, an intro and a list of blocks, where a block is a
numbered route (`steps`), a fork with a card per branch (`split`), or a plain
list (`notes`). Credit the author in the `credit` field; it renders under the
title.

---

## How the server works, and the end game

`mechanics.html` and `endgame.html` both come out of one script:

```bash
python tools/build_mechanics.py
```

`mechanics.html` is the rules of combat: the experience curve and what a level
gap costs, what every stat gives at each tenth and twenty fifth point, the
crit, cast and attack speed formulas, the element table, the status effects,
the potion and refine ladders, warps and commands.

`endgame.html` is what waits after the route: champions, summoned bosses, the
Roaming Archaeologist, guilds and raids, the Nightmare dungeons with Depth,
Resistance and Agony, the Challenge dungeons, and the three reputation lines.

Everything on both pages comes from the Server Overview document the server
owner keeps, plus the stat breakpoint and element table posts in the Discord
server information channel. When that document changes, edit the data lists at
the top of the script rather than the markup: `STATS`, `ELEMENT_TABLE`,
`NOVICE`, `COMMANDS`, `REFINE_WEAPON`, `REFINE_ARMOUR`, `ORES`, `EXP_GAP`.

The element table is `ELEMENT_TABLE[attacker][defender] = (direction, values)`,
where direction is `up` for more damage dealt and `down` for less, and the four
values are the four levels of the defender's element. Every element also has
its own colour, `--el-<name>` in both theme blocks in `style.css`, so a row or
a column can be found without reading it.

The status effect cards reuse the codex markup and the `codex.d1` to `codex.d9`
keys from the class index, so those descriptions are already translated.

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

## The server is open

The server opened on Friday, 7 August 2026, so the site says so outright.
There is no countdown and no pre-launch wording left anywhere: the hero badge
carries a green pulsing dot and the words behind `hero.badgeLive`, and the
line under the lede, `hero.live`, says since when.

The green is one token, `--live`, declared in `:root` in `style.css` with a
darker value under `html[data-theme="light"]`. Only `.badge.-live .dot` uses
it, so making another element read as online is a matter of adding the class.

The opening date is written in four places: `hero.live` and `faq.a8` in each
locale file, the English in `index.html`, and the FAQ answer in the JSON-LD
block at the top of that page.

## The status codex

Combat runs on status effects, so each family has a colour that is used
everywhere: inline in skill text, on the chips above each skill list, and on
the reference cards at the bottom of `classes.html` (anchor `#codex`).

The colours live in one place, `:root` in `style.css`, as `--kw-bleed`,
`--kw-burn` and so on, with darker values under `html[data-theme="light"]`.

The terms themselves are defined in the `STATUS` list in
`tools/status_codex.py`. Matching is case sensitive, so an ordinary lowercase
"cold" or "slow" in a sentence is left alone. To add a status, add a row there
with a new key, add `--kw-<key>` and a `.kw-<key>` rule to both theme blocks
in `style.css`, add a `codex.<key>` line to all five locales, and re-run the
build.

The card descriptions are keyed by family name, `codex.bleed`, `codex.breach`
and so on, not by position, so a new family can be inserted anywhere in the
list without renumbering the others.

Vulnerable and Breach are two families, not one. Vulnerable strips up to 40%
of hard and soft defence, Breach does the same to magic defence, and the
Scholar, Warlock and Soul Reaper trees are built around Breach specifically.
The longest term wins when they overlap, so "Internal Bleeding" is never
matched as "Bleeding".

Each class page shows chips only for the statuses that class actually
mentions, so a Crusader page shows Bleeding, Blind and Vulnerable and nothing
else.

## The doram

Doram is in the game and Doram is in a cell. Typing `thereisnohope` anywhere
on the site, with nothing focused, opens a small dialog that admits it. There
is no link to it and no hint of it, which is the whole point.

It lives in section 8 of `assets/js/main.js` and builds its own markup, so it
works on all 65 pages without a line of HTML anywhere. Keystrokes are only
counted while no field has focus, so typing into the database search or the
class filter never sets it off. Its five strings are `egg.tag`, `egg.p1`,
`egg.p2`, `egg.foot` and `egg.btn` in the locale files, read at the moment the
dialog opens, so it speaks whatever language the visitor picked. The button
says Bruh in all six.

---

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
