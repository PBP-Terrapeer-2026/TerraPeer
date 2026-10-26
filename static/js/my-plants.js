// My Plants client-side interactivity (Fetch/AJAX). Every feature also works without JS.
(() => {
  document.documentElement.classList.add('js');

  const live = document.createElement('p');
  live.className = 'visually-hidden';
  live.setAttribute('role', 'status');
  live.setAttribute('aria-live', 'polite');
  document.body.append(live);
  const announce = (text) => { live.textContent = ''; window.setTimeout(() => { live.textContent = text; }, 30); };

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
        const url = new URL(window.location.href);
        url.search = params.toString();
        window.history.replaceState({}, '', url);
        const count = results.querySelector('[data-result-count]');
        status.textContent = count ? `${count.textContent}.` : 'Your plant list is up to date.';
      } catch (error) {
        if (error.name !== 'AbortError') status.textContent = 'Could not load your plants. Press Filter to try again.';
      } finally {
        if (pending === controller) results.removeAttribute('aria-busy');
      }
    };
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
      if (reset) { filters.reset(); filters.querySelector('[name=q]').value = ''; load(new URLSearchParams()); }
      else { load(new URL(page.href).searchParams); results.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
  }

  // 2. Change the growth stage without reloading the plant page.
  const stageForm = document.querySelector('[data-stage-form]');
  if (stageForm) {
    const badge = document.querySelector('[data-stage-badge]');
    const steps = document.querySelector('[data-stage-steps]');
    const art = document.querySelector('[data-plant-art]');
    const statusBadge = document.querySelector('[data-plant-status]');
    const statusText = document.querySelector('[data-plant-status-text]');
    const button = stageForm.querySelector('button[type=submit]');
    stageForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const select = stageForm.elements.growth_stage;
      if (select.value === 'finished' && stageForm.dataset.originalStage !== 'finished'
          && !window.confirm('Mark this plant Finished? It stays in your garden history and stops new care tasks.')) return;
      button.disabled = true;
      try {
        const response = await fetch(stageForm.action, {
          method: 'POST', body: new FormData(stageForm), headers: { Accept: 'application/json' },
        });
        if (response.redirected) { redirectToLogin(response); return; }
        const data = await response.json();
        if (!response.ok) throw new Error(data.errors?.growth_stage?.[0]?.message || 'Could not save the stage.');
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
        announce(`Growth stage saved: ${plant.growth_stage_label}.`);
      } catch (error) {
        announce(error.message);
        window.alert(error.message);
      } finally {
        button.disabled = false;
      }
    });
  }

  // 3. Delete from the confirmation modal; a 409 (linked records) is shown inside the modal.
  const deleteForm = document.querySelector('[data-delete-form]');
  if (deleteForm) {
    const error = deleteForm.querySelector('[data-delete-error]');
    deleteForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const response = await fetch(deleteForm.action, {
        method: 'POST', body: new FormData(deleteForm), headers: { Accept: 'application/json' },
      });
      if (response.redirected) { redirectToLogin(response); return; }
      if (response.ok) { window.location.assign(deleteForm.dataset.listUrl || '/my-plants/'); return; }
      const data = await response.json().catch(() => ({}));
      error.textContent = data.error || 'Could not delete this plant. Try again.';
      error.classList.remove('d-none');
    });
  }

  // 4. One-tap condition check-ins on the plant page.
  const checkInForm = document.querySelector('[data-check-in-form]');
  if (checkInForm) {
    const list = document.querySelector('[data-check-in-list]');
    const empty = document.querySelector('[data-check-in-empty]');
    const count = document.querySelector('[data-check-in-count]');
    const error = checkInForm.querySelector('[data-check-in-error]');
    const setCount = (n) => {
      count.textContent = `${n} check-in${n === 1 ? '' : 's'}`;
      empty.classList.toggle('d-none', n > 0);
    };
    checkInForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      error.textContent = '';
      if (!checkInForm.querySelector('[name=condition]:checked')) { error.textContent = 'Choose how the plant looks first.'; return; }
      const button = checkInForm.querySelector('button[type=submit]');
      button.disabled = true;
      try {
        const response = await fetch(checkInForm.action, {
          method: 'POST', body: new FormData(checkInForm), headers: { Accept: 'application/json' },
        });
        if (response.redirected) { redirectToLogin(response); return; }
        const data = await response.json();
        if (!response.ok) throw new Error(Object.values(data.errors || {})[0]?.[0]?.message || 'Could not save the check-in.');
        list.insertAdjacentHTML('afterbegin', data.html);
        setCount(data.count);
        checkInForm.reset();
        announce(`Check-in saved: ${data.check_in.condition_label}.`);
      } catch (err) {
        error.textContent = err.message;
      } finally {
        button.disabled = false;
      }
    });
    list.addEventListener('submit', async (event) => {
      const form = event.target.closest('[data-check-in-delete]');
      if (!form) return;
      event.preventDefault();
      const response = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } });
      if (response.redirected) { redirectToLogin(response); return; }
      if (!response.ok) { announce('Could not remove the check-in.'); return; }
      const data = await response.json();
      form.closest('[data-check-in]').remove();
      setCount(data.count);
      announce('Check-in removed.');
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
})();
