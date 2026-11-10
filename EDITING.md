# Brewtanist — editing and maintenance

## Owner entry points
- Website: https://brewtanist.github.io/
- Thai editing guide: https://brewtanist.github.io/admin/
- Content editor: https://app.pagescms.org/

First use requires the owner to sign in to Pages CMS with GitHub and grant its GitHub App access to this repository. ChatGPT's GitHub connection does not grant Pages CMS access. Select only this repository, not all repositories. Do not paste credentials into chat or commit tokens.

## Architecture
- Jekyll reads `_data/brewtanist/*.json` and renders root `index.html` on the existing GitHub Pages build.
- `.pages.yml` defines eight Thai-labeled forms and a media library.
- Text is HTML-escaped by Liquid. External link output accepts HTTPS or local absolute paths only.
- Production content and JSON-LD are generated as HTML; website visitors do not need client-side JavaScript to read them.
- Images are served from `/brewtanist/assets/`. Do not hotlink private Drive URLs.
- Bai Jamjuree (Thai and Latin), Lexend and MuseoModerno are served locally as WOFF2. License files are next to them in `brewtanist/fonts/`.
- Save to `main` publishes through the existing Pages deployment. There is no independent draft system or one-click WYSIWYG live preview in this configuration.
- No checkout, user accounts, payment collection or analytics trackers were added.

## Content
`home.json`: hero, story, visit; optional `hero_image_side` = `left` or `right` (default).
`settings.json`: business info, hours, social links and SEO. Opening-hour FAQ and JSON-LD use the same values. `days` must match the human-readable `opening_days` label. The optional legacy `phone_link` key is unused; the call link is derived from `phone`.
`coffee.json`: menu/category cards; `products.json`: product renders; `roastery.json`: roasting narrative with optional real photo; `gallery.json`: image list; `faq.json`: additional questions.

Content defaults were adapted from the previous website and the owner's confirmed cash/PromptPay/QR payment information. Existing blend tasting profiles were carried over, not revalidated against live stock. The prior social collage remains in the gallery list with visibility off, and can be re-enabled. No roasting-process photo has been invented or substituted.

## Editing images
Use the CMS image picker to upload or reuse files. Do not delete an image used by another section. Use `position` / image position fields to change crop focus: center/top/bottom/left/right. Product renders use contain rather than cover. Uploaded images are public; only upload approved brand assets.

For an updated photograph, upload it under a new filename so the CMS uses that original immediately. For shop JPGs, run `python3 tools/build_shop_thumbnails.py` (Pillow) and commit the generated WebP files and `_data/shop_thumbnails.json`. The browser uses an available thumbnail size and retains the original as a fallback.

## Rollback
Pre-redesign snapshot: branch `backup/brewtanist-before-cms-20260912`, commit `eaa0bf79085471f9923b2f98136d204620d3325d`.
Prefer reverting only the affected content file through a new commit. Do not force-push or delete the repository. The original website in the personal repository was left unchanged during migration.

## Legacy workflow caution
The old ZIP-mirror workflow was deliberately not copied. Use Pages CMS on brewtanist/brewtanist.github.io, branch main. The migration workflow is one-time and refuses to overwrite an existing site.

## Verify after saving
Check the latest `pages build and deployment` run, load `/`, inspect the changed section, verify image paths, mobile layout, and Google Maps/phone/Shopee links. Pages CMS owner login and image-upload flow must be completed/tested in the owner's browser.

Docs: https://pagescms.org/docs/quick-start/ ; https://pagescms.org/docs/configuration/ ; https://jekyllrb.com/docs/datafiles/


## Brand repository
Production repository: brewtanist/brewtanist.github.io. Sign in as pumplcrs-hub, but select the brewtanist organization and this repository in Pages CMS. Its GitHub App needs separate access to the organization. Do not continue editing the old personal repository. Asset paths remain /brewtanist/assets intentionally.

## Presentation languages

The customer homepage, shop and public editing guide each have Thai, English and Simplified Chinese URLs. Thai uses the original paths; English starts with `/en/`, Chinese with `/zh/`. Each edition is rendered by Jekyll, including metadata and product listings. The language switch works without JavaScript; with JavaScript it also retains the visitor's current search, category and fragment.

Edit Thai copy and shared business facts in `_data/brewtanist/`. Edit the corresponding text in `_data/translations/en.json` and `zh.json`, UI strings in `_data/ui/`, and the public editing guide in `_data/admin_guide.yml`. Translation records match stable IDs, not positions in a list. Keep existing IDs when changing or reordering a card, gallery image, FAQ or roast step. New entries need the same unique ID in Thai and in both translations. Change the photo, stock visibility, opening hours or SKU only in the Thai data; all languages read these values directly from the same records.

Run `python3 tools/test_storefront.py _site` after building. It checks all nine localized pages, equivalent language links and the exact link, description and artwork of every visible shop item. Hosted services such as Shopee, Google Maps, GitHub and Pages CMS use their own language settings.
