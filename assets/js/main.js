/* ==========================================================================
   Nightmare RO - site behaviour
   Theme, menus, scroll reveals, class filtering, art toggles.
   ========================================================================== */

(function () {
  'use strict';

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
