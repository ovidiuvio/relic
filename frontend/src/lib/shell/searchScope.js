// What the navbar search searches on each page, where Enter takes you, and which filter
// tokens (type: tag: by: after: before: size:) that list takes. Everywhere is everything the
// user may see (its list is /search); pages without a list search it.
import { FILTER_KEYS } from "../search/query";

const RELIC_FILTERS = FILTER_KEYS; // everything
const OWN_FILTERS = FILTER_KEYS.filter((k) => k !== "by"); // lists where by: means nothing or isn't offered

export const EVERYWHERE = { key: "everywhere", label: "Everywhere", icon: "globe", placeholder: "Search everything you can see", path: "/search", filters: RELIC_FILTERS };
export const RECENT = { key: "recent", label: "Recent", icon: "clock", placeholder: "Search public relics", path: "/recent", filters: RELIC_FILTERS };
export const MINE = { key: "my-relics", label: "My relics", icon: "user", placeholder: "Search your relics", path: "/my-relics", filters: OWN_FILTERS };
export const BOOKMARKS = { key: "my-bookmarks", label: "Bookmarks", icon: "bookmark", placeholder: "Search your bookmarks", path: "/my-bookmarks", filters: RELIC_FILTERS };

/** The lists you can pick in the scope menu, Everywhere first (spaces are added from the sidebar's list). */
export const LIST_SCOPES = [EVERYWHERE, RECENT, MINE, BOOKMARKS];

export function spaceScope(space) {
  return {
    key: `space:${space.id}`,
    label: space.name || "Untitled space",
    icon: "layers",
    placeholder: `Search ${space.name || "this space"}`,
    path: `/spaces/${space.id}`,
    filters: RELIC_FILTERS,
  };
}

export function searchScope(section, props = {}) {
  switch (section) {
    case "my-relics":
      return MINE;
    case "my-bookmarks":
      return BOOKMARKS;
    case "spaces":
      return { key: "spaces", label: "Spaces", icon: "layers", placeholder: "Search spaces", path: "/spaces", filters: [] };
    case "admin":
      return props.tab === "users"
        ? { key: "admin-users", label: "Users", icon: "user", placeholder: "Search users by name, ID or key", path: "/admin/users", filters: [] }
        : { key: "admin-relics", label: "All relics", icon: "shield", placeholder: "Search every relic", path: "/admin/relics", filters: OWN_FILTERS };
    case "recent":
      return RECENT;
    case "space-view":
      return { key: `space:${props.spaceId}`, label: "This space", icon: "layers", placeholder: "Search this space", path: `/spaces/${props.spaceId}`, filters: RELIC_FILTERS };
    default:
      return EVERYWHERE; // /search, and pages without a list
  }
}
