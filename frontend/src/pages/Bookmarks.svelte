<script>
  // Bookmarks: relics you saved, grouped by when you bookmarked them. Removing a bookmark
  // (row action or the inspector's toggle) drops the row at once, with Undo in the toast.
  import { untrack } from "svelte";
  import Icon from "../lib/ui/Icon.svelte";
  import PageBar from "../lib/shell/PageBar.svelte";
  import TypeFacets from "../lib/relics/TypeFacets.svelte";
  import TagPicker from "../lib/relics/TagPicker.svelte";
  import FilterChips from "../lib/relics/FilterChips.svelte";
  import { facetTypes, facetKeyOf, baseType } from "../lib/relics/typeFacets";
  import RelicWorkbench from "../lib/relics/RelicWorkbench.svelte";
  import { PagedFeed } from "../lib/data/PagedFeed.svelte.js";
  import { nextSort, sortParams, sortQuery, parseSort } from "../lib/relics/sort";
  import { filterUrl } from "../lib/relics/filters";
  import { refreshSidebar } from "../lib/shell/sidebarData";
  import { getUserBookmarks, addBookmark, removeBookmark } from "../services/api";
  import { copyRelicContent, downloadRelic, fastForkRelic, copyToClipboard } from "../services/relicActions";
  import { showToast } from "../stores/toastStore";
  import { navigate } from "../utils/navigation";

  let { tagFilter = null, search = null, typeFilter = null, ownerFilter = null, sort: sortValue = null } = $props();

  const feed = new PagedFeed((params) => getUserBookmarks(params).then((r) => r.data), { rows: "bookmarks", facets: true });

  // The type facet as the content types to send; derived, so new counts don't reload the same list.
  const typesParam = $derived(facetTypes(typeFilter, feed.facets?.types));
  // The sort lives in the URL (?sort=size-desc) so links and search history keep it.
  const sort = $derived(parseSort(sortValue));

  // The API sorts "created_at" by when you bookmarked, which is what the date column shows.
  $effect(() => {
    const params = { tag: tagFilter || undefined, search: search || undefined, owner: ownerFilter || undefined, types: typesParam, ...sortParams(sort) };
    untrack(() => feed.reset(params));
  });

  const withParams = (changes) => filterUrl("/my-bookmarks", changes);

  // Undo puts the bookmark back and reloads, so the row returns to its place.
  function removed(relic) {
    feed.remove(relic.id);
    refreshSidebar();
    showToast(`Removed “${relic.name || "Untitled"}” from bookmarks`, "success", 3000, {
      label: "Undo",
      run: async () => {
        try {
          await addBookmark(relic.id);
          feed.reload();
          refreshSidebar();
        } catch {
          showToast("Couldn’t restore the bookmark", "error");
        }
      },
    });
  }

  async function removeRow(relic) {
    try {
      await removeBookmark(relic.id);
      removed(relic);
    } catch {
      showToast("Couldn’t remove the bookmark", "error");
    }
  }

  const actions = [
    { icon: "link", title: "Copy link", run: (r) => copyToClipboard(`${location.origin}/${r.id}`, "Link copied") },
    { icon: "copy", title: "Copy content", run: (r) => copyRelicContent(r.id) },
    { icon: "raw", title: "View raw", run: (r) => window.open(`/${r.id}/raw`, "_blank", "noopener") },
    { icon: "fork", title: "Fast fork", run: (r) => fastForkRelic(r) },
    { icon: "download", title: "Download", run: (r) => downloadRelic(r.id, r.name, r.content_type) },
    { icon: "bookmark", title: "Remove bookmark", run: removeRow },
  ];

  const filtered = $derived(!!(search || tagFilter || typeFilter || ownerFilter));
</script>

<RelicWorkbench
  {feed}
  grouped={sort.key === "date"}
  dateField="bookmarked_at"
  dateLabel="Bookmarked"
  highlight={search || ""}
  {actions}
  {sort}
  onsort={(key) => navigate(withParams({ sort: sortQuery(nextSort(sort, key)) }), { replace: true })}
  showPublic
  emptyText={filtered ? "None of your bookmarks match these filters." : "No bookmarks yet. Bookmark a relic to keep it here."}
  emptyAction={filtered ? { href: "/my-bookmarks", label: "Clear filters" } : { href: "/recent", label: "Browse recent relics" }}
  ontag={(tag) => navigate(withParams({ tag, search: null }))}
  onowner={(r) => navigate(withParams({ owner: r.owner_public_id }))}
  ontype={(r) => navigate(withParams({ type: baseType(r.content_type) }))}
  onbookmark={(relic, bookmarked) => !bookmarked && removed(relic)}
>
  {#snippet pagebar({ inspectorOpen, toggleInspector })}
    <PageBar title={search || tagFilter || ownerFilter ? "Results" : "Bookmarks"} count={feed.total} {inspectorOpen} ontoggleinspector={toggleInspector}>
      {#snippet filters()}
        {#if search}
          <span class="r-chip-filter">{search}<button onclick={() => navigate(withParams({ search: null }))} aria-label="Clear search"><Icon name="x" /></button></span>
        {/if}
        {#if tagFilter}
          <span class="r-chip-filter">#{tagFilter}<button onclick={() => navigate(withParams({ tag: null }))} aria-label="Clear tag filter"><Icon name="x" /></button></span>
        {/if}
        <FilterChips owner={ownerFilter} type={typeFilter} relics={feed.items} hrefFor={withParams} />
      <span class="r-pagebar-sep"></span>
        <TypeFacets active={facetKeyOf(typeFilter)} types={feed.facets?.types} showCounts={filtered} hrefFor={(type) => withParams({ type })} />
      {/snippet}
      {#snippet options()}
        <TagPicker active={tagFilter} tags={feed.facets?.tags} hrefFor={(tag) => withParams({ tag })} />
      {/snippet}
    </PageBar>
  {/snippet}

  {#snippet status()}
    <span><Icon name="bookmark" />{feed.total == null ? "…" : feed.total.toLocaleString("en-US")} bookmarks</span>
    <span>{feed.items.length.toLocaleString("en-US")} loaded</span>
    {#if feed.error}<span class="status-error">Couldn’t load more. <button class="r-link" onclick={() => feed.reload()}>Retry</button></span>{/if}
    <span class="r-gap"></span>
    <span class="r-hints"><span><kbd class="r-kbd">/</kbd>search</span><span><kbd class="r-kbd">↑</kbd><kbd class="r-kbd">↓</kbd>move</span><span><kbd class="r-kbd">]</kbd>inspector</span></span>
  {/snippet}
</RelicWorkbench>
