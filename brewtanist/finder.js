'use strict';
(() => {
  const root = document.querySelector('[data-coffee-finder]');
  const form = root?.querySelector('[data-finder-form]');
  const result = root?.querySelector('[data-finder-result]');
  const staticLinks = root?.querySelector('[data-finder-static]');
  if (!root || !form || !result || !staticLinks) return;

  let copy, products;
  try {
    copy = JSON.parse(document.getElementById('coffee-finder-copy').textContent);
    products = JSON.parse(document.getElementById('coffee-finder-products').textContent);
    if (!Array.isArray(products) || products.some(p => !p.id || !Array.isArray(p.tasteTags) || !Array.isArray(p.drinkTags))) return;
  } catch {
    // Keep server-rendered category links if configuration is invalid.
    return;
  }

  const title = result.querySelector('[data-finder-result-title]');
  const lead = result.querySelector('[data-finder-result-lead]');
  const items = result.querySelector('[data-finder-result-items]');
  const beanQuestions = [...form.querySelectorAll('[data-finder-bean-question]')];
  const choice = key => form.querySelector('input[name="' + key + '"]:checked')?.value;

  function syncQuestions() {
    const beans = !choice('format') || choice('format') === 'beans';
    for (const question of beanQuestions) {
      question.hidden = !beans;
      question.disabled = !beans;
    }
  }

  function addText(tag, className, content, parent) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = content;
    parent.append(element);
    return element;
  }

  function addShopLink(parent, text, href, external = false) {
    const link = addText('a', 'finder-result-link', text, parent);
    link.href = href;
    if (external) {
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
    }
    return link;
  }

  function rank(taste, drink) {
    return products.map((product, index) => {
      const tasteMatch = taste !== 'unsure' && product.tasteTags.includes(taste);
      const drinkMatch = drink !== 'unsure' && product.drinkTags.includes(drink);
      return { product, index, score: (tasteMatch ? 3 : 0) + (drinkMatch ? 2 : 0) };
    }).filter(match => match.score > 0).sort((a, b) => b.score - a.score || a.index - b.index);
  }

  function show() {
    items.replaceChildren();
    const format = choice('format');
    const taste = choice('taste') || 'unsure';
    const drink = choice('drink') || 'unsure';

    if (format === 'capsules' || format === 'drip') {
      title.textContent = format === 'capsules' ? copy.category_capsules : copy.category_drip;
      lead.textContent = copy.category_lead;
      const category = format === 'capsules' ? 'capsules' : 'drip';
      addShopLink(items, copy.category_link, location.pathname + '?category=' + category + '#catalog');
    } else {
      const ranked = rank(taste, drink);
      const unsure = taste === 'unsure' && drink === 'unsure';
      const shown = unsure || ranked.length === 0
        ? products.map(product => ({product}))
        : ranked.slice(0, 3);
      title.textContent = unsure || ranked.length === 0 ? copy.all_title : copy.result_title;
      lead.textContent = unsure || ranked.length === 0 ? copy.all_lead : copy.result_lead;
      for (const {product} of shown) {
        const card = document.createElement('article');
        card.className = 'finder-match';
        addText('h4', '', product.name, card);
        addText('p', 'finder-match-notes', product.notes, card);
        addText('p', '', product.description, card);
        if (typeof product.url === 'string' && /^https:\/\/shopee\.co\.th\//.test(product.url)) {
          addShopLink(card, copy.view_shopee, product.url, true);
        }
        items.append(card);
      }
    }
    form.hidden = true;
    result.hidden = false;
    title.focus({preventScroll: true});
    result.scrollIntoView({block: 'nearest', behavior: 'auto'});
  }

  form.addEventListener('change', syncQuestions);
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    show();
  });
  root.querySelector('[data-finder-restart]').addEventListener('click', () => {
    form.reset();
    syncQuestions();
    result.hidden = true;
    form.hidden = false;
    items.replaceChildren();
    form.querySelector('input[name="format"]').focus({preventScroll: true});
  });
  syncQuestions();
  staticLinks.hidden = true;
  form.hidden = false;
})();
