/* ==========================================================================
   Nightmare RO - "which class are you" test
   --------------------------------------------------------------------------
   Nine scenarios in Midgard score six traits. The top two traits pick one of
   fifteen archetypes, each of which points at a class. The class the player
   used to main only nudges the wording, never the maths, so the same answers
   always land in the same place.
   ========================================================================== */

(function () {
  'use strict';

  var root = document.getElementById('quiz');
  if (!root) return;

  var $ = function (id) { return document.getElementById(id); };

  /* ------------------------------------------------------------- the traits */

  var TRAITS = {
    force: { label: 'Force', blurb: 'You solve problems by hitting them until they stop being problems.' },
    guile: { label: 'Guile', blurb: 'You would rather the fight be over before it looks like a fight.' },
    ward: { label: 'Ward', blurb: 'You are the reason the rest of the party is still standing.' },
    arcane: { label: 'Arcane', blurb: 'You read the manual. Twice. Then you rewrote it.' },
    wild: { label: 'Wild', blurb: 'A plan is a thing you abandon the moment something funnier appears.' },
    bond: { label: 'Bond', blurb: 'The game is other people. Everything else is scenery.' }
  };

  /* ---------------------------------------------------------- the questions */

  var QUESTIONS = [
    {
      q: 'A Poring has swallowed your last Red Potion and is hopping away, entirely unbothered.',
      a: [
        { t: 'Run it down and flatten it.', s: { force: 3, wild: 1 } },
        { t: 'Wait by the spot it always hops back to.', s: { guile: 3, ward: 1 } },
        { t: 'Let it go. Potions are a solved problem.', s: { arcane: 2, ward: 2 } },
        { t: 'Whistle. Someone else will corner it.', s: { bond: 3, guile: 1 } }
      ]
    },
    {
      q: 'The Kafra in Prontera asks where you are headed, mostly out of politeness.',
      a: [
        { t: '"Somewhere that hits back."', s: { force: 3, wild: 1 } },
        { t: '"Somewhere nobody has bothered to map."', s: { wild: 3, guile: 1 } },
        { t: '"The archive. I have reading to finish."', s: { arcane: 3, ward: 1 } },
        { t: '"Wherever they are short a fifth."', s: { bond: 3, ward: 1 } }
      ]
    },
    {
      q: 'Your party wipes on the first pull of a guild raid. The silence is getting long.',
      a: [
        { t: '"My call. Again, from the top."', s: { ward: 2, bond: 2 } },
        { t: '"The pull order was wrong. Here it is written down."', s: { arcane: 3, bond: 1 } },
        { t: '"I will hold it this time. Just keep hitting."', s: { ward: 3, force: 1 } },
        { t: '"Let me try something stupid."', s: { wild: 3, force: 1 } }
      ]
    },
    {
      q: 'Under Geffen you find a door with no handle, no hinges and a very faint draught.',
      a: [
        { t: 'Hit it until it becomes a doorway.', s: { force: 3 } },
        { t: 'Sit with it. Doors like this open on a schedule.', s: { guile: 2, ward: 2 } },
        { t: 'Copy the sigils down before touching anything.', s: { arcane: 3 } },
        { t: 'Walk through and find out. That is what HP is for.', s: { wild: 3 } }
      ]
    },
    {
      q: 'A champion monster is guarding the relic you need. It has not seen you yet.',
      a: [
        { t: 'Open with everything. Nothing survives the first ten seconds.', s: { force: 3, wild: 1 } },
        { t: 'Stack every status on it before it takes a step.', s: { guile: 3, arcane: 1 } },
        { t: 'Pull it somewhere with better ground and outlast it.', s: { ward: 3, guile: 1 } },
        { t: 'Wait for the others. This is a five person problem.', s: { bond: 3, ward: 1 } }
      ]
    },
    {
      q: 'Someone in the guild chat is asking, for the fourth time, how refining works.',
      a: [
        { t: 'Answer it. Again. Properly.', s: { bond: 3, ward: 1 } },
        { t: 'Paste the table you wrote months ago.', s: { arcane: 3, bond: 1 } },
        { t: 'Tell them to just swing at +10 and find out.', s: { wild: 3, force: 1 } },
        { t: 'Say nothing and go back to farming.', s: { guile: 2, force: 2 } }
      ]
    },
    {
      q: 'You have exactly one skill point left and two things you want.',
      a: [
        { t: 'The bigger number. Always the bigger number.', s: { force: 3, wild: 1 } },
        { t: 'The one that sets up the other three skills.', s: { guile: 2, arcane: 2 } },
        { t: 'The one that stops you dying at the worst moment.', s: { ward: 3 } },
        { t: 'The one that helps whoever is standing next to you.', s: { bond: 3 } }
      ]
    },
    {
      q: 'Deep in a Nightmare Dungeon the map itself starts draining your health.',
      a: [
        { t: 'Push faster. Kill it before the floor kills you.', s: { force: 2, wild: 2 } },
        { t: 'Back out and come back with the right shadow set.', s: { arcane: 2, ward: 2 } },
        { t: 'Map every safe pocket on the way down.', s: { guile: 3, arcane: 1 } },
        { t: 'Call the group. Nobody goes down there alone.', s: { bond: 3, ward: 1 } }
      ]
    },
    {
      q: 'Last one. Someone asks what you actually enjoy about all this.',
      a: [
        { t: '"The moment a health bar disappears."', s: { force: 3, wild: 1 } },
        { t: '"Finding the thing everyone else walked past."', s: { guile: 3, wild: 1 } },
        { t: '"Surviving something that should have killed me."', s: { ward: 3, force: 1 } },
        { t: '"Working out exactly why it works."', s: { arcane: 3, guile: 1 } },
        { t: '"The people. Obviously the people."', s: { bond: 3, ward: 1 } }
      ]
    }
  ];

  /* --------------------------------------------------------- the archetypes */

  /* One per unordered pair of traits, so every combination lands somewhere. */
  var ARCHETYPES = [
    { pair: 'force+guile', name: 'The Red Verdict',
      motto: 'You do not threaten. You conclude.',
      body: 'You open fights you have already decided the end of. Bleed, break, finish, and be somewhere else before the body lands.',
      pick: 'Lord Knight', alt: 'Guillotine Cross' },
    { pair: 'force+ward', name: 'The Bulwark Oath',
      motto: 'The line holds because you are standing on it.',
      body: 'You go in first, stay in longest, and treat your own health bar as a resource rather than a warning.',
      pick: 'Royal Guard', alt: 'Paladin' },
    { pair: 'arcane+force', name: 'The Rune-Bitten',
      motto: 'You wrote the spell on the blade yourself.',
      body: 'Muscle bores you and theory alone is not enough. You want a toolbox you built, carved into something heavy.',
      pick: 'Rune Knight', alt: 'Sorcerer' },
    { pair: 'force+wild', name: 'The Dawn Fist',
      motto: 'Momentum is a defensive stat if you commit hard enough.',
      body: 'You close distance for a living. Nothing you do is subtle and nothing you do is slow.',
      pick: 'Sura', alt: 'Champion' },
    { pair: 'bond+force', name: 'The Standing Order',
      motto: 'Someone has to go first. It may as well be you.',
      body: 'You lead from the front, and the buff you leave behind matters as much as the hit you land.',
      pick: 'Paladin', alt: 'Royal Guard' },
    { pair: 'guile+ward', name: 'The Far Quiet',
      motto: 'The best position is the one nothing reaches.',
      body: 'You would rather set the board than be on it. Traps, spacing, patience, and a very long sightline.',
      pick: 'Ranger', alt: 'Sniper' },
    { pair: 'arcane+guile', name: 'The Twin Smoke',
      motto: 'Two things happened. You only saw one.',
      body: 'You like layered rotations where the setup is invisible and the payoff is not survivable.',
      pick: 'Maboroshi', alt: 'Night Watch' },
    { pair: 'guile+wild', name: 'The Sixth Shadow',
      motto: 'If it is not nailed down it is a build option.',
      body: 'You steal, copy, misdirect and improvise. Nobody, including you, knows what you will do next.',
      pick: 'Shadow Chaser', alt: 'Stalker' },
    { pair: 'bond+guile', name: 'The Whispered Ledger',
      motto: 'Everything is chemistry, including people.',
      body: 'You keep the party alive with things you brewed yourself, and you keep a quiet list of what everyone owes you.',
      pick: 'Biochemist', alt: 'Geneticist' },
    { pair: 'arcane+ward', name: 'The Long Study',
      motto: 'You have read what is about to happen.',
      body: 'You want to understand the fight more than you want to win it quickly, and that understanding is what keeps you upright.',
      pick: 'Scholar', alt: 'High Wizard' },
    { pair: 'ward+wild', name: 'The Iron Improviser',
      motto: 'It held. Do not ask how.',
      body: 'You build the answer on site out of whatever is lying around, then armour it badly and use it anyway.',
      pick: 'Mechanic', alt: 'Mastersmith' },
    { pair: 'bond+ward', name: 'The Kept Flame',
      motto: 'Nobody drops while you are watching.',
      body: 'You measure a good run by how few times anyone needed you, and you are always there the moment they do.',
      pick: 'Arch Bishop', alt: 'High Priest' },
    { pair: 'arcane+wild', name: 'The Hollow Chorus',
      motto: 'You called something and it answered.',
      body: 'Big, strange, expensive magic. You want the screen to go quiet and then very much not quiet.',
      pick: 'Warlock', alt: 'Soul Reaper' },
    { pair: 'arcane+bond', name: 'The Star-Reader',
      motto: 'You borrowed the sky and gave it to a friend.',
      body: 'Your power lands on other people. You read the situation, then hand someone else the answer.',
      pick: 'Soul Ascetic', alt: 'Sorcerer' },
    { pair: 'bond+wild', name: 'The Road Song',
      motto: 'The party plays better when you are in the room.',
      body: 'You are the reason a bad run is still a good night. Everything you do lands on someone else and comes back louder.',
      pick: 'Minstrel/Wanderer', alt: 'Clown/Gypsy' }
  ];

  /* --------------------------------------------- what you used to main */

  var OLD_CLASSES = [
    { v: '', label: 'Pick one', family: null, note: '' },
    { v: 'Knight', family: 'Swordsman', note: 'Knight is still here, but it forks: one path keeps the tight rotations, the other hands you rune magic and a blank page.' },
    { v: 'Crusader', family: 'Swordsman', note: 'Crusader kept the shield and lost the dead weight. Both of its endings are real damage now, not a compromise.' },
    { v: 'Blacksmith', family: 'Merchant', note: 'Blacksmith stopped being a crafting hobby with a hammer attached. It hits, and it hits with upkeep.' },
    { v: 'Alchemist', family: 'Merchant', note: 'Alchemist lost the bottle spam and gained a homunculus that acts on its own and chemistry that actually scales.' },
    { v: 'Assassin', family: 'Thief', note: 'Assassin still opens from nowhere, but poison is a system now rather than a consumable you forgot to buy.' },
    { v: 'Rogue', family: 'Thief', note: 'Rogue finally has a reason to exist beyond stealing. Copying and stripping are a build, not a party trick.' },
    { v: 'Wizard', family: 'Mage', note: 'Wizard split into the one that perfects the cast and the one that stops caring about cast time entirely.' },
    { v: 'Sage', family: 'Mage', note: 'Sage is no longer the class you rolled by accident. Both endings are specialists with a job to do.' },
    { v: 'Hunter', family: 'Archer', note: 'Hunter kept the falcon and got traps that stay on the floor doing work instead of being one-shot consumables.' },
    { v: 'Bard or Dancer', family: 'Archer', note: 'Bard and Dancer are not a two-account chore any more. One person, one instrument, real numbers.' },
    { v: 'Priest', family: 'Acolyte', note: 'Priest is not a heal bot. The healing is still there, but so is a reason to be pointed at the enemy.' },
    { v: 'Monk', family: 'Acolyte', note: 'Monk still ends fights in one combo. It just has more ways to reach the combo now.' },
    { v: 'Taekwon, Ninja or Gunslinger', family: 'Taekwon', note: 'The odd classes are not side projects here. They get the same fifty skill points and the same attention as everyone else.' },
    { v: 'Never played before', family: null, note: 'No baggage, then. That is the easiest way to meet a server where none of the old knowledge applies anyway.' }
  ];

  /* ------------------------------------------------------------------ state */

  var step = -1;          // -1 is the intro screen
  var answers = [];
  var oldClass = '';
  var scores = { force: 0, guile: 0, ward: 0, arcane: 0, wild: 0, bond: 0 };
  var classes = {};
  var result = null;

  /* ------------------------------------------------------------------ utils */

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function pairKey(a, b) { return [a, b].sort().join('+'); }

  function tally() {
    var s = { force: 0, guile: 0, ward: 0, arcane: 0, wild: 0, bond: 0 };
    answers.forEach(function (pick, i) {
      var add = QUESTIONS[i].a[pick].s;
      for (var k in add) s[k] += add[k];
    });
    return s;
  }

  function ranked(s) {
    return Object.keys(s).sort(function (a, b) {
      if (s[b] !== s[a]) return s[b] - s[a];
      return a.localeCompare(b);       // stable when tied
    });
  }

  function decide() {
    scores = tally();
    var order = ranked(scores);
    var key = pairKey(order[0], order[1]);
    var arch = ARCHETYPES.filter(function (x) { return x.pair === key; })[0] || ARCHETYPES[0];
    var old = OLD_CLASSES.filter(function (x) { return x.v === oldClass; })[0] || OLD_CLASSES[0];
    var cls = classes[arch.pick] || null;
    var alt = classes[arch.alt] || null;

    var sameFamily = old.family && cls && cls.family === old.family;

    return {
      arch: arch, cls: cls, alt: alt, old: old, order: order,
      sameFamily: sameFamily,
      why: buildWhy(arch, cls, old, order, sameFamily)
    };
  }

  function buildWhy(arch, cls, old, order, sameFamily) {
    var out = [];
    var t1 = TRAITS[order[0]].label, t2 = TRAITS[order[1]].label;

    out.push('Your answers leaned hardest on <b>' + t1 + '</b> and <b>' + t2 +
             '</b>, and that pairing is exactly what ' + esc(arch.pick) + ' is built around.');

    if (cls) {
      out.push(esc(cls.name) + ' sits in the ' + esc(cls.family) + ' line' +
               (cls.parent ? ', coming out of ' + esc(cls.parent) : '') +
               '. ' + esc(cls.summary));
    }

    if (old.v && old.family) {
      out.push(sameFamily
        ? 'You already main ' + esc(old.v) + ', so this is the same road with a different surface. ' + esc(old.note)
        : 'You come in from ' + esc(old.v) + '. ' + esc(old.note) +
          ' What the test is pointing at is a different family entirely, which on this server is less of a leap than it sounds: every tree was rewritten, so nobody is starting from experience.');
    } else if (old.v) {
      out.push(esc(old.note));
    }

    return out;
  }

  /* ------------------------------------------------------------------ views */

  function progress() {
    return '<div class="quiz-progress" role="group" aria-label="Progress">' +
      QUESTIONS.map(function (_, i) {
        return '<span class="' + (i < step ? '-done' : i === step ? '-now' : '') + '"></span>';
      }).join('') + '</div>';
  }

  function renderIntro() {
    root.innerHTML =
      '<div class="quiz-card">' +
        '<p class="eyebrow">Nine questions</p>' +
        '<h2>Which one of these are you, really?</h2>' +
        '<p class="muted">Every skill tree on this server was rewritten, so the class you mained for years might not be the class that fits you any more. Nine scenarios, no wrong answers, one honest suggestion at the end.</p>' +
        '<label class="quiz-label" for="oldClass">What did you main before?</label>' +
        '<select id="oldClass">' +
          OLD_CLASSES.map(function (o) {
            return '<option value="' + esc(o.v) + '">' + esc(o.v || o.label) + '</option>';
          }).join('') +
        '</select>' +
        '<p class="dim">Only used to word the result. It does not change which class you get.</p>' +
        '<button class="btn -primary -lg -block" id="quizStart" type="button">Begin</button>' +
      '</div>';

    $('quizStart').addEventListener('click', function () {
      oldClass = $('oldClass').value;
      step = 0;
      render();
    });
  }

  function renderQuestion() {
    var q = QUESTIONS[step];
    root.innerHTML =
      '<div class="quiz-card">' +
        progress() +
        '<p class="eyebrow">Scenario ' + (step + 1) + ' of ' + QUESTIONS.length + '</p>' +
        '<h2 class="quiz-q">' + esc(q.q) + '</h2>' +
        '<div class="quiz-answers">' +
          q.a.map(function (a, i) {
            return '<button class="quiz-answer" type="button" data-i="' + i + '">' +
                     esc(a.t) + '</button>';
          }).join('') +
        '</div>' +
        (step > 0 ? '<button class="btn -quiet -sm quiz-back" id="quizBack" type="button">Back</button>' : '') +
      '</div>';

    Array.prototype.forEach.call(root.querySelectorAll('.quiz-answer'), function (btn) {
      btn.addEventListener('click', function () {
        answers[step] = parseInt(btn.dataset.i, 10);
        step++;
        if (step >= QUESTIONS.length) {
          result = decide();
          step = QUESTIONS.length;
        }
        render();
      });
    });

    var back = $('quizBack');
    if (back) back.addEventListener('click', function () { step--; render(); });
  }

  function traitBars() {
    var max = Math.max.apply(null, Object.keys(scores).map(function (k) { return scores[k]; })) || 1;
    return '<ul class="quiz-bars">' + ranked(scores).slice(0, 4).map(function (k) {
      return '<li><span>' + TRAITS[k].label + '</span>' +
             '<span class="quiz-bar"><i style="width:' +
             Math.round(scores[k] / max * 100) + '%"></i></span></li>';
    }).join('') + '</ul>';
  }

  function renderResult() {
    var r = result;
    var cls = r.cls;

    root.innerHTML =
      '<div class="quiz-result" id="quizResult">' +
        '<div class="quiz-result-head">' +
          '<p class="eyebrow">Your archetype</p>' +
          '<h2>' + esc(r.arch.name) + '</h2>' +
          '<p class="quiz-motto">' + esc(r.arch.motto) + '</p>' +
          '<p class="muted">' + esc(r.arch.body) + '</p>' +
          traitBars() +
        '</div>' +

        '<div class="quiz-pick">' +
          (cls && cls.art
            ? '<div class="quiz-art"><img src="' + esc(cls.art) + '" alt="' + esc(cls.name) + '"></div>'
            : '') +
          '<div class="quiz-pick-body">' +
            '<p class="eyebrow">Play this</p>' +
            '<h3>' + esc(cls ? cls.name : r.arch.pick) + '</h3>' +
            (cls ? '<p class="tag -accent">' + esc(cls.family) + ' line<span aria-hidden="true"> · </span>' +
                   'Tier ' + cls.tier + '</p>' : '') +
            '<div class="quiz-why">' + r.why.map(function (p) {
              return '<p>' + p + '</p>';
            }).join('') + '</div>' +
          '</div>' +
        '</div>' +

        (cls && cls.skills.length
          ? '<div class="quiz-skills"><p class="eyebrow">What you will be pressing</p>' +
            '<ul class="skill-list">' + cls.skills.map(function (s) {
              return '<li class="skill"><strong>' + esc(s.name) + '</strong><p>' +
                     esc(s.text) + '</p></li>';
            }).join('') + '</ul></div>'
          : '') +

        '<div class="quiz-alt">' +
          '<p class="eyebrow">If that one does not grab you</p>' +
          '<p>Try <a href="classes/' + esc(r.alt ? r.alt.slug : '') + '.html"><b>' +
            esc(r.arch.alt) + '</b></a>' +
            (r.alt ? '. ' + esc(r.alt.summary) : '.') + '</p>' +
        '</div>' +

        '<div class="quiz-actions">' +
          (cls ? '<a class="btn -primary" href="classes/' + esc(cls.slug) + '.html">Read the full class</a>' : '') +
          '<button class="btn -ghost" id="quizImage" type="button">Save as image</button>' +
          '<button class="btn -ghost" id="quizCopy" type="button">Copy for Discord</button>' +
          '<button class="btn -quiet" id="quizAgain" type="button">Take it again</button>' +
        '</div>' +
      '</div>';

    $('quizAgain').addEventListener('click', function () {
      step = -1; answers = []; result = null; render();
      window.scrollTo(0, 0);
    });
    $('quizCopy').addEventListener('click', function () { copyResult(this); });
    $('quizImage').addEventListener('click', function () { saveImage(this); });

    var url = shareUrl();
    if (history.replaceState) history.replaceState(null, '', url);
  }

  function render() {
    if (step < 0) return renderIntro();
    if (step >= QUESTIONS.length && result) return renderResult();
    renderQuestion();
  }

  /* ------------------------------------------------------------------ share */

  function shareUrl() {
    return location.origin + location.pathname + '?r=' + encodeURIComponent(result.arch.pair);
  }

  function copyResult(btn) {
    var r = result;
    var lines = [
      '**' + r.arch.name + '**',
      '_' + r.arch.motto + '_',
      '',
      'Nightmare RO says I should play **' + (r.cls ? r.cls.name : r.arch.pick) + '**' +
        (r.cls ? ' (' + r.cls.family + ' line, tier ' + r.cls.tier + ')' : '') + '.',
      'Second choice: ' + r.arch.alt + '.',
      '',
      'Find yours: <' + location.origin + location.pathname + '>'
    ];
    copy(lines.join('\n'), btn, 'Copied');
  }

  function copy(text, btn, done) {
    var flash = function () {
      var old = btn.dataset.label || btn.textContent;
      btn.dataset.label = old;
      btn.textContent = done;
      setTimeout(function () { btn.textContent = btn.dataset.label; }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(flash, function () { legacy(text, flash); });
    } else {
      legacy(text, flash);
    }
  }

  function legacy(text, done) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); done(); } catch (e) {}
    document.body.removeChild(ta);
  }

  /* ------------------------------------------------------- the shareable png */

  function loadImage(src) {
    return new Promise(function (res, rej) {
      var im = new Image();
      im.onload = function () { res(im); };
      im.onerror = rej;
      im.src = src;
    });
  }

  function wrap(ctx, text, maxWidth) {
    var words = text.split(' ');
    var lines = [];
    var line = '';
    words.forEach(function (w) {
      var test = line ? line + ' ' + w : w;
      if (ctx.measureText(test).width > maxWidth && line) {
        lines.push(line);
        line = w;
      } else {
        line = test;
      }
    });
    if (line) lines.push(line);
    return lines;
  }

  function saveImage(btn) {
    var r = result;
    var W = 1200, H = 630;
    var c = document.createElement('canvas');
    c.width = W; c.height = H;
    var ctx = c.getContext('2d');

    var jobs = [loadImage('assets/img/logo.png')];
    if (r.cls && r.cls.art) jobs.push(loadImage(r.cls.art));

    Promise.all(jobs).then(function (imgs) {
      var logo = imgs[0], art = imgs[1];

      ctx.fillStyle = '#07060a';
      ctx.fillRect(0, 0, W, H);

      var glow = ctx.createRadialGradient(W * 0.72, H * 0.5, 20, W * 0.72, H * 0.5, 460);
      glow.addColorStop(0, 'rgba(232,17,43,0.42)');
      glow.addColorStop(1, 'rgba(232,17,43,0)');
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, W, H);

      if (art) {
        var ah = 560;
        var aw = art.width * (ah / art.height);
        ctx.globalAlpha = 0.96;
        ctx.drawImage(art, W - aw - 40, H - ah - 10, aw, ah);
        ctx.globalAlpha = 1;
      }

      // left column, over a soft scrim so text stays readable
      var scrim = ctx.createLinearGradient(0, 0, W * 0.72, 0);
      scrim.addColorStop(0, 'rgba(7,6,10,0.96)');
      scrim.addColorStop(1, 'rgba(7,6,10,0)');
      ctx.fillStyle = scrim;
      ctx.fillRect(0, 0, W * 0.72, H);

      var lh = logo.height * (72 / logo.width * (logo.width / logo.width));
      var lw = 210;
      lh = logo.height * (lw / logo.width);
      ctx.drawImage(logo, 64, 52, lw, lh);

      var y = 52 + lh + 56;

      ctx.fillStyle = '#ff4d55';
      ctx.font = '500 20px "JetBrains Mono", monospace';
      ctx.fillText('YOUR ARCHETYPE', 64, y);

      y += 56;
      ctx.fillStyle = '#f2eff5';
      ctx.font = '800 58px Outfit, sans-serif';
      wrap(ctx, r.arch.name, 560).forEach(function (l) {
        ctx.fillText(l, 64, y);
        y += 62;
      });

      y += 6;
      ctx.fillStyle = '#a49dae';
      ctx.font = '400 24px Inter, sans-serif';
      wrap(ctx, r.arch.motto, 540).forEach(function (l) {
        ctx.fillText(l, 64, y);
        y += 32;
      });

      y += 34;
      ctx.fillStyle = '#736c7e';
      ctx.font = '500 18px "JetBrains Mono", monospace';
      ctx.fillText('PLAY THIS', 64, y);

      y += 46;
      ctx.fillStyle = '#e8112b';
      ctx.font = '700 44px Outfit, sans-serif';
      ctx.fillText(r.cls ? r.cls.name : r.arch.pick, 64, y);

      ctx.fillStyle = '#736c7e';
      ctx.font = '400 19px Inter, sans-serif';
      ctx.fillText('nightmarero.pages.dev', 64, H - 44);

      c.toBlob(function (blob) {
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'nightmarero-' + (r.cls ? r.cls.slug : 'result') + '.png';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
      }, 'image/png');
    }).catch(function () {
      btn.textContent = 'Could not build the image';
    });
  }

  /* ------------------------------------------------------------------- boot */

  fetch('assets/data/classes-brief.json')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      (data.classes || []).forEach(function (c) { classes[c.name] = c; });
      render();
    })
    .catch(function () {
      root.innerHTML = '<div class="quiz-card"><p class="muted">The test could not load. Try a refresh.</p></div>';
    });
})();
