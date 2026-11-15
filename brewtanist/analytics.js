'use strict';
(() => {
  const node = document.getElementById('brewtanist-analytics-config');
  if (!node) return;
  let settings;
  try {
    settings = JSON.parse(node.textContent);
  } catch {
    return;
  }

  const id = typeof settings.measurementId === 'string' ? settings.measurementId.trim() : '';
  const enabled = settings.enabled === true && /^G-[A-Z0-9]{6,20}$/.test(id);
  const allowed = new Set(['shop_outbound', 'directions_click', 'contact_click', 'finder_complete', 'generate_lead']);
  const storageKey = 'brewtanist-analytics-consent-v1';
  let granted = false;
  let loaded = false;

  // Never send a URL, form content, email, phone number, RFQ reference, or arbitrary user text.
  function eventParams(name, data) {
    const params = {};
    if (name === 'shop_outbound' && /^[0-9]{1,24}$/.test(String(data.item_id || ''))) {
      params.item_id = String(data.item_id);
    }
    if (name === 'contact_click' && ['phone', 'email', 'facebook', 'instagram', 'tiktok', 'line'].includes(data.method)) {
      params.contact_method = data.method;
    }
    if (name === 'finder_complete' && ['beans', 'capsules', 'drip'].includes(data.coffee_type)) {
      params.coffee_type = data.coffee_type;
    }
    if (name === 'generate_lead') params.lead_source = 'oem_form';
    return params;
  }

  function track(name, data = {}) {
    if (!enabled || !granted || !allowed.has(name) || typeof window.gtag !== 'function') return false;
    window.gtag('event', name, eventParams(name, data));
    return true;
  }
  window.BrewtanistAnalytics = Object.freeze({track});
  if (!enabled) return;

  const copy = settings.copy || {};
  const text = (key, fallback) => typeof copy[key] === 'string' && copy[key] ? copy[key] : fallback;
  const state = () => {
    try { return localStorage.getItem(storageKey); } catch { return null; }
  };
  const remember = choice => {
    try { localStorage.setItem(storageKey, choice); } catch { /* Consent applies to this page only. */ }
  };

  function startAnalytics() {
    if (loaded) return;
    loaded = true;
    granted = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    // Basic consent mode: the Google script is not requested before acceptance.
    window.gtag('consent', 'default', {
      analytics_storage: 'denied', ad_storage: 'denied',
      ad_user_data: 'denied', ad_personalization: 'denied'
    });
    window.gtag('js', new Date());
    window.gtag('consent', 'update', {analytics_storage: 'granted'});
    window.gtag('config', id, {
      send_page_view: false,
      allow_google_signals: false,
      allow_ad_personalization_signals: false
    });
    // Exclude free-text searches, referral codes and other query parameters from page_location.
    window.gtag('event', 'page_view', {
      page_location: location.origin + location.pathname,
      page_title: document.title
    });
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
    document.head.append(script);
  }

  const banner = document.createElement('aside');
  banner.className = 'brew-analytics-banner';
  banner.setAttribute('role', 'region');
  banner.setAttribute('aria-label', text('label', 'Website statistics'));
  banner.hidden = true;
  const message = document.createElement('p');
  message.textContent = text('message', 'Allow anonymous site usage statistics with Google Analytics?');
  banner.append(message);
  const controls = document.createElement('div');
  controls.className = 'brew-analytics-actions';
  const button = (label, callback) => {
    const element = document.createElement('button');
    element.type = 'button';
    element.textContent = label;
    element.addEventListener('click', callback);
    controls.append(element);
    return element;
  };

  function decide(choice) {
    remember(choice);
    banner.hidden = true;
    if (choice === 'granted') {
      startAnalytics();
    } else if (loaded) {
      // Reload without loading the Google tag, including after consent is revoked.
      location.reload();
    }
  }
  button(text('decline', 'No thanks'), () => decide('denied'));
  button(text('accept', 'Allow statistics'), () => decide('granted')).className = 'brew-analytics-accept';
  banner.append(controls);
  document.body.append(banner);

  const footer = document.querySelector('.footer-bottom');
  if (footer) {
    const manage = document.createElement('button');
    manage.type = 'button';
    manage.className = 'brew-analytics-manage';
    manage.textContent = text('manage', 'Statistics settings');
    manage.addEventListener('click', () => {
      banner.hidden = false;
      banner.querySelector('button')?.focus();
    });
    footer.append(manage);
  }
  const saved = state();
  if (saved === 'granted') startAnalytics();
  else if (saved !== 'denied') banner.hidden = false;

  document.addEventListener('click', event => {
    const anchor = event.target.closest?.('a[href]');
    if (!anchor) return;
    const href = anchor.getAttribute('href') || '';
    if (/^tel:/i.test(href)) return track('contact_click', {method: 'phone'});
    if (/^mailto:/i.test(href)) return track('contact_click', {method: 'email'});
    let url;
    try { url = new URL(href, location.href); } catch { return; }
    const host = url.hostname.toLowerCase();
    if (host === 'shopee.co.th' || host.endsWith('.shopee.co.th')) {
      const match = url.pathname.match(/^\/product\/\d+\/(\d+)\/?$/);
      return track('shop_outbound', {item_id: match ? match[1] : ''});
    }
    if (host === 'maps.google.com' || host === 'maps.app.goo.gl' ||
        ((host === 'www.google.com' || host === 'google.com') && url.pathname.startsWith('/maps'))) {
      return track('directions_click');
    }
    const destinations = [
      ['facebook.com', 'facebook'], ['instagram.com', 'instagram'],
      ['tiktok.com', 'tiktok'], ['lin.ee', 'line'], ['line.me', 'line']
    ];
    for (const [domain, method] of destinations) {
      if (host === domain || host.endsWith('.' + domain)) {
        return track('contact_click', {method});
      }
    }
  });
})();
