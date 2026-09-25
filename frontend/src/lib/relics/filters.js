// List filters live in the URL (?search=, ?tag=), so changing one is a navigation.

/** `path` with the current query string changed: null or "" removes a parameter. */
export function filterUrl(path, changes) {
  const params = new URLSearchParams(location.search);
  for (const [key, value] of Object.entries(changes)) {
    if (value) params.set(key, value);
    else params.delete(key);
  }
  const qs = params.toString();
  return `${path}${qs ? `?${qs}` : ""}`;
}
