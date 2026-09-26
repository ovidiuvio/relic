// What the navbar search searches on each page, and where Enter takes you.
export function searchScope(section, props = {}) {
  switch (section) {
    case "my-relics":
      return { label: "My relics", placeholder: "Search your relics", path: "/my-relics" };
    case "my-bookmarks":
      return { label: "Bookmarks", placeholder: "Search your bookmarks", path: "/my-bookmarks" };
    case "spaces":
      return { label: "Spaces", placeholder: "Search spaces", path: "/spaces" };
    case "admin":
      return props.tab === "users"
        ? { label: "Users", placeholder: "Search users by name, ID or key", path: "/admin/users" }
        : { label: "All relics", placeholder: "Search every relic", path: "/admin/relics" };
    case "space-view":
      return { label: "This space", placeholder: "Search this space", path: `/spaces/${props.spaceId}` };
    default:
      return { label: "Recent", placeholder: "Search public relics", path: "/recent" };
  }
}
