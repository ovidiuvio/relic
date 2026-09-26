<script>
  // A relic index (.rix) in the viewer: the relics it lists, in the relic list. They load five at
  // a time (with the index's title, description and tag overrides applied), then filter, search
  // and sort here in the page. Selecting a row hands it to the viewer, whose inspector shows it;
  // counters open that inspector's sections. Phones open the relic instead.
  import Icon from "../ui/Icon.svelte";
  import PageBar from "../shell/PageBar.svelte";
  import RelicList from "../relics/RelicList.svelte";
  import { nextSort } from "../relics/sort";
  import { tagName } from "../relics/format";
  import { layout } from "../shell/layout";
  import { getRelic } from "../../services/api";
  import { getTypeLabel } from "../../services/typeUtils";
  import { copyRelicContent, downloadRelic, fastForkRelic, copyToClipboard } from "../../services/relicActions";
  import { navigate } from "../../utils/navigation";
  import { rememberList, relicIdFromHref } from "./listContext";

  let {
    processed,
    selectedId = null,
    onselect, // (relic, section?) show it in the viewer's inspector, optionally at a section
  } = $props();

  const title = $derived(processed.meta?.title || "Relic index");
  const description = $derived(processed.meta?.description || "");

  let relics = $state.raw([]);
  let loading = $state(true);
  let progress = $state(0);
  let total = $state(0);
  let search = $state("");
  let tag = $state(null);
  let sort = $state({ key: "date", dir: "desc" });

  async function load() {
    const items = processed.relics || [];
    total = items.length;
    relics = [];
    progress = 0;
    loading = true;
    const results = [];
    for (let i = 0; i < items.length; i += 5) {
      const batch = items.slice(i, i + 5).map(async (item) => {
        if (!/^[a-f0-9]{32}$/i.test(item.id)) return null; // not a relic ID
        try {
          const { data } = await getRelic(item.id);
          if (item.title) data.name = item.title;
          if (item.description) data.description = item.description;
          if (item.tags) data.tags = item.tags;
          return data;
        } catch {
          return null; // gone, or not visible to you
        }
      });
      results.push(...(await Promise.all(batch)).filter(Boolean));
      progress = Math.min(i + 5, items.length);
      relics = [...results];
    }
    loading = false;
  }
  load();

  /** After the inspector changed or deleted one of them. */
  export function update(relic) {
    relics = relics.map((r) => (r.id === relic.id ? { ...r, ...relic } : r));
  }
  export function remove(id) {
    relics = relics.filter((r) => r.id !== id);
  }

  // Client-side sort over the same columns the server lists sort by.
  const SORT_VALUE = {
    date: (r) => r.created_at,
    name: (r) => (r.name || r.id).toLowerCase(),
    owner: (r) => (r.owner_name || "").toLowerCase(),
    size: (r) => r.size_bytes ?? 0,
    views: (r) => r.access_count ?? 0,
    bookmarks: (r) => r.bookmark_count ?? 0,
    comments: (r) => r.comments_count ?? 0,
    forks: (r) => r.forks_count ?? 0,
  };

  const shown = $derived.by(() => {
    const term = search.trim().toLowerCase();
    const rows = relics.filter((r) => {
      const tags = (r.tags ?? []).map((t) => tagName(t).toLowerCase());
      if (tag && !tags.includes(tag.toLowerCase())) return false;
      if (!term) return true;
      return (
        (r.name || "").toLowerCase().includes(term) ||
        r.id.includes(term) ||
        getTypeLabel(r.content_type).toLowerCase().includes(term) ||
        tags.some((t) => t.includes(term))
      );
    });
    const value = SORT_VALUE[sort.key];
    const dir = sort.dir === "asc" ? 1 : -1;
    return rows.sort((a, b) => (value(a) < value(b) ? -dir : value(a) > value(b) ? dir : 0));
  });

  // Opening one of the index's relics remembers the index (as filtered and sorted now), so the
  // viewer can step through it and come back.
  function remember() {
    rememberList(title, location.pathname + location.search, { items: shown });
  }

  function open(relic) {
    remember();
    navigate(`/${relic.id}`);
  }

  function onDocumentClick(event) {
    const id = relicIdFromHref(event.target.closest?.("a[href]")?.getAttribute("href"));
    if (id && shown.some((r) => r.id === id)) remember();
  }

  function select(relic, section = null) {
    if ($layout.phone) return open(relic);
    onselect?.(relic, section);
  }

  const actions = [
    { icon: "link", title: "Copy link", run: (r) => copyToClipboard(`${location.origin}/${r.id}`, "Link copied") },
    { icon: "copy", title: "Copy content", run: (r) => copyRelicContent(r.id) },
    { icon: "raw", title: "View raw", run: (r) => window.open(`/${r.id}/raw`, "_blank", "noopener") },
    { icon: "fork", title: "Fast fork", run: (r) => fastForkRelic(r) },
    { icon: "download", title: "Download", run: (r) => downloadRelic(r.id, r.name, r.content_type) },
  ];

  function onSearchKey(event) {
    if (event.key === "Escape" && search) {
      event.stopPropagation();
      search = "";
    }
  }
</script>

<svelte:document onclickcapture={onDocumentClick} />

<div class="rix">
  <PageBar {title} count={loading ? null : relics.length}>
    {#snippet filters()}
      {#if loading}<span class="rix-progress" role="status"><Icon name="clock" />Loading {progress} of {total}</span>{/if}
      {#if tag}
        <span class="r-chip-filter">#{tag}<button onclick={() => (tag = null)} aria-label="Clear tag filter"><Icon name="x" /></button></span>
      {/if}
    {/snippet}
    {#snippet options()}
      <label class="r-input r-input-sm rix-search">
        <Icon name="search" />
        <input bind:value={search} placeholder="Filter by name, type, tag or ID" aria-label="Filter this index" onkeydown={onSearchKey} />
        {#if search}<button onclick={() => (search = "")} aria-label="Clear filter"><Icon name="x" /></button>{/if}
      </label>
    {/snippet}
  </PageBar>
  {#if description}<p class="rix-desc">{description}</p>{/if}

  <RelicList
    relics={shown}
    loading={loading && !relics.length}
    grouped={sort.key === "date"}
    highlight={search}
    showPublic
    {actions}
    {sort}
    onsort={(key) => (sort = nextSort(sort, key))}
    {selectedId}
    onselect={(r) => select(r)}
    onopen={open}
    oncounter={(r, section) => select(r, section)}
    ontag={(t) => (tag = t)}
    emptyText={search || tag ? "No relics in this index match." : loading ? "Loading…" : "No relics in this index that you can see."}
  />
</div>

<style>
  .rix {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    background: var(--surface);
    color: var(--ink);
    font: 13px/1.45 var(--font-sans);
  }
  .rix-progress {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: var(--ink-3);
    font-size: 12.5px;
  }
  .rix-progress :global(.r-icon) {
    width: 13px;
    height: 13px;
  }
  .rix-search {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 260px;
  }
  .rix-search :global(.r-icon) {
    flex: none;
    width: 13px;
    height: 13px;
    color: var(--ink-3);
  }
  .rix-search input {
    flex: 1;
    min-width: 0;
  }
  .rix-search button {
    display: grid;
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink-3);
    cursor: pointer;
  }
  .rix-desc {
    margin: 0;
    padding: var(--space-2) var(--space-4);
    border-bottom: 1px solid var(--line);
    color: var(--ink-2);
    font-size: 12.5px;
  }
  @media (max-width: 767px) {
    .rix-search {
      width: 160px;
    }
  }
</style>
