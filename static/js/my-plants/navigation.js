import { announce } from './api.js';

let pending;
const isPlantPage = (url) => url.origin === location.origin
  && /^\/my-plants\/(?:add\/|\d+\/(?:edit\/|delete\/|recap\/)?)?$/.test(url.pathname);

export async function navigate(value, { replace = false, history = true } = {}) {
  const url = new URL(value, location.href);
  if (!isPlantPage(url)) throw new Error('That page is outside My Plants.');
  pending?.abort();
  const controller = new AbortController();
  pending = controller;
  const current = document.querySelector('#main-content');
  current.setAttribute('aria-busy', 'true');
  try {
    const response = await fetch(url, { signal: controller.signal, headers: { Accept: 'text/html' } });
    if (response.redirected && !isPlantPage(new URL(response.url))) { location.assign(response.url); return; }
    if (!response.ok) throw new Error(`Could not open that page (${response.status}). Please try again.`);
    const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
    const next = doc.querySelector('#main-content');
    if (!next?.querySelector('.plants-shell')) throw new Error('The page could not be loaded. Please refresh and try again.');
    for (const modal of document.querySelectorAll('.modal.show')) {
      const instance = window.bootstrap?.Modal.getInstance(modal);
      if (instance) await new Promise((resolve) => {
        modal.addEventListener('hidden.bs.modal', resolve, { once: true });
        instance.hide();
      });
    }
    if (controller.signal.aborted) return;
    document.dispatchEvent(new Event('plants:unmount'));
    current.replaceChildren(...next.childNodes);
    document.title = doc.title;
    if (history) window.history[replace ? 'replaceState' : 'pushState']({ plants: true }, '', url);
    document.dispatchEvent(new Event('plants:mount'));
    const heading = current.querySelector('h1');
    if (heading) { heading.tabIndex = -1; heading.focus({ preventScroll: true }); }
    if (url.hash) document.getElementById(url.hash.slice(1))?.scrollIntoView();
    else window.scrollTo({ top: 0, behavior: 'instant' });
  } finally {
    if (pending === controller) current.removeAttribute('aria-busy');
  }
}

export function startNavigation() {
  window.history.replaceState({ plants: true }, '', location.href);
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey
      || !link || link.target || link.hasAttribute('download') || link.hasAttribute('data-bs-toggle')
      || link.hasAttribute('data-page') || link.hasAttribute('data-reset')) return;
    const url = new URL(link.href);
    if (!isPlantPage(url) || (url.pathname === location.pathname && url.search === location.search && url.hash)) return;
    event.preventDefault();
    navigate(url).catch(showNavigationError);
  });
  window.addEventListener('popstate', () => {
    if (isPlantPage(new URL(location.href))) navigate(location.href, { history: false }).catch(showNavigationError);
    else location.reload();
  });
}

function showNavigationError(error) {
  if (error.name === 'AbortError') return;
  let alert = document.querySelector('[data-navigation-error]');
  if (!alert) {
    alert = document.createElement('p');
    alert.className = 'alert alert-danger';
    alert.setAttribute('role', 'alert');
    alert.dataset.navigationError = '';
    document.querySelector('.plants-shell').prepend(alert);
  }
  alert.textContent = error.message;
  announce(error.message);
}
