// Progressive enhancement: each feature has an independent ES module.
import { announce, requestJSON } from './my-plants/api.js';
import { navigate, startNavigation } from './my-plants/navigation.js';
import { mountPlantForm } from './my-plants/forms.js';
import { mountBulkActions } from './my-plants/bulk.js';
import { mountCheckIns } from './my-plants/check-ins.js';

let lifetime;
function mountPage() {
  lifetime?.abort();
  lifetime = new AbortController();
  const { signal } = lifetime;
  document.documentElement.classList.add('js');
  const redirectToLogin = (response) => {
    const login = new URL(response.url);
    login.searchParams.set('next', window.location.pathname + window.location.search);
    window.location.assign(login);
  };

  // 1. Live filtering of the plant list (search, stage, status, sort, pagination).
  const filters = document.querySelector('#plant-filters');
  const results = document.querySelector('#plant-results');
  if (filters && results) {
    const status = document.querySelector('#filter-status');
    let pending;
    let timer;
    const load = async (params) => {
      pending?.abort();
      const controller = new AbortController();
      pending = controller;
      results.setAttribute('aria-busy', 'true');
      status.textContent = 'Finding your plants…';
      try {
        const response = await fetch(`${filters.dataset.fragmentUrl}?${params}`, {
          signal: controller.signal, headers: { Accept: 'text/html', 'X-Requested-With': 'fetch' },
        });
        if (response.redirected) { redirectToLogin(response); return; }
        if (!response.ok) throw new Error();
        const html = await response.text();
        if (controller.signal.aborted) return;
        results.innerHTML = html;
        results.dispatchEvent(new Event('plants:results'));
        const url = new URL(window.location.href);
        url.search = params.toString();
        window.history.replaceState({ plants: true }, '', url);
        const count = results.querySelector('[data-result-count]');
        status.textContent = count ? `${count.textContent}.` : 'Your plant list is up to date.';
      } catch (error) {
        if (error.name !== 'AbortError') status.textContent = 'Could not load your plants. Press Filter to try again.';
      } finally {
        if (pending === controller) results.removeAttribute('aria-busy');
      }
    };
    signal.addEventListener('abort', () => { pending?.abort(); clearTimeout(timer); }, { once: true });
    const params = () => {
      const data = new URLSearchParams(new FormData(filters));
      for (const [key, value] of [...data.entries()]) if (!value) data.delete(key);
      return data;
    };
    filters.addEventListener('submit', (event) => { event.preventDefault(); clearTimeout(timer); load(params()); });
    filters.addEventListener('change', (event) => { if (event.target.name !== 'q') { clearTimeout(timer); load(params()); } });
    filters.querySelector('[name=q]').addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => load(params()), 300); });
    document.addEventListener('click', (event) => {
      const reset = event.target.closest('[data-reset]');
      const page = event.target.closest('[data-page]');
      if ((!reset && !page) || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
      event.preventDefault();
      clearTimeout(timer);
      if (reset) {
        for (const field of filters.elements) {
          if (!field.name) continue;
          if (field.type === 'radio') field.checked = field.value === '';
          else field.value = field.name === 'sort' ? 'newest' : '';
        }
        load(new URLSearchParams());
      }
      else { load(new URL(page.href).searchParams); results.scrollIntoView({ behavior: 'auto', block: 'start' }); }
    }, { signal });
  }

  // 2. Change the growth stage without reloading. A new stage needs a photo (checked again on the server).
  const art = document.querySelector('[data-plant-art]');
  const photoList = document.querySelector('[data-photo-list]');
  const photoCount = document.querySelector('[data-photo-count]');
  const photoEmpty = document.querySelector('[data-photo-empty]');
  const setCover = (url, alt) => {
    if (!art || !url) return;
    let img = art.querySelector('img.mp-photo');
    if (!img) {
      art.querySelector('svg')?.remove();
      img = document.createElement('img');
      img.className = 'mp-photo';
      art.prepend(img);
    }
    img.src = url;
    img.alt = alt;
    art.classList.add('has-photo');
  };
  const addTile = (html, count) => {
    if (!photoList || !html) return;
    photoList.insertAdjacentHTML('afterbegin', html);
    if (photoCount) photoCount.textContent = `${count} photo${count === 1 ? '' : 's'} · stored privately in your account`;
    photoEmpty?.classList.add('d-none');
  };
  const resetPicker = (form) => {
    form.querySelectorAll('[data-photo-input]').forEach((input) => { input.value = ''; input.dispatchEvent(new Event('change')); });
  };

  const stageForm = document.querySelector('[data-stage-form]');
  if (stageForm) {
    const select = stageForm.elements.growth_stage;
    const badge = document.querySelector('[data-stage-badge]');
    const steps = document.querySelector('[data-stage-steps]');
    const statusBadge = document.querySelector('[data-plant-status]');
    const statusText = document.querySelector('[data-plant-status-text]');
    const photoPanel = stageForm.querySelector('[data-stage-photo]');
    const photoInput = stageForm.querySelector('[data-photo-input]');
    const error = stageForm.querySelector('[data-stage-error]');
    const recapCta = document.querySelector('[data-recap-cta]');
    const button = stageForm.querySelector('button[type=submit]');
    const syncPanel = () => {
      const changed = select.value !== stageForm.dataset.originalStage;
      const keepOpen = photoInput.classList.contains('is-invalid');
      photoPanel.hidden = !changed && !keepOpen;
      photoInput.required = changed;
    };
    syncPanel();
    select.addEventListener('change', () => { error.textContent = ''; syncPanel(); if (!photoPanel.hidden) photoInput.focus(); });
    stageForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      error.textContent = '';
      const changed = select.value !== stageForm.dataset.originalStage;
      if (changed && !photoInput.files.length) {
        photoPanel.hidden = false;
        error.textContent = 'Add a photo of the plant at its new stage.';
        photoInput.focus();
        return;
      }
      if (select.value === 'finished' && changed
          && !window.confirm('Mark this plant Finished? It stays in your garden history.')) return;
      button.disabled = true;
      try {
        const response = await fetch(stageForm.action, {
          method: 'POST', body: new FormData(stageForm), headers: { Accept: 'application/json' },
        });
        if (response.redirected) { redirectToLogin(response); return; }
        const data = await response.json();
        if (!response.ok) {
          const errors = data.errors || {};
          throw new Error(data.error || (errors.photo || errors.growth_stage || errors.caption || [{}])[0].message || 'Could not save the stage.');
        }
        const plant = data.plant;
        stageForm.dataset.originalStage = plant.growth_stage;
        badge.textContent = plant.growth_stage_label;
        badge.className = `badge mp-stage mp-stage-${plant.growth_stage} ms-1 align-middle`;
        art.className = art.className.replace(/mp-art-(growing|flowering|fruiting|harvesting|finished)/, `mp-art-${plant.growth_stage}`);
        const label = plant.status.charAt(0).toUpperCase() + plant.status.slice(1);
        statusBadge.textContent = label;
        if (statusText) statusText.textContent = label;
        for (const step of data.steps) {
          const item = steps.querySelector(`[data-step="${step.value}"]`);
          item.className = `mp-step is-${step.state}`;
          if (step.state === 'current') item.setAttribute('aria-current', 'step'); else item.removeAttribute('aria-current');
        }
        if (data.photo) {
          setCover(data.photo.url, `Latest photo of ${plant.name}`);
          addTile(data.photo_html, photoList ? photoList.children.length + 1 : 1);
        }
        resetPicker(stageForm);
        stageForm.elements.caption.value = '';
        syncPanel();
        recapCta?.classList.toggle('d-none', !data.recap_url);
        announce(`Growth stage saved: ${plant.growth_stage_label}.`);
      } catch (err) {
        error.textContent = err.message;
        announce(err.message);
      } finally {
        button.disabled = false;
      }
    });
  }

  // Add a progress photo to the diary, and delete photos.
  const photoForm = document.querySelector('[data-photo-form]');
  if (photoForm) {
    const error = photoForm.querySelector('[data-photo-error]');
    photoForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      error.textContent = '';
      if (!photoForm.querySelector('[data-photo-input]').files.length) { error.textContent = 'Choose a photo first.'; return; }
      const button = photoForm.querySelector('button[type=submit]');
      button.disabled = true;
      try {
        const response = await fetch(photoForm.action, { method: 'POST', body: new FormData(photoForm), headers: { Accept: 'application/json' } });
        if (response.redirected) { redirectToLogin(response); return; }
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || (data.errors?.photo || data.errors?.caption || [{}])[0].message || 'Could not save the photo.');
        addTile(data.html, data.count);
        setCover(data.photo.url, 'Latest photo');
        photoForm.reset();
        resetPicker(photoForm);
        announce('Photo added to the diary.');
      } catch (err) {
        error.textContent = err.message;
      } finally {
        button.disabled = false;
      }
    });
  }
  photoList?.addEventListener('submit', async (event) => {
    const form = event.target.closest('[data-photo-delete]');
    if (!form) return;
    event.preventDefault();
    const button = form.querySelector('button');
    if (button.disabled || !window.confirm('Delete this photo? It will also disappear from the recap.')) return;
    button.disabled = true;
    try {
      const data = await requestJSON(form.action, { method: 'POST', body: new FormData(form) });
      form.closest('[data-photo-tile]').remove();
      if (photoCount) photoCount.textContent = `${data.count} photo${data.count === 1 ? '' : 's'} · stored privately in your account`;
      photoEmpty?.classList.toggle('d-none', data.count > 0);
      if (data.cover_photo_url) setCover(data.cover_photo_url, 'Latest photo');
      else await navigate(location.href, { replace: true });
      announce('Photo deleted.');
    } catch (error) { announce(error.message); }
    finally { button.disabled = false; }
  });

  // Preview a chosen photo and catch files over 5 MB before uploading.
  document.querySelectorAll('[data-photo-picker]').forEach((picker) => {
    const input = picker.querySelector('[data-photo-input]');
    const preview = picker.querySelector('[data-photo-preview]');
    const help = picker.querySelector('[data-photo-help]');
    const defaultHelp = help?.textContent || '';
    let objectUrl;
    signal.addEventListener('abort', () => { if (objectUrl) URL.revokeObjectURL(objectUrl); }, { once: true });
    input?.addEventListener('change', () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      preview.querySelector('img')?.remove();
      preview.classList.add('is-empty');
      input.classList.remove('is-invalid');
      if (help) help.textContent = defaultHelp;
      const file = input.files[0];
      if (!file) return;
      if (file.size > 5 * 1024 * 1024) {
        input.value = '';
        input.classList.add('is-invalid');
        if (help) help.textContent = 'That photo is larger than 5 MB. Choose a smaller one.';
        return;
      }
      objectUrl = URL.createObjectURL(file);
      const img = document.createElement('img');
      img.src = objectUrl;
      img.alt = '';
      preview.append(img);
      preview.classList.remove('is-empty');
    });
  });

  document.querySelector('[data-print]')?.addEventListener('click', () => window.print());

  // Delete from the modal, then fetch the garden without a document reload.
  const deleteForm = document.querySelector('[data-delete-form]');
  if (deleteForm) {
    deleteForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const error = deleteForm.querySelector('[data-delete-error]');
      const button = deleteForm.querySelector('[type=submit]');
      if (button.disabled) return;
      button.disabled = true; error.classList.add('d-none');
      let deleted = false;
      try {
        await requestJSON(deleteForm.action, { method: 'POST', body: new FormData(deleteForm) });
        deleted = true;
        await navigate(deleteForm.dataset.listUrl || '/my-plants/');
        announce('Plant deleted.');
      } catch (failure) {
        error.textContent = deleted ? 'The plant was deleted. Open My Plants to refresh your garden.' : failure.message;
        error.classList.remove('d-none');
      } finally { button.disabled = deleted; }
    });
  }

  // 5. Perenual species lookup on the add / edit form.
  const lookup = document.querySelector('[data-species-lookup]');
  if (lookup) {
    const button = lookup.querySelector('[data-species-search]');
    const query = lookup.querySelector('#species-query');
    const status = lookup.querySelector('[data-species-status]');
    const list = lookup.querySelector('[data-species-results]');
    const species = document.querySelector('#id_species_name');
    const speciesId = document.querySelector('#id_perenual_species_id');
    species?.addEventListener('input', () => { speciesId.value = ''; });
    const search = async () => {
      const q = query.value.trim();
      if (q.length < 2) { status.textContent = 'Enter at least two characters.'; return; }
      const indoor = lookup.querySelector('[name=species-indoor]:checked')?.value || '';
      button.disabled = true;
      status.textContent = 'Looking up species…';
      list.replaceChildren();
      try {
        const response = await fetch(`${lookup.dataset.url}?${new URLSearchParams({ q, indoor })}`, { headers: { Accept: 'application/json' } });
        if (response.redirected) { status.textContent = 'Your session has expired. Log in again to search.'; return; }
        const data = await response.json();
        if (!response.ok) throw new Error(data.error);
        status.textContent = data.results.length ? `${data.results.length} result(s). Choose one to fill the species. Source: Perenual.` : 'No species found. Try another name or type it yourself.';
        for (const item of data.results) {
          const option = document.createElement('button');
          option.type = 'button';
          option.className = 'list-group-item list-group-item-action';
          option.textContent = item.name;
          if (item.scientific_name) {
            const small = document.createElement('small');
            small.textContent = item.scientific_name;
            option.append(small);
          }
          option.addEventListener('click', () => {
            list.querySelectorAll('.active').forEach((el) => el.classList.remove('active'));
            option.classList.add('active');
            species.value = item.name;
            speciesId.value = item.id;
            status.textContent = `${item.name} selected. Save the form to keep it.`;
          });
          list.append(option);
        }
      } catch (error) {
        status.textContent = error.message || 'Species search is unavailable right now. You can still type the species yourself.';
      } finally {
        button.disabled = false;
      }
    };
    button.addEventListener('click', search);
    query.addEventListener('keydown', (event) => { if (event.key === 'Enter') { event.preventDefault(); if (!button.disabled) search(); } });
  }
  mountPlantForm();
  mountBulkActions();
  mountCheckIns();
}

mountPage();
document.addEventListener('plants:mount', mountPage);
document.addEventListener('plants:unmount', () => lifetime?.abort());
startNavigation();
