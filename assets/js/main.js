/* ==========================================================================
   Nightmare RO - site behaviour
   Theme, menus, countdown, scroll reveals, class filtering, art toggles.
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

  /* --------------------------------------------------------- 4. countdown */

  var LAUNCH = Date.UTC(2026, 7, 7, 0, 0, 0); // August 7, 2026, 00:00 UTC
  var cd = $('#countdown');

  if (cd) {
    var cells = {
      d: cd.querySelector('[data-cd="d"]'),
      h: cd.querySelector('[data-cd="h"]'),
      m: cd.querySelector('[data-cd="m"]'),
      s: cd.querySelector('[data-cd="s"]')
    };
    var pad = function (n) { return n < 10 ? '0' + n : String(n); };

    var tick = function () {
      var left = LAUNCH - Date.now();
      if (left <= 0) {
        cd.hidden = true;
        var live = $('#liveNow');
        if (live) live.hidden = false;
        clearInterval(timer);
        return;
      }
      var s = Math.floor(left / 1000);
      cells.d.textContent = Math.floor(s / 86400);
      cells.h.textContent = pad(Math.floor(s / 3600) % 24);
      cells.m.textContent = pad(Math.floor(s / 60) % 60);
      cells.s.textContent = pad(s % 60);
    };
    tick();
    var timer = setInterval(tick, 1000);
  }

  /* ----------------------------------------------------- 5. scroll reveals */

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

  /* ------------------------------------------------ 6. class list filtering */

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

  /* ----------------------------------------------- 7. class art male/female */

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
