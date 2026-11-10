"""Rebuild the café's responsive AVIF photos with Pillow 13.0 and PyYAML.

Run python3 tools/build_cafe_photos.py after replacing a listed JPEG in place.
For new CMS paths the templates display the uploaded original immediately. Add
the path and desired pixel widths to _data/photo_widths.yml to optimize it.
"""

from io import BytesIO
from pathlib import Path

import yaml
from PIL import Image, ImageCms, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "brewtanist/assets/photos"


def generate():
    widths_by_url = yaml.safe_load((ROOT / "_data/photo_widths.yml").read_text())
    DEST.mkdir(parents=True, exist_ok=True)
    for url, widths in widths_by_url.items():
        source = ROOT / url.lstrip("/")
        with Image.open(source) as photo:
            image = ImageOps.exif_transpose(photo)
            profile = image.info.get("icc_profile")
            if profile:
                image = ImageCms.profileToProfile(
                    image, ImageCms.ImageCmsProfile(BytesIO(profile)),
                    ImageCms.createProfile("sRGB"), outputMode="RGB"
                )
            else:
                image = image.convert("RGB")

            for width in widths:
                if width <= 0 or width > image.width:
                    raise ValueError(f"{source.name}: width {width} exceeds the useful range 1–{image.width}")
                height = round(image.height * width / image.width)
                frame = image.resize((width, height), Image.Resampling.LANCZOS)
                encoded = BytesIO()
                frame.save(encoded, "AVIF", quality=62, speed=6, max_threads=2,
                           icc_profile=b"", exif=b"", xmp=b"")
                target = DEST / f"{source.stem}-{width}.avif"
                content = encoded.getvalue()
                if not target.exists() or target.read_bytes() != content:
                    target.write_bytes(content)


if __name__ == "__main__":
    generate()
