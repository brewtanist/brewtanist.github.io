import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {calculate,currency,revise,makeLine,newOffer,importData,requestFile,documentDescription,extendedLine,unitName} from '../brewtanist/quote-model.mjs';

const quote=newOffer('th');
Object.assign(quote,{name:'Sample',discount:'3.10',taxRate:'7',lines:[
  {...makeLine('beans'),qty:'2.125',price:'123.45'},
  {...makeLine('service'),qty:'1',price:'4.35'}
]});
const totals=calculate(quote);
assert.deepEqual(totals.amounts,[26233n,435n]);
assert.equal(totals.subtotal,26668n);
assert.equal(totals.discount,310n);
assert.equal(totals.tax,1845n);
assert.equal(currency(totals.total,'en'),'282.03');
assert.equal(calculate({...quote,discount:'266.68'}).total,0n);
assert.equal(extendedLine({...makeLine(),qty:'.5',price:'1.'}),50n);
assert.throws(()=>calculate({...quote,discount:'266.69'}));
assert.throws(()=>calculate({...quote,taxRate:'101'}));
assert.throws(()=>calculate({...quote,lines:[{...makeLine(),qty:'0.001',price:''}]}));
assert.throws(()=>calculate({...quote,lines:[{...makeLine(),qty:'0',price:'500'}]}));
const draft={kind:'brewtanist-oem-quote',schemaVersion:1,history:[],current:quote,request:null};
revise(draft);
draft.current.lines[0].price='99.50';
assert.equal(draft.current.revision,2);
assert.equal(draft.history[0].revision,1);
assert.equal(draft.history[0].lines[0].price,'123.45');
assert.deepEqual(importData(JSON.parse(JSON.stringify(draft)),{}),draft);
assert.throws(()=>importData({...draft,history:[]},{}));
const request={kind:'brewtanist-oem-rfq',schemaVersion:1,reference:'RFQ-20261110-ABC123FF',language:'en',
  createdAt:'2026-11-10T01:00:00Z', contact:{name:'A',company:'B',email:'c@example.com',phone:''},
  products:{beans:{quantityKg:70,packGrams:250,roast:'medium',grind:'whole'},capsules:{quantityUnits:1200,system:'Example',perBox:10}},
  project:{flavour:'',packaging:'',frequency:'once',destination:'',targetDate:'',budget:'',notes:''}};
const labels=Object.fromEntries(['th','en','zh'].map(lang=>[
  lang,JSON.parse(readFileSync(new URL('../_data/quote_desk/'+lang+'.json',import.meta.url),'utf8'))
]));
const received=requestFile(request,labels);
assert.deepEqual(received.current.lines.map(l=>[l.qty,l.unit,l.price]),[['70','kg',''],['1200','capsule','']]);
assert.equal(received.current.rfq,request.reference);
assert.equal(received.current.doclang,'en');
assert.equal(received.current.lines[0].description,'250 g per bag · Medium roast · Whole beans');
assert.equal(received.current.lines[1].description,'Example · 10 capsules per box');
const singleCapsule={...request,products:{capsules:{...request.products.capsules,quantityUnits:1,perBox:1}}};
assert.equal(requestFile(singleCapsule,labels).current.lines[0].description,'Example · 1 capsule per box');
for (const [unit,one,many] of [['capsule','capsule','capsules'],['box','box','boxes'],['lot','lot','lots'],['kg','kg','kg']]) {
  assert.equal(unitName(unit,'1.00',labels.en),one);
  assert.equal(unitName(unit,'2',labels.en),many);
}
const firstEnglishBeans={...received.current.lines[0],description:'Bag size (g) 250 · Medium roast · Whole bean'};
const firstEnglishCapsules={...received.current.lines[1],description:'Example · Capsules per box 10'};
assert.equal(documentDescription(firstEnglishBeans,request,'en',labels),firstEnglishBeans.description);
assert.equal(documentDescription(firstEnglishBeans,request,'zh',labels),'每袋 250 克 · 中度烘焙 · 整豆');
assert.equal(documentDescription(firstEnglishCapsules,request,'zh',labels),'Example · 每盒 10 粒');
const editedEnglish={...firstEnglishBeans,description:'Bag size (g) 250 · Medium roast · Whole bean · seasonal blend'};
assert.equal(documentDescription(editedEnglish,request,'zh',labels),editedEnglish.description);
assert.equal(documentDescription(received.current.lines[0],request,'th',labels),'ขนาดถุง (กรัม) 250 · คั่วกลาง · เต็มเมล็ด');
assert.equal(documentDescription(received.current.lines[0],request,'zh',labels),'每袋 250 克 · 中度烘焙 · 整豆');
assert.equal(documentDescription(received.current.lines[1],request,'zh',labels),'Example · 每盒 10 粒');
assert.equal(documentDescription({...received.current.lines[0],description:'Custom'},request,'th',labels),'Custom');
const zhRequest={...request,language:'zh'};
const zhQuote=requestFile(zhRequest,labels);
const oldChineseBeans={...zhQuote.current.lines[0],description:'每袋克重（克） 250 · 中焙 · 整豆'};
const oldChineseCapsules={...zhQuote.current.lines[1],description:'Example · 每盒胶囊数 10'};
const sourceLines=received.current.lines;
assert.equal(documentDescription(oldChineseBeans,zhRequest,'zh',labels),oldChineseBeans.description);
assert.equal(documentDescription(oldChineseBeans,zhRequest,'en',labels),sourceLines[0].description);
assert.equal(documentDescription(oldChineseCapsules,zhRequest,'en',labels),sourceLines[1].description);
const staffEdited={...oldChineseBeans,description:oldChineseBeans.description+'（仅限首单）'};
assert.equal(documentDescription(staffEdited,zhRequest,'en',labels),staffEdited.description);
assert.throws(()=>importData({kind:'unknown'},labels));
console.log('Quote math, version history and request import checks passed.');
