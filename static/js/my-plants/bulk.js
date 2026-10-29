import { announce, requestJSON } from './api.js';
import { navigate } from './navigation.js';

export function mountBulkActions() {
  const results = document.querySelector('#plant-results');
  if (!results) return;
  results.addEventListener('change', (event) => syncSelection(results, event.target));
  results.addEventListener('submit', async (event) => {
    const form = event.target.closest('[data-bulk-form]');
    if (!form) return;
    event.preventDefault();
    const selected = [...form.querySelectorAll('[name=plant_ids]:checked')];
    const error = form.querySelector('[data-bulk-error]');
    if (!selected.length || form.getAttribute('aria-busy') === 'true') return;
    if (!window.confirm(`Permanently delete ${selected.length} selected plant(s), including their photos and check-ins?`)) return;
    const body = new FormData(form);
    const cards = selected.map((input) => input.closest('.col'));
    const button = form.querySelector('[type=submit]');
    error.textContent = '';
    form.setAttribute('aria-busy', 'true'); button.disabled = true;
    cards.forEach((card) => { card.hidden = true; });
    announce(`Deleting ${selected.length} plants…`);
    let committed = false;
    try {
      const data = await requestJSON(form.action, { method: 'POST', body });
      committed = true;
      await navigate(location.href, { replace: true });
      announce(`${data.deleted_count} plants deleted.`);
    } catch (failure) {
      if (!committed) cards.forEach((card) => { card.hidden = false; });
      error.textContent = committed ? 'Plants were deleted. Refresh the garden to update this list.' : failure.message;
      announce(`Deletion could not finish. ${failure.message}`);
    } finally {
      form.removeAttribute('aria-busy'); button.disabled = committed;
    }
  });
}

function syncSelection(results, target) {
  const all = results.querySelector('[data-select-page]');
  const inputs = [...results.querySelectorAll('[name=plant_ids]')];
  if (!all) return;
  // The change target identifies a page-wide selection, while individual changes update its mixed state.
  if (target === all) inputs.forEach((input) => { input.checked = all.checked; });
  const count = inputs.filter((input) => input.checked).length;
  all.checked = count > 0 && count === inputs.length;
  all.indeterminate = count > 0 && count < inputs.length;
  results.querySelector('[data-selected-count]').textContent = `${count} selected`;
}
