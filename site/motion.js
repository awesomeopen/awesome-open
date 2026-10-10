/* Optional GSAP motion. Static content, native scrolling and controls work without it. */
(function () {
  'use strict';
  if (!window.gsap || !window.ScrollTrigger || !window.matchMedia) return;
  var gsap = window.gsap;
  gsap.registerPlugin(window.ScrollTrigger);
  var media = gsap.matchMedia();
  media.add('(min-width: 901px) and (prefers-reduced-motion: no-preference)', function () {
    var sheets = gsap.utils.toArray('.observation-sheet');
    var room = document.querySelector('.reading-room');
    var intro = document.querySelector('.reading-intro');
    if (!room || !intro || sheets.length < 2) return;
    // The editorial title holds while independent observation sheets pass it.
    window.ScrollTrigger.create({trigger: room, start: 'top 100px', end: 'bottom bottom', pin: intro, pinSpacing: false, invalidateOnRefresh: true});
    sheets.slice(0, -1).forEach(function (sheet, i) {
      // Paper-sheet stacking: no content is hidden, removed or moved out of tab order.
      gsap.to(sheet, {scale: 0.96, rotate: i % 2 ? 1 : -1, ease: 'none', scrollTrigger: {trigger: sheet, start: 'top 150px', end: 'bottom 150px', scrub: true, pin: true, pinSpacing: false, invalidateOnRefresh: true}});
    });
    gsap.to('.prefix-flora', {rotation: 20, ease: 'none', scrollTrigger: {trigger: '.hero', start: 'top top', end: 'bottom top', scrub: 0.7}});
  });
  // matchMedia automatically reverts every pin/tween when motion preferences change.
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { window.ScrollTrigger.refresh(); });
})();
