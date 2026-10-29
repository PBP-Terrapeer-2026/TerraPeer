import { announce, requestJSON } from './api.js';

export function mountCheckIns() {
  const form = document.querySelector('[data-check-in-form]');
  if (!form) return;
  const list = document.querySelector('[data-check-in-list]');
  const count = document.querySelector('[data-check-in-count]');
  const empty = document.querySelector('[data-check-in-empty]');
  const error = form.querySelector('[data-check-in-error]');
  let busy = false;
  const setCount = (value) => {
    count.textContent = `${value} check-in${value === 1 ? '' : 's'}`;
    empty.classList.toggle('d-none', value > 0);
  };
  const lock = (value) => {
    busy = value;
    form.querySelector('[type=submit]').disabled = value;
    list.querySelectorAll('button').forEach((button) => { button.disabled = value; });
  };
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (busy) return;
    error.textContent = '';
    const selected = form.querySelector('[name=condition]:checked');
    if (!selected) { error.textContent = 'Choose how the plant looks first.'; return; }
    const previous = parseInt(count.textContent, 10);
    const pending = document.createElement('li');
    pending.className = 'list-group-item mp-pending';
    pending.dataset.pendingCheckIn = '';
    pending.textContent = `${form.querySelector(`label[for="${selected.id}"]`).textContent.trim()} · Saving…`;
    pending.setAttribute('aria-busy', 'true');
    list.prepend(pending); setCount(previous + 1); lock(true);
    try {
      const data = await requestJSON(form.action, { method: 'POST', body: new FormData(form) });
      pending.outerHTML = data.html;
      setCount(data.count); form.reset();
      announce(`Check-in saved: ${data.check_in.condition_label}.`);
    } catch (failure) {
      pending.remove(); setCount(previous);
      error.textContent = failure.message;
      announce(`Check-in was not saved. ${failure.message}`);
    } finally { lock(false); }
  });
  list.addEventListener('submit', async (event) => {
    const deletion = event.target.closest('[data-check-in-delete]');
    if (!deletion) return;
    event.preventDefault();
    if (busy) return;
    const row = deletion.closest('[data-check-in]');
    const previous = parseInt(count.textContent, 10);
    error.textContent = ''; row.hidden = true; setCount(previous - 1); lock(true);
    try {
      const data = await requestJSON(deletion.action, { method: 'POST', body: new FormData(deletion) });
      row.remove(); setCount(data.count); announce('Check-in removed.');
    } catch (failure) {
      row.hidden = false; setCount(previous); error.textContent = failure.message;
      announce('Could not remove the check-in.');
    } finally { lock(false); }
  });
}
