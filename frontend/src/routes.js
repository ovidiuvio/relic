// Define the application routes as path patterns mapping to lazy-loaded Svelte components.
// Each route uses `loader` for dynamic import() — no eager components to avoid pulling
// heavy transitive dependencies (monaco, highlight) into the main bundle.

// Shared by the "/" route (New relic) and the fallback. Must be a stable reference: App.svelte
// awaits the loader in the template, so a fresh closure per match would remount the
// component (and discard in-progress form state) on every re-route.
const relicFormLoader = () => import("./pages/NewRelic.svelte");

const routes = [
  {
    pattern: /^\/$/,
    loader: relicFormLoader,
    section: "new",
    fullBleed: true,
    getProps: (match, urlParams) => ({
      spaceId: urlParams.get('space'),
      upload: urlParams.get('upload') === '1'
    })
  },
  {
    pattern: /^\/fork\/([a-f0-9]{32})$/,
    loader: () => import("./pages/Fork.svelte"),
    section: "fork",
    fullBleed: true,
    getProps: (match) => ({ relicId: match[1] })
  },
  {
    pattern: /^\/recent$/,
    loader: () => import("./pages/Recent.svelte"),
    section: "recent",
    fullBleed: true,
    getProps: (match, urlParams) => ({
      tagFilter: urlParams.get('tag'),
      search: urlParams.get('search'),
      typeFilter: urlParams.get('type'),
      ownerFilter: urlParams.get('owner'),
      sort: urlParams.get('sort'),
      after: urlParams.get('after'),
      before: urlParams.get('before'),
      size: urlParams.get('size')
    })
  },
  {
    pattern: /^\/search$/,
    loader: () => import("./pages/Search.svelte"),
    section: "search",
    fullBleed: true,
    getProps: (match, urlParams) => ({
      tagFilter: urlParams.get('tag'),
      search: urlParams.get('search'),
      typeFilter: urlParams.get('type'),
      ownerFilter: urlParams.get('owner'),
      source: urlParams.get('source'),
      sort: urlParams.get('sort'),
      after: urlParams.get('after'),
      before: urlParams.get('before'),
      size: urlParams.get('size')
    })
  },
  {
    pattern: /^\/my-relics$/,
    loader: () => import("./pages/MyRelics.svelte"),
    section: "my-relics",
    fullBleed: true,
    getProps: (match, urlParams) => ({
      tagFilter: urlParams.get('tag'),
      search: urlParams.get('search'),
      typeFilter: urlParams.get('type'),
      sort: urlParams.get('sort'),
      after: urlParams.get('after'),
      before: urlParams.get('before'),
      size: urlParams.get('size')
    })
  },
  {
    pattern: /^\/my-bookmarks$/,
    loader: () => import("./pages/Bookmarks.svelte"),
    section: "my-bookmarks",
    fullBleed: true,
    getProps: (match, urlParams) => ({
      tagFilter: urlParams.get('tag'),
      search: urlParams.get('search'),
      typeFilter: urlParams.get('type'),
      ownerFilter: urlParams.get('owner'),
      sort: urlParams.get('sort'),
      after: urlParams.get('after'),
      before: urlParams.get('before'),
      size: urlParams.get('size')
    })
  },
  {
    pattern: /^\/spaces$/,
    loader: () => import("./pages/Spaces.svelte"),
    section: "spaces",
    fullBleed: true,
    getProps: (match, urlParams) => ({
      search: urlParams.get('search'),
      create: urlParams.get('create') === '1'
    })
  },
  {
    pattern: /^\/spaces\/([^\/]+)$/,
    loader: () => import("./pages/Space.svelte"),
    section: "space-view",
    fullBleed: true,
    getProps: (match, urlParams) => ({
      spaceId: match[1],
      tagFilter: urlParams.get('tag'),
      search: urlParams.get('search'),
      typeFilter: urlParams.get('type'),
      ownerFilter: urlParams.get('owner'),
      sort: urlParams.get('sort'),
      after: urlParams.get('after'),
      before: urlParams.get('before'),
      size: urlParams.get('size')
    })
  },
  {
    pattern: /^\/admin(?:\/([a-z]+))?$/,
    loader: () => import("./pages/Admin.svelte"),
    section: "admin",
    fullBleed: true,
    getProps: (match, urlParams) => ({
      tab: match[1] || "overview",
      search: urlParams.get('search'),
      tag: urlParams.get('tag'),
      visibility: urlParams.get('visibility'),
      type: urlParams.get('type'),
      sort: urlParams.get('sort'),
      after: urlParams.get('after'),
      before: urlParams.get('before'),
      size: urlParams.get('size')
    })
  },
  {
    // Catch-all for relic viewing, optionally matching a file path in archives
    // Requires that the first part is NOT one of our predefined root paths.
    // e.g. /relic_id/some/path
    pattern: /^\/([^\/]+)(?:\/(.*))?$/,
    loader: () => import("./pages/RelicView.svelte"),
    section: "relic",
    fullBleed: true,
    getProps: (match) => {
      // Validate that the first param is not a known root-level route path.
      // "new" is included even though there's no /new route: old links to /new?space=id must
      // fall through to the fallback (RelicForm) rather than match as a relic ID.
      const reserved = ["api", "recent", "search", "my-relics", "my-bookmarks", "spaces", "new", "fork", "admin"];
      if (reserved.includes(match[1])) {
        return null; // Signals this route shouldn't match
      }
      return {
        relicId: match[1],
        filePath: match[2] || null
      };
    }
  }
];

/**
 * Returns the canonical path for a given section name.
 * Centralizes any section→path mappings so App.svelte doesn't need to know them.
 * @param {string} section
 * @returns {string}
 */
export function sectionToPath(section) {
  // "new" maps to root — there is no /new route
  return section === "new" ? "/" : `/${section}`;
}

/**
 * Matches a given pathname to an application route.
 * @param {string} path The URL pathname (e.g. window.location.pathname)
 * @param {URLSearchParams} urlParams The query params
 * @returns {{ loader: Function, props: Object, section: string }} or a default configuration.
 *
 * Route shape:
 *   pattern  {RegExp}   - matched against the cleaned pathname
 *   loader   {Function} - () => Promise<module> dynamic import of the Svelte component.
 *                         Must be a stable reference (see relicFormLoader above).
 *   section  {string}   - identifier used for active nav state
 *   fullBleed {boolean} - the page draws its own full-width frame (page bar, list, inspector)
 *   getProps {Function} - (match, urlParams) => Object | null
 *                         Return null to reject the match and fall through to the next route.
 */
export function matchRoute(path, urlParams) {
  // Strip trailing slashes unless it's exactly "/"
  const cleanPath = path !== "/" ? path.replace(/\/+$/, "") : path;

  for (const route of routes) {
    const match = cleanPath.match(route.pattern);
    if (match) {
      const props = route.getProps(match, urlParams);
      // If a route returns null props, it effectively rejects the match.
      if (props !== null) {
        return {
          loader: route.loader,
          props: props,
          section: route.section,
          fullBleed: !!route.fullBleed,
        };
      }
    }
  }

  // Fallback to "new" if nothing matches
  return {
    loader: relicFormLoader,
    props: { spaceId: urlParams.get('space'), upload: false },
    section: "new",
    fullBleed: true,
  };
}
