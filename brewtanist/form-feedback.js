(() => {
  const form = document.querySelector('#oem-form, #offer');
  if (!form) return;
  let field, message;

  function clear() {
    if (!message) return;
    const ids = (field.getAttribute('aria-describedby') || '').split(/\s+/)
      .filter(id => id && id !== message.id);
    if (ids.length) field.setAttribute('aria-describedby', ids.join(' '));
    else field.removeAttribute('aria-describedby');
    message.remove();
    message = null;
  }

  const copy = {
    en: {
      date: 'Enter a valid date.', number: 'Enter a number.', choose: 'Choose an option.',
      required: 'Fill in this field.', email: 'Enter a valid email address.',
      fromDate: n => `Choose ${n} or a later date.`,
      minimum: n => `Enter ${n} or more.`, maximum: n => `Enter ${n} or less.`,
      whole: 'Enter a whole number.',
      precision: n => `Use no more than ${n} decimal ${n === 1 ? 'place' : 'places'}.`,
      format: 'Check the format of this field.'
    },
    'zh-Hans': {
      date: '请输入有效日期。', number: '请输入有效数字。', choose: '请选择一项。',
      required: '请填写此项。', email: '请填写有效的邮箱地址。',
      fromDate: n => `请选择 ${n} 或之后的日期。`,
      minimum: n => `数值不能小于 ${n}。`, maximum: n => `数值不能大于 ${n}。`,
      whole: '请输入整数。', precision: n => `最多可填写 ${n} 位小数。`,
      format: '请检查此项的填写格式。'
    }
  };

  function description(input, labels) {
    const v = input.validity;
    if (v.customError) return input.validationMessage;
    if (v.badInput) return input.type === 'date' ? labels.date : labels.number;
    if (v.valueMissing) return input.type === 'radio' ? labels.choose : labels.required;
    if (v.typeMismatch && input.type === 'email') return labels.email;
    if (v.rangeUnderflow) return input.type === 'date' ? labels.fromDate(input.min) : labels.minimum(input.min);
    if (v.rangeOverflow) return labels.maximum(input.max);
    if (v.stepMismatch) {
      if (input.step === '1') return labels.whole;
      const decimals = (input.step.split('.')[1] || '').length;
      if (decimals) return labels.precision(decimals);
    }
    return labels.format;
  }

  form.addEventListener('invalid', event => {
    const lang = document.documentElement.lang;
    const labels = copy[lang];
    if (!labels) return;
    event.preventDefault();
    // A single submit can report several fields. Show the first one in DOM order.
    if (event.target !== form.querySelector('input:invalid, select:invalid, textarea:invalid')) return;
    clear();
    field = event.target;
    message = document.createElement('small');
    message.id = (lang === 'en' ? 'en' : 'zh') + '-field-feedback';
    message.setAttribute('role', 'alert');
    message.textContent = description(field, labels);
    field.insertAdjacentElement('afterend', message);
    const ids = [field.getAttribute('aria-describedby'), message.id].filter(Boolean);
    field.setAttribute('aria-describedby', ids.join(' '));
    field.focus();
  }, true);

  form.addEventListener('input', clear);
  form.addEventListener('change', clear);
  document.addEventListener('click', clear, true);
  window.addEventListener('popstate', clear);
})();
