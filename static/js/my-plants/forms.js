import { announce, requestJSON } from './api.js';
import { navigate } from './navigation.js';

export function mountPlantForm() {
  const form = document.querySelector('[data-plant-form]');
  if (!form) return;
  const summary = form.querySelector('[data-form-errors]');
  const status = form.querySelector('[data-form-status]');
  const submit = form.querySelector('[type=submit]');
  const photo = form.querySelector('[data-photo-input]');
  const stage = form.elements.growth_stage;
  const syncPhoto = () => {
    photo.required = Boolean(form.dataset.originalStage && stage.value !== form.dataset.originalStage);
  };
  stage.addEventListener('change', syncPhoto);
  syncPhoto();
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (submit.disabled) return;
    summary.classList.add('d-none');
    form.querySelectorAll('[data-field-error]').forEach((node) => { node.textContent = ''; });
    form.querySelectorAll('[aria-invalid]').forEach((node) => {
      node.removeAttribute('aria-invalid'); node.classList.remove('is-invalid');
    });
    submit.disabled = true;
    form.setAttribute('aria-busy', 'true');
    status.textContent = 'Saving your plant…';
    try {
      const data = await requestJSON(form.action, { method: 'POST', body: new FormData(form) });
      status.textContent = 'Saved. Opening your plant…';
      await navigate(data.plant.url);
      announce(`${data.plant.name} saved.`);
    } catch (error) {
      // A failed navigation after a successful save must not invite duplicate creation.
      if (status.textContent.startsWith('Saved.')) {
        summary.replaceChildren(document.createTextNode('Your plant was saved. '));
        const link = document.createElement('a');
        link.href = location.pathname.endsWith('/add/') ? '/my-plants/' : location.pathname.replace(/edit\/$/, '');
        link.textContent = 'Open your garden'; summary.append(link);
      } else {
        summary.textContent = error.message;
        for (const [name, errors] of Object.entries(error.fields || {})) {
          const field = form.elements.namedItem(name);
          const node = [...form.querySelectorAll('[data-field-error]')].find((item) => item.dataset.fieldError === name);
          if (node) node.textContent = errors.map((item) => item.message).join(' ');
          if (field?.classList) { field.classList.add('is-invalid'); field.setAttribute('aria-invalid', 'true'); if (node) field.setAttribute('aria-describedby', node.id); }
        }
        status.textContent = '';
        submit.disabled = false;
      }
      summary.classList.remove('d-none');
      summary.focus();
    } finally {
      form.removeAttribute('aria-busy');
    }
  });
}
