// What the navbar search searches on each page, and where Enter takes you.
export function searchScope(section, props = {}) {
  switch (section) {
    case "my-relics":
      return { label: "My relics", placeholder: "Search your relics", path: "/my-relics" };
    case "my-bookmarks":
      return { label: "Bookmarks", placeholder: "Search your bookmarks", path: "/my-bookmarks" };
    case "spaces":
      return { label: "Spaces", placeholder: "Search spaces", path: "/spaces" };
    case "space-view":
      return { label: "This space", placeholder: "Search this space", path: `/spaces/${props.spaceId}` };
    default:
      return { label: "Recent", placeholder: "Search public relics", path: "/recent" };
  }
}
