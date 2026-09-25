// Relic list sorting: the columns the API can sort by and what a header click does.

/**
 * Sortable list columns: the API field and the direction a first click uses.
 * A sort is { key, dir }; clicking the active column again flips dir.
 */
export const SORT_COLUMNS = {
  date: { field: "created_at", dir: "desc" },
  name: { field: "name", dir: "asc" },
  owner: { field: "owner", dir: "asc" },
  size: { field: "size", dir: "desc" },
  views: { field: "access_count", dir: "desc" },
  bookmarks: { field: "bookmark_count", dir: "desc" },
  comments: { field: "comments_count", dir: "desc" },
  forks: { field: "forks_count", dir: "desc" },
};

export const DEFAULT_SORT = { key: "date", dir: "desc" };

/** The next sort after clicking a column header. */
export function nextSort(current, key) {
  if (current.key === key) return { key, dir: current.dir === "asc" ? "desc" : "asc" };
  return { key, dir: SORT_COLUMNS[key].dir };
}

/** API params for a sort. */
export const sortParams = (sort) => ({ sort_by: SORT_COLUMNS[sort.key].field, sort_order: sort.dir });
