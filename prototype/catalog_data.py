"""Validate GitHub-backed draft products. Never writes production or makes network calls."""
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from decimal import Decimal
import base64
import io
import json
import re
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IDS = {'plantman', 'ozmo', 'lazybug'}
OPTIONAL = ('price', 'sizes', 'grinding', 'origin', 'productUrl')
REQUIRED = ('id', 'name', 'profile', 'notes', 'image', 'alt', 'theme')
Image.MAX_IMAGE_PIXELS = 40_000_000

def image_path(value, root=ROOT, owned=False):
    if not isinstance(value, str) or not value or '\\' in value or '%' in value:
        raise ValueError('รูปสินค้า: ใช้ไฟล์จากคลังรูปเท่านั้น')
    parts = PurePosixPath(value).parts
    if '..' in parts or urlsplit(value).scheme or value.startswith('//'):
        raise ValueError('รูปสินค้า: ไม่อนุญาตลิงก์ภายนอกหรือเส้นทางย้อนกลับ')
    target = (root / value.lstrip('/')).resolve()
    allowed = [(root / 'prototype/media').resolve()]
    if owned:
        allowed.append((root / 'brewtanist/assets').resolve())
    if not any(target.is_relative_to(folder) for folder in allowed):
        raise ValueError('รูปสินค้า: ต้องอยู่ในคลังรูปของร่าง')
    if target.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'} or not target.is_file():
        raise ValueError('ไม่พบรูป JPG / PNG / WebP: ' + value)
    if target.stat().st_size > 8_000_000:
        raise ValueError('รูปใหญ่เกิน 8 MB: ' + value)
    try:
        with Image.open(target) as image:
            if image.format not in {'JPEG', 'PNG', 'WEBP'} or image.width * image.height > 40_000_000:
                raise ValueError('ชนิดหรือขนาดรูปไม่รองรับ')
            image.verify()
    except Exception as exc:
        raise ValueError('เปิดรูปไม่สำเร็จ: ' + value) from exc
    return target

def embedded_image(value, root=ROOT, owned=False):
    target = image_path(value, root, owned)
    with Image.open(target) as original:
        # Re-encode raster pixels: strip EXIF/metadata; never include SVG or font files.
        from PIL import ImageOps
        image = ImageOps.exif_transpose(original).convert('RGBA' if 'A' in original.getbands() else 'RGB')
        image.thumbnail((1400, 1400))
        output = io.BytesIO()
        image.save(output, format='WEBP', quality=88, method=4)
    payload = base64.b64encode(output.getvalue()).decode('ascii')
    if len(payload) > 3_900_000:
        raise ValueError('รูปหลังย่อยังใหญ่เกินไป: ' + value)
    return 'data:image/webp;base64,' + payload

def validate_products(raw, root=ROOT):
    if not isinstance(raw, dict) or raw.get('schemaVersion') != 1 or type(raw.get('schemaVersion')) is not int:
        raise ValueError('รุ่นข้อมูลสินค้าไม่ถูกต้อง')
    rows = raw.get('items')
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError('ใช้สามสินค้าเดิมก่อน หากไม่ต้องการแสดงให้ปิดสวิตช์แทนการลบ')
    seen, clean = set(), []
    expected = set(REQUIRED) | set(OPTIONAL) | {'visible', 'verified', 'tasteTags', 'drinkTags'}
    for row in rows:
        if not isinstance(row, dict) or set(row) - expected:
            raise ValueError('มีช่องข้อมูลสินค้าที่ไม่รองรับ')
        out = dict(row)
        for key in REQUIRED:
            if not isinstance(out.get(key), str) or not out[key].strip() or len(out[key]) > 1000:
                raise ValueError('กรอกข้อมูลให้ครบ: ' + key)
            out[key] = out[key].strip()
        if out['id'] not in IDS or out['id'] in seen:
            raise ValueError('รหัสสินค้าซ้ำหรือไม่ตรงกับสามรายการเดิม')
        seen.add(out['id'])
        if out['theme'] not in IDS:
            raise ValueError('สีพื้นหลังไม่ถูกต้อง')
        for key in OPTIONAL:
            out[key] = '' if out.get(key) is None else out.get(key, '')
            if not isinstance(out[key], str) or len(out[key]) > 1000:
                raise ValueError('ข้อมูลต้องเป็นข้อความ: ' + key)
            out[key] = out[key].strip()
        if out['price'] and (not re.fullmatch(r'\d{1,6}(?:\.\d{1,2})?', out['price']) or Decimal(out['price']) <= 0):
            raise ValueError('ราคา: ใช้ตัวเลขมากกว่า 0 หรือเว้นว่าง')
        if out['productUrl']:
            try:
                link = urlsplit(out['productUrl'])
                valid = link.scheme == 'https' and link.hostname == 'shopee.co.th' and not link.username and not link.password and link.port in (None, 443)
            except ValueError:
                valid = False
            if not valid or any(ord(c) < 32 for c in out['productUrl']):
                raise ValueError('ลิงก์สินค้า: ใช้ https://shopee.co.th/... เท่านั้น')
        for key in ('visible', 'verified'):
            if type(out.get(key)) is not bool:
                raise ValueError('ตั้งค่าสวิตช์ให้ถูกต้อง: ' + key)
        for key, allowed in [('tasteTags', {'chocolate', 'sweet', 'fruity'}), ('drinkTags', {'black', 'milk'})]:
            values = out.get(key) or []
            if not isinstance(values, list) or any(not isinstance(v, str) or v not in allowed for v in values):
                raise ValueError('ตรวจตัวเลือกช่วยเลือกกาแฟ: ' + key)
            out[key] = list(dict.fromkeys(values))
        image_path(out['image'], root)
        clean.append(out)
    return clean

def load_products(root=ROOT):
    return validate_products(json.loads((root / 'prototype/products.json').read_text(encoding='utf-8')), root)

def warnings_for(rows):
    output = []
    for row in rows:
        missing = [key for key in OPTIONAL if not row[key]]
        output.append({'id': row['id'], 'name': row['name'], 'visible': row['visible'], 'unconfirmed': missing, 'owner_reviewed': row['verified']})
    return output
