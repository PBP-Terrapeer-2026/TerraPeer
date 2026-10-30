// Shared transport and accessible feedback for the My Plants modules.
export function announce(message) {
  let live = document.querySelector('[data-plants-announcer]');
  if (!live) {
    live = document.createElement('p');
    live.className = 'visually-hidden';
    live.dataset.plantsAnnouncer = '';
    live.setAttribute('role', 'status');
    live.setAttribute('aria-live', 'polite');
    document.body.append(live);
  }
  live.textContent = message;
}

export async function requestJSON(url, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 25000);
  try {
    const response = await fetch(url, {
      ...options, signal: controller.signal,
      headers: { Accept: 'application/json', ...options.headers },
    });
    if (response.redirected) {
      const target = new URL(response.url);
      if (target.origin === location.origin && target.pathname.startsWith('/login/')) location.assign(target);
      throw new Error('Your session has expired. Log in again to continue.');
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const first = Object.values(data.errors || {})[0]?.[0]?.message;
      const error = new Error(data.error || first || (response.status === 403
        ? 'Your form has expired. Refresh the page before trying again.' : 'Could not save. Please try again.'));
      error.fields = data.errors || {};
      error.status = response.status;
      throw error;
    }
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The request timed out. Check your connection before trying again.');
    if (error instanceof TypeError) throw new Error('Could not reach the server. Check your connection and try again.');
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}
