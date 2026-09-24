// Client-side navigation helpers. App.svelte re-routes on `popstate`, so pushing
// history and dispatching that event is all a navigation needs.

// Paths served by nginx/backend rather than the SPA.
const SERVER_PATHS = /^\/(api|docs|openapi\.json|install\.sh)(\/|$)|\/raw$/;

export function navigate(path, { replace = false } = {}) {
  const url = path.startsWith("/") ? path : `/${path}`;
  if (replace) {
    window.history.replaceState({}, "", url);
  } else {
    window.history.pushState({}, "", url);
  }
  window.dispatchEvent(new PopStateEvent("popstate"));
}

/**
 * Returns the in-app path for a click on an internal link, or null when the
 * browser should handle it (new tab, download, external, server-rendered path).
 */
export function internalLinkTarget(event) {
  if (event.defaultPrevented || event.button !== 0) return null;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return null;

  const anchor = event.target.closest?.("a[href]");
  if (!anchor) return null;
  if (anchor.target && anchor.target !== "_self") return null;
  if (anchor.hasAttribute("download") || anchor.dataset.reload !== undefined) return null;

  const url = new URL(anchor.href, window.location.href);
  if (url.origin !== window.location.origin) return null;
  if (SERVER_PATHS.test(url.pathname)) return null;
  // Same-page hash links (e.g. #L12 line anchors) are left to the browser.
  if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) {
    return null;
  }

  return url.pathname + url.search + url.hash;
}
