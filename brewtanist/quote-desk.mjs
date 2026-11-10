import {TYPES,UNITS,MAX_LINES,makeLine,newOffer,extendedLine,calculate,currency,validateForIssue,revise,importData,isRFQ,documentDescription} from './quote-model.mjs?v=2';

const get=id=>document.getElementById(id);
const allLabels=JSON.parse(get('quote-labels').textContent);
const seller=JSON.parse(get('quote-seller').textContent);
const form=get('offer');
const field=key=>form.elements.namedItem(key);
const langs={th:'th',en:'en',zh:'zh-Hans'};
const headerFields=['name','company','email','phone','rfq','number','issued','valid','doclang','discount','taxRate','terms'];
const projectKeys=['flavour','packaging','frequency','destination','targetDate','budget','notes'];
const backendOrigin='https://brewtanist-oem-requests.pumplcrs.chatgpt.site';
let language=document.body.dataset.lang;
let file={kind:'brewtanist-oem-quote',schemaVersion:1,current:newOffer(language),history:[],request:null};
let dirty=false, printTarget=null, received=false;
const tr=key=>allLabels[language][key];
function node(tag,text,cls) {
  const n=document.createElement(tag);
  if(text!=null)n.textContent=text;
  if(cls)n.className=cls;
  return n;
}
function note(key) {
  const isImport=key==='loaded' || key==='invalidFile';
  get('import-message').textContent=isImport?tr(key):'';
  get('messages').textContent=key && !isImport?tr(key):'';
}
function button(title,action) {
  const b=node('button',title);
  b.type='button';b.addEventListener('click',action);return b;
}
function labeled(caption,control) {
  const label=node('label');
  label.append(node('span',caption),control);return label;
}
function readHeader() {
  for(const key of headerFields)file.current[key]=field(key).value;
}
function tableValue(dl,label,value) {dl.append(node('dt',label),node('dd',value));}
function amountWithUnit(value,lang) {
  return currency(value,lang)+' '+allLabels[lang].baht;
}
function showTotals() {
  const q=file.current, t=allLabels[language], out=get('totals');
  const prices={};
  try {Object.assign(prices,calculate(q));} catch { /* Incomplete rows remain visibly unpriced. */ }
  out.replaceChildren();
  for(const key of ['subtotal','discount','tax','total']) {
    tableValue(out,t[key],prices[key]==null?'—':amountWithUnit(prices[key],language));
  }
  for (let i=0;i<q.lines.length;i++) {
    const output=get('lines').children[i]?.querySelector('output');if(!output)continue;
    try {output.value=amountWithUnit(extendedLine(q.lines[i]),language);} catch {output.value='—';}
  }
}
function makeSelect(options,selected,onChange) {
  const s=document.createElement('select');
  for(const key of options)s.append(new Option(tr(key),key));
  s.value=selected;s.addEventListener('change',()=>onChange(s.value));return s;
}
function makeInput(value,onInput,settings={}) {
  const el=document.createElement('input');
  Object.assign(el,settings);el.value=value;
  el.addEventListener('input',()=>onInput(el.value));return el;
}
function drawLines() {
  const outer=get('lines');outer.replaceChildren();
  file.current.lines.forEach((line,i)=>{
    const edit=key=>value=>{line[key]=value;dirty=true;note();showTotals();};
    const row=node('section',null,'quote-line');
    const top=node('div',null,'line-fields');
    let unitSelect;
    const typeSelect=makeSelect(TYPES,line.type,value=>{
      line.type=value;line.unit=makeLine(value).unit;unitSelect.value=line.unit;dirty=true;note();showTotals();
    });
    unitSelect=makeSelect(UNITS,line.unit,edit('unit'));
    const qty=makeInput(line.qty,edit('qty'),{type:'number',step:'.001',min:'.001',max:'999999999.999',inputMode:'decimal',required:true});
    const price=makeInput(line.price,edit('price'),{type:'number',step:'.01',min:'0',max:'9999999999.99',inputMode:'decimal',required:true});
    top.append(labeled(tr('type'),typeSelect),labeled(tr('qty'),qty),labeled(tr('unit'),unitSelect),labeled(tr('unitPrice'),price));
    const desc=makeInput(documentDescription(line,file.request,language,allLabels),edit('description'),{maxLength:1000});
    const descLabel=labeled(tr('desc'),desc);descLabel.className='description';
    const foot=node('div',null,'line-foot'), money=node('span');
    money.append(document.createTextNode(tr('lineTotal')+' '),node('output','—'));
    const remove=button(tr('remove'),()=>{
      if(file.current.lines.length<2)return;
      file.current.lines.splice(i,1);dirty=true;drawLines();showTotals();
    });
    remove.disabled=file.current.lines.length===1;
    foot.append(money,remove);row.append(top,descLabel,foot);outer.append(row);
  });
}
function drawSource() {
  const request=file.request,list=get('source-list');
  get('source-panel').hidden=!request;list.replaceChildren();if(!request)return;
  tableValue(list,tr('rfq'),request.reference);
  for(const key of projectKeys) {
    const value=request.project[key];if(!value)continue;
    const frequencyLabel = value === 'discuss' ? 'undecided' : value;
    tableValue(list,tr(key),key==='frequency'&&['undecided','once','monthly','other'].includes(frequencyLabel)?tr(frequencyLabel):value);
  }
  const b=request.products.beans, c=request.products.capsules;
  if(b) {
    tableValue(list,tr('beans'),String(b.quantityKg)+' '+tr('kg'));
    if(b.packGrams)tableValue(list,tr('packGrams'),String(b.packGrams));
    tableValue(list,tr('roast'),tr(b.roast));tableValue(list,tr('grind'),tr(b.grind));
  }
  if(c) {
    tableValue(list,tr('capsules'),String(c.quantityUnits)+' '+tr('capsule'));
    if(c.perBox)tableValue(list,tr('perBox'),String(c.perBox));
    if(c.system)tableValue(list,tr('system'),c.system);
  }
}
function drawHistory() {
  const hist=get('history');hist.replaceChildren();
  if(!file.history.length){hist.append(node('li',tr('emptyHistory')));return;}
  for(const q of [...file.history].reverse()) {
    const value=amountWithUnit(calculate(q).total,language);
    const li=node('li',q.number+' · '+tr('revisionText').replace('{n}',q.revision)+' · '+q.issued+' · '+value+' ');
    li.append(button(tr('prior'),()=>printOffer(q)));hist.append(li);
  }
}
function render() {
  const q=file.current;
  for(const key of headerFields)field(key).value=q[key];
  field('revision').value=q.revision;field('number').readOnly=file.history.length>0;
  drawLines();drawHistory();drawSource();showTotals();updateEmailButton();
}
function switchLanguage(next,push) {
  if(!(next in langs))return;
  language=next;document.body.dataset.lang=next;document.documentElement.lang=langs[next];
  for(const n of document.querySelectorAll('[data-t]'))n.textContent=tr(n.dataset.t);
  const prefix=next==='th'?'':'/'+next;
  get('guide-link').href=prefix+'/admin/';
  get('private-inbox').href=backendOrigin+'/staff/?lang='+next;
  for(const a of get('ui-locales').querySelectorAll('a')) {
    if(a.dataset.lang===next)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');
  }
  get('ui-locales').setAttribute('aria-label',tr('language'));
  document.title=tr('title')+' | Brewtanist';note();render();
  if(push)history.pushState({language:next},'',prefix+'/admin/quotes/');
}
get('ui-locales').addEventListener('click',event=>{
  const a=event.target.closest('a[data-lang]');
  if(!a || event.ctrlKey || event.shiftKey || event.metaKey || event.altKey)return;
  event.preventDefault();if(a.dataset.lang!==language)switchLanguage(a.dataset.lang,true);
});
window.addEventListener('popstate',()=>switchLanguage(location.pathname.startsWith('/en/')?'en':location.pathname.startsWith('/zh/')?'zh':'th',false));
function updateEmailButton() {
  const email=field('email');
  get('compose').disabled=!email.value.trim() || !email.validity.valid || /[\r\n,;?&]/.test(email.value);
}
form.addEventListener('submit',e=>e.preventDefault());
form.addEventListener('input',()=>{dirty=true;readHeader();note();showTotals();updateEmailButton();});
form.addEventListener('change',()=>{dirty=true;readHeader();showTotals();updateEmailButton();});
get('add').addEventListener('click',()=>{
  if(file.current.lines.length>=MAX_LINES){note('max');return;}
  file.current.lines.push(makeLine('service'));dirty=true;drawLines();showTotals();
  get('lines').lastElementChild.querySelector('select').focus();
});
function currentIsReady() {
  readHeader();note();
  if(!form.reportValidity())return false;
  try{validateForIssue(file.current);return true;}catch(e){note(e.message);return false;}
}
function prepareDocument(q) {
  const t=allLabels[q.doclang], doc=get('document');
  const c=calculate(q), money=value=>amountWithUnit(value,q.doclang);
  doc.replaceChildren();doc.lang=langs[q.doclang];doc.setAttribute('aria-label',t.quotation);
  const head=node('header');head.append(node('h1',t.quotation));
  const meta=node('div',null,'doc-meta');
  for(const [key,value] of [['number',q.number],['revision',q.revision],['issued',q.issued],['valid',q.valid],['rfq',q.rfq]]) {
    if(value)meta.append(node('span',key==='revision'?t.revisionText.replace('{n}',value):t[key]+' '+value));
  }
  head.append(meta);doc.append(head);
  const sender=node('section',null,'doc-contact');sender.append(node('h2',t.provider),node('strong',seller.brand),node('p',seller.address[q.doclang]),node('p',(q.doclang==='zh' ? seller.phoneZh : seller.phone)+' · brewtanist@gmail.com'));
  const customer=node('section',null,'doc-contact');customer.append(node('h2',t.billed),node('strong',[q.company,q.name].filter(Boolean).join(' · ')));
  const reach=[q.email,q.phone].filter(Boolean);if(reach.length)customer.append(node('p',reach.join(' · ')));
  doc.append(sender,customer);
  const table=node('table'),thead=node('thead'),titles=node('tr');
  for(const key of ['desc','qty','unit','unitPrice','lineTotal']){const h=node('th',t[key]);h.scope='col';titles.append(h);}
  thead.append(titles);table.append(thead);
  const tbody=node('tbody');
  q.lines.forEach((line,i)=>{
    const row=node('tr'),description=node('td');
    description.append(node('strong',t[line.type]));
    if(line.description)description.append(node('p',documentDescription(line,file.request,q.doclang,allLabels),'doc-copy'));
    row.append(description,node('td',line.qty),node('td',t[line.unit]),node('td',currency(extendedLine({...line,qty:'1'}),q.doclang)),node('td',currency(c.amounts[i],q.doclang)));tbody.append(row);
  });
  table.append(tbody);doc.append(table);
  const totals=node('dl',null,'totals doc-money');
  tableValue(totals,t.subtotal,money(c.subtotal));
  if(c.discount>0n)tableValue(totals,t.discount,money(c.discount));
  if(q.taxRate!=='' && Number(q.taxRate)>0)tableValue(totals,t.tax+' ('+q.taxRate+'%)',money(c.tax));
  tableValue(totals,t.total,money(c.total));doc.append(totals);
  if(q.terms.trim())doc.append(node('h2',t.termsShort),node('p',q.terms,'doc-copy'));
}
function printOffer(offer) {printTarget=offer;prepareDocument(offer);window.print();}
get('print').addEventListener('click',()=>{if(currentIsReady())printOffer(file.current);});
window.addEventListener('beforeprint',()=>{
  const q=printTarget||file.current;
  try{validateForIssue(q);prepareDocument(q);}catch(e){get('document').replaceChildren(node('p',tr(e.message),'empty'));}
});
window.addEventListener('afterprint',()=>{printTarget=null;});
get('compose').addEventListener('click',()=>{
  if(!currentIsReady() || get('compose').disabled)return;
  const q=file.current,t=allLabels[q.doclang],subject=t.quotation+' '+q.number+' · '+t.revisionText.replace('{n}',q.revision);
  const body=[subject,q.rfq?t.rfq+' '+q.rfq:'',t.draftBody,seller.brand].filter(Boolean).join('\n\n');
  const email=q.email.trim().split('@').map(encodeURIComponent).join('@');
  location.href='mailto:'+email+'?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(body);
});
get('new-revision').addEventListener('click',()=>{
  if(!currentIsReady())return;
  try{revise(file);dirty=true;render();note('newDone');}catch(e){note(e.message);}
});
get('save').addEventListener('click',()=>{
  readHeader();
  const blob=new Blob([JSON.stringify(file,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob),a=node('a');
  const safeNumber=file.current.number.replace(/[^a-z0-9_.-]/gi,'_').slice(0,80)||'OEM';
  a.href=url;a.download=safeNumber+'-R'+file.current.revision+'.json';document.body.append(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),30000);dirty=false;note('saved');
});
function openData(data) {
  const parsed=importData(data,allLabels);
  if(dirty && !window.confirm(tr('replace')))return;
  file=parsed;dirty=data.kind==='brewtanist-oem-rfq';printTarget=null;render();note('loaded');
}
get('open-file').addEventListener('click',()=>get('file').click());
get('file').addEventListener('change',async event=>{
  const input=event.target,selected=input.files[0];
  input.value='';if(!selected)return;
  try{if(selected.size>24*1024*1024)throw Error();openData(JSON.parse(await selected.text()));}
  catch{note('invalidFile');}
});
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
get('quote-app').hidden=false;render();
if(window.opener) {
  const origins=[location.origin,backendOrigin];
  window.addEventListener('message',event=>{
    if(received || event.source!==window.opener || !origins.includes(event.origin) || event.data?.type!=='brewtanist-open-rfq')return;
    if(!isRFQ(event.data.rfq)){note('invalidFile');return;}
    received=true;openData(event.data.rfq);
  });
  for(const origin of origins)window.opener.postMessage({type:'brewtanist-quote-ready'},origin);
}
