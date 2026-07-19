// Define the application routes as path patterns mapping to lazy-loaded Svelte components.
// Each route uses `loader` for dynamic import() — no eager components to avoid pulling
// heavy transitive dependencies (monaco, highlight) into the main bundle.
const routes = [
  {
    pattern: /^\/$/,
    loader: () => import("./components/RelicForm.svelte"),
    section: "new",
    getProps: (match, urlParams) => ({
      spaceId: urlParams.get('space')
    })
  },
  {
    pattern: /^\/recent$/,
    loader: () => import("./components/RecentRelics.svelte"),
    section: "recent",
    getProps: (match, urlParams) => ({
      tagFilter: urlParams.get('tag')
    })
  },
  {
    pattern: /^\/my-relics$/,
    loader: () => import("./components/MyRelics.svelte"),
    section: "my-relics",
    getProps: (match, urlParams) => ({
      tagFilter: urlParams.get('tag')
    })
  },
  {
    pattern: /^\/my-bookmarks$/,
    loader: () => import("./components/MyBookmarks.svelte"),
    section: "my-bookmarks",
    getProps: (match, urlParams) => ({
      tagFilter: urlParams.get('tag')
    })
  },
  {
    pattern: /^\/spaces$/,
    loader: () => import("./components/SpacesList.svelte"),
    section: "spaces",
    getProps: () => ({})
  },
  {
    pattern: /^\/spaces\/([^\/]+)$/,
    loader: () => import("./components/SpaceViewer.svelte"),
    section: "space-view",
    getProps: (match, urlParams) => ({
      spaceId: match[1],
      tagFilter: urlParams.get('tag')
    })
  },
  {
    pattern: /^\/admin$/,
    loader: () => import("./components/AdminPanel.svelte"),
    section: "admin",
    getProps: () => ({})
  },
  {
    // Catch-all for relic viewing, optionally matching a file path in archives
    pattern: /^\/([^\/]+)(?:\/(.*))?$/,
    loader: () => import("./components/RelicViewer.svelte"),
    section: "relic",
    getProps: (match) => {
      const reserved = ["api", "recent", "my-relics", "my-bookmarks", "spaces", "new", "admin"];
      if (reserved.includes(match[1])) {
        return null;
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
 * Routes can be eager (`component` field) or lazy (`loader` field).
 */
export function matchRoute(path, urlParams) {
  // Strip trailing slashes unless it's exactly "/"
  const cleanPath = path !== "/" ? path.replace(/\/+$/, "") : path;

  for (const route of routes) {
    const match = cleanPath.match(route.pattern);
    if (match) {
      const props = route.getProps(match, urlParams);
      if (props !== null) {
        return {
          loader: route.loader,
          props: props,
          section: route.section,
        };
      }
    }
  }

  // Fallback to "new" if nothing matches
  return {
    loader: () => import("./components/RelicForm.svelte"),
    props: { spaceId: urlParams.get('space') },
    section: "new"
  };
}
