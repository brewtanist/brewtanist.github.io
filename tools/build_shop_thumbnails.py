"""Rebuild small shop-card WebPs after replacing a source JPG (requires Pillow)."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json

from PIL import Image, ImageCms, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SHOP = ROOT / "brewtanist/assets/shop"
DEST = SHOP / "thumbs"
DEST.mkdir(exist_ok=True)
manifest = {}
for path in sorted(SHOP.glob("*.jpg")):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        if image.info.get("icc_profile"):
            image = ImageCms.profileToProfile(
                image, ImageCms.ImageCmsProfile(BytesIO(image.info["icc_profile"])),
                ImageCms.createProfile("sRGB"), outputMode="RGB")
        else:
            image = image.convert("RGB")
        candidates = []
        for target in sorted({min(image.width, width) for width in (480, 800)}):
            thumb = image.resize((target, round(image.height * target / image.width)), Image.Resampling.LANCZOS)
            encoded = BytesIO()
            thumb.save(encoded, format="WEBP", quality=82, method=6, icc_profile=b"", exif=b"")
            data = encoded.getvalue()
            filename = f"{path.stem}-{target}-{sha256(data).hexdigest()[:8]}.webp"
            dest = DEST / filename
            dest.write_bytes(data)
            candidates.append(f"/{dest.relative_to(ROOT).as_posix()} {target}w")
        manifest["/" + path.relative_to(ROOT).as_posix()] = ", ".join(candidates)
(ROOT / "_data/shop_thumbnails.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"Generated responsive images for {len(manifest)} shop images.")
