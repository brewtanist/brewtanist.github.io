"use strict";
(() => {
  const form = document.querySelector("#oem-form");
  if (!form) return;
  const root = document.querySelector("main[data-language]");
  const copy = JSON.parse(document.getElementById("oem-text").textContent);
  const chinese = root.dataset.language === "zh";
  const fieldSeparator = chinese ? "：" : ": ";
  const quantityWithUnit = (number, unit) => number + (chinese ? "" : " ") + unit;
  const review = document.getElementById("oem-review");
  const title = document.getElementById("oem-review-title");
  const summary = document.getElementById("oem-summary");
  const status = document.getElementById("oem-status");
  const send = document.getElementById("oem-submit");
  const edit = document.getElementById("oem-edit");
  const emailLink = document.getElementById("oem-email");
  const input = name => form.elements.namedItem(name);
  const value = name => input(name).value.trim();
  const optionalNumber = name => value(name) === "" ? null : Number(value(name));
  const draftKey = "brewtanist-oem-language-transfer-v1";
  let request;
  let fingerprint;
  let confirmed = false;
  let pending = false;

  function localDate() {
    const now = new Date();
    const part = n => String(n).padStart(2, "0");
    return [now.getFullYear(), part(now.getMonth() + 1), part(now.getDate())].join("-");
  }
  function reference() {
    const bytes = crypto.getRandomValues(new Uint8Array(4));
    const hex = Array.from(bytes, b => b.toString(16).padStart(2, "0")).join("").toUpperCase();
    return "RFQ-" + localDate().replaceAll("-", "") + "-" + hex;
  }
  function selectProducts() {
    const type = value("productType");
    for (const kind of ["beans", "capsules"]) {
      const group = document.getElementById("oem-" + kind);
      group.hidden = group.disabled = type !== kind && type !== "both";
    }
  }
  function validate() {
    const phone = value("phone");
    const digits = phone.replace(/\D/g, "");
    input("name").setCustomValidity(value("name") ? "" : copy.invalid_name);
    input("email").setCustomValidity(!phone && !value("email") ? copy.invalid_contact : "");
    input("phone").setCustomValidity(phone && (!/^[+\d\s().-]+$/.test(phone) || digits.length < 7 || digits.length > 18) ? copy.invalid_phone : "");
    input("targetDate").min = localDate();
    return form.reportValidity();
  }
  function getValues() {
    const type = value("productType");
    const products = {};
    if (type !== "capsules") {
      products.beans = {quantityKg: Number(value("beanQuantity")), packGrams: optionalNumber("packGrams"), roast: value("roast"), grind: value("grind")};
    }
    if (type !== "beans") {
      products.capsules = {quantityUnits: Number(value("capsuleQuantity")), system: value("system"), perBox: optionalNumber("perBox")};
    }
    const strings = keys => Object.fromEntries(keys.map(k => [k, value(k)]));
    return {
      language: root.dataset.language,
      contact: strings(["name", "company", "email", "phone"]),
      products,
      project: strings(["flavour", "packaging", "frequency", "destination", "targetDate", "budget", "notes"])
    };
  }
  function formatBrief(rfq) {
    const lines = [copy.title, copy.reference + fieldSeparator + rfq.reference];
    const line = (label, text) => { if (text !== null && text !== undefined && text !== "") lines.push(label + fieldSeparator + text); };
    const beans = rfq.products.beans;
    if (beans) {
      lines.push("", copy.beans);
      line(copy.quantity, quantityWithUnit(beans.quantityKg, copy.kg));
      line(copy.grams, beans.packGrams);
      line(copy.roast, copy[beans.roast]);
      line(copy.grind, copy[beans.grind]);
    }
    const capsules = rfq.products.capsules;
    if (capsules) {
      lines.push("", copy.capsules);
      line(copy.quantity, quantityWithUnit(capsules.quantityUnits, copy.units));
      line(copy.system, capsules.system);
      line(copy.per_box, capsules.perBox);
    }
    lines.push("", copy.project);
    const p = rfq.project;
    line(copy.flavour, p.flavour); line(copy.packaging, p.packaging);
    line(copy.frequency, p.frequency === "discuss" ? copy.undecided : copy[p.frequency]);
    line(copy.destination, p.destination); line(copy.date, p.targetDate);
    line(copy.budget, p.budget); line(copy.notes, p.notes);
    lines.push("", copy.contact);
    for (const [key, text] of Object.entries(rfq.contact)) line(copy[key], text);
    return lines.join("\n");
  }
  function configureEmail(showFallback = false) {
    const address = root.dataset.email;
    if (!address || (root.dataset.endpoint && !showFallback) || confirmed) {
      emailLink.hidden = true;
      document.getElementById("oem-email-help").hidden = true;
      return;
    }
    const prefix = "mailto:" + address + "?subject=" + encodeURIComponent(copy.short_name + " · " + request.reference) + "&body=";
    const complete = prefix + encodeURIComponent(summary.value);
    const attach = complete.length > 1900;
    const short = [copy.email_body, request.reference, request.contact.name, request.contact.email || request.contact.phone];
    if (request.products.beans) short.push(copy.beans + fieldSeparator + quantityWithUnit(request.products.beans.quantityKg, copy.kg));
    if (request.products.capsules) short.push(copy.capsules + fieldSeparator + quantityWithUnit(request.products.capsules.quantityUnits, copy.units));
    emailLink.href = attach ? prefix + encodeURIComponent(short.join("\n")) : complete;
    emailLink.hidden = false;
    emailLink.className = root.dataset.endpoint ? "oem-link" : "btn";
    document.getElementById("oem-email-help").hidden = !attach;
  }
  function startReview() {
    const fields = getValues();
    const signature = JSON.stringify(fields);
    if (!request || signature !== fingerprint) {
      request = {kind: "brewtanist-oem-rfq", schemaVersion: 1, reference: reference(), createdAt: new Date().toISOString(), ...fields};
      fingerprint = signature;
      confirmed = false;
    }
    summary.value = formatBrief(request);
    document.getElementById("oem-ref").textContent = request.reference;
    document.getElementById("oem-next").textContent = confirmed ? copy.success : root.dataset.endpoint ? copy.review_online : root.dataset.email ? copy.manual_email : copy.manual;
    title.textContent = confirmed ? copy.sent_title : copy.result;
    send.hidden = !root.dataset.endpoint || confirmed;
    status.textContent = "";
    configureEmail();
    form.hidden = true;
    review.hidden = false;
    title.focus();
    title.scrollIntoView({block:"start"});
  }
  function resumeForm() {
    if (pending) return;
    review.hidden = true;
    form.hidden = false;
    const first = form.querySelector("input[name=productType]:checked");
    first.focus();
    first.scrollIntoView({block: "center"});
  }
  function rememberLanguageTransition(link) {
    if (!link || !link.href || pending || confirmed) return;
    const target = new URL(link.href);
    if (target.origin !== location.origin || target.pathname === location.pathname) return;
    // Transient handoff only when the visitor explicitly switches this form's language.
    const fields = [...form.querySelectorAll("input,select,textarea")].filter(el => el.type !== "radio" || el.checked);
    const values = Object.fromEntries(fields.map(el => [el.name, el.value]));
    try { sessionStorage.setItem(draftKey, JSON.stringify({at: Date.now(), path: target.pathname, values})); } catch { /* Storage may be disabled. */ }
  }
  function restoreLanguageTransition() {
    try {
      const raw = sessionStorage.getItem(draftKey);
      if (!raw) return;
      sessionStorage.removeItem(draftKey);
      const prior = JSON.parse(raw);
      if (prior.path !== location.pathname || Date.now() - prior.at > 180000) return;
      for (const elem of form.querySelectorAll("input,select,textarea")) {
        const text = prior.values[elem.name];
        if (typeof text !== "string") continue;
        if (elem.type === "radio") elem.checked = elem.value === text;
        else elem.value = text;
      }
    } catch { /* Use the blank form if storage or the draft is unavailable. */ }
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    if (validate()) startReview();
  });
  form.addEventListener("input", event => {
    event.target.setCustomValidity?.("");
    if (event.target.name === "phone" || event.target.name === "email") {
      input("email").setCustomValidity("");
      input("phone").setCustomValidity("");
    }
  });
  form.addEventListener("change", event => { if (event.target.name === "productType") selectProducts(); });
  edit.addEventListener("click", resumeForm);
  document.querySelector("[data-language-menu]")?.addEventListener("click", event => {
    if (!event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) rememberLanguageTransition(event.target.closest("a"));
  });
  document.getElementById("oem-copy").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(summary.value);
      status.textContent = copy.copied;
    } catch {
      summary.focus(); summary.select(); status.textContent = copy.copy_hint;
    }
  });
  document.getElementById("oem-download").addEventListener("click", () => {
    if (!request) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(request, null, 2) + "\n"], {type:"application/json"}));
    const a = document.createElement("a");
    a.href = url; a.download = request.reference + ".json";
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  send.addEventListener("click", async () => {
    if (!request || pending || confirmed || !root.dataset.endpoint) return;
    pending = true; send.disabled = true; edit.disabled = true;
    status.textContent = copy.pending;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(root.dataset.endpoint, {
        method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(request),
        credentials: "omit", referrerPolicy: "no-referrer", signal: controller.signal
      });
      if (!response.ok) {
        if (response.status === 409) {
          request.reference = reference();
          startReview();
        }
        const reason = {409: copy.ref_conflict, 413: copy.too_large, 422: copy.invalid_request, 429: copy.rate_limit};
        const problem = new Error("Intake unavailable");
        problem.display = reason[response.status];
        throw problem;
      }
      const receipt = await response.json();
      if (receipt.ok !== true || receipt.reference !== request.reference) throw Error("Receipt could not be verified");
      confirmed = true; send.hidden = true; edit.hidden = true; configureEmail();
      title.textContent = copy.sent_title; title.focus();
      document.getElementById("oem-next").textContent = copy.success;
      status.textContent = "";
    } catch (error) { configureEmail(true); status.textContent = error.display || copy.failed; }
    finally { clearTimeout(timer); pending = false; send.disabled = false; edit.disabled = false; }
  });
  input("targetDate").min = localDate();
  restoreLanguageTransition();
  selectProducts();
  form.hidden = false;
})();
