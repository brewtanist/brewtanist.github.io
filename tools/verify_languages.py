"""Check what GitHub Pages rendered, including localized card text and shared SKU facts."""
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

TAGS = {"th": "th", "en": "en", "zh": "zh-Hans"}
ROUTES = {k: ("" if k == "th" else "/" + k) for k in TAGS}

def verify_languages(build, root, parse):
    native = {p.stem: json.loads(p.read_text()) for p in (root / "_data/brewtanist").glob("*.json")}
    sources = {"th": native}
    for lang in ("en", "zh"):
        sources[lang] = json.loads((root / f"_data/translations/{lang}.json").read_text())
        for section, key in (("marketplace", "items"), ("products", "items"), ("coffee", "cards"),
                             ("gallery", "images"), ("roastery", "steps"), ("faq", "items")):
            ids = lambda rows: sorted(row["id"] for row in rows)
            assert ids(native[section][key]) == ids(sources[lang][section][key]), f"{lang}: review translations for {section}"
    visible = {i["id"]: i for i in native["marketplace"]["items"] if i["visible"]}
    for lang, tag in TAGS.items():
        text = sources[lang]
        for section in ("/", "/shop/", "/oem/", "/admin/"):
            route = ROUTES[lang] + section
            page = parse((build / route.strip("/") / "index.html").read_text(), route)
            assert page.select(tag="html")[0].attrs["lang"] == tag, route
            links = page.select(tag="link")
            canonical = next(x.attrs["href"] for x in links if x.attrs.get("rel") == "canonical")
            assert canonical == "https://brewtanist.github.io" + route, route
            alt = {x.attrs["hreflang"]: urlsplit(x.attrs["href"]).path for x in links if x.attrs.get("hreflang")}
            assert alt == {**{TAGS[k]: v + section for k,v in ROUTES.items()}, "x-default": section}, route
            published = {urlsplit(a.attrs.get("href","")).path for a in page.select(tag="a")}
            assert all(v + section in published for v in ROUTES.values()), f"Missing switch link: {route}"
            if section in ("/", "/shop/"):
                assert ROUTES[lang] + "/oem/" in published, f"Missing OEM entry on {route}"
            main = page.select(tag="main")[0]
            if lang != "th":
                assert not re.search(r"[ก-๛]", main.text()), f"Thai leaked into {route}"
            if section == "/":
                heading = main.select(tag="h1")[0]
                assert ''.join(heading.text().split()) == ''.join(text['home']['hero_title'].split()), route
                profile = next(json.loads(el.text()) for el in page.select(tag="script") if el.attrs.get("type")=="application/ld+json")
                hours = profile['openingHoursSpecification'][0]
                assert (hours["opens"],hours["closes"],profile["telephone"],profile["hasMap"]) == tuple(native["settings"][k] for k in ("opens","closes","phone","maps")), route
            if section != "/shop/":
                continue
            cards = main.select(attribute="data-shop-card")
            translations = {i["id"]: i for i in text["marketplace"]["items"]}
            assert {c.attrs["id"] for c in cards} == {"shop-"+i for i in visible}, route
            for card in cards:
                key = card.attrs["id"].removeprefix("shop-")
                localized = translations[key]
                assert card.select(tag="p")[0].text().strip() == localized["description"], (route,key,'description')
                assert [x.text().strip() for x in card.select(tag="li")] == localized["details"], (route,key,'details')
                product = visible[key]
                target = f"https://shopee.co.th/product/{native['marketplace']['shopId']}/{product['shopeeItemId']}"
                assert all(x.attrs.get("href")==target for x in card.select(tag="a")), (route,key,'link')
                if product.get("image"):
                    im=card.select(tag="img")[0]
                    assert im.attrs.get("src")==product["image"] and im.attrs.get("alt")==localized["alt"], (route,key,'image')
        desk_route = ROUTES[lang] + "/admin/quotes/"
        desk = parse((build / desk_route.strip("/") / "index.html").read_text(), desk_route)
        assert desk.select(tag="html")[0].attrs["lang"] == tag, desk_route
        assert any(el.attrs.get("name") == "robots" and "noindex" in el.attrs.get("content", "") for el in desk.select(tag="meta")), desk_route
        assert {p + "/admin/quotes/" for p in ROUTES.values()} <= {a.attrs.get("href") for a in desk.select(tag="a")}, desk_route
    return len(TAGS) * 5
