# Brewtanist Preview Lab 01

ต้นแบบแยกจากเว็บจริง: แคตตาล็อก / หน้าสินค้า / เปรียบเทียบ / Coffee Finder / Content Studio

## วิธีทดลอง
เปิด `dist/index.html` ใน Chrome, Edge หรือ Safari ที่เปิด JavaScript ได้ ภาพของร้านฝังไว้ในไฟล์เดียวแล้ว ไม่ต้องเปิดแชร์ Drive และไม่ต้องรัน Server สำหรับตัวอย่าง ฟอนต์ CI โหลดจาก Google Fonts เมื่อออนไลน์; เมื่อออฟไลน์ใช้ฟอนต์สำรอง ไม่มีไฟล์ฟอนต์แนบมาด้วย

- `#/catalog`: ค้นหาสินค้า กรองตาม Tasting notes และเลือกเทียบ
- `#/product/plantman`, `#/product/ozmo`, `#/product/lazybug`: หน้ารายตัวพร้อมขยายรูป
- `#/finder`: ตอบ 3 ข้อ ดูเหตุผลที่แนะนำ
- `#/compare`: เทียบเฉพาะสินค้าที่เลือก
- `#/studio`: แก้ข้อความ รูป และกฎ ดูตัวอย่าง Desktop/Mobile

## การแก้ไขที่ไม่กระทบเว็บจริง
Content Studio เก็บร่างใน localStorage ของเบราว์เซอร์นี้เท่านั้น ไม่ใช่ระบบล็อกอินหรือ Pages CMS ตัวจริง ไม่เรียก GitHub API และไม่มีรหัสผ่านหรือ Token

1. เลือก Blend และแก้ข้อความหรือรูป
2. ตรวจภาพตัวอย่างและรายการข้อมูลที่ขาด
3. กดบันทึกร่างในเครื่อง หรือส่งออก `brewtanist-draft.json`
4. ปุ่มส่งออกเว็บตัวอย่างสร้าง HTML ไฟล์เดียวพร้อมรูปที่แก้ สำหรับส่งให้ทีมตรวจ
5. การเผยแพร่จริงเป็นอีกขั้น ต้องตรวจและอนุมัติก่อน ไม่ทำผ่านหน้านี้

ร่างในเครื่องอาจหายเมื่อเคลียร์ข้อมูล Browser หรือใช้ Private mode จึงควรส่งออก JSON ก่อนปิดงานสำคัญ อย่าใส่ข้อมูลลูกค้า รหัสผ่าน หรือข้อมูลลับ ตัวต้นแบบและ Repository เป็นสาธารณะ; noindex ไม่ใช่การควบคุมสิทธิ์เข้าถึง

## Source and evidence
ต้นทาง: `_data/brewtanist/products.json` และภาพใน `brewtanist/assets/` ที่ commit `d5fb938873581dbc21ad1fafcdc9d89a5695313d`

ชื่อสินค้า ระดับคั่ว Tasting notes และคำอธิบายคงตามข้อมูลที่บันทึกอยู่ ไม่ใช่การยืนยันกับสต็อก/ล็อตปัจจุบัน ไม่เติมราคา ขนาด น้ำหนัก ตัวเลือกการบด แหล่งปลูก รายการส่วนผสม หรือลิงก์ SKU ขึ้นเอง

ภาพหน้าแคตตาล็อกเป็นภาพเดิมจาก home.json; ภาพสินค้าสามภาพเป็น owned 3D renders เดิม

## Coffee Finder rules (prototype, pending owner review)
- รูปแบบแคปซูลและ Drip Bag: ไม่แนะนำสินค้าถุงเมล็ดกาแฟแทน เพราะไม่มีรายการที่ยืนยันแล้ว
- โทนรสตรงกับ tags ที่จัดจาก notes: +3 คะแนนภายในระบบ
- กาแฟดำ/กาแฟนม: +2 เฉพาะคำอธิบายเดิมระบุรูปแบบนั้นชัดเจน
- ไม่มีหลักฐานว่าตรง: ไม่บวกคะแนน ไม่อ้างว่าไม่เหมาะ
- ไม่พบคะแนน: ไม่เดาหรือบังคับผลลัพธ์
- คะแนนไม่ใช่ความแม่นยำทางสถิติ และไม่แสดงเป็นเปอร์เซ็นต์
- ตรวจสอบและแก้ tags ได้ใน Studio; แก้เนื้อหาแล้วเครื่องหมายตรวจข้อมูลจะถูกรีเซ็ต

## What is not implemented
No payment, cart, order, stock sync, account login, analytics trackers, marketing consent collection, scheduled messages, production CMS writes or production deployment. Product routes use URL hashes for portable review; real indexable product URLs and server-rendered SEO are a separate production task.

## Build and test
```
python3 prototype/build.py
python3 -m pip install playwright==1.56.0
python3 -m playwright install --with-deps chromium
python3 prototype/test_preview.py
```

The branch workflow checks that production files are unchanged, runs browser tests and saves the generated HTML and screenshots to this preview branch only. Main is never updated by this workflow. No GitHub Pages deployment is used for the prototype.

## Production gate
Confirm prices, sizes, grind options, current notes, per-product links, finder mapping and actual packaging; approve a hosting platform appropriate for the intended commercial website; design authenticated editorial drafts/reviews. Do not merge this prototype into the existing Pages website simply to make the preview public.
