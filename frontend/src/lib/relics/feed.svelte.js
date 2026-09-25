// A paged relic feed: loads the first page, appends more on demand, and ignores responses
// that arrive after a newer reset (typing in search, changing sort).
//
//   const feed = new RelicFeed((params) => listRelics(params).then((r) => r.data));
//   feed.reset({ sort_by: "created_at", sort_order: "desc" });
//   feed.more();
export class RelicFeed {
  relics = $state([]);
  total = $state(null);
  loading = $state(false);
  error = $state(null);
  hasMore = $derived(this.total != null && this.relics.length < this.total);

  #fetch;
  #params = {};
  #gen = 0;
  #pageSize;

  /** @param {(params: object) => Promise<{relics: object[], total: number}>} fetch */
  constructor(fetch, pageSize = 50) {
    this.#fetch = fetch;
    this.#pageSize = pageSize;
  }

  reset(params = {}) {
    this.#params = params;
    return this.#load(0);
  }

  more() {
    if (this.loading || !this.hasMore) return;
    return this.#load(this.relics.length);
  }

  reload() {
    return this.#load(0);
  }

  /** Drop a relic from the loaded rows (after delete or un-bookmark) without reloading. */
  remove(id) {
    const before = this.relics.length;
    this.relics = this.relics.filter((r) => r.id !== id);
    if (this.total != null && this.relics.length < before) this.total -= 1;
  }

  async #load(offset) {
    const gen = ++this.#gen;
    this.loading = true;
    this.error = null;
    try {
      const data = await this.#fetch({ ...this.#params, limit: this.#pageSize, offset });
      if (gen !== this.#gen) return;
      const rows = data.relics ?? [];
      if (offset) {
        // Offset paging over tied sort values can repeat a row across pages; keep the first.
        const seen = new Set(this.relics.map((r) => r.id));
        this.relics = [...this.relics, ...rows.filter((r) => !seen.has(r.id))];
      } else {
        this.relics = rows;
      }
      this.total = data.total ?? rows.length;
    } catch (error) {
      if (gen !== this.#gen) return;
      console.error("[RelicFeed] load failed", error);
      this.error = error;
      if (!offset) {
        this.relics = [];
        this.total = 0;
      }
    } finally {
      if (gen === this.#gen) this.loading = false;
    }
  }
}

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
