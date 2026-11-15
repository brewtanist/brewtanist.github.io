# Brewtanist — SEO + Conversion Measurement (15 November 2026)

## Production state

The website remains on `https://brewtanist.github.io/` and keeps Jekyll, GitHub Pages, Shop, OEM, Pages CMS and its three languages. No paid tracking service is activated.

**Analytics is deliberately OFF** in `_data/brewtanist/analytics.json`:

```json
{"enabled": false, "measurement_id": ""}
```

There is no GA4 property ID verified for this site. This configuration does not send analytics events, set analytics cookies or load a Google tag. It also hides consent controls.

## Measurement design

If the site owner later supplies a VERIFIED GA4 Measurement ID and approves the customer-facing privacy notice, enable analytics through a reviewed code change. On first visit, the website asks for consent in Thai, English or Chinese before loading any Google script. The visitor can decline or change a stored choice using the footer settings control.

| Event | Meaning | Trigger |
|---|---|---|
| `page_view` | Page viewed | After analytics consent, with origin + path only (no query or fragment) |
| `shop_outbound` | Click to Shopee | A click on a Shopee link; numeric item ID only if available |
| `directions_click` | Click to Google Maps | A Maps link, not an arrival at the café |
| `contact_click` | Click phone/email/social/LINE | Contact intent, not a completed call or message |
| `finder_complete` | Coffee Finder answered | Format choice only (beans, capsules or drip) |
| `generate_lead` | OEM request received | ONLY when the existing RFQ endpoint confirms a matching receipt |

Events NEVER include a customer's name, email, phone, RFQ reference, search query, free-text response, or full destination URL. Payment and purchases are on Shopee and are NOT measured as a website conversion here. GA4 may also auto-collect outbound `click` events with Enhanced Measurement; do not sum them with `shop_outbound` as two independent buyers.

The script uses **basic consent mode**. It does not request gtag.js until the visitor accepts, and revoking consent reloads the page without the tag. This is a technical consent mechanism; the owner remains responsible for the final privacy policy, retention and legal compliance.

## Activation gates

1. Confirm ownership of the GA4 property and its `G-...` Measurement ID. Do not guess it, and do not place private tokens in the public GitHub repository.
2. Review the privacy notice, data retention and rights process with the owner. Confirm Google Analytics collection is appropriate for this business.
3. Update `_data/brewtanist/analytics.json` to `enabled: true` and the verified public Measurement ID on a separate branch/PR.
4. Verify consent decisions, the tag, and events in GA4 DebugView (with browser consent). Check website traffic and referral attribution before claiming conversion data.
5. If the owner has not approved these steps, keep `enabled: false` and leave the ID empty.

## Local SEO

- Google Business Profile: the website, phone, hours, business name and location should be checked against the owner-controlled profile. Avoid editing fields if the latest value cannot be read; never infer the subdistrict from secondary listings.
- The website currently publishes LocalBusiness JSON-LD, multilingual canonical / hreflang tags, a nine-URL sitemap, robots.txt and real product-to-Shopee links.
- The LocalBusiness entity `@id` and `url` should consistently point to the brand-root website, with linked official socials and Shopee store.
- Google Search Console should be set up directly with the owner's Google account, then submit `https://brewtanist.github.io/sitemap.xml`. No claim is made here that the property is verified or URLs are indexed.

## Tests

The `Verify Brewtanist Jekyll storefront` workflow compiles the exact GitHub Pages site, validates links/metadata, then uses a test-only dummy measurement ID for browser tests. The dummy ID never reaches production. Tests include rejection, acceptance, withdrawal, no calls before opt-in, localization, a Shop click, Coffee Finder and a **mocked** OEM receipt. No real OEM request or GA4 transmission is made in tests.
