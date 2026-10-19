/* Local serif selection. Applied before paint; no storage or remote font service. */
(function () {
  'use strict';
  var choices = { fraunces: 'Fraunces', instrument: 'Instrument Serif', poltawski: 'Półtawski Nowy' };
  var initial = new URL(location.href).searchParams.get('serif');
  if (!Object.prototype.hasOwnProperty.call(choices, initial)) initial = 'poltawski';
  var root = document.documentElement;
  var base = new URL('./', document.currentScript.src);
  var selected = initial;
  var generation = 0;
  var originalLinks = new WeakMap();
  var families = { fraunces: 'Fraunces', instrument: 'Instrument Serif', poltawski: 'Poltawski Nowy' };
  var status, select, panel;
  var message = '';
  var style = document.createElement('link');
  style.rel = 'stylesheet'; style.href = new URL('serif-preview.css', base).href;
  document.head.appendChild(style);

  function say(text) { message = text; if (status) status.textContent = text; }
  function decorate(scope) {
    var links = scope.querySelectorAll('a[href]');
    links.forEach(function (a) {
      if (a.hasAttribute('download') || a.dataset.serifExit !== undefined) return;
      var original = originalLinks.has(a) ? originalLinks.get(a) : a.getAttribute('href');
      var url = new URL(original, document.baseURI);
      if (original.startsWith('#') && url.origin === location.origin && url.pathname === location.pathname) return;
      var explicit = new URL(location.href).searchParams.get('serif');
      if (!Object.prototype.hasOwnProperty.call(choices, explicit)) {
        if (originalLinks.has(a)) a.setAttribute('href', original);
        return;
      }
      if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname)) return;
      var path = url.pathname.slice(base.pathname.length);
      if (!/^(?:index\.html)?$|^(?:observatory|draws)\/(?:index\.html)?$|^records\/[^/]+\.html$|^design\/(?:index\.html)?$/.test(path)) return;
      originalLinks.set(a, original);
      url.searchParams.set('serif', selected);
      if (a.href !== url.href) a.href = url.href;
    });
  }
  function apply(choice, write) {
    selected = choice;
    var ticket = ++generation;
    if (select) select.value = choice;
    if (write) {
      var url = new URL(location.href); url.searchParams.set('serif', choice);
      history.pushState(null, '', url);
    }
    if (panel) decorate(document);
    // Inline variables override the shared no-JavaScript default before rendering.
    root.style.setProperty('--rs-display', '"' + families[choice] + '", Georgia, serif');
    root.style.setProperty('--rs-display-weight', choice === 'fraunces' ? '300' : '400');
    root.style.setProperty('--rs-wordmark-weight', choice === 'fraunces' ? '600' : '400');
    root.style.setProperty('--rs-display-axes', choice === 'fraunces' ? '"SOFT" 100, "WONK" 1' : 'normal');
    root.dataset.serif = choice;
    say(choices[choice] + (choice === 'fraunces' ? ' · original weights' : ' · regular 400'));
    function verifyFont() {
      if (ticket !== generation || !document.fonts) return;
      document.fonts.load((choice === 'fraunces' ? '300' : '400') + ' 16px "' + families[choice] + '"').then(function (faces) {
        if (ticket === generation && !faces.length) say('Font unavailable. Showing a system serif.');
      }).catch(function () { if (ticket === generation) say('Could not load ' + choices[choice] + '. Showing a system serif.'); });
    }
    // Wait for linked @font-face rules, not an early duplicate FontFace request.
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', verifyFont, { once: true });
    else verifyFont();
  }
  apply(initial, false);
  function ready() {
    panel = document.createElement('aside'); panel.className = 'serif-preview'; panel.setAttribute('aria-label', 'Typography selection');
    var label = document.createElement('label'); label.htmlFor = 'serif-preview-choice'; label.textContent = 'Serif font';
    select = document.createElement('select'); select.id = 'serif-preview-choice';
    Object.keys(choices).forEach(function (key) { var option = document.createElement('option'); option.value = key; option.textContent = choices[key]; select.appendChild(option); });
    select.value = selected;
    select.addEventListener('change', function () { apply(select.value, true); });
    status = document.createElement('span'); status.setAttribute('role', 'status'); status.textContent = message;
    var exit = document.createElement('a'); exit.dataset.serifExit = ''; exit.textContent = 'Reset to default';
    function exitURL() { var url = new URL(location.href); url.searchParams.delete('serif'); exit.href = url.href; }
    exitURL(); exit.addEventListener('pointerdown', exitURL); exit.addEventListener('focus', exitURL); exit.addEventListener('click', exitURL);
    panel.append(label, select, status, exit);
    var skip = document.body.querySelector('.skip-link,.skip');
    if (skip && skip.parentNode === document.body) skip.after(panel);
    else document.body.prepend(panel);
    decorate(document);
    new MutationObserver(function (records) {
      if (records.some(function (record) { return Array.from(record.addedNodes).some(function (node) { return node.nodeType === 1; }); })) decorate(document);
    }).observe(document.body, { childList: true, subtree: true });
    window.addEventListener('popstate', function () {
      var choice = new URL(location.href).searchParams.get('serif');
      if (!Object.prototype.hasOwnProperty.call(choices, choice)) choice = 'poltawski';
      apply(choice, false); exitURL();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready);
  else ready();
}());
