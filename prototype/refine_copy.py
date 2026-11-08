"""Refine preview copy only; do not modify production files or product facts."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'prototype'

def replace_all(text, pairs, filename):
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new)
        elif new and new in text:
            continue
        else:
            raise ValueError(f'{filename}: expected text not found: {old[:100]}')
    return text

p = BASE / 'template.html'
s = p.read_text(encoding='utf-8')
pairs = [
 ('Brewtanist · Coffee discovery preview', 'Brewtanist · เลือกกาแฟกลับบ้าน'),
 ('BREWTANIST / PREVIEW LAB 01', 'BREWTANIST / PREVIEW 02'),
 ('ต้นแบบสำหรับตรวจงาน · ไม่รับชำระเงิน · ไม่แก้เว็บจริง', 'เว็บตัวอย่าง · ยังไม่เปิดขายบนเว็บนี้'),
 ('data-nav="finder">Coffee Finder', 'data-nav="finder">ช่วยเลือกกาแฟ'),
 ('data-nav="compare">เทียบ Blend', 'data-nav="compare">เทียบกาแฟ'),
 ('data-nav="studio">ทดลองแก้ไข', 'data-nav="studio">แก้ข้อความและรูป'),
 ('กาแฟ ต้นไม้ และสิ่งใหม่ ๆ ที่อยากให้ลอง', 'Cafe & Coffee Roaster · ปราจีนบุรี'),
 ('ต้นแบบจากข้อมูลเว็บเดิม · ราคาและรายการขายยังรอยืนยัน', 'ดูราคาและสินค้าที่มีขายล่าสุดได้ที่ Shopee'),
 ('หน้าแก้ไขต้นแบบ', 'แก้ข้อความและรูป'),
 ("items.length+' Blend จากข้อมูลที่มี'", "items.length+' รายการ'"),
 ("title('เลือกกาแฟในแบบของคุณ')", "title('เลือกกาแฟกลับบ้าน')"),
 ('THE BREWTANIST / COFFEE EXPLORER', 'THE BREWTANIST / COFFEE FOR HOME'),
 ('หากาแฟที่เข้ากับคุณ <span', 'ช่วยเลือกกาแฟ <span'),
 ('เลือกดูเอง ↓', 'ดูกาแฟทั้งหมด ↓'),
 ('ไม่ต้องสมัครสมาชิก · คำตอบไม่ถูกส่งออกจากหน้านี้', 'ตอบ 3 ข้อ ไม่ต้องสมัครสมาชิก'),
 ('A BLEND FOR YOUR KIND OF DAY.', 'BREWTANIST HOUSE BLENDS'),
 ('Roasted with character.', 'Mr. Plantman · Mr. Ozmo · Ms. Lazybug'),
 ('Same curiosity.<br>Different characters.', 'House Blend<br>ของ Brewtanist'),
 ('เริ่มต้นด้วย House Blend ที่มีข้อมูลอยู่แล้ว เลือกดูแต่ละตัว หรือวางข้างกันเพื่อเทียบกลิ่นรสและระดับคั่ว', 'แต่ละตัวต่างกันที่ระดับคั่วและกลิ่นรส กดดูรายละเอียด หรือเลือกเทียบก่อนตัดสินใจ'),
 ('ค้นหาชื่อ หรือ Tasting notes', 'ค้นชื่อกาแฟหรือกลิ่นรส'),
 ('ยังเลือกไม่ถูก?<br>เริ่มจากสิ่งที่ชอบ', 'ยังเลือกไม่ถูก?<br>เราช่วยเลือกได้'),
 ('ตอบ 3 ข้อ แล้วดู Blend ที่มีข้อมูลใกล้กับคำตอบของคุณ พร้อมเหตุผลที่ตรวจสอบได้', 'ชอบรสแบบไหน ดื่มดำหรือใส่นม? ตอบสามข้อ แล้วมาดูกันว่าตัวไหนน่าลอง'),
 ('ลอง Coffee Finder ↗', 'ลองเลือกกาแฟ ↗'),
 ('FROM OUR COFFEE BAR TO YOUR CUP', 'TAKE BREWTANIST HOME'),
 ('Take a little<br>Brewtanist home.', 'เลือกกาแฟกลับบ้าน'),
 ('รู้จักร้านและดูพิกัด ↗', 'ดูร้านและพิกัด ↗'),
 ("' บาท · ค่าทดลอง' : 'ราคา: รอยืนยัน'", "' บาท · ราคาในร่าง' : 'สอบถามร้าน'"),
 ('ภาพ 3D ของแบรนด์ · กดเพื่อขยาย · บรรจุภัณฑ์จริงควรตรวจจากรายการขายล่าสุด', 'ภาพจำลองบรรจุภัณฑ์ · แตะเพื่อดูภาพใหญ่'),
 ("${p.verified?'ร้านทำเครื่องหมายตรวจแล้วในต้นแบบ':'ข้อมูลเดิม · รอร้านตรวจอีกครั้ง'}", "${p.verified?'ร้านตรวจร่างแล้ว':'House Blend'}"),
 ('เพิ่มไว้เปรียบเทียบ', 'เลือกเทียบ'),
 ("p.sizes||'ยังไม่มีข้อมูลยืนยัน'", "p.sizes||'ดูขนาดที่ Shopee'"),
 ("p.grinding||'สอบถามร้านก่อนเลือก'", "p.grinding||'สอบถามร้าน'"),
 ("p.origin||'รอยืนยันข้อมูล'", "p.origin||'สอบถามร้าน'"),
 ('<div><dt>สต็อก</dt><dd>ไม่ได้เชื่อมระบบสต็อก</dd></div>', '<!-- Stock is not claimed without a connected source. -->'),
 ("${link?'ตรวจรายการสินค้าบน Shopee':'เปิดร้าน Brewtanist บน Shopee'}", "${link?'ดูสินค้านี้ที่ Shopee':'ดูร้านใน Shopee'}"),
 ('ลอง Coffee Finder</a>', 'ช่วยเลือกกาแฟ</a>'),
 ('<strong>ต้นแบบนี้ยังไม่รับออเดอร์หรือรับเงิน</strong>', '<strong>สั่งซื้อผ่าน Shopee</strong>'),
 ("${link?'ลิงก์นี้เป็นค่าที่กรอกทดลองในหน้าแก้ไข':'ยังไม่มีลิงก์สินค้ารายตัว ปุ่มด้านบนจึงเปิดหน้าร้าน Shopee'} ราคา ขนาด และสต็อกต้องตรวจที่ช่องทางขายอีกครั้ง", "${link?'ปุ่มนี้เปิดลิงก์สินค้าที่ใส่ไว้ในร่าง':'ปุ่มนี้เปิดหน้าร้าน Brewtanist'} ดูราคา ขนาด และตัวเลือกที่มีขายได้ที่นั่น"),
 ('ข้อมูลนี้มาจากไหน?', 'หมายเหตุสำหรับคนตรวจเว็บ'),
 ('ชื่อ ระดับคั่ว และ Tasting notes นำจากไฟล์สินค้าในเว็บไซต์เดิม ไม่ได้ยืนยันกับสินค้าล็อตปัจจุบัน กฎ Coffee Finder เป็นการจัดหมวดจากข้อความเหล่านี้เพื่อทดลองใช้งาน', 'ร่างนี้ใช้ชื่อ ระดับคั่ว และ Tasting notes จากเว็บเดิมของร้าน ควรตรวจให้ตรงกับสินค้าที่ขายอยู่ก่อนนำไปใช้จริง'),
 ('ยังไม่มีสูตรชงเฉพาะตัว ส่วนประกอบ หรือความเข้ากันได้กับเครื่องแคปซูลที่ยืนยันแล้ว จึงไม่เติมข้อมูลเหล่านี้ขึ้นเอง', 'สูตรชง แหล่งปลูก และรุ่นเครื่องแคปซูลยังไม่ได้ใส่ไว้ เพิ่มในร่างได้เมื่อร้านตรวจข้อมูลแล้ว'),
 ('ลองเทียบอีกคาแรกเตอร์', 'ลองดูอีกสองตัว'),
 ("title:'อยากชงกาแฟแบบไหน?'", "title:'กำลังหากาแฟแบบไหน?'"),
 ('เลือกรูปแบบสินค้าที่คุณต้องการก่อน', 'เลือกแบบที่ใช้ชงอยู่ที่บ้าน'),
 ('ใช้กับอุปกรณ์ชงของคุณ', 'สำหรับอุปกรณ์ชงกาแฟที่บ้าน'),
 ('ต้องตรวจระบบเครื่องและรุ่นที่รองรับ', 'สำหรับเครื่องชงแคปซูล'),
 ('เลือกสิ่งที่ใกล้กับรสนิยมของคุณที่สุด', 'เลือกข้อที่ใกล้กับกาแฟที่ชอบดื่ม'),
 ('โทนกลิ่นรสที่ระบุในข้อมูลสินค้า', 'ชอบกลิ่นช็อกโกแลตและถั่ว'),
 ('กลิ่นรสหอมหวานตาม Tasting notes', 'ชอบกลิ่นวานิลลาและรัมเรซิน'),
 ('โทน Floral, Fruity และ Tea-like', 'ชอบกลิ่นดอกไม้ ผลไม้ หรือชา'),
 ('ขอดูตัวเลือกแบบไม่ฟันธง', 'ลองดูหลายตัวก่อน'),
 ('เราจะใช้ข้อนี้เฉพาะสินค้าที่มีข้อมูลรองรับ', 'นึกถึงแก้วที่สั่งหรือชงดื่มบ่อยที่สุด'),
 ('เปรียบเทียบจากกลิ่นรสก่อน', 'เลือกจากกลิ่นรสก่อน'),
 ("reasons.push('Tasting notes มีโทน '+labels[answers[1]])", "reasons.push('กลิ่นรสโทน '+labels[answers[1]]+' ที่คุณเลือก')"),
 ("reasons.push('คำอธิบายเดิมระบุ '+labels[answers[2]])", "reasons.push('เลือกดื่มเป็น'+labels[answers[2]]+'ได้')"),
 ('COFFEE FINDER / FIND YOUR CHARACTER', 'BREWTANIST / COFFEE FINDER'),
 ('กาแฟแก้วถัดไป<br>เริ่มจากคุณ', 'ชอบกาแฟแบบไหน?'),
 ('ไม่ต้องรู้ศัพท์กาแฟทั้งหมด เลือกสิ่งที่ชอบ แล้วค่อยดูรายละเอียดด้วยกัน', 'เลือกแบบที่ดื่มอยู่ หรือรสที่อยากลอง ไม่แน่ใจข้อไหนก็เลือก “ยังไม่แน่ใจ” ได้'),
 ('Three small steps.', 'ตอบแค่ 3 ข้อ'),
 ('ตอบได้โดยไม่ต้องลงชื่อหรือให้ข้อมูลติดต่อ ไม่มีการส่งคำตอบไปยังระบบอื่น', 'ไม่ต้องลงชื่อหรือกรอกเบอร์โทร คำตอบอยู่แค่ในเบราว์เซอร์นี้'),
 ("quiz.step===2?'ดูผลลัพธ์':'ถัดไป'", "quiz.step===2?'ดูกาแฟที่แนะนำ':'ถัดไป'"),
 ('ยังไม่ควรแนะนำ Blend<br>สำหรับ${esc(labels[format])}จากข้อมูลนี้', 'ดู${esc(labels[format])}ที่ Shopee'),
 ('ต้นแบบมีรายละเอียดเฉพาะเมล็ดกาแฟทั้งสาม Blend ยังไม่มีรายการ ${esc(labels[format])} ที่ยืนยันแล้ว จึงไม่เอาข้อมูลถุงเมล็ดกาแฟมาจับคู่แทน', 'หน้านี้ยังไม่มีรายละเอียด${esc(labels[format])}ให้เทียบ ดูรายการที่ร้าน Shopee ก่อนได้ หรือทักร้านให้ช่วยเลือก'),
 ('ตรวจรายการที่ร้าน Shopee ↗', 'ดูร้านใน Shopee ↗'),
 ('คำตอบยังไม่ชี้ไปที่คาแรกเตอร์ใดเป็นพิเศษ เราจึงไม่จัดอันดับหรือเดาว่าตัวไหนเหมาะที่สุด', 'ยังไม่มีตัวไหนตรงชัด ๆ ลองดูรายละเอียดทั้งสามตัว หรือเลือกเทียบกลิ่นรสก่อนก็ได้'),
 ('บางตัวตรงเฉพาะโทนกลิ่นรส แต่ยังไม่มีข้อมูลยืนยันเรื่องกาแฟนม ควรสอบถามร้านก่อนเลือก<br>', 'บางตัวตรงกับกลิ่นรสที่ชอบ แต่ยังไม่มีคำแนะนำสำหรับชงกับนม ทักร้านถามก่อนได้<br>'),
 ('ผลนี้จับคู่จากคำอธิบายเดิม ไม่ใช่การรับรองรสชาติหรือสูตรชง ไม่มีการใช้คะแนนเปอร์เซ็นต์ความแม่นยำ', 'ใช้คำแนะนำนี้ช่วยเลือกเบื้องต้น แล้วลองอ่านรายละเอียดของแต่ละตัวก่อนตัดสินใจ'),
 ('YOUR COFFEE EXPLORATION', 'BREWTANIST / YOUR PICKS'),
 ('คาแรกเตอร์ที่น่าลอง', 'กาแฟที่น่าลอง'),
 ('เทียบเฉพาะข้อมูลที่มี ราคา ขนาด และสต็อกจะไม่ถูกสมมติขึ้นมา', 'วางตัวที่สนใจไว้ข้างกัน แล้วดูว่าชอบกลิ่นรสและระดับคั่วแบบไหน'),
 ("['Tasting notes','notes'],['คาแรกเตอร์','description']", "['กลิ่นรส','notes'],['รสชาติ','description']"),
 ("p[k]||'รอยืนยันข้อมูล'", "p[k]||'สอบถามร้าน'"),
 ('กด “เลือกเทียบ” ที่การ์ดสินค้าได้สูงสุด 3 ตัว', 'กลับไปเลือกกาแฟ แล้วติ๊ก “เลือกเทียบ” ได้ทีละไม่เกิน 3 ตัว'),
 ('มีรูปแบบข้อมูลที่ต้องแก้', 'มีข้อมูลที่ต้องแก้'),
 ('โครงสร้างข้อมูลใช้ได้', 'รูปแบบข้อมูลถูกต้อง'),
 ('แม้ตรวจครบ การบันทึกหน้านี้ก็ไม่เผยแพร่เว็บจริง ยังต้องตรวจ Hosting และอนุมัติการขึ้นเว็บแยกต่างหาก', 'หน้านี้บันทึกได้เฉพาะร่างในเครื่อง ส่งออกไฟล์ให้ทีมตรวจได้ แต่ยังไม่ขึ้นเว็บจริง'),
 ("p.sizes||'รอยืนยัน'", "p.sizes||'ดูขนาดที่ Shopee'"),
 ("p.grinding||'รอยืนยัน'", "p.grinding||'สอบถามร้าน'"),
 ('ปุ่มตัวอย่าง · ไม่มี Checkout', 'ตัวอย่างปุ่ม Shopee'),
 ('ภาพและข้อความที่แก้ยังไม่ถูกส่งขึ้น GitHub หรือเว็บจริง', 'ยังไม่ขึ้นเว็บจริง'),
 ("title('Content Studio')", "title('แก้ข้อความและรูป')"),
 ('แก้ก่อน เห็นก่อน<br>ค่อยนำขึ้นเว็บจริง', 'แก้ข้อความและรูป<br>ดูตัวอย่างได้เลย'),
 ('ลองแก้ข้อความหรืออัปโหลดรูป แล้วดูตัวอย่างด้านข้าง การบันทึกอยู่ในเบราว์เซอร์เครื่องนี้ ไม่ใช่ Pages CMS และไม่ส่งขึ้นเว็บจริง', 'เลือกสินค้าที่จะแก้ แล้วดูผลด้านข้าง ร่างจะเก็บในเบราว์เซอร์นี้ ยังไม่ขึ้นเว็บจริง'),
 ('LOCAL DRAFT / ไม่มีการส่งข้อมูล', 'ร่างในเครื่องนี้'),
 ('แสดงในแคตตาล็อกต้นแบบ', 'แสดงสินค้านี้'),
 ("field('notes','Tasting notes',p.notes)", "field('notes','กลิ่นรส / Tasting notes',p.notes)"),
 ('ราคา ขนาด และข้อมูลที่ยังขาด', 'ราคา ขนาด และลิงก์สินค้า'),
 ('ตรวจและแก้กฎ Coffee Finder', 'ตั้งค่าตัวช่วยเลือกกาแฟ'),
 ('กฎเริ่มต้นจัดหมวดจาก Tasting notes และคำอธิบายเดิม ไม่ใช่ผลชิมหรือสูตรที่ร้านรับรอง', 'เลือกกลิ่นรสและรูปแบบการดื่มของตัวนี้ ระบบจะใช้จับคู่กับคำตอบลูกค้า ตรวจให้ตรงกับกาแฟก่อนบันทึก'),
 ('มีข้อมูลรองรับ ${labels[k]}', 'แนะนำสำหรับ${labels[k]}'),
 ('ฉันตรวจข้อมูลและกฎของตัวนี้แล้ว (ในต้นแบบ)', 'ตรวจข้อมูลและคำแนะนำของตัวนี้แล้ว'),
 ('เบราว์เซอร์ไม่ให้บันทึกถาวร กรุณาส่งออกไฟล์ร่างก่อนปิด', 'บันทึกในเครื่องไม่ได้ กดเก็บไฟล์ร่างก่อนปิดหน้านี้'),
 ('ข้อความที่แก้จะถูกเก็บอัตโนมัติในเบราว์เซอร์นี้', 'เก็บร่างอัตโนมัติในเบราว์เซอร์นี้'),
 ('>ส่งออกไฟล์ร่าง</button>', '>เก็บไฟล์ร่าง</button>'),
 ('>ส่งออกเว็บตัวอย่าง</button>', '>โหลดเว็บตัวอย่าง</button>'),
 ('นำเข้าไฟล์ร่าง JSON<input', 'เปิดไฟล์ร่างที่เก็บไว้ (.json)<input'),
 ('คืนข้อมูลต้นฉบับทั้งชุด', 'กลับไปใช้ข้อมูลเริ่มต้น'),
 ('<strong>ไม่มีปุ่ม Publish ในต้นแบบ</strong>ส่งออกไฟล์ร่างเพื่อรีวิวได้ แต่การเผยแพร่จริงต้องผ่านผู้ดูแล ไม่ต้องใส่รหัสผ่าน GitHub หรือ Token ในหน้านี้', '<strong>บันทึกร่าง ไม่ใช่เผยแพร่</strong>กด “เก็บไฟล์ร่าง” เพื่อส่งให้ทีมตรวจ หรือ “โหลดเว็บตัวอย่าง” เพื่อเปิดดูพร้อมรูป ไม่ต้องใส่รหัสผ่านในหน้านี้'),
 ('ยังไม่มีหน้านี้', 'ไม่พบสินค้านี้'),
 ('สินค้านี้อาจถูกซ่อน หรือ URL ไม่ตรงกับต้นแบบ', 'สินค้านี้อาจถูกซ่อนไว้ ลองกลับไปดูกาแฟทั้งหมด'),
 ('ส่งออกไฟล์ร่างแล้ว ยังไม่เปลี่ยนเว็บจริง', 'เก็บไฟล์ร่างแล้ว'),
 ('ส่งออกเว็บตัวอย่างแบบไฟล์เดียวแล้ว', 'โหลดเว็บตัวอย่างพร้อมรูปแล้ว'),
 ('บันทึกร่างในเครื่องแล้ว เว็บจริงไม่เปลี่ยน', 'บันทึกร่างแล้ว · ยังไม่ขึ้นเว็บจริง'),
 ('ยังเก็บในเครื่องไม่ได้ กรุณาส่งออกไฟล์', 'บันทึกในเครื่องไม่ได้ กดเก็บไฟล์ร่างแทน'),
 ('คืนค่าต้นฉบับทั้งสาม Blend? การแก้ในเครื่องนี้จะหาย ควรส่งออกไฟล์ร่างก่อน', 'กลับไปใช้ข้อมูลเริ่มต้นทั้งสามตัว? ข้อความและรูปที่แก้ไว้จะหาย กดเก็บไฟล์ร่างไว้ก่อนถ้ายังต้องการใช้'),
 ('บันทึกอัตโนมัติในเครื่องแล้ว · ยังไม่เปลี่ยนเว็บจริง', 'เก็บร่างแล้ว · ยังไม่ขึ้นเว็บจริง'),
 ('นำเข้าไฟล์ร่างแล้ว เว็บจริงยังไม่เปลี่ยน', 'เปิดไฟล์ร่างแล้ว · ยังไม่ขึ้นเว็บจริง'),
 ('เปลี่ยนรูปในต้นแบบแล้ว ไม่มีการอัปโหลดขึ้นเว็บจริง', 'เปลี่ยนรูปในร่างแล้ว'),
]
s = replace_all(s, pairs, p.name)
# Preserve a saved user draft, updating only strings identical to the old defaults.
migration = """  // Refresh old default copy without overwriting owner-written draft text.
  const old = DEFAULT.previousCopy;
  if (old) {
    for (const k of ['title','intro']) if (d[k] === old[k]) d[k] = DEFAULT[k];
    for (const p of d.products) {
      if (p.description === old.descriptions[p.id]) p.description = DEFAULT.products.find(x=>x.id===p.id).description;
    }
  }
