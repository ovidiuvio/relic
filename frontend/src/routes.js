import RelicForm from "./components/RelicForm.svelte";
import RelicViewer from "./components/RelicViewer.svelte";
import RecentRelics from "./components/RecentRelics.svelte";
import MyRelics from "./components/MyRelics.svelte";
import MyBookmarks from "./components/MyBookmarks.svelte";
import AdminPanel from "./components/AdminPanel.svelte";
import SpacesList from "./components/SpacesList.svelte";
import SpaceViewer from "./components/SpaceViewer.svelte";

// Define the application routes as path patterns mapping to Svelte components.
const routes = [
  {
    pattern: /^\/$/,
    component: RelicForm,
    section: "new",
    getProps: (match, urlParams) => ({
      spaceId: urlParams.get('space')
    })
  },
  {
    pattern: /^\/recent$/,
    component: RecentRelics,
    section: "recent",
    getProps: (match, urlParams) => ({
      tagFilter: urlParams.get('tag')
    })
  },
  {
    pattern: /^\/my-relics$/,
    component: MyRelics,
    section: "my-relics",
    getProps: (match, urlParams) => ({
      tagFilter: urlParams.get('tag')
    })
  },
  {
    pattern: /^\/my-bookmarks$/,
    component: MyBookmarks,
    section: "my-bookmarks",
    getProps: (match, urlParams) => ({
      tagFilter: urlParams.get('tag')
    })
  },
  {
    pattern: /^\/spaces$/,
    component: SpacesList,
    section: "spaces",
    getProps: () => ({})
  },
  {
    pattern: /^\/spaces\/([^\/]+)$/,
    component: SpaceViewer,
    section: "space-view",
    getProps: (match, urlParams) => ({
      spaceId: match[1],
      tagFilter: urlParams.get('tag')
    })
  },
  {
    pattern: /^\/admin$/,
    component: AdminPanel,
    section: "admin",
    getProps: () => ({})
  },
  {
    // Catch-all for relic viewing, optionally matching a file path in archives
    // Requires that the first part is NOT one of our predefined root paths.
    // e.g. /relic_id/some/path
    pattern: /^\/([^\/]+)(?:\/(.*))?$/,
    component: RelicViewer,
    section: "relic",
    getProps: (match) => {
      // Validate that the first param is not a known root-level route path.
      // "new" is included even though there's no /new route, because SpacesList and SpaceViewer
      // dispatch navigate('new?space=id') which lands on /new. The reserved check ensures that
      // falls through to the fallback (RelicForm) rather than matching as a relic ID.
      const reserved = ["api", "recent", "my-relics", "my-bookmarks", "spaces", "new", "admin"];
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
 * @returns {{ component: any, props: Object, section: string }} or a default configuration.
 *
 * Route shape:
 *   pattern   {RegExp}   - matched against the cleaned pathname
 *   component {any}      - Svelte component to render
 *   section   {string}   - identifier used for active nav state
 *   getProps  {Function} - (match, urlParams) => Object | null
 *                          Return null to reject the match and fall through to the next route.
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
          component: route.component,
          props: props,
          section: route.section,
        };
      }
    }
  }

  // Fallback to "new" if nothing matches
  return {
    component: RelicForm,
    props: { spaceId: urlParams.get('space') },
    section: "new"
  };
}
