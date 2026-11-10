'use strict';
// All business content is rendered by Jekyll; JavaScript only enhances navigation/layout.
const menu = document.querySelector('.mobile-nav');
if (menu) {
  menu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => { menu.open = false; }));
}
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || event.defaultPrevented) return;
  const submenu = document.activeElement?.closest('.coffee-menu[open]');
  const disclosure = submenu || (menu?.open ? menu : null);
  if (!disclosure) return;
  event.preventDefault();
  disclosure.open = false;
  disclosure.querySelector('summary').focus();
});
// Optional desktop image-side control. Mobile always keeps the headline first.
const leftHero = document.querySelector('.hero-grid.image-left .hero-visual');
if (leftHero) {
  const desktop = window.matchMedia('(min-width: 801px)');
  const placeHero = () => { leftHero.style.order = desktop.matches ? '-1' : ''; };
  placeHero();
  if (desktop.addEventListener) desktop.addEventListener('change', placeHero);
  else desktop.addListener(placeHero);
}

// Warm the other customer page only on pointer/keyboard intent. Native links
// stay usable without JavaScript and no background prefetch runs on page load.
(() => {
  const connection = navigator.connection;
  if (connection?.saveData || /(^|-)2g$/.test(connection?.effectiveType || '')) return;
  const next = location.pathname === '/' ? '/shop/' : '/';
  let requested = false;
  const warm = event => {
    if (requested || (event.type === 'pointerover' && event.pointerType !== 'mouse')) return;
    const anchor = event.target.closest?.('a[href]');
    if (!anchor || anchor.origin !== location.origin || anchor.pathname !== next) return;
    const hint = document.createElement('link');
    if (!hint.relList.supports('prefetch')) return;
    requested = true;
    hint.rel = 'prefetch';
    hint.href = anchor.pathname + anchor.search;
    document.head.append(hint);
  };
  document.addEventListener('focusin', warm);
  document.addEventListener('pointerover', warm, {passive: true});
})();
