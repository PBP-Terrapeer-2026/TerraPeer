/* Tutorial 5: Fetch + FormData. Django remains the source of truth. */
(() => {
    const main = document.getElementById('main-content');
    if (!main?.dataset.listUrl) return;
    const root = document.getElementById('modal-root');
    const filters = document.getElementById('filters');
    let listRequest, weatherRequest, dialogRequest, opener, busy = false;
    const csrf = () => document.querySelector('[name=csrfmiddlewaretoken]').value;

    function message(text, error = false) {
        const node = document.getElementById('feedback');
        node.textContent = text; // Never render user text through innerHTML.
        node.hidden = false;
        node.classList.toggle('error', error);
    }
    async function request(url, options = {}) {
        const response = await fetch(url, {
            credentials: 'same-origin',
            ...options,
            headers: {
                'Accept': 'application/json',
                ...(options.method === 'POST' ? {
                    'X-CSRFToken': csrf()
                } : {}),
                ...options.headers
            }
        });
        const data = await response.json().catch(() => ({}));
        if (response.status === 401) {
            message('Your session expired. Sign in again; your open form has not been cleared.', true);
            const link = document.createElement('a');
            link.textContent = ' Sign in';
            link.href = '/accounts/login/?next=' + encodeURIComponent(location.pathname);
            document.getElementById('feedback').append(link);
        }
        return {
            response,
            data
        };
    }

    function responseError(response, data) {
        return data.message || (response.status === 403 ? 'Request rejected. Refresh the page and sign in again.' : `Request failed (${response.status}). Please try again.`);
    }
    async function refreshList() {
        listRequest?.abort();
        listRequest = new AbortController();
        const node = document.getElementById('task-list');
        node.setAttribute('aria-busy', 'true');
        try {
            const query = new URLSearchParams(new FormData(filters));
            const {
                response,
                data
            } = await request(main.dataset.listUrl + '?' + query, {
                signal: listRequest.signal
            });
            if (!response.ok) throw new Error(responseError(response, data));
            node.innerHTML = data.html; // Trusted, autoescaped Django template fragment.
            document.getElementById('pending-count').textContent = data.pending_count + ' pending';
        } catch (error) {
            if (error.name !== 'AbortError') message(error.message || 'Could not refresh tasks.', true);
        } finally {
            node.removeAttribute('aria-busy');
        }
    }
    async function refreshWeather(day = 0) {
        weatherRequest?.abort();
        weatherRequest = new AbortController();
        const node = document.getElementById('weather-slot');
        node.setAttribute('aria-busy', 'true');
        try {
            const {
                response,
                data
            } = await request(main.dataset.weatherUrl + '?day=' + day, {
                signal: weatherRequest.signal
            });
            if (data.html) node.innerHTML = data.html; // Includes server-rendered 503 error/retry state.
            else if (!response.ok) throw new Error(responseError(response, data));
        } catch (error) {
            if (error.name === 'AbortError') return;
            node.replaceChildren();
            const section = document.createElement('section');
            section.className = 'panel weather';
            const h = document.createElement('h2');
            h.textContent = 'Forecast unavailable';
            const p = document.createElement('p');
            p.textContent = 'Your care tasks are still available.';
            const retry = document.createElement('button');
            retry.className = 'btn secondary';
            retry.dataset.weather = '0';
            retry.textContent = 'Try again';
            section.append(h, p, retry);
            node.append(section);
        } finally {
            node.removeAttribute('aria-busy');
        }
    }

    function syncRepeat() {
        const select = root.querySelector('[name=repeat]');
        if (!select) return;
        const show = select.value === 'every';
        root.querySelector('#interval-field').hidden = !show;
        root.querySelector('#repeat-hint').hidden = !show;
        const field = root.querySelector('[name=interval]');
        field.required = show;
        field.disabled = !show;
    }

    function fillDialog(html, validation = false) {
        root.innerHTML = '<div class="backdrop"><section class="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title"></section></div>';
        root.querySelector('.dialog').innerHTML = html;
        document.body.style.overflow = 'hidden';
        main.inert = true;
        document.querySelector('header').inert = true;
        syncRepeat();
        const focus = validation ? root.querySelector('[aria-invalid=true]') : root.querySelector('input:not([type=hidden]), select, button');
        focus?.focus();
    }
    async function openDialog(url) {
        if (busy) return;
        if (!root.contains(document.activeElement)) opener = document.activeElement;
        dialogRequest?.abort();
        dialogRequest = new AbortController();
        try {
            const {
                response,
                data
            } = await request(url, {
                signal: dialogRequest.signal
            });
            if (!response.ok) throw new Error(responseError(response, data));
            fillDialog(data.html);
        } catch (error) {
            if (error.name !== 'AbortError') message(error.message, true)
        }
    }

    function closeDialog() {
        if (busy) return;
        dialogRequest?.abort();
        root.replaceChildren();
        document.body.style.overflow = '';
        main.inert = false;
        document.querySelector('header').inert = false;
        if (opener?.isConnected) opener.focus();
        else document.querySelector('[data-open]')?.focus();
    }
    async function mutate(url, form = null, button = null) {
        if (busy) return;
        busy = true;
        const controls = [...root.querySelectorAll('button')];
        if (button) controls.push(button);
        controls.forEach(b => b.disabled = true);
        try {
            const {
                response,
                data
            } = await request(url, {
                method: 'POST',
                body: form ? new FormData(form) : new FormData()
            });
            if (response.status === 422 && data.html) {
                fillDialog(data.html, true);
                return;
            }
            if (!response.ok) throw new Error(responseError(response, data));
            busy = false;
            closeDialog();
            message(data.message);
            await refreshList();
        } catch (error) {
            const slot = root.querySelector('#modal-error');
            if (slot) slot.textContent = error.message || 'Could not connect. Your inputs are kept.';
            else message(error.message || 'Could not connect.', true);
        } finally {
            busy = false;
            controls.forEach(b => b.disabled = false);
        }
    }
    document.addEventListener('click', event => {
        const button = event.target.closest('button');
        if (!button) return;
        if (button.dataset.open) openDialog(button.dataset.open);
        else if (button.hasAttribute('data-close')) closeDialog();
        else if (button.dataset.complete) mutate(button.dataset.complete, null, button);
        else if (button.hasAttribute('data-reset')) {
            filters.elements.time.value = 'all';
            filters.elements.status.value = 'all';
            refreshList();
        } else if (button.hasAttribute('data-weather')) refreshWeather(button.dataset.weather);
    });
    document.addEventListener('submit', event => {
        if (['care-form', 'delete-form'].includes(event.target.id)) {
            event.preventDefault();
            mutate(event.target.action, event.target, event.submitter);
        }
        if (event.target === filters) {
            event.preventDefault();
            refreshList();
        }
    });
    filters.addEventListener('change', refreshList);
    document.getElementById('plant-select').addEventListener('change', event => location.assign(event.target.value));

    function clearFieldError(event) {
        const field = event.target;
        if (!field.name) return;
        field.removeAttribute('aria-invalid');
        const error = root.querySelector('#error-' + field.name);
        if (error) error.replaceChildren();
    }
    root.addEventListener('input', clearFieldError);
    root.addEventListener('change', event => {
        clearFieldError(event);
        if (event.target.name === 'repeat') syncRepeat();
    });
    document.addEventListener('keydown', event => {
        if (!root.children.length) return;
        if (event.key === 'Escape') closeDialog();
        if (event.key === 'Tab') {
            const items = [...root.querySelectorAll('button,input,select,textarea,a[href]')].filter(n => !n.disabled && n.type !== 'hidden' && n.getClientRects().length);
            if (event.shiftKey && document.activeElement === items[0]) {
                event.preventDefault();
                items.at(-1)?.focus();
            } else if (!event.shiftKey && document.activeElement === items.at(-1)) {
                event.preventDefault();
                items[0]?.focus();
            }
        }
    });
    refreshWeather();
    if (new URLSearchParams(location.search).get('action') === 'add') openDialog(document.querySelector('[data-open]').dataset.open);
})();
