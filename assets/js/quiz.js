/* ==========================================================================
   Nightmare RO - "which class are you" test
   --------------------------------------------------------------------------
   Thirteen questions score six traits. The top two traits pick one of fifteen
   archetypes, and the third trait picks which class inside that archetype you
   get, which is what stops half the server sharing a result: 15 archetypes
   times 4 runner-up traits is 45 endings across 43 different classes.

   The class the player used to main only nudges the wording, never the maths,
   so the same answers always land in the same place.
   ========================================================================== */

(function () {
  'use strict';

  /* Ask for our own files under the build stamp the page carries, so a copy
     cached before the last deploy is at an address we never request again.
     i18n.js defines it and is the first script on every page. */
  function fresh(url) {
    return window.NM_FRESH ? window.NM_FRESH(url) : url;
  }

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

  /* Each question is a plain situation with plain answers. Scenery got in the
     way of people understanding what they were picking, so it is gone.

     Every trait is the 3 point answer on the same number of questions, so no
     trait wins by having been offered more often. */

  var QUESTIONS = [
    {
      q: 'How do you like to fight?',
      hint: 'The distance you are comfortable at.',
      a: [
        { t: 'Right on top of it, trading hits.', s: { force: 3, ward: 1 } },
        { t: 'Close, but only when it cannot hit back.', s: { guile: 3, force: 1 } },
        { t: 'From across the screen.', s: { arcane: 3, guile: 1 } },
        { t: 'Wherever the party needs me to stand.', s: { bond: 3, ward: 1 } },
        { t: 'Anywhere, as long as I keep moving.', s: { wild: 3, force: 1 } }
      ]
    },
    {
      q: 'Do you want something fighting alongside you?',
      hint: 'Pets, homunculi, drones, spirits, summons.',
      a: [
        { t: 'Yes. Half my damage should come from it.', s: { arcane: 3, bond: 1 } },
        { t: 'Something small that keeps me alive is enough.', s: { ward: 3, bond: 1 } },
        { t: 'No. I want my own hands on everything.', s: { force: 3, guile: 1 } },
        { t: 'Only if it does something unpredictable.', s: { wild: 3, arcane: 1 } }
      ]
    },
    {
      q: 'A boss is about to start a long, dangerous cast.',
      a: [
        { t: 'Burn everything now and end it before the cast finishes.', s: { force: 3, wild: 1 } },
        { t: 'Interrupt it. That is what my kit is for.', s: { guile: 3, arcane: 1 } },
        { t: 'Take the hit on purpose and keep everyone behind me.', s: { ward: 3, bond: 1 } },
        { t: 'Shout the timer so nobody eats it.', s: { bond: 3, arcane: 1 } },
        { t: 'Do something reckless and hope it breaks the cast.', s: { wild: 3, guile: 1 } }
      ]
    },
    {
      q: 'How many buttons do you want to press?',
      a: [
        { t: 'Two or three, hit very hard.', s: { force: 3, ward: 1 } },
        { t: 'A long combo where the order matters.', s: { guile: 3, arcane: 1 } },
        { t: 'A whole bar of situational tools.', s: { arcane: 3, ward: 1 } },
        { t: 'Whatever is off cooldown. I improvise.', s: { wild: 3, force: 1 } },
        { t: 'A few, as long as the defensive ones are on the bar.', s: { ward: 3, arcane: 1 } }
      ]
    },
    {
      q: 'Your party wipes on the first pull of a raid.',
      a: [
        { t: '"My call. Again, from the top."', s: { bond: 3, ward: 1 } },
        { t: '"The pull order was wrong. Here it is written down."', s: { arcane: 3, bond: 1 } },
        { t: '"I will hold it this time. Just keep hitting."', s: { ward: 3, force: 1 } },
        { t: '"Let me try something stupid."', s: { wild: 3, force: 1 } }
      ]
    },
    {
      q: 'You find a sealed door with no handle and no hinges.',
      a: [
        { t: 'Hit it until it is a doorway.', s: { force: 3, wild: 1 } },
        { t: 'Watch it for a while. Doors like this open on a timer.', s: { guile: 3, ward: 1 } },
        { t: 'Copy the markings down before touching anything.', s: { arcane: 3, guile: 1 } },
        { t: 'Walk into it and find out. That is what HP is for.', s: { wild: 3, force: 1 } }
      ]
    },
    {
      q: 'A champion monster is guarding what you came for. It has not seen you.',
      a: [
        { t: 'Open with everything and end it in ten seconds.', s: { force: 3, wild: 1 } },
        { t: 'Stack every status on it before it takes a step.', s: { guile: 3, arcane: 1 } },
        { t: 'Pull it somewhere better and outlast it.', s: { ward: 3, guile: 1 } },
        { t: 'Wait for the others. This is a group problem.', s: { bond: 3, ward: 1 } }
      ]
    },
    {
      q: 'Someone asks in guild chat, for the fourth time, how refining works.',
      a: [
        { t: 'Answer it again, properly.', s: { bond: 3, ward: 1 } },
        { t: 'Paste the table you wrote months ago.', s: { arcane: 3, bond: 1 } },
        { t: 'Tell them to swing at +10 and find out.', s: { wild: 3, force: 1 } },
        { t: 'Say nothing and go back to farming.', s: { guile: 3, force: 1 } }
      ]
    },
    {
      q: 'One skill point left, two things you want.',
      a: [
        { t: 'The bigger number. Always the bigger number.', s: { force: 3, wild: 1 } },
        { t: 'The one that sets up the other three skills.', s: { guile: 3, arcane: 1 } },
        { t: 'The one that stops you dying at the worst moment.', s: { ward: 3, guile: 1 } },
        { t: 'The one that helps whoever is standing next to you.', s: { bond: 3, ward: 1 } }
      ]
    },
    {
      q: 'Deep in a Nightmare Dungeon the floor itself starts draining your health.',
      a: [
        { t: 'Push faster. Kill it before the floor kills me.', s: { force: 3, wild: 1 } },
        { t: 'Back out and return with the right shadow set.', s: { arcane: 3, ward: 1 } },
        { t: 'Map every safe pocket on the way down.', s: { guile: 3, arcane: 1 } },
        { t: 'Call the group. Nobody goes down there alone.', s: { bond: 3, ward: 1 } }
      ]
    },
    {
      q: 'A boss beats you three times in a row. What changes on the fourth?',
      a: [
        { t: 'My gear. I come back stronger.', s: { force: 3, arcane: 1 } },
        { t: 'My timing. I know its pattern now.', s: { guile: 3, ward: 1 } },
        { t: 'My resistances. It stops being able to kill me.', s: { ward: 3, arcane: 1 } },
        { t: 'My party. I bring people.', s: { bond: 3, force: 1 } },
        { t: 'My whole build. I come back with a different idea.', s: { wild: 3, arcane: 1 } }
      ]
    },
    {
      q: 'What does a good evening on the server look like?',
      a: [
        { t: 'Farming a spot I have down to a routine.', s: { ward: 3, force: 1 } },
        { t: 'Poking at something nobody has figured out yet.', s: { wild: 3, guile: 1 } },
        { t: 'Rebuilding my character around a new idea.', s: { arcane: 3, wild: 1 } },
        { t: 'Whatever the people in voice chat are doing.', s: { bond: 3, wild: 1 } }
      ]
    },
    {
      q: 'Last one. What do you actually enjoy about this?',
      a: [
        { t: 'The moment a health bar disappears.', s: { force: 3, wild: 1 } },
        { t: 'Finding the thing everyone else walked past.', s: { guile: 3, wild: 1 } },
        { t: 'Surviving something that should have killed me.', s: { ward: 3, force: 1 } },
        { t: 'Working out exactly why it works.', s: { arcane: 3, guile: 1 } },
        { t: 'The people. Obviously the people.', s: { bond: 3, ward: 1 } }
      ]
    }
  ];

  /* --------------------------------------------------------- the archetypes */

  /* One per unordered pair of traits, so every combination lands somewhere.

     `by` is the interesting part: it maps the third strongest trait onto a
     class, which is how two people with the same top pair still come out
     somewhere different. `pick` is the fallback if the third trait is missing
     from the map. 43 of the 55 classes are reachable. */

  var ARCHETYPES = [
    { pair: 'force+guile', name: 'The Red Verdict',
      motto: 'You do not threaten. You conclude.',
      body: 'You open fights you have already decided the end of. Bleed, break, finish, and be somewhere else before the body lands.',
      pick: 'Lord Knight',
      by: { ward: 'Lord Knight', arcane: 'Assassin Cross', wild: 'Guillotine Cross', bond: 'Rune Knight' } },

    { pair: 'force+ward', name: 'The Bulwark Oath',
      motto: 'The line holds because you are standing on it.',
      body: 'You go in first, stay in longest, and treat your own health bar as a resource rather than a warning.',
      pick: 'Royal Guard',
      by: { guile: 'Paladin', arcane: 'Rune Knight', wild: 'Lord Knight', bond: 'Royal Guard' } },

    { pair: 'arcane+force', name: 'The Rune-Bitten',
      motto: 'You wrote the spell on the blade yourself.',
      body: 'Muscle bores you and theory alone is not enough. You want a toolbox you built, carved into something heavy.',
      pick: 'Rune Knight',
      by: { guile: 'Sorcerer', ward: 'Rune Knight', wild: 'Warlock', bond: 'Sage' } },

    { pair: 'force+wild', name: 'The Dawn Fist',
      motto: 'Momentum is a defensive stat if you commit hard enough.',
      body: 'You close distance for a living. Nothing you do is subtle and nothing you do is slow.',
      pick: 'Sura',
      by: { guile: 'Guillotine Cross', ward: 'Champion', arcane: 'Star Gladiator', bond: 'Sura' } },

    { pair: 'bond+force', name: 'The Standing Order',
      motto: 'Someone has to go first. It may as well be you.',
      body: 'You lead from the front, and the buff you leave behind matters as much as the hit you land.',
      pick: 'Paladin',
      by: { guile: 'Royal Guard', ward: 'Paladin', arcane: 'Crusader', wild: 'Star Emperor' } },

    { pair: 'guile+ward', name: 'The Far Quiet',
      motto: 'The best position is the one nothing reaches.',
      body: 'You would rather set the board than be on it. Traps, spacing, patience, and a very long sightline.',
      pick: 'Ranger',
      by: { force: 'Sniper', arcane: 'Ranger', wild: 'Hunter', bond: 'Sniper' } },

    { pair: 'arcane+guile', name: 'The Twin Smoke',
      motto: 'Two things happened. You only saw one.',
      body: 'You like layered rotations where the setup is invisible and the payoff is not survivable.',
      pick: 'Maboroshi',
      by: { force: 'Night Watch', ward: 'Kagemusha', wild: 'Maboroshi', bond: 'Shadow Chaser' } },

    { pair: 'guile+wild', name: 'The Sixth Shadow',
      motto: 'If it is not nailed down it is a build option.',
      body: 'You steal, copy, misdirect and improvise. Nobody, including you, knows what you will do next.',
      pick: 'Shadow Chaser',
      by: { force: 'Stalker', ward: 'Rogue', arcane: 'Shadow Chaser', bond: 'Rebel' } },

    { pair: 'bond+guile', name: 'The Whispered Ledger',
      motto: 'Everything is chemistry, including people.',
      body: 'You keep the party alive with things you brewed yourself, and you keep a quiet list of what everyone owes you.',
      pick: 'Biochemist',
      by: { force: 'Geneticist', ward: 'Biochemist', arcane: 'Alchemist', wild: 'Geneticist' } },

    { pair: 'arcane+ward', name: 'The Long Study',
      motto: 'You have read what is about to happen.',
      body: 'You want to understand the fight more than you want to win it quickly, and that understanding is what keeps you upright.',
      pick: 'Scholar',
      by: { force: 'Sage', guile: 'Scholar', wild: 'High Wizard', bond: 'Sorcerer' } },

    { pair: 'ward+wild', name: 'The Iron Improviser',
      motto: 'It held. Do not ask how.',
      body: 'You build the answer on site out of whatever is lying around, then armour it badly and use it anyway.',
      pick: 'Mechanic',
      by: { force: 'Mastersmith', guile: 'Mechanic', arcane: 'Blacksmith', bond: 'Mastersmith' } },

    { pair: 'bond+ward', name: 'The Kept Flame',
      motto: 'Nobody drops while you are watching.',
      body: 'You measure a good run by how few times anyone needed you, and you are always there the moment they do.',
      pick: 'Arch Bishop',
      by: { force: 'High Priest', guile: 'Priest', arcane: 'Arch Bishop', wild: 'High Priest' } },

    { pair: 'arcane+wild', name: 'The Hollow Chorus',
      motto: 'You called something and it answered.',
      body: 'Big, strange, expensive magic. You want the screen to go quiet and then very much not quiet.',
      pick: 'Warlock',
      by: { force: 'High Wizard', guile: 'Soul Reaper', ward: 'Wizard', bond: 'Warlock' } },

    { pair: 'arcane+bond', name: 'The Star-Reader',
      motto: 'You borrowed the sky and gave it to a friend.',
      body: 'Your power lands on other people. You read the situation, then hand someone else the answer.',
      pick: 'Soul Ascetic',
      by: { force: 'Star Emperor', guile: 'Soul Linker', ward: 'Soul Ascetic', wild: 'Sky Emperor' } },

    { pair: 'bond+wild', name: 'The Road Song',
      motto: 'The party plays better when you are in the room.',
      body: 'You are the reason a bad run is still a good night. Everything you do lands on someone else and comes back louder.',
      pick: 'Minstrel/Wanderer',
      by: { force: 'Clown/Gypsy', guile: 'Minstrel/Wanderer', ward: 'Bard and Dancer', arcane: 'Clown/Gypsy' } }
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

  /* Ties used to fall back on the alphabet, which quietly handed every close
     result to arcane and bond. Break them on conviction instead: how many
     answers touched the trait at all, then which one you picked first. */

  function breadth() {
    var n = { force: 0, guile: 0, ward: 0, arcane: 0, wild: 0, bond: 0 };
    var first = {};
    answers.forEach(function (pick, i) {
      var add = QUESTIONS[i].a[pick].s;
      for (var k in add) {
        n[k]++;
        if (first[k] == null) first[k] = i;
      }
    });
    return { count: n, first: first };
  }

  function ranked(s) {
    var b = breadth();
    return Object.keys(s).sort(function (a, b2) {
      if (s[b2] !== s[a]) return s[b2] - s[a];
      if (b.count[b2] !== b.count[a]) return b.count[b2] - b.count[a];
      var fa = b.first[a] == null ? 99 : b.first[a];
      var fb = b.first[b2] == null ? 99 : b.first[b2];
      if (fa !== fb) return fa - fb;
      return a.localeCompare(b2);
    });
  }

  function decide() {
    scores = tally();
    var order = ranked(scores);
    var key = pairKey(order[0], order[1]);
    var arch = ARCHETYPES.filter(function (x) { return x.pair === key; })[0] || ARCHETYPES[0];
    var old = OLD_CLASSES.filter(function (x) { return x.v === oldClass; })[0] || OLD_CLASSES[0];

    /* the third trait decides which class inside the archetype you get */
    var third = order[2];
    var pickName = (arch.by && arch.by[third]) || arch.pick;
    var cls = classes[pickName] || null;

    /* the runner up is the archetype's other most common ending, and it is
       never the same class as the one you were just given */
    var others = [];
    for (var t in (arch.by || {})) {
      if (arch.by[t] !== pickName && others.indexOf(arch.by[t]) === -1) {
        others.push(arch.by[t]);
      }
    }
    if (arch.pick !== pickName && others.indexOf(arch.pick) === -1) {
      others.unshift(arch.pick);
    }
    var altName = others[0] || arch.pick;
    var alt = classes[altName] || null;

    var sameFamily = old.family && cls && cls.family === old.family;

    return {
      arch: arch, cls: cls, alt: alt, altName: altName, old: old, order: order,
      third: third, sameFamily: sameFamily,
      why: buildWhy(arch, cls, old, order, sameFamily)
    };
  }

  function buildWhy(arch, cls, old, order, sameFamily) {
    var out = [];
    var t1 = TRAITS[order[0]].label, t2 = TRAITS[order[1]].label;

    var t3 = TRAITS[order[2]].label;
    out.push('Your answers leaned hardest on <b>' + t1 + '</b> and <b>' + t2 +
             '</b>, which is what this archetype is built around. <b>' + t3 +
             '</b> came third, and that is what narrowed it to ' +
             esc(cls ? cls.name : arch.pick) + ' rather than the others in the same bracket.');

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
        '<p class="eyebrow">' + QUESTIONS.length + ' ' + ui('count') + '</p>' +
        '<h2>' + esc(ui('title')) + '</h2>' +
        '<p class="muted">' + esc(ui('lede')) + '</p>' +
        '<label class="quiz-label" for="oldClass">' + esc(ui('mainedLabel')) + '</label>' +
        '<select id="oldClass">' +
          OLD_CLASSES.map(function (o) {
            return '<option value="' + esc(o.v) + '">' + esc(o.v || o.label) + '</option>';
          }).join('') +
        '</select>' +
        '<p class="dim">' + esc(ui('mainedNote')) + '</p>' +
        '<button class="btn -primary -lg -block" id="quizStart" type="button">' + esc(ui('begin')) + '</button>' +
      '</div>';

    $('quizStart').addEventListener('click', function () {
      oldClass = $('oldClass').value;
      step = 0;
      render();
    });
  }

  function renderQuestion() {
    var q = question(step);
    root.innerHTML =
      '<div class="quiz-card">' +
        progress() +
        '<p class="eyebrow">' + ui('question') + ' ' + (step + 1) + ' ' + ui('of') + ' ' + QUESTIONS.length + '</p>' +
        '<h2 class="quiz-q">' + esc(q.q) + '</h2>' +
        (q.hint ? '<p class="quiz-hint">' + esc(q.hint) + '</p>' : '') +
        '<div class="quiz-answers">' +
          q.a.map(function (a, i) {
            return '<button class="quiz-answer" type="button" data-i="' + i + '">' +
                     esc(a.t) + '</button>';
          }).join('') +
        '</div>' +
        (step > 0 ? '<button class="btn -quiet -sm quiz-back" id="quizBack" type="button">' + esc(ui('back')) + '</button>' : '') +
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
      return '<li><span>' + esc(traitLabel(k)) + '</span>' +
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
          '<p class="eyebrow">' + esc(ui('archetype')) + '</p>' +
          '<h2>' + esc(r.arch.name) + '</h2>' +
          '<p class="quiz-motto">' + esc(r.arch.motto) + '</p>' +
          '<p class="muted">' + esc(r.arch.body) + '</p>' +
          traitBars() +
        '</div>' +

        /* Sharing sits here, above the fold, because people were screenshotting
           the page rather than scrolling to the bottom for these. */
        '<div class="quiz-share">' +
          '<button class="btn -primary" id="quizImageCopy" type="button">' + esc(ui('copyImage')) + '</button>' +
          '<button class="btn -ghost" id="quizImage" type="button">' + esc(ui('saveImage')) + '</button>' +
          '<button class="btn -ghost" id="quizCopy" type="button">' + esc(ui('copyText')) + '</button>' +
        '</div>' +

        '<div class="quiz-pick">' +
          (cls && cls.art
            ? '<div class="quiz-art"><img src="' + esc(cls.art) + '" alt="' + esc(cls.name) + '"></div>'
            : '') +
          '<div class="quiz-pick-body">' +
            '<p class="eyebrow">' + esc(ui('playThis')) + '</p>' +
            '<h3>' + esc(cls ? cls.name : r.arch.pick) + '</h3>' +
            (cls ? '<p class="tag -accent">' +
                   esc(ui('line').replace('{f}', cls.family)) +
                   '<span aria-hidden="true"> · </span>' +
                   ui('tier') + ' ' + cls.tier + '</p>' : '') +
            '<div class="quiz-why">' + r.why.map(function (p) {
              return '<p>' + p + '</p>';
            }).join('') + '</div>' +
          '</div>' +
        '</div>' +

        (cls && cls.skills.length
          ? '<div class="quiz-skills"><p class="eyebrow">' + esc(ui('pressing')) + '</p>' +
            '<ul class="skill-list">' + cls.skills.map(function (s) {
              return '<li class="skill"><strong>' + esc(s.name) + '</strong><p>' +
                     esc(s.text) + '</p></li>';
            }).join('') + '</ul></div>'
          : '') +

        '<div class="quiz-alt">' +
          '<p class="eyebrow">' + esc(ui('notGrab')) + '</p>' +
          '<p>' + esc(ui('tryThis')) + ' <a href="classes/' + esc(r.alt ? r.alt.slug : '') + '.html"><b>' +
            esc(r.altName) + '</b></a>' +
            (r.alt ? '. ' + esc(r.alt.summary) : '.') + '</p>' +
        '</div>' +

        '<div class="quiz-actions">' +
          (cls ? '<a class="btn -primary" href="classes/' + esc(cls.slug) + '.html">' + esc(ui('readClass')) + '</a>' : '') +
          '<button class="btn -quiet" id="quizAgain" type="button">' + esc(ui('again')) + '</button>' +
        '</div>' +
      '</div>';

    $('quizAgain').addEventListener('click', function () {
      step = -1; answers = []; result = null; render();
      window.scrollTo(0, 0);
    });
    $('quizCopy').addEventListener('click', function () { copyResult(this); });
    $('quizImage').addEventListener('click', function () { saveImage(this); });
    $('quizImageCopy').addEventListener('click', function () { copyImage(this); });

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
      'Second choice: ' + r.altName + '.',
      '',
      'Find yours: <' + location.origin + location.pathname + '>'
    ];
    copy(lines.join('\n'), btn, ui('copiedText'));
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

  /* Draws the share card and hands back a PNG blob. Both the download button
     and the copy to clipboard button run through this. */
  function buildCard() {
    var r = result;
    var W = 1200, H = 630;
    var c = document.createElement('canvas');
    c.width = W; c.height = H;
    var ctx = c.getContext('2d');

    var jobs = [loadImage('assets/img/logo.png')];
    if (r.cls && r.cls.art) jobs.push(loadImage(r.cls.art));

    return Promise.all(jobs).then(function (imgs) {
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

      return new Promise(function (res) {
        c.toBlob(function (blob) { res(blob); }, 'image/png');
      });
    });
  }

  function flashLabel(btn, text) {
    if (!btn.dataset.label) btn.dataset.label = btn.textContent;
    btn.textContent = text;
    setTimeout(function () { btn.textContent = btn.dataset.label; }, 1800);
  }

  function saveImage(btn) {
    buildCard().then(function (blob) {
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'nightmarero-' +
                   (result.cls ? result.cls.slug : 'result') + '.png';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
    }).catch(function () {
      flashLabel(btn, ui('imageFailed'));
    });
  }

  /* Straight onto the clipboard as an image, so it can be pasted into Discord
     without ever touching the downloads folder. Browsers that cannot do that
     get the download instead, which is the same end result with one more
     step. */
  function copyImage(btn) {
    var canCopy = window.ClipboardItem && navigator.clipboard &&
                  navigator.clipboard.write;
    if (!canCopy) return saveImage(btn);

    buildCard().then(function (blob) {
      var item = new ClipboardItem({ 'image/png': blob });
      return navigator.clipboard.write([item]);
    }).then(function () {
      flashLabel(btn, ui('copied'));
    }).catch(function () {
      saveImage(btn);
    });
  }

  /* --------------------------------------------------------------- language

     English lives in this file. The other languages are one JSON per locale
     under assets/quiz/, fetched the first time that language is picked and
     then kept. Only the wording is swapped, never the scoring, so a French
     player and an English player answering the same way get the same class.

     Class names and skill names stay in English on purpose, the same as
     everywhere else on the site, because that is how they read in game. */

  var EN = {
    ui: {
      count: 'questions',
      title: 'Which one of these are you, really?',
      lede: 'Every skill tree on this server was rewritten, so the class you mained for years might not be the class that fits you any more. Straight questions about how you like to play, no wrong answers, one suggestion at the end.',
      mainedLabel: 'What did you main before?',
      mainedNote: 'Only used to word the result. It does not change which class you get.',
      begin: 'Begin',
      question: 'Question',
      of: 'of',
      back: 'Back',
      archetype: 'Your archetype',
      playThis: 'Play this',
      pressing: 'What you will be pressing',
      notGrab: 'If that one does not grab you',
      tryThis: 'Try',
      readClass: 'Read the full class',
      again: 'Take it again',
      copyImage: 'Copy image for Discord',
      saveImage: 'Save as image',
      copyText: 'Copy as text',
      copied: 'Copied, paste it in Discord',
      copiedText: 'Copied',
      imageFailed: 'Could not build the image',
      loadFailed: 'The test could not load. Try a refresh.',
      line: '{f} line',
      tier: 'Tier'
    }
  };

  var lang = 'en';
  var packs = { en: EN };

  function T() { return packs[lang] || EN; }
  function ui(key) { return (T().ui && T().ui[key]) || EN.ui[key] || key; }

  function question(i) {
    var base = QUESTIONS[i];
    var tr = (T().questions || [])[i];
    if (!tr) return base;
    return {
      q: tr.q || base.q,
      hint: tr.hint || base.hint,
      a: base.a.map(function (a, n) {
        return { t: (tr.a && tr.a[n]) || a.t, s: a.s };
      })
    };
  }

  function traitLabel(key) {
    return (T().traits && T().traits[key]) || TRAITS[key].label;
  }

  function loadPack(code) {
    if (packs[code]) return Promise.resolve();
    return fetch(fresh('assets/quiz/' + code + '.json'))
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) { if (data) packs[code] = data; })
      .catch(function () {});
  }

  document.addEventListener('nm:lang', function (e) {
    var code = e.detail.lang;
    loadPack(code).then(function () {
      lang = packs[code] ? code : 'en';
      if (classes && Object.keys(classes).length) render();
    });
  });

  /* ------------------------------------------------------------------- boot */

  fetch(fresh('assets/data/classes-brief.json'))
    .then(function (r) { return r.json(); })
    .then(function (data) {
      (data.classes || []).forEach(function (c) { classes[c.name] = c; });
      var current = window.NM_I18N && window.NM_I18N.current;
      if (current && current !== 'en') {
        return loadPack(current).then(function () {
          if (packs[current]) lang = current;
          render();
        });
      }
      render();
    })
    .catch(function () {
      root.innerHTML = '<div class="quiz-card"><p class="muted">' +
                       ui('loadFailed') + '</p></div>';
    });
})();
