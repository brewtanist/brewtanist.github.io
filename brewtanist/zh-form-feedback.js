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

  function description(input) {
    const v = input.validity;
    if (v.customError) return input.validationMessage;
    if (v.badInput) return input.type === 'date' ? '请输入有效日期。' : '请输入有效数字。';
    if (v.valueMissing) return input.type === 'radio' ? '请选择一项。' : '请填写此项。';
    if (v.typeMismatch && input.type === 'email') return '请填写有效的邮箱地址。';
    if (v.rangeUnderflow) return input.type === 'date' ? '请选择 ' + input.min + ' 或之后的日期。' : '数值不能小于 ' + input.min + '。';
    if (v.rangeOverflow) return '数值不能大于 ' + input.max + '。';
    if (v.stepMismatch) {
      if (input.step === '1') return '请输入整数。';
      const decimals = (input.step.split('.')[1] || '').length;
      if (decimals) return '最多可填写 ' + decimals + ' 位小数。';
    }
    return '请检查此项的填写格式。';
  }

  form.addEventListener('invalid', event => {
    if (document.documentElement.lang !== 'zh-Hans') return;
    event.preventDefault();
    // A single submit can report several fields. Show the first one in DOM order.
    if (event.target !== form.querySelector('input:invalid, select:invalid, textarea:invalid')) return;
    clear();
    field = event.target;
    message = document.createElement('small');
    message.id = 'zh-field-feedback';
    message.setAttribute('role', 'alert');
    message.textContent = description(field);
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
