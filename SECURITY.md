# Security maintenance

## Scope and checks (26 November 2026)

The public storefront is **https://brewtanist.github.io/** on GitHub Pages/Jekyll. The configured OEM intake is a separate Sites Worker at **https://brewtanist-oem-requests.pumplcrs.chatgpt.site**. Public quote-desk pages are local tools; only the backend can authorize access to stored customer requests.

Confirmed before this change: HTTPS redirect and HSTS on the storefront; an early restrictive meta CSP; consent-gated analytics; anonymous API collection access denied; staff inbox returns 401 without identity; a foreign Origin gets 403. The backend code has an owner allowlist, server-side schema/type/length checks, a 16 KiB streaming body limit, same-origin checks on deletion, private no-store responses, exact-origin/window checks for the quotation handoff, and keyed hourly rate counters with idempotent retry handling. Backend input, authorization, rate and replay tests use synthetic local data only.

The backend counter permits 12 new requests/hour per pseudonymous bucket, with a 16-bit hash prefix and a shared fallback when ingress identity is missing. It is abuse mitigation, not a dedicated WAF or exact per-person limit. Verify trusted ingress identity at the platform boundary. Authenticated identity headers must only be supplied by the Sites ingress, never an untrusted direct origin. Runtime secrets and client data remain in the private service; do not copy them here.

## Repository controls added

- Checksum-verified Gitleaks 8.30.1 checks all fetched Git refs and the current files on pull requests, main pushes and weekly. Output is redacted. On a finding, rotate/revoke the credential first; do not paste it into a public issue.
- Dependabot reviews GitHub Actions versions weekly. The storefront has no npm/pip application dependency manifest; Jekyll/Pages is provider-managed. Review and test update PRs instead of automatically merging them.
- Local environment files, common private-key files, logs and backup bundles are ignored. This is an accident-prevention measure, not access control or secret deletion.
- Source backups are made after successful scanning on main pushes and weekly. Each Git bundle is verified by a fresh mirror restore and HEAD comparison, retained as an Actions artifact for 30 days. Keep independent copies in a private backup location.

## Release and rollback

Open a PR and wait for Security checks and source backup plus Verify Brewtanist Jekyll storefront to pass before merging changes affecting templates/configuration. GitHub Pages is currently branch-published; CI is **not** an enforced deployment gate unless repository branch rules require it. Preserve the CMS and its editing workflow when configuring protection.

Rollback by reverting the change through a tested PR. Backend versions have their own Sites rollback and must retain the same project, audience and R2 binding. The pre-change backend was version 4; keep it available before publishing a new version. Source rollback does not roll back customer data.

## Monitoring and remaining account controls

Existing daily storefront monitoring and weekly bounded OEM access/CORS checks are retained. GitHub schedules may be delayed; enable Actions failure notifications in the owner's account and add independent uptime alerts if immediate detection is required. A successful monitor is not a penetration test.

Still requires account/platform access and is **not asserted as completed**:

- MFA/passkeys on the GitHub owners, Pages CMS sign-in identity and the ChatGPT/Sites owner; private recovery codes and least-privilege collaborators. Browser code cannot enforce these account settings.
- GitHub secret scanning/push protection and protected-main requirements. Verify these in repository settings.
- WAF/custom response headers for GitHub Pages: a `github.io` subdomain cannot be placed into the user's own DNS zone. Use a verified custom domain and authorized edge provider, or migrate after staging and DNS rollback review. HTML meta CSP cannot enforce anti-framing response headers. The unused Render blueprint does not prove an active deployment.
- Private OEM/R2 data backup, encrypted destination, retention and restore drill. Current source backups do **not** contain customer requests, runtime secrets or platform configuration. No live customer data was downloaded or copied in this audit.

Do not treat CSP, CORS, client form validation or hiding admin links as authentication. Never store customer requests, access tokens, recovery codes or passwords in this public repository.
