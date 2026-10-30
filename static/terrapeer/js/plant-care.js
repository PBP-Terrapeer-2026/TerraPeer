/* Tutorial 5: Fetch + FormData. Django remains the source of truth. */
(() => {
    const main = document.getElementById('main-content');
    if (!main?.dataset.listUrl) return;
    const root = document.getElementById('modal-root');
    const filters = document.getElementById('filters');
    let listRequest, weatherRequest, dialogRequest, opener, busy = false;
    const inertBefore = new Map();
    class SessionExpiredError extends Error {}
    const csrf = () => document.querySelector('[name=csrfmiddlewaretoken]').value;

    function message(text, error = false, undoUrl = null) {
        const node = document.getElementById('feedback');
        node.textContent = text; // Never render user text through innerHTML.
        node.hidden = false;
        node.classList.toggle('error', error);
        if (undoUrl) {
            const undo = document.createElement('button');
            undo.type = 'button';
            undo.className = 'feedback-undo';
            undo.dataset.undo = undoUrl;
            undo.textContent = 'Undo';
            node.append(undo);
        }
        const dismiss = document.createElement('button');
        dismiss.type = 'button';
        dismiss.className = 'feedback-dismiss';
        dismiss.setAttribute('aria-label', 'Dismiss notification');
        dismiss.textContent = '×';
        dismiss.addEventListener('click', () => node.hidden = true);
        node.append(dismiss);
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
            link.href = (data.login_url || '/login/') + '?next=' + encodeURIComponent(location.pathname);
            document.getElementById('feedback').append(link);
            const slot = root.querySelector('#modal-error');
            if (slot) {
                slot.textContent = 'Your session expired. Your inputs are kept. ';
                slot.append(link.cloneNode(true));
            }
            throw new SessionExpiredError('Your session expired.');
        }
        return {
            response,
            data
        };
    }

    function responseError(response, data) {
        return data.message || (response.status === 403 ? 'Request rejected. Refresh the page and sign in again.' : `Request failed (${response.status}). Please try again.`);
    }
    // Retain unchanged cards instead of rebuilding every DOM node.
    function patchTaskList(node, html) {
        const template = document.createElement('template');
        template.innerHTML = html; // Autoescaped, server-owned Django fragment.
        const key = item => item.dataset.taskId ? 'task:' + item.dataset.taskId : item.className;
        const existing = new Map([...node.children].map(item => [key(item), item]));
        const desired = [...template.content.children].map(fresh => {
            const old = existing.get(key(fresh));
            if (old?.querySelector('details')?.open) fresh.querySelector('details')?.setAttribute('open', '');
            return old?.isEqualNode(fresh) ? old : fresh;
        });
        let cursor = node.firstElementChild;
        for (const item of desired) {
            if (item !== cursor) node.insertBefore(item, cursor);
            cursor = item.nextElementSibling;
        }
        const keep = new Set(desired);
        [...node.children].forEach(item => {
            if (!keep.has(item)) item.remove();
        });
    }

    function patchPanel(selector, html) {
        const template = document.createElement('template');
        template.innerHTML = html;
        const fresh = template.content.firstElementChild;
        const current = document.querySelector(selector);
        if (!current.isEqualNode(fresh)) current.replaceWith(fresh);
    }

    async function refreshList() {
        listRequest?.abort();
        const controller = new AbortController();
        listRequest = controller;
        const node = document.getElementById('task-list');
        node.setAttribute('aria-busy', 'true');
        try {
            const query = new URLSearchParams(new FormData(filters));
            const {
                response,
                data
            } = await request(main.dataset.listUrl + '?' + query, {
                signal: controller.signal
            });
            if (!response.ok) throw new Error(responseError(response, data));
            if (controller !== listRequest) return false;
            const scrollTop = window.scrollY;
            patchTaskList(node, data.html);
            document.getElementById('pending-count').textContent = data.pending_count + ' pending';
            // The same server snapshot supplies cards, calendar and totals.
            patchPanel('.calendar-card', data.calendar_html);
            patchPanel('.summary-card', data.summary_html);
            window.scrollTo({
                top: scrollTop,
                behavior: 'instant'
            });
            history.replaceState(null, '', location.pathname + '?' + query);
            return true;
        } catch (error) {
            if (error.name !== 'AbortError' && !(error instanceof SessionExpiredError)) message(error.message || 'Could not refresh tasks.', true);
            return false;
        } finally {
            if (controller === listRequest) node.removeAttribute('aria-busy');
        }
    }
    async function refreshWeather(day = 0) {
        weatherRequest?.abort();
        const controller = new AbortController();
        weatherRequest = controller;
        const node = document.getElementById('weather-slot');
        node.setAttribute('aria-busy', 'true');
        try {
            const {
                response,
                data
            } = await request(main.dataset.weatherUrl + '?day=' + day, {
                signal: controller.signal
            });
            if (controller !== weatherRequest) return;
            if (data.html) {
                node.innerHTML = data.html;
                const disclosure = node.querySelector('.weather-expand');
                if (disclosure) disclosure.open = !window.matchMedia('(max-width: 740px)').matches;
            } // Includes server-rendered 503 error/retry state.
            else if (!response.ok) throw new Error(responseError(response, data));
        } catch (error) {
            if (error.name === 'AbortError' || error instanceof SessionExpiredError) return;
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
            if (controller === weatherRequest) node.removeAttribute('aria-busy');
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
        for (const node of document.body.children) {
            if (node === root || node.tagName === 'SCRIPT') continue;
            if (!inertBefore.has(node)) inertBefore.set(node, node.inert);
            node.inert = true;
        }
        syncRepeat();
        const focus = validation ? root.querySelector('[aria-invalid=true]') : root.querySelector('input:not([type=hidden]), select, button');
        focus?.focus();
    }
    async function openDialog(url) {
        if (busy) return;
        if (!root.contains(document.activeElement)) opener = document.activeElement;
        dialogRequest?.abort();
        const controller = new AbortController();
        dialogRequest = controller;
        try {
            const {
                response,
                data
            } = await request(url, {
                signal: controller.signal
            });
            if (!response.ok) throw new Error(responseError(response, data));
            if (controller === dialogRequest) fillDialog(data.html);
        } catch (error) {
            if (error.name !== 'AbortError' && !(error instanceof SessionExpiredError)) message(error.message, true);
        }
    }

    function closeDialog() {
        if (busy || !root.children.length) return;
        dialogRequest?.abort();
        root.replaceChildren();
        document.body.style.overflow = '';
        for (const [node, previous] of inertBefore) node.inert = previous;
        inertBefore.clear();
        if (opener?.isConnected) opener.focus({
            preventScroll: true
        });
        else document.querySelector('[data-open]')?.focus({
            preventScroll: true
        });
    }
    async function mutate(url, form = null, button = null) {
        if (busy) return;
        busy = true;
        const focusTaskId = button?.closest('[data-task-id]')?.dataset.taskId;
        const controls = [...root.querySelectorAll('button')];
        if (button) controls.push(button);
        const disabledBefore = controls.map(control => control.disabled);
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
            busy = true;
            message(data.message, false, data.undo_url);
            const refreshed = await refreshList();
            if (!refreshed && !document.querySelector('#feedback a')) {
                message('Saved, but the view could not refresh. Reload to see the latest tasks.', true, data.undo_url);
            }
            if (refreshed && focusTaskId) {
                const target = document.querySelector('[data-task-id="' + focusTaskId + '"] .check') ||
                    document.querySelector('#feedback [data-undo]') ||
                    document.querySelector('#feedback .feedback-dismiss');
                target?.focus({
                    preventScroll: true
                });
            }
        } catch (error) {
            if (error instanceof SessionExpiredError) return;
            const slot = root.querySelector('#modal-error');
            if (slot) slot.textContent = error.message || 'Could not connect. Your inputs are kept.';
            else message(error.message || 'Could not connect.', true);
        } finally {
            busy = false;
            controls.forEach((control, index) => control.disabled = disabledBefore[index]);
        }
    }
    document.addEventListener('click', event => {
        const button = event.target.closest('button');
        if (!button) return;
        if (button.hasAttribute('data-status') || button.hasAttribute('data-overdue')) {
            filters.elements.status.value = button.dataset.status || 'Pending';
            filters.elements.overdue.value = button.hasAttribute('data-overdue') ? '1' : '';
            filters.querySelectorAll('.status-tabs button').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
            refreshList();
        } else if (button.dataset.open) openDialog(button.dataset.open);
        else if (button.hasAttribute('data-close')) closeDialog();
        else if (button.dataset.complete) mutate(button.dataset.complete, null, button);
        else if (button.dataset.undo) mutate(button.dataset.undo, null, button);
        else if (button.hasAttribute('data-reset')) {
            filters.elements.date.value = '';
            filters.elements.action.value = '';
            filters.elements.overdue.value = '';
            filters.querySelectorAll('.status-tabs button').forEach(item => item.setAttribute('aria-pressed', String(item.dataset.status === 'all')));
            filters.elements.time.value = 'all';
            filters.elements.status.value = 'all';
            refreshList();
        } else if (button.hasAttribute('data-weather')) refreshWeather(button.dataset.weather);
    });
    document.getElementById('space-form')?.addEventListener('submit', async event => {
        event.preventDefault();
        const form = event.currentTarget;
        const button = form.querySelector('button[type="submit"]');
        if (button.disabled) return;
        button.disabled = true;
        try {
            const { response, data } = await request(form.action, { method: 'POST', body: new FormData(form) });
            if (!response.ok) throw new Error(responseError(response, data));
            message(data.message);
            await Promise.all([refreshWeather(), refreshList()]);
        } catch (error) {
            if (!(error instanceof SessionExpiredError)) message(error.message || 'Could not save location.', true);
        } finally {
            button.disabled = false;
        }
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
    filters.addEventListener('change', event => {
        if (event.target.name === 'time') filters.elements.date.value = '';
        if (event.target.id !== 'plant-select') refreshList();
    });
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
    const mobileWeather = window.matchMedia('(max-width: 740px)');
    mobileWeather.addEventListener('change', event => {
        const disclosure = document.querySelector('.weather-expand');
        if (disclosure) disclosure.open = !event.matches;
    });
    refreshWeather();
    if (new URLSearchParams(location.search).get('action') === 'add') openDialog(document.querySelector('[data-open]').dataset.open);
})();
