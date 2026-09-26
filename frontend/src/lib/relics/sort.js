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

/** The ?sort= value for a sort ("size-desc"), or null for the default. */
export function sortQuery(sort) {
  return sort.key === DEFAULT_SORT.key && sort.dir === DEFAULT_SORT.dir ? null : `${sort.key}-${sort.dir}`;
}

/** The sort a ?sort= value names; the default when it's missing or not one of `allowed`. */
export function parseSort(value, allowed = null) {
  const m = /^([a-z]+)-(asc|desc)$/.exec(value || "");
  if (!m || !SORT_COLUMNS[m[1]] || (allowed && !allowed.includes(m[1]))) return DEFAULT_SORT;
  return { key: m[1], dir: m[2] };
}

/** API params for a sort. */
export const sortParams = (sort) => ({ sort_by: SORT_COLUMNS[sort.key].field, sort_order: sort.dir });
