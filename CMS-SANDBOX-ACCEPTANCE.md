# Brewtanist — Pages CMS owner acceptance (isolated QA branch)

**Status:** A branch and CI checks can be prepared by GitHub. Actual Pages CMS login, authenticated Save and image upload are **not** verified until the owner completes the steps below. No public shop product, business fact or production content is changed for this test.

## Safety boundary

| Resource | Branch | What happens |
| --- | --- | --- |
| Live website | `main` | A successful Pages build publishes the actual customer site |
| CMS acceptance | `qa/pages-cms-owner-check` | Save writes to this separate branch; GitHub Actions validates the Jekyll output, but this branch is **not** the selected production Pages source |

**Note:** Both branches belong to a public GitHub repository. Uploaded images and text on the QA branch can still be viewed in GitHub. Use only non-sensitive, owner-approved images and a clearly artificial test caption. Never upload a customer RFQ, phone numbers, credentials or private files.

## Owner test: one short session

1. Sign in at <https://app.pagescms.org/> with a GitHub account that can edit `brewtanist/brewtanist.github.io`. If the GitHub App requests installation, authorize **only** that repository under the `brewtanist` organization. ChatGPT's GitHub connection is separate and does not sign you into Pages CMS.
2. In Pages CMS select `brewtanist/brewtanist.github.io`, then **confirm the branch selector is `qa/pages-cms-owner-check`**, not `main`. If the QA branch cannot be selected, stop here—do not create a new CMS configuration or test by saving on `main`.
3. Open **01 · หน้าบนและเรื่องราว**. Change only the optional **ข้อความเพิ่มเติมใต้คำแนะนำร้าน (ถ้ามี)** field (`home.json > hero_caption`) to `CMS QA TEST — 2026-11-17`. Press **Save**. Refresh the editor and make sure the text persists. This is a disposable QA-only text change, not customer-facing copy.
4. Open the media picker and upload one **non-sensitive, owned JPG/PNG/WebP** with a filename containing `cms-qa` (for example, a photo of a blank mug). Confirm it appears in the media library and the new file is committed to `brewtanist/assets/` on the **QA branch**. If testing how an image field changes a card, do so only in this branch. Do not use a customer's photo or a private receipt.
5. In GitHub, check the QA branch's commit history and the latest [Verify Brewtanist Jekyll storefront](https://github.com/brewtanist/brewtanist.github.io/actions/workflows/storefront-check.yml) run for `qa/pages-cms-owner-check`. Confirm it **passes**. A passed CI proves that the saved content built; it does not prove every image was personally approved.
6. Open <https://brewtanist.github.io/> and confirm the live hero has **not** gained the `CMS QA TEST` caption. Compare the `main` commit history with the QA changes; the new test commit must be only on the QA branch.
7. In the **QA branch**, restore the original caption to an empty string and delete the disposable `cms-qa` image from the branch if possible. Confirm the cleanup commit and rerun validation. Do **not** merge the QA branch into `main`—its test content is intentionally disposable.

## Evidence to record in Issue #6

Record the date, whether Pages CMS opened the repository, whether the QA branch could be selected, whether Save survived a refresh, whether the image appeared, the QA commit hash, the CI result, and whether the live site stayed unchanged. **Do not** paste passwords, tokens, visitor information, or screenshots containing private data.

## After acceptance

Once the owner has approved the real content and the CMS test is complete, edit **`main`** intentionally and verify the GitHub Pages deployment plus mobile/desktop output. For the two missing Shop images, use **matching, seller-approved photographs** of `thailand-ban-huay-khanum` and `everyday-bucket-bag`. Do not invent photos or substitute another SKU's packaging.

The OEM Staff Inbox and actual RFQ delivery require a **separate authenticated and owner-approved test**. No Pages CMS acceptance step here accesses that service or sends customer information.
