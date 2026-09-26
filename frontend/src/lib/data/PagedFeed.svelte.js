// A paged feed of items with an id (relics, spaces): loads the first page, appends more on
// demand, and ignores responses that arrive after a newer reset (typing in search, sorting).
//
//   const feed = new PagedFeed((params) => listRelics(params).then((r) => r.data));
//   feed.reset({ sort_by: "created_at", sort_order: "desc" });
//   feed.more();
//
// The fetch returns { items, total }, or the API's own shape with `rows` naming the list
// (default "relics": { relics, total }).
export class PagedFeed {
  // Raw: rows are API data, replaced whole (never edited in place), and a long scroll can hold
  // thousands of them; deep proxies would only add cost.
  items = $state.raw([]);
  total = $state(null);
  loading = $state(false);
  error = $state(null);
  // With `facets`: counts per content type and the top tags for the list as filtered, before its
  // type filter ({ types: { "text/x-python": 12 }, tags: [{ name, count }] }). From the first page.
  facets = $state.raw(null);
  hasMore = $derived(this.total != null && this.items.length < this.total);

  #fetch;
  #params = {};
  #gen = 0;
  #pageSize;
  #rows;
  #withFacets;

  /** @param {(params: object) => Promise<object>} fetch */
  constructor(fetch, { rows = "relics", pageSize = 50, facets = false } = {}) {
    this.#fetch = fetch;
    this.#rows = rows;
    this.#withFacets = facets;
    this.#pageSize = pageSize;
  }

  reset(params = {}) {
    this.#params = params;
    return this.#load(0);
  }

  more() {
    if (this.loading || !this.hasMore) return;
    return this.#load(this.items.length);
  }

  reload() {
    return this.#load(0);
  }

  /** Merge fresh fields into a loaded row (after an edit) without reloading. */
  update(item) {
    this.items = this.items.map((r) => (r.id === item.id ? { ...r, ...item } : r));
  }

  /** Drop an item from the loaded rows (after delete or un-bookmark) without reloading. */
  remove(id) {
    const before = this.items.length;
    this.items = this.items.filter((r) => r.id !== id);
    if (this.total != null && this.items.length < before) this.total -= 1;
  }

  async #load(offset) {
    const gen = ++this.#gen;
    this.loading = true;
    this.error = null;
    try {
      const data = await this.#fetch({
        ...this.#params,
        limit: this.#pageSize,
        offset,
        facets: this.#withFacets && !offset ? true : undefined,
      });
      if (gen !== this.#gen) return;
      const rows = data.items ?? data[this.#rows] ?? [];
      if (offset) {
        // Offset paging over tied sort values can repeat a row across pages; keep the first.
        const seen = new Set(this.items.map((r) => r.id));
        this.items = [...this.items, ...rows.filter((r) => !seen.has(r.id))];
      } else {
        this.items = rows;
        if (data.facets) this.facets = data.facets;
      }
      this.total = data.total ?? rows.length;
    } catch (error) {
      if (gen !== this.#gen) return;
      console.error("[PagedFeed] load failed", error);
      this.error = error;
      if (!offset) {
        this.items = [];
        this.total = 0;
      }
    } finally {
      if (gen === this.#gen) this.loading = false;
    }
  }
}
