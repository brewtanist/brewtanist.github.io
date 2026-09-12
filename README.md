# The Brewtanist — Cafe & Coffee Roaster

About us: the Brewtanist informational website, published at **https://brewtanist.github.io/**.

## Edit the website

- Thai editing guide: https://brewtanist.github.io/admin/
- Editor: https://app.pagescms.org/
- In Pages CMS select organization **brewtanist**, repository **brewtanist.github.io**, branch **main**.
- Pages CMS needs its own GitHub App access to this organization and repository. Its permission is separate from ChatGPT's GitHub connection.
- Saving on main publishes to the live website after a successful GitHub Pages build.
- Edit the seven Thai-labeled forms; no HTML editing is needed for normal text and image changes.
- Do not keep editing the previous personal-account repository: it is not synchronized to this repository.

## Maintenance

Content: `_data/brewtanist/*.json`. CMS definition: `.pages.yml`.
Homepage template: `index.html`. CSS/JS: `brewtanist/site.css`, `brewtanist/site.js`.
Images: `brewtanist/assets/`. Image paths intentionally retain this directory for CMS compatibility.
Canonical, Open Graph URL and business structured data point to the new brand root URL.
Sitemap: https://brewtanist.github.io/sitemap.xml

The owner's latest content was migrated from source commit `70202b9492d3846ae07c06cd391d373867252f6a`; the seven JSON files and images were copied without changing their content.
The former ZIP-mirror workflow was not copied. The import workflow is one-time and refuses to overwrite an existing website.

Public informational website only. No checkout, personal account system, database, analytics tracker, or font binaries added. See EDITING.md for maintenance details.