"""
if '// Refresh old default copy' not in s:
    marker = '  return d;\n}\ntry {'
    if s.count(marker) != 1:
        raise ValueError('Draft migration marker changed')
    s = s.replace(marker, migration + marker)
p.write_text(s, encoding='utf-8')

p = BASE / 'build.py'
s = p.read_text(encoding='utf-8')
if '# Approved copy-only overlay' not in s:
    marker = "    raw_json = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\\\u003c')"
    if marker not in s:
        # Locate the serialization line by its unique function prefix.
        lines = [line for line in s.splitlines() if line.startswith('    raw_json = json.dumps(data,')]
        if len(lines) != 1:
            raise ValueError('Build serialization marker changed')
        marker = lines[0]
    overlay = """    # Approved copy-only overlay; source notes, roast and finder tags stay unchanged.
    copy = json.loads((ROOT / 'prototype' / 'copy.th.json').read_text(encoding='utf-8'))
    if set(copy['descriptions']) != {p['id'] for p in items}:
        raise ValueError('Copy must match exactly the saved product ids')
    data['previousCopy'] = {'title': data['title'], 'intro': data['intro'], 'descriptions': {p['id']: p['description'] for p in items}}
    for key in ['title', 'intro', 'sourceDescription']:
        if not isinstance(copy[key], str) or not copy[key].strip():
            raise ValueError('Empty editorial copy: ' + key)
        data[key] = copy[key]
    for item in items:
        item['description'] = copy['descriptions'][item['id']]
    data['copyRevision'] = copy['revision']
