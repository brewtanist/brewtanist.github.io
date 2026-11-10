"""Exercise language switches with one fictional order. Never send a request or email."""
import argparse
import json
import mimetypes
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
LANGS = {"th": "th", "en": "en", "zh": "zh-Hans"}
ORIGIN = "https://brewtanist.github.io"


def dictionary(group, lang):
    return json.loads((ROOT / "_data" / group / (lang + ".json")).read_text())


def switch(page, lang):
    menu = page.locator("[data-language-menu]")
    menu.locator("summary").click()
    menu.locator(f'[hreflang="{LANGS[lang]}"]').click()
    expect(page.locator("html")).to_have_attribute("lang", LANGS[lang])


def download(page, selector):
    with page.expect_download() as out:
        page.locator(selector).click()
    return json.loads(Path(out.value.path()).read_text())


def products(page):
    return page.locator("[data-shop-card]:visible").evaluate_all(
        "cards => cards.map(c => [c.id, c.querySelector('.shop-buy').href])")


def run(page, engine, pdf_dir):
    page.goto(ORIGIN + "/", wait_until="domcontentloaded")
    for lang in ("en", "zh", "th"):
        switch(page, lang)
        expect(page.locator("#visit")).to_contain_text("WiFi")
    page.locator('.collection-links a[href*="category=single-origin"]').click()
    field = page.locator("#shop-search")
    field.fill(dictionary("ui", "th")["single-origin"])
    matches = products(page)
    assert matches, "Thai search did not find a single origin"
    for lang in ("en", "zh", "th"):
        switch(page, lang)
        expect(page.locator('[data-filter="single-origin"]')).to_have_attribute("aria-pressed", "true")
        assert products(page) == matches, f"Different products after switch to {lang}"
    page.locator("[data-shop-reset]").click()
    selected = products(page)
    for lang in ("zh", "en", "th"):
        switch(page, lang)
        assert products(page) == selected, f"SKU or Shopee destination changed in {lang}"
        data = (json.loads((ROOT/"_data/brewtanist/marketplace.json").read_text()) if lang == "th"
                else dictionary("translations", lang)["marketplace"])
        names = {"shop-" + item["id"]: item["name"] for item in data["items"]}
        for sku, _ in selected:
            expect(page.locator(f"#{sku} h3")).to_have_text(names[sku])
    if not page.locator('.nav-links a[href="/oem/"]').is_visible():
        page.locator(".mobile-nav>summary").click()
    page.locator('header a[href="/oem/"]:visible').first.click()
    page.locator('[name="productType"][value="both"]').check()
    values = {"beanQuantity": "12.5", "packGrams": "250", "capsuleQuantity": "240", "perBox": "10",
              "name": "DEMO", "company": "QA SAMPLE", "email": "qa@example.invalid"}
    for key, value in values.items():
        page.locator(f'[name="{key}"]').fill(value)
    page.locator('[name="roast"]').select_option("medium")
    switch(page, "en")
    for key, value in values.items():
        expect(page.locator(f'[name="{key}"]')).to_have_value(value)
    page.locator("#oem-form button[type=submit]").click()
    ref = page.locator("#oem-ref").inner_text()
    assert ref
    for lang in ("en", "zh", "th"):
        if lang != "en":
            switch(page, lang)
        expect(page.locator("#oem-review")).to_be_visible()
        expect(page.locator("#oem-ref")).to_have_text(ref)
        form = dictionary("oem_form", lang)
        summary = page.locator("#oem-summary").input_value()
        assert all(s in summary for s in [ref, form["beans"], form["capsules"], form["kg"], form["units"], "12.5", "240"])
        brief = download(page, "#oem-download")
        assert brief["reference"] == ref and brief["products"]["beans"]["quantityKg"] == 12.5
        assert brief["products"]["capsules"]["quantityUnits"] == 240 and brief["contact"]["company"] == "QA SAMPLE"

    page.goto(ORIGIN + "/admin/", wait_until="domcontentloaded")
    page.locator('a[href="/admin/quotes/"]').click()
    expect(page.locator("#quote-app")).to_be_visible()
    page.locator("#file").set_input_files({"name":"demo.json","mimeType":"application/json","buffer":json.dumps(brief).encode()})
    expect(page.locator('[name="rfq"]')).to_have_value(ref)
    page.locator('[name="number"]').fill("DEMO-LANGUAGE-QA")
    prices = page.locator('#lines input[step=".01"]')
    prices.nth(0).fill("320.50")
    prices.nth(1).fill("8.75")
    page.locator('[name="discount"]').fill("106.25")
    page.locator('[name="taxRate"]').fill("7")
    page.evaluate("window.print = () => window.dispatchEvent(new Event('beforeprint'))")
    for lang in ("en", "zh", "th"):
        page.locator(f'#ui-locales [data-lang="{lang}"]').click()
        labels = dictionary("quote_desk", lang)
        assert [v.input_value() for v in prices.all()] == ["320.50","8.75"]
        assert labels["beans"] == dictionary("oem_form", lang)["beans"]
        assert labels["capsules"] == dictionary("oem_form", lang)["capsules"]
        expect(page.locator("#totals dd").last).to_contain_text("6,420.00")
        page.locator('[name="doclang"]').select_option(lang)
        page.locator("#print").click()
        page.emulate_media(media="print")
        doc = page.locator("#document")
        expect(doc).to_have_attribute("lang", LANGS[lang])
        expect(doc.locator("h1")).to_have_text(labels["quotation"])
        rows = doc.locator("tbody tr")
        for i, (product, qty, unit, price, subtotal) in enumerate([
            ("beans", "12.5", "kg", "320.50", "4,006.25"), ("capsules", "240", "capsule", "8.75", "2,100.00")]):
            fields = rows.nth(i).locator("td")
            expect(fields.nth(0)).to_contain_text(labels[product])
            assert [" ".join(x.inner_text().split()) for x in fields.all()[1:]] == [qty, labels[unit], price, subtotal]
        amounts = doc.locator(".doc-money dd").all_inner_texts()
        for value, amount in zip(["6,106.25", "106.25", "420.00", "6,420.00"], amounts, strict=True):
            assert value in amount and labels["baht"] in amount, (lang, amount)
        if engine == "chromium":
            page.evaluate("document.fonts.ready")
            raw = page.pdf(format="A4", prefer_css_page_size=True)
            pdf = PdfReader(BytesIO(raw))
            assert len(pdf.pages) == 1, f"{lang}: example should fit one A4 page"
            written = pdf.pages[0].extract_text()
            assert all(s in written for s in ["DEMO-LANGUAGE-QA", "4,006.25", "2,100.00", "6,106.25", "106.25", "420.00", "6,420.00"]), (lang, written)
            if pdf_dir:
                (pdf_dir / f"quotation-{lang}.pdf").write_bytes(raw)
        page.emulate_media(media="screen")
    print(f"{engine}: {len(selected)} products, {len(matches)} preserved search results, one request, three quotations at THB 6,420.00", flush=True)


