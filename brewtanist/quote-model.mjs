const LANGUAGES = ['th', 'en', 'zh'];
export const TYPES = ['beans', 'capsules', 'service', 'custom'];
export const UNITS = ['kg', 'capsule', 'pack', 'box', 'lot', 'piece'];
export const MAX_LINES = 60;
export const MAX_REVISIONS = 50;
const readText = (v, max = 4000) => typeof v === 'string' && v.length <= max;
const shared = (obj, keys, max) => keys.every(key => readText(obj?.[key], max));
const langOK = value => LANGUAGES.includes(value);
const calendar = /^\d{4}-\d{2}-\d{2}$/;
const validDate = value => calendar.test(value) && !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0,10) === value;
export function dateToday() {
  const d = new Date();
  return [d.getFullYear(), ...[d.getMonth()+1, d.getDate()].map(n => String(n).padStart(2,'0'))].join('-');
}
export function makeLine(type = 'beans') {
  return {type, description:'', qty:'1', unit:{beans:'kg',capsules:'capsule',service:'lot',custom:'piece'}[type], price:''};
}
export function newOffer(language) {
  const date = dateToday();
  const suffix = Array.from(crypto.getRandomValues(new Uint8Array(4)), b => b.toString(16).padStart(2,'0')).join('').toUpperCase();
  return {number:'Q-'+date.replaceAll('-','')+'-'+suffix,revision:1,issued:date,valid:'',doclang:language,
    name:'',company:'',email:'',phone:'',rfq:'',lines:[makeLine()],discount:'',taxRate:'',terms:''};
}
// All amounts are represented as integer satang. Quantities permit three decimal
// places. Each extended line and the tax on the discounted subtotal round half up.
function scaled(value, precision, max, optional = false) {
  if (optional && value === '') return 0n;
  const text = String(value).replace(/^\.(?=\d)/,'0.');
  const parts = /^(\d{1,12})(?:\.(\d*))?$/.exec(text);
  if (!parts || (parts[2]?.length || 0) > precision) throw Error('priceError');
  const factor = 10n ** BigInt(precision);
  const n = BigInt(parts[1]) * factor + BigInt((parts[2] || '').padEnd(precision,'0') || '0');
  if (n > max) throw Error('priceError');
  return n;
}
export function extendedLine(line) {
  const qty = scaled(line.qty,3,999999999999n);
  const price = scaled(line.price,2,999999999999n);
  if (!qty) throw Error('priceError');
  return (qty * price + 500n) / 1000n;
}
export function calculate(quote) {
  if (quote.lines.length === 0) throw Error('priceError');
  const amounts = quote.lines.map(extendedLine);
  const subtotal = amounts.reduce((total,n) => total+n,0n);
  const discount = scaled(quote.discount,2,999999999999n,true);
  if (discount > subtotal) throw Error('priceError');
  const taxRate = scaled(quote.taxRate,2,10000n,true);
  const tax = ((subtotal-discount)*taxRate+5000n)/10000n;
  return {amounts,subtotal,discount,tax,total:subtotal-discount+tax};
}
export function currency(amount,lang) {
  const whole = new Intl.NumberFormat(lang, { maximumFractionDigits:0 }).format(amount/100n);
  return whole + '.' + (amount%100n).toString().padStart(2,'0');
}
export function validateForIssue(offer) {
  if (!offer.number.trim() || !(offer.name.trim() || offer.company.trim())) throw Error('headerError');
  if (!validDate(offer.issued) || (offer.valid && (!validDate(offer.valid) || offer.valid<offer.issued))) throw Error('dateError');
  return calculate(offer);
}
export function revise(file) {
  validateForIssue(file.current);
  if (file.history.length >= MAX_REVISIONS) throw Error('max');
  const previous=structuredClone(file.current), date=dateToday();
  file.history.push(previous);
  file.current={...structuredClone(previous),revision:previous.revision+1,issued:date,valid:previous.valid<date?'':previous.valid};
}
export function isRFQ(o) {
  if (o?.kind!=='brewtanist-oem-rfq' || o.schemaVersion!==1 || !langOK(o.language) ||
      !readText(o.reference,80) || !/^RFQ-\d{8}-[\da-f]{8}$/i.test(o.reference) ||
      !readText(o.createdAt,40) || Number.isNaN(Date.parse(o.createdAt)) ||
      !shared(o.contact,['name','company','phone','email'],300) || !o.contact.name.trim() ||
      !(o.contact.email || o.contact.phone) || !o.products || !o.project ||
      !shared(o.project,['flavour','packaging','frequency','destination','targetDate','budget','notes'])) return false;
  const {beans,capsules}=o.products;
  const positive = n => typeof n==='number' && Number.isFinite(n) && n>0 && n<=999999999;
  const pack = n => n===null || (positive(n) && Number.isInteger(n));
  return !!(beans || capsules) && (!beans || (positive(beans.quantityKg) && pack(beans.packGrams)
      && ['discuss','light','medium','dark'].includes(beans.roast) && ['discuss','whole','ground'].includes(beans.grind)))
    && (!capsules || (pack(capsules.quantityUnits) && !!capsules.quantityUnits && pack(capsules.perBox) && readText(capsules.system)));
}
export function requestFile(rfq, labels) {
  if (!isRFQ(rfq)) throw Error('invalidFile');
  const q=newOffer(rfq.language), t=labels[rfq.language];
  Object.assign(q, {name:rfq.contact.name,company:rfq.contact.company,email:rfq.contact.email,phone:rfq.contact.phone,rfq:rfq.reference,lines:[]});
  const {beans,capsules}=rfq.products;
  if(beans) {
    const line=makeLine('beans');
    line.qty=String(beans.quantityKg);
    line.description=requestDescription(beans,'beans',t);
    q.lines.push(line);
  }
  if(capsules) {
    const line=makeLine('capsules');
    line.qty=String(capsules.quantityUnits);
    line.description=requestDescription(capsules,'capsules',t);
    q.lines.push(line);
  }
  return {kind:'brewtanist-oem-quote',schemaVersion:1,current:q,history:[],request:rfq};
}
// Older v1 files stored the generated Chinese description as plain text.
const previousChineseSpecs = {
  packSpec:'每袋克重（克） {n}', boxSpec:'每盒胶囊数 {n}',
  light:'浅焙', medium:'中焙', dark:'深焙', whole:'整豆', ground:'研磨'
};
function requestDescription(product,type,t) {
  const parts=type==='beans' ? [
    product.packGrams && t.packSpec.replace('{n}',product.packGrams),
    product.roast!=='discuss' && t[product.roast],
    product.grind!=='discuss' && t[product.grind]
  ] : [product.system, product.perBox && t.boxSpec.replace('{n}',product.perBox)];
  return parts.filter(Boolean).join(' · ');
}
export function documentDescription(line,request,lang,labels) {
  const product=request?.products[line.type];
  if(!product || lang===request.language) return line.description;
  const original=requestDescription(product,line.type,labels[request.language]);
  const wasGenerated=line.description===original || (request.language==='zh' &&
    line.description===requestDescription(product,line.type,previousChineseSpecs));
  return wasGenerated ? requestDescription(product,line.type,labels[lang]) : line.description;
}
function assertOfferShape(q) {
  if (!q || !langOK(q.doclang) || !Number.isInteger(q.revision) || q.revision<1 || q.revision>MAX_REVISIONS+1 ||
      !shared(q,['name','company','email','phone','rfq'],300) || !readText(q.number,80) ||
      !shared(q,['issued','valid','discount','taxRate'],24) || !readText(q.terms) ||
      !Array.isArray(q.lines) || q.lines.length<1 || q.lines.length>MAX_LINES ||
      !q.lines.every(l=>TYPES.includes(l?.type) && UNITS.includes(l.unit) && readText(l.description,1000) && shared(l,['qty','price'],24))) {
    throw Error('invalidFile');
  }
}
export function importData(data,labels) {
  if (data?.kind==='brewtanist-oem-rfq') return requestFile(data,labels);
  if (data?.kind!=='brewtanist-oem-quote' || data.schemaVersion!==1 || !Array.isArray(data.history) ||
      data.history.length>MAX_REVISIONS || (data.request && !isRFQ(data.request))) throw Error('invalidFile');
  assertOfferShape(data.current);
  if (data.current.revision!==data.history.length+1) throw Error('invalidFile');
  data.history.forEach((q,n)=>{
    assertOfferShape(q);
    if(q.revision!==n+1 || q.number!==data.current.number) throw Error('invalidFile');
    validateForIssue(q);
  });
  return data;
}
