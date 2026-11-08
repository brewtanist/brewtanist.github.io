'use strict';
// The full catalogue is server-rendered. Search and filters only refine the view.
(() => {
  const grid = document.querySelector('[data-shop-grid]');
  if (!grid) return;
  const cards = [...grid.querySelectorAll('[data-shop-card]')];
  const controls = document.querySelector('[data-shop-controls]');
  const filters = [...document.querySelectorAll('[data-filter]')];
  const search = document.querySelector('#shop-search');
  const result = document.querySelector('[data-result-count]');
  const empty = document.querySelector('[data-shop-empty]');
  const reset = document.querySelector('[data-shop-reset]');
  const categories = new Set(filters.map(button => button.dataset.filter));
  const normalise = value => value.normalize('NFKC').toLocaleLowerCase('th').replace(/\s+/g, ' ').trim();
  const entries = cards.map(card => ({card, search: normalise(card.dataset.search || '')}));
  let category = 'all';
  let query = '';

  function readLocation() {
    const params = new URLSearchParams(window.location.search);
    category = categories.has(params.get('category')) ? params.get('category') : 'all';
    query = (params.get('q') || '').slice(0, 120);
    search.value = query;
  }

  function render(updateLocation = false) {
    const terms = normalise(query).split(' ').filter(Boolean);
    let count = 0;
    for (const entry of entries) {
      const show = (category === 'all' || entry.card.dataset.category === category)
        && terms.every(term => entry.search.includes(term));
      entry.card.hidden = !show;
      if (show) count += 1;
    }
    for (const button of filters) button.setAttribute('aria-pressed', String(button.dataset.filter === category));
    result.textContent = count + ' รายการ' + (category !== 'all' || query ? ' จาก ' + cards.length : '');
    empty.hidden = count !== 0;
    reset.hidden = category === 'all' && !query;
    if (updateLocation) {
      const url = new URL(window.location.href);
      if (category === 'all') url.searchParams.delete('category');
      else url.searchParams.set('category', category);
      if (query) url.searchParams.set('q', query);
      else url.searchParams.delete('q');
      window.history.replaceState(null, '', url);
    }
  }

  function clear() {
    category = 'all';
    query = '';
    search.value = '';
    render(true);
    search.focus({preventScroll: true});
  }
  filters.forEach(button => button.addEventListener('click', () => { category = button.dataset.filter; render(true); }));
  search.addEventListener('input', () => { query = search.value; render(true); });
  reset.addEventListener('click', clear);
  document.querySelector('[data-shop-clear]').addEventListener('click', clear);
  window.addEventListener('popstate', () => { readLocation(); render(); });
  readLocation();
  render();
  controls.hidden = false;
})();