"""
    s = s.replace(marker, overlay + marker)
p.write_text(s, encoding='utf-8')

p = BASE / 'test_preview.py'
s = p.read_text(encoding='utf-8')
s = replace_all(s, [
    ("to_contain_text('รอยืนยัน')", "to_contain_text('สอบถามร้าน')"),
    ("to_contain_text('ยังไม่ควรแนะนำ Blend')", "to_contain_text('ดูแคปซูลที่ Shopee')"),
    ("get_by_text('ราคา ขนาด และข้อมูลที่ยังขาด', exact=True)", "get_by_text('ราคา ขนาด และลิงก์สินค้า', exact=True)"),
    ("to_have_text('ยังไม่มีหน้านี้')", "to_have_text('ไม่พบสินค้านี้')"),
], p.name)
extra = """
        # Copy changes must not manufacture product facts or overwrite owner drafts.
        page.evaluate('window.BrewtanistPreview.reset()')
        page.goto(BASE+'#/catalog')
        expect(page.locator('h1')).to_have_text('เลือกกาแฟ\\nกลับไปชงที่บ้าน')
        saved=page.evaluate('window.BrewtanistPreview.getData()')
        source=json.loads((ROOT/'_data'/'brewtanist'/'products.json').read_text())
        for current, original in zip(saved['products'], source['items']):
            for key in ['name','profile','notes','alt','theme']:
                assert current[key] == original[key], 'Unapproved product fact changed: '+key
            for key in ['price','sizes','grinding','origin','productUrl']:
                assert current[key] == '', 'Unconfirmed value invented: '+key
        assert saved['copyRevision']==2
        for path in ['catalog','product/plantman','finder','compare']:
            page.goto(BASE+'#/'+path)
            content=page.locator('#app').inner_text()
            for phrase in ['เหตุผลที่ตรวจสอบได้','จากข้อมูลที่มี','ฟันธง','เปอร์เซ็นต์ความแม่นยำ','ยกระดับ','ตอบโจทย์']:
                assert phrase not in content, 'Unwanted wording: '+phrase
        record('Plain Thai copy and unchanged source product facts')

        old=page.evaluate('window.BrewtanistPreview.getData()')
        old['title']=old['previousCopy']['title']
        old['intro']=old['previousCopy']['intro']
        old['products'][0]['description']=old['previousCopy']['descriptions']['plantman']
        old['products'][1]['description']='ข้อความที่เจ้าของร้านแก้เอง'
        old['products'][1]['name']='ชื่อที่เจ้าของร้านตั้งไว้'
        page.evaluate('(d)=>localStorage.setItem("brewtanist-preview-lab-v1",JSON.stringify(d))',old)
        page.reload(wait_until='networkidle')
        migrated=page.evaluate('window.BrewtanistPreview.getData()')
        assert migrated['title']=='เลือกกาแฟ\\nกลับไปชงที่บ้าน'
        assert migrated['products'][0]['description']==saved['products'][0]['description']
        assert migrated['products'][1]['description']=='ข้อความที่เจ้าของร้านแก้เอง'
        assert migrated['products'][1]['name']=='ชื่อที่เจ้าของร้านตั้งไว้'
        page.evaluate('window.BrewtanistPreview.reset()')
        record('Saved owner drafts preserved while previous default copy is refreshed')