def main():
    args = argparse.ArgumentParser(description=__doc__)
    source = args.add_mutually_exclusive_group(required=True)
    source.add_argument("--build", type=Path)
    source.add_argument("--live", action="store_true")
    args.add_argument("--pdf-dir", type=Path)
    options = args.parse_args()
    if options.pdf_dir:
        options.pdf_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        for engine, width in [("chromium", 390), ("webkit", 1440)]:
            browser = getattr(pw, engine).launch()
            page = browser.new_page(viewport={"width":width, "height":900}, locale="en-US")
            errors, writes = [], []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            def route(r):
                url = urlsplit(r.request.url)
                if r.request.method not in ("GET","HEAD"):
                    writes.append(url.path)
                    return r.abort()
                if options.build and url.netloc == "brewtanist.github.io":
                    file = options.build / url.path.lstrip("/")
                    if file.is_dir():
                        file = file / "index.html"
                    if file.is_file():
                        return r.fulfill(path=str(file), content_type=mimetypes.guess_type(file)[0] or "application/octet-stream")
                    return r.abort()
                return r.continue_() if options.live and url.netloc == "brewtanist.github.io" else r.abort()
            page.route("**/*", route)
            run(page, engine, options.pdf_dir)
            assert not errors and not writes, (errors, writes)
            browser.close()


if __name__ == "__main__":
    main()
