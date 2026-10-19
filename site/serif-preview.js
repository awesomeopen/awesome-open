/* Explicit, URL-only typography comparison. No storage, analytics or remote fonts. */
(function () {
  'use strict';
  var choices = { fraunces: 'Fraunces', instrument: 'Instrument Serif', poltawski: 'Półtawski Nowy' };
  var initial = new URL(location.href).searchParams.get('serif');
  if (!Object.prototype.hasOwnProperty.call(choices, initial)) return;
  var root = document.documentElement;
  var base = new URL('./', document.currentScript.src);
  var selected = initial;
  var generation = 0;
  var loaded = {};
  var status, select, panel;
  var message = '';
  var style = document.createElement('link');
  style.rel = 'stylesheet'; style.href = new URL('serif-preview.css', base).href;
  document.head.appendChild(style);

  function say(text) { message = text; if (status) status.textContent = text; }
  function reset() {
    ['--rs-display', '--rs-display-weight', '--rs-wordmark-weight', '--rs-display-axes'].forEach(function (key) { root.style.removeProperty(key); });
    delete root.dataset.serif;
  }
  function decorate(scope) {
    var links = scope.querySelectorAll('a[href]');
    links.forEach(function (a) {
      if (a.hasAttribute('download') || a.dataset.serifExit !== undefined) return;
      var url = new URL(a.getAttribute('href'), document.baseURI);
      if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname)) return;
      var path = url.pathname.slice(base.pathname.length);
      if (!/^(?:index\.html)?$|^(?:observatory|spotlight)\/(?:index\.html)?$|^records\/[^/]+\.html$|^design\/(?:index\.html)?$/.test(path)) return;
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
    if (choice === 'fraunces') { reset(); say('Fraunces · original weights'); return; }
    reset();
    say('Loading ' + choices[choice] + '…');
    if (!window.FontFace || !document.fonts) { say('Font loading unavailable. Showing Fraunces.'); return; }
    if (!loaded[choice]) {
      var face = new FontFace('Preview ' + choice, 'url("' + new URL('vendor/serif-preview/' + choice + '.woff2', base).href + '")', { weight: '400', style: 'normal' });
      loaded[choice] = face.load().then(function (font) { document.fonts.add(font); return font; }).catch(function (error) { delete loaded[choice]; throw error; });
    }
    loaded[choice].then(function () {
      if (ticket !== generation) return;
      root.style.setProperty('--rs-display', '"Preview ' + choice + '", Georgia, serif');
      root.style.setProperty('--rs-display-weight', '400');
      root.style.setProperty('--rs-wordmark-weight', '400');
      root.style.setProperty('--rs-display-axes', 'normal');
      root.dataset.serif = choice;
      say(choices[choice] + ' · regular 400');
    }).catch(function () { if (ticket === generation) { reset(); say('Could not load ' + choices[choice] + '. Showing Fraunces.'); } });
  }
  apply(initial, false);
  function ready() {
    panel = document.createElement('aside'); panel.className = 'serif-preview'; panel.setAttribute('aria-label', 'Typography preview');
    var label = document.createElement('label'); label.htmlFor = 'serif-preview-choice'; label.textContent = 'Serif preview';
    select = document.createElement('select'); select.id = 'serif-preview-choice';
    Object.keys(choices).forEach(function (key) { var option = document.createElement('option'); option.value = key; option.textContent = choices[key]; select.appendChild(option); });
    select.value = selected;
    select.addEventListener('change', function () { apply(select.value, true); });
    status = document.createElement('span'); status.setAttribute('role', 'status'); status.textContent = message;
    var exit = document.createElement('a'); exit.dataset.serifExit = ''; exit.textContent = 'Exit preview';
    function exitURL() { var url = new URL(location.href); url.searchParams.delete('serif'); exit.href = url.href; }
    exitURL(); exit.addEventListener('pointerdown', exitURL); exit.addEventListener('focus', exitURL); exit.addEventListener('click', exitURL);
    panel.append(label, select, status, exit); document.body.prepend(panel);
    decorate(document);
    new MutationObserver(function (records) {
      if (records.some(function (record) { return Array.from(record.addedNodes).some(function (node) { return node.nodeType === 1; }); })) decorate(document);
    }).observe(document.body, { childList: true, subtree: true });
    window.addEventListener('popstate', function () {
      var choice = new URL(location.href).searchParams.get('serif');
      if (!Object.prototype.hasOwnProperty.call(choices, choice)) { location.reload(); return; }
      apply(choice, false); exitURL();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready);
  else ready();
}());