"""
if '# Copy changes must not manufacture' not in s:
    marker = "        assert not errors, 'Browser errors: '+repr(errors)"
    if marker not in s:
        raise ValueError('Test insertion marker changed')
    s = s.replace(marker, extra + '\n' + marker)
p.write_text(s, encoding='utf-8')

(BASE/'VOICE.md').write_text('''# Brewtanist website voice

พูดเหมือนแนะนำกาแฟให้คนที่หน้าร้าน อ่านแล้วรู้ว่ากาแฟเป็นแบบไหนและต้องกดตรงไหนต่อ

- ใช้ชื่อจริงและกลิ่นรสที่ร้านมีข้อมูลอยู่แล้ว ไม่เติมคำว่าอร่อยที่สุด ขายดีที่สุด หรือรับรองว่าจะชอบ
- เขียนว่า “ช่วยเลือกกาแฟ”, “ชอบกาแฟแบบไหน?”, “ดูกาแฟทั้งหมด” แทนคำอธิบายวิธีคิดของระบบ
- เล่าให้เห็นรสจริง เช่น ดาร์กช็อกโกแลต คาราเมล ถั่ว ไม่ใช้คำว่า “ยกระดับ”, “ตอบโจทย์ทุกไลฟ์สไตล์” หรือ “ประสบการณ์เหนือระดับ”
- ใช้ “กลิ่นรส” ในคำแนะนำทั่วไป เก็บ Tasting notes ภาษาอังกฤษเดิมไว้ใต้ชื่อสินค้า
- ไม่เปลี่ยนความหมายของกลิ่นรสเป็นส่วนผสม ไม่เติมแหล่งปลูก สูตรชง ราคา หรือสต็อก
- ข้อมูลที่ลูกค้าต้องเช็กให้บอกสั้น ๆ เช่น “ดูขนาดที่ Shopee” หรือ “สอบถามร้าน”
- คำเตือนเรื่องการแก้ร่างอยู่ในหน้าแก้ไข ส่วนรายละเอียดแหล่งข้อมูลอยู่ในหมายเหตุที่เปิดอ่านได้
- ปุ่มบันทึกต้องบอกว่าเก็บร่างในเครื่อง ไม่อ้างว่าเผยแพร่แล้ว

## Scope of revision 02

Only the isolated prototype is changed. The production index, all original CMS JSON files, source product facts, images, pricing, availability and recommendation tags are untouched. Owner-written local drafts are preserved. Descriptions are restatements of the source rather than new claims. The original three-question matching logic remains unchanged.
''',encoding='utf-8')
print(json.dumps({'revision':2,'changed_scope':'prototype only','production_written':False,'copy_replacements':len(pairs)},ensure_ascii=False))
