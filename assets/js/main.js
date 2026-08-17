/* ==========================================================================
   Nightmare RO - site behaviour
   Theme, menus, scroll reveals, class filtering, art toggles.
   ========================================================================== */

(function () {
  'use strict';

  /* Ask for our own files under the build stamp the page carries, so a copy
     cached before the last deploy is at an address we never request again.
     i18n.js defines it and is the first script on every page. */
  function fresh(url) {
    return window.NM_FRESH ? window.NM_FRESH(url) : url;
  }

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  /* ------------------------------------------------------------- 1. theme */

  var themeBtn = $('#themeToggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem('nm-theme', next); } catch (e) {}
    });
  }

  /* ------------------------------------------------------ 2. sticky header */

  var header = $('#siteHeader');
  if (header) {
    var onScroll = function () {
      header.classList.toggle('is-stuck', window.scrollY > 12);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ------------------------------------------------------ 3. mobile drawer */

  var drawer = $('#drawer');
  var burger = $('#burger');
  if (drawer && burger) {
    var openDrawer = function (open) {
      drawer.dataset.open = String(open);
      burger.setAttribute('aria-expanded', String(open));
      document.body.classList.toggle('no-scroll', open);
      if (open) { var f = drawer.querySelector('a, button'); if (f) f.focus(); }
    };
    burger.addEventListener('click', function () { openDrawer(true); });
    var closeBtn = $('#drawerClose');
    if (closeBtn) closeBtn.addEventListener('click', function () { openDrawer(false); });
    $$('a', drawer).forEach(function (a) {
      a.addEventListener('click', function () { openDrawer(false); });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && drawer.dataset.open === 'true') openDrawer(false);
    });
  }

  /* ------------------------------------------------- 3b. nav dropdown */

  /* Hover already opens it in CSS. This is for keyboard and touch, where
     there is no hover to work with. */
  var dropBtns = $$('.nav-drop-btn');
  if (dropBtns.length) {
    var closeDrops = function (except) {
      dropBtns.forEach(function (b) {
        if (b !== except) b.setAttribute('aria-expanded', 'false');
      });
    };
    dropBtns.forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var open = btn.getAttribute('aria-expanded') === 'true';
        closeDrops(btn);
        btn.setAttribute('aria-expanded', String(!open));
      });
    });
    document.addEventListener('click', function () { closeDrops(null); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeDrops(null);
    });
  }

  /* ---------------------------------------------- 3c. community videos

     The class pages ship a thumbnail and a play button, not an embed. The
     player is only built when someone asks for it, so a page with five clips
     on it still loads like a page with none. */

  var vidGrid = document.querySelector('.vid-grid');
  if (vidGrid) {
    vidGrid.addEventListener('click', function (e) {
      var card = e.target.closest('.vid-card');
      if (!card) return;
      var id = card.dataset.video;
      var frame = document.createElement('iframe');
      frame.src = 'https://www.youtube-nocookie.com/embed/' + id +
                  '?autoplay=1&rel=0';
      frame.title = card.getAttribute('aria-label') || 'Video';
      frame.allow = 'accelerometer; autoplay; encrypted-media; picture-in-picture';
      frame.allowFullscreen = true;
      frame.loading = 'lazy';
      var slot = document.createElement('div');
      slot.className = 'vid-frame';
      slot.appendChild(frame);
      card.replaceWith(slot);
    });
  }

  /* ------------------------------------------------- 3d. the site search

     The menu can only ever be six words wide, and the site is now eighteen
     hundred things: classes, skills, items, cards, bosses, quests, statuses
     and every field worth levelling on. So there is one box that searches
     all of it, on / or Ctrl+K.

     It is built at runtime, the same trick the rest of the chrome uses, so
     no page carries markup for it. The index is one file, fetched the first
     time somebody reaches for the search and warmed the moment a pointer
     touches the button, so the first open feels like it was already there. */

  (function () {
    var tools = $('.header-tools');
    if (!tools || !window.fetch) return;

    /* Class pages sit one level down, and the logo already knows how far. */
    var brand = $('.brand');
    var PREFIX = (brand ? brand.getAttribute('href') : 'index.html')
      .replace(/index\.html$/, '');

    var t = function (key, fallback) {
      var table = window.NM_I18N_TABLE || {};
      return table[key] || fallback;
    };

    /* Accents are how a word is spelled, not how it gets typed into a
       search box. Stripping them keeps "Kobold" and "Ktullanux" findable
       from a keyboard that is not the one the name was written on. */
    var flat = function (s) {
      return s.normalize
        ? s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
        : s.toLowerCase();
    };

    var esc = function (s) {
      return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
                      .replace(/>/g, '&gt;');
    };

    /* A page outranks an item, because "fire" is the name of a hundred
       cards and of one section that explains what fire actually does. */
    var WEIGHT = {
      page: 60, 'class': 52, boss: 40, quest: 38, status: 36,
      map: 30, skill: 26, item: 20, drops: 44
    };
    var LABEL = {
      page: 'Pages', 'class': 'Classes', skill: 'Skills',
      item: 'Items and cards', boss: 'Bosses', quest: 'Quests',
      status: 'Status effects', map: 'Fields and dungeons',
      drops: 'Dropped by'
    };
    var PER_GROUP = 7;
    var TOTAL = 28;

    var rows = [];
    var pending = null;

    var load = function () {
      if (pending) return pending;
      pending = fetch(fresh(PREFIX + 'assets/data/search.json'))
        .then(function (r) { return r.json(); })
        .then(function (json) {
          rows = json.rows.map(function (r) {
            return {
              title: r[0], sub: r[1], url: r[2], group: r[3],
              ft: flat(r[0]), fs: flat(r[1] + ' ' + (r[4] || ''))
            };
          });
        })
        .catch(function () { pending = null; });
      return pending;
    };

    var score = function (row, q, tokens) {
      var s = 0;
      var i = row.ft.indexOf(q);
      if (row.ft === q) s = 1000;
      else if (i === 0) s = 700;
      else if (i > 0 && row.ft.charAt(i - 1) === ' ') s = 520;
      else if (i > 0) s = 340;
      else if (row.fs.indexOf(q) > -1) s = 150;
      else if (tokens.length > 1) {
        var all = row.ft + ' ' + row.fs;
        for (var k = 0; k < tokens.length; k++) {
          if (all.indexOf(tokens[k]) < 0) return 0;
        }
        s = 110;
      }
      if (!s) return 0;
      /* Between two equal matches the shorter name is the one meant. */
      return s + (WEIGHT[row.group] || 0) - Math.min(row.title.length, 48) / 6;
    };

    var find = function (raw) {
      var q = flat(raw.trim());
      if (!q) {
        return rows.filter(function (r) { return r.group === 'page'; })
                   .slice(0, 8);
      }
      var tokens = q.split(/\s+/);
      var hits = [];
      for (var i = 0; i < rows.length; i++) {
        var s = score(rows[i], q, tokens);
        if (s > 0) hits.push([s, rows[i]]);
      }
      hits.sort(function (a, b) { return b[0] - a[0]; });

      /* Cap each group so nine hundred cards cannot bury the one page. */
      var seen = {};
      var out = [];
      for (var j = 0; j < hits.length && out.length < TOTAL; j++) {
        var g = hits[j][1].group;
        seen[g] = (seen[g] || 0) + 1;
        if (seen[g] > PER_GROUP) continue;
        out.push(hits[j][1]);
      }
      return out;
    };

    /* The matched run is marked, so it is obvious why a row is in the list. */
    var mark = function (text, q) {
      if (!q) return esc(text);
      var at = flat(text).indexOf(q);
      if (at < 0) return esc(text);
      return esc(text.slice(0, at)) + '<mark>' +
             esc(text.slice(at, at + q.length)) + '</mark>' +
             esc(text.slice(at + q.length));
    };

    /* ---------------------------------------------------------- the panel */

    var back = null, input = null, list = null, note = null, tip = null;
    var cur = -1;
    var opener = null;

    var isOpen = function () { return back && !back.hidden; };

    var close = function () {
      if (!isOpen()) return;
      back.hidden = true;
      document.body.classList.remove('no-scroll');
      if (opener) opener.focus();
    };

    var move = function (step) {
      var items = $$('.find-hit', list);
      if (!items.length) return;
      cur = (cur + step + items.length) % items.length;
      items.forEach(function (el, i) {
        var on = i === cur;
        el.classList.toggle('is-on', on);
        el.setAttribute('aria-selected', String(on));
        if (on) {
          el.scrollIntoView({ block: 'nearest' });
          input.setAttribute('aria-activedescendant', el.id);
        }
      });
    };

    var render = function () {
      var raw = input.value;
      var q = flat(raw.trim());
      cur = -1;
      input.removeAttribute('aria-activedescendant');

      if (!rows.length) {
        list.innerHTML = '';
        note.hidden = false;
        note.textContent = t('find.loading', 'Loading the index');
        return;
      }

      var hits = find(raw);
      if (!hits.length) {
        list.innerHTML = '';
        note.hidden = false;
        note.textContent = t('find.none', 'Nothing matched') +
                           ' “' + raw.trim() + '”';
        return;
      }
      note.hidden = true;

      var html = '';
      var group = null;
      var n = 0;
      hits.forEach(function (r) {
        if (r.group !== group) {
          group = r.group;
          html += '<li class="find-group" role="presentation">' +
                  esc(q ? t('find.g.' + group, LABEL[group])
                        : t('find.jump', 'Jump to')) + '</li>';
        }
        html += '<li role="presentation">' +
                '<a class="find-hit" role="option" id="find-hit-' + n + '"' +
                ' aria-selected="false" href="' + esc(PREFIX + r.url) + '">' +
                '<b>' + mark(r.title, q) + '</b>' +
                '<span>' + esc(r.sub) + '</span></a></li>';
        n++;
      });
      list.innerHTML = html;
    };

    var build = function () {
      back = document.createElement('div');
      back.className = 'find-back';
      back.hidden = true;
      back.innerHTML =
        '<div class="find-panel" role="dialog" aria-modal="true">' +
          '<div class="find-bar">' +
            '<svg class="find-ico" aria-hidden="true">' +
              '<use href="#i-search"></use></svg>' +
            '<input type="search" id="findInput" autocomplete="off"' +
            ' spellcheck="false" role="combobox" aria-expanded="true"' +
            ' aria-controls="findList" aria-autocomplete="list">' +
            '<kbd class="find-esc">Esc</kbd>' +
          '</div>' +
          '<ul class="find-list" id="findList" role="listbox"></ul>' +
          '<p class="find-note" hidden></p>' +
          '<p class="find-tip"></p>' +
        '</div>';
      document.body.appendChild(back);

      input = $('#findInput', back);
      list = $('#findList', back);
      note = $('.find-note', back);
      tip = $('.find-tip', back);

      back.addEventListener('click', function (e) {
        if (e.target === back) close();
      });
      list.addEventListener('click', function (e) {
        if (e.target.closest('.find-hit')) close();
      });
      list.addEventListener('mousemove', function (e) {
        var hit = e.target.closest('.find-hit');
        if (!hit) return;
        var items = $$('.find-hit', list);
        cur = items.indexOf(hit);
        items.forEach(function (el, i) {
          el.classList.toggle('is-on', i === cur);
          el.setAttribute('aria-selected', String(i === cur));
        });
      });

      var tick = null;
      input.addEventListener('input', function () {
        clearTimeout(tick);
        tick = setTimeout(render, 70);
      });

      input.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
        else if (e.key === 'Escape') { e.preventDefault(); close(); }
        else if (e.key === 'Enter') {
          var on = $('.find-hit.is-on', list) || $('.find-hit', list);
          if (on) { e.preventDefault(); on.click(); }
        }
      });
    };

    var words = function () {
      if (!input) return;
      input.placeholder = t('find.placeholder',
        'Search classes, items, bosses, quests');
      input.setAttribute('aria-label', t('find.label', 'Search the site'));
      tip.textContent = t('find.tip',
        'Enter opens, arrows move, Esc closes');
    };

    var open = function (from) {
      opener = from || null;
      if (!back) build();
      words();
      back.hidden = false;
      document.body.classList.add('no-scroll');
      input.value = '';
      render();
      load().then(render);
      input.focus();
    };

    /* ------------------------------------------------------- the way in */

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'icon-btn find-btn';
    btn.id = 'findBtn';
    btn.innerHTML =
      '<svg aria-hidden="true"><use href="#i-search"></use></svg>' +
      '<span class="find-btn-word"></span><kbd>/</kbd>';
    tools.insertBefore(btn, tools.firstChild);

    var label = function () {
      btn.setAttribute('aria-label', t('find.label', 'Search the site'));
      btn.title = t('find.label', 'Search the site');
      $('.find-btn-word', btn).textContent = t('find.btn', 'Search');
    };
    label();
    document.addEventListener('nm:lang', function () { label(); words(); });

    btn.addEventListener('click', function () { open(btn); });
    btn.addEventListener('pointerenter', load);
    btn.addEventListener('focus', load);

    /* The drawer gets one too, at the top, where a thumb already is. */
    var drawerNav = document.querySelector('.drawer nav');
    if (drawerNav) {
      var dbtn = document.createElement('button');
      dbtn.type = 'button';
      dbtn.className = 'drawer-find';
      dbtn.innerHTML =
        '<svg aria-hidden="true"><use href="#i-search"></use></svg><span></span>';
      var dlabel = function () {
        dbtn.querySelector('span').textContent =
          t('find.placeholder', 'Search classes, items, bosses, quests');
      };
      dlabel();
      document.addEventListener('nm:lang', dlabel);
      drawerNav.insertBefore(dbtn, drawerNav.firstChild);
      dbtn.addEventListener('click', function () {
        var d = $('#drawer');
        var b = $('#burger');
        if (d) d.dataset.open = 'false';
        if (b) b.setAttribute('aria-expanded', 'false');
        open(null);
      });
    }

    /* Slash is what every wiki uses, Ctrl+K is what every app uses. Both. */
    document.addEventListener('keydown', function (e) {
      if (isOpen()) return;
      if ((e.key === 'k' || e.key === 'K') && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        open(btn);
        return;
      }
      var el = e.target;
      var typing = el && (el.isContentEditable ||
        /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName));
      if (e.key === '/' && !typing && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        open(btn);
      }
    });
  })();

  /* ----------------------------------------------------- 4. scroll reveals */

  var reveals = $$('.reveal');
  if (reveals.length) {
    if (!('IntersectionObserver' in window)) {
      reveals.forEach(function (el) { el.classList.add('is-in'); });
    } else {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-in');
          io.unobserve(entry.target);
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.06 });
      reveals.forEach(function (el) { io.observe(el); });
    }
  }

  /* ------------------------------------------------ 5. class list filtering */

  var grid = $('#classIndex');
  if (grid) {
    var search = $('#classSearch');
    var chips = $$('.chip[data-tier]');
    var empty = $('#classEmpty');
    var tier = 'all';

    var run = function () {
      var q = (search && search.value || '').trim().toLowerCase();
      var shown = 0;

      $$('[data-class]', grid).forEach(function (card) {
        var okTier = tier === 'all' || card.dataset.tier === tier;
        var okText = !q || card.dataset.search.indexOf(q) !== -1;
        var ok = okTier && okText;
        card.classList.toggle('is-hidden', !ok);
        if (ok) shown++;
      });

      $$('.branch', grid).forEach(function (branch) {
        var any = $$('[data-class]:not(.is-hidden)', branch).length > 0;
        branch.classList.toggle('is-hidden', !any);
      });

      if (empty) empty.hidden = shown > 0;
    };

    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        tier = chip.dataset.tier;
        chips.forEach(function (c) { c.setAttribute('aria-pressed', String(c === chip)); });
        run();
      });
    });

    if (search) search.addEventListener('input', run);
    run();
  }

  /* ----------------------------------------------- 6. class art male/female */

  $$('.sex-toggle').forEach(function (group) {
    var img = $('.portrait img');
    if (!img) return;

    $$('button', group).forEach(function (btn) {
      btn.addEventListener('click', function () {
        $$('button', group).forEach(function (b) {
          b.setAttribute('aria-pressed', String(b === btn));
        });
        img.src = btn.dataset.src;
        img.alt = btn.dataset.alt || img.alt;
      });
    });
  });

  /* ------------------------------------------------------- 7. the doram */

  /* Doram is in the game and Doram is in a cell. Type the word and the site
     admits it. Nothing links here and nothing hints at it, which is the
     point. Keystrokes are only counted when nothing is focused, so typing
     into the database search never sets it off. */

  (function () {
    var CODE = 'thereisnohope';
    var typed = '';
    var open = null;

    var t = function (key, fallback) {
      var table = window.NM_I18N_TABLE || {};
      return table[key] || fallback;
    };

    function close() {
      if (!open) return;
      var back = open.back, focus = open.focus;
      open = null;
      document.removeEventListener('keydown', onKey, true);
      back.remove();
      if (focus && focus.focus) focus.focus();
    }

    function onKey(e) {
      if (e.key === 'Escape') { e.stopPropagation(); close(); }
    }

    function reveal() {
      if (open) return;
      var focus = document.activeElement;

      var back = document.createElement('div');
      back.className = 'egg-back';
      back.innerHTML =
        '<div class="egg-card" role="dialog" aria-modal="true" aria-labelledby="eggTitle">' +
          '<div class="egg-bars" aria-hidden="true"></div>' +
          '<div class="egg-body">' +
            '<p class="egg-tag">' + t('egg.tag', 'Prisoner record') + '</p>' +
            '<h2 id="eggTitle">Doram</h2>' +
            '<p class="egg-p">' + t('egg.p1', 'Yes, the cat people are in the game. They are also in a cell, behind a locked door, on a map nobody can warp to.') + '</p>' +
            '<p class="egg-p -strong">' + t('egg.p2', 'That is exactly where they should be.') + '</p>' +
            '<p class="egg-foot">' + t('egg.foot', 'Nothing to see here. Move along.') + '</p>' +
            '<button class="btn -primary egg-btn" type="button">' + t('egg.btn', 'Bruh') + '</button>' +
          '</div>' +
        '</div>';

      back.addEventListener('click', function (e) {
        if (e.target === back || e.target.closest('.egg-btn')) close();
      });

      document.body.appendChild(back);
      open = { back: back, focus: focus };
      document.addEventListener('keydown', onKey, true);
      back.querySelector('.egg-btn').focus();
    }

    document.addEventListener('keydown', function (e) {
      if (open || e.ctrlKey || e.metaKey || e.altKey) return;

      var el = e.target;
      if (el && (el.isContentEditable ||
                 /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName))) {
        typed = '';
        return;
      }

      if (e.key.length !== 1) return;
      typed = (typed + e.key.toLowerCase()).slice(-CODE.length);
      if (typed === CODE) { typed = ''; reveal(); }
    });
  })();

  /* ------------------------------------------ 7b. loading screen gallery */

  /* The grid in the HTML is already a set of links to the full JPGs, so this
     only adds the nice parts: tier filters, the viewer with arrow keys, a
     thumbnail rail, and the cursor glow on each card. The open screen is
     mirrored into the URL hash so a specific one can be linked. */

  (function () {
    var grid = $('#lsGrid');
    if (!grid) return;

    var cards = $$('.ls-card', grid);
    if (!cards.length) return;

    var chips = $$('[data-ls-filter]');
    var counter = $('#lsCountN');
    var shown = cards.slice();     // the filtered set, in grid order
    var box = null;                // viewer element, built on first open
    var at = -1;
    var lastFocus = null;

    var t = function (key, fallback) {
      var table = window.NM_I18N_TABLE || {};
      return table[key] || fallback;
    };

    var full = function (card) { return $('.ls-shot', card).getAttribute('href'); };
    var thumb = function (card) { return $('img', card).getAttribute('src'); };

    /* ---------------------------------------------------------- filtering */

    var filter = function (tier) {
      shown = cards.filter(function (card) {
        var ok = tier === 'all' || card.dataset.tier === tier;
        card.hidden = !ok;
        return ok;
      });
      if (counter) counter.textContent = String(shown.length);
      if (box) rail();
    };

    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        chips.forEach(function (c) { c.setAttribute('aria-pressed', String(c === chip)); });
        filter(chip.dataset.lsFilter);
      });
    });

    /* ------------------------------------------------------------- viewer */

    var hash = function (slug) {
      if (!history.replaceState) return;
      history.replaceState(null, '', slug ? '#' + slug : location.pathname + location.search);
    };

    var preload = function (card) {
      if (!card) return;
      var img = new Image();
      img.src = full(card);
    };

    var rail = function () {
      var strip = $('[data-ls-rail]', box);
      strip.innerHTML = '';
      shown.forEach(function (card, i) {
        var b = document.createElement('button');
        b.type = 'button';
        b.dataset.lsGo = String(i);
        b.setAttribute('aria-label', card.dataset.name);
        b.innerHTML = '<img src="' + thumb(card) + '" alt="" loading="lazy" decoding="async">';
        strip.appendChild(b);
      });
      mark();
    };

    var mark = function () {
      $$('[data-ls-go]', box).forEach(function (b, i) {
        var on = i === at;
        b.setAttribute('aria-current', String(on));
        if (on && b.scrollIntoView) {
          b.scrollIntoView({ block: 'nearest', inline: 'center' });
        }
      });
    };

    var show = function (i) {
      if (!shown.length) return;
      at = (i + shown.length) % shown.length;
      var card = shown[at];
      var img = $('[data-ls-img]', box);
      var dl = $('[data-ls-dl]', box);

      img.src = full(card);
      img.alt = $('img', card).getAttribute('alt');
      $('[data-ls-name]', box).textContent = card.dataset.name;
      var tier = card.dataset.tier === 'third'
        ? t('ls.fThird', card.dataset.role)
        : t('ls.fTrans', card.dataset.role);
      $('[data-ls-meta]', box).textContent =
        tier + '  ·  ' + (at + 1) + ' / ' + shown.length;
      dl.href = full(card);
      dl.setAttribute('download', 'nightmarero-loading-' + card.dataset.slug + '.jpg');

      mark();
      hash(card.dataset.slug);
      preload(shown[(at + 1) % shown.length]);
      preload(shown[(at - 1 + shown.length) % shown.length]);
    };

    var close = function () {
      if (!box) return;
      box.remove();
      box = null;
      at = -1;
      document.body.classList.remove('no-scroll');
      document.removeEventListener('keydown', onKey, true);
      hash(null);
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    };

    function onKey(e) {
      if (!box) return;
      if (e.key === 'Escape') { e.stopPropagation(); close(); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); show(at + 1); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); show(at - 1); }
    }

    var build = function () {
      box = document.createElement('div');
      box.className = 'ls-box';
      box.setAttribute('role', 'dialog');
      box.setAttribute('aria-modal', 'true');
      box.setAttribute('aria-label', t('ls.viewer', 'Loading screen viewer'));
      box.innerHTML =
        '<div class="ls-box-top">' +
          '<div class="ls-box-title">' +
            '<strong data-ls-name></strong>' +
            '<span data-ls-meta></span>' +
          '</div>' +
          '<div class="ls-box-tools">' +
            '<a class="btn -primary -sm" data-ls-dl href="#" download>' +
              '<svg aria-hidden="true"><use href="#i-download"></use></svg>' +
              '<span>' + t('ls.getThis', 'Download') + '</span>' +
            '</a>' +
            '<button class="icon-btn" type="button" data-ls-close aria-label="' +
              t('ls.close', 'Close') + '">' +
              '<svg aria-hidden="true"><use href="#i-close"></use></svg>' +
            '</button>' +
          '</div>' +
        '</div>' +
        '<div class="ls-stage">' +
          '<button class="ls-arrow -prev" type="button" data-ls-step="-1" aria-label="' +
            t('ls.prev', 'Previous screen') + '">' +
            '<svg aria-hidden="true"><use href="#i-arrow"></use></svg>' +
          '</button>' +
          '<img data-ls-img alt="" decoding="async">' +
          '<button class="ls-arrow -next" type="button" data-ls-step="1" aria-label="' +
            t('ls.next', 'Next screen') + '">' +
            '<svg aria-hidden="true"><use href="#i-arrow"></use></svg>' +
          '</button>' +
        '</div>' +
        '<div class="ls-rail" data-ls-rail></div>';

      box.addEventListener('click', function (e) {
        var step = e.target.closest('[data-ls-step]');
        if (step) { show(at + Number(step.dataset.lsStep)); return; }

        var go = e.target.closest('[data-ls-go]');
        if (go) { show(Number(go.dataset.lsGo)); return; }

        if (e.target.closest('[data-ls-close]')) { close(); return; }

        /* clicking the empty space around the picture closes it */
        if (e.target === box || e.target.classList.contains('ls-stage')) close();
      });

      document.body.appendChild(box);
      document.body.classList.add('no-scroll');
      document.addEventListener('keydown', onKey, true);
      rail();
    };

    var open = function (card) {
      var i = shown.indexOf(card);
      if (i === -1) { filter('all'); chips.forEach(function (c) {
        c.setAttribute('aria-pressed', String(c.dataset.lsFilter === 'all'));
      }); i = shown.indexOf(card); }
      if (i === -1) return;

      lastFocus = document.activeElement;
      if (!box) build();
      show(i);
      var x = $('[data-ls-close]', box);
      if (x) x.focus();
    };

    grid.addEventListener('click', function (e) {
      var link = e.target.closest('[data-ls-open]');
      if (!link || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
      e.preventDefault();
      open(link.closest('.ls-card'));
    });

    /* cursor glow, one listener per card, pointer devices only */
    if (matchMedia('(hover: hover)').matches) {
      cards.forEach(function (card) {
        var shot = $('.ls-shot', card);
        shot.addEventListener('mousemove', function (e) {
          var r = shot.getBoundingClientRect();
          card.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100).toFixed(1) + '%');
          card.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100).toFixed(1) + '%');
        }, { passive: true });
      });
    }

    /* grab the lot, one download at a time so the browser keeps up */
    var all = $('#lsGetAll');
    if (all) {
      all.addEventListener('click', function () {
        var label = $('span', all);
        var was = label ? label.textContent : '';
        if (label) label.textContent = t('ls.getting', 'Starting downloads...');
        all.disabled = true;

        cards.forEach(function (card, i) {
          setTimeout(function () {
            var a = document.createElement('a');
            a.href = full(card);
            a.download = 'nightmarero-loading-' + card.dataset.slug + '.jpg';
            document.body.appendChild(a);
            a.click();
            a.remove();
            if (i === cards.length - 1) {
              all.disabled = false;
              if (label) label.textContent = was;
            }
          }, i * 450);
        });
      });
    }

    filter('all');

    /* deep link, e.g. loading-screens.html#warlock. Also watched after load,
       so pasting a link while already on the page opens the right one. */
    var fromHash = function () {
      var slug = location.hash.slice(1);
      if (!slug) return;
      var want = cards.filter(function (c) { return c.dataset.slug === slug; })[0];
      if (want && (!box || shown[at] !== want)) open(want);
    };

    window.addEventListener('hashchange', fromHash);
    fromHash();
  })();

  /* -------------------------------------------------------------- 8. misc */

  var year = $('#year');
  if (year) year.textContent = String(new Date().getFullYear());

  /* Nudge the hero art with the pointer, gently. The float animation owns
     `translate` on the images themselves, so this moves the container.
     Skipped for touch screens and for anyone who asked for reduced motion. */
  var art = $('.hero-art');
  if (art && matchMedia('(hover: hover)').matches &&
      !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var pending = false;
    var px = 0, py = 0;
    window.addEventListener('mousemove', function (e) {
      px = (e.clientX / window.innerWidth - 0.5) * 18;
      py = (e.clientY / window.innerHeight - 0.5) * 10;
      if (pending) return;
      pending = true;
      requestAnimationFrame(function () {
        art.style.transform = 'translate3d(' + px.toFixed(1) + 'px,' + py.toFixed(1) + 'px,0)';
        pending = false;
      });
    }, { passive: true });
  }
})();
