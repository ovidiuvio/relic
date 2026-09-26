<script>
  // Everywhere (/search): every relic you can see, in one list: public ones, yours, ones you
  // bookmarked, restricted ones shared with you, and those in your spaces. With a search it's
  // ordered by best match (a column header sorts it instead); each row says why it's visible and
  // the Where facets (?source=) narrow it to one reason. Filters work as on every list.
  import { untrack } from "svelte";
  import Icon from "../lib/ui/Icon.svelte";
  import PageBar from "../lib/shell/PageBar.svelte";
  import TypeFacets from "../lib/relics/TypeFacets.svelte";
  import WhereFacets from "../lib/relics/WhereFacets.svelte";
  import TagPicker from "../lib/relics/TagPicker.svelte";
  import FilterChips from "../lib/relics/FilterChips.svelte";
  import CopyResultsLink from "../lib/relics/CopyResultsLink.svelte";
  import { rangeParams } from "../lib/search/ranges";
  import { facetTypes, facetKeyOf, baseType } from "../lib/relics/typeFacets";
  import RelicWorkbench from "../lib/relics/RelicWorkbench.svelte";
  import { PagedFeed } from "../lib/data/PagedFeed.svelte.js";
  import { nextSort, sortParams, sortQuery, parseSort } from "../lib/relics/sort";
  import { searchEverywhere } from "../services/api";
  import { copyRelicContent, downloadRelic, fastForkRelic, copyToClipboard } from "../services/relicActions";
  import { navigate } from "../utils/navigation";
  import { filterUrl } from "../lib/relics/filters";

  let {
    tagFilter = null,
    search = null,
    typeFilter = null,
    ownerFilter = null,
    source = null,
    sort: sortValue = null,
    after = null,
    before = null,
    size = null,
  } = $props();

  const feed = new PagedFeed((params) => searchEverywhere(params).then((r) => r.data), { facets: true });

  const typesParam = $derived(facetTypes(typeFilter, feed.facets?.types));
  // A search orders by best match until a column header asks for another sort.
  const bestMatch = $derived(!sortValue && !!search);
  const sort = $derived(bestMatch ? null : parseSort(sortValue));

  $effect(() => {
    const params = {
      tag: tagFilter || undefined,
      search: search || undefined,
      owner: ownerFilter || undefined,
      source: source || undefined,
      types: typesParam,
      ...(bestMatch ? { sort_by: "relevance" } : sortParams(sort)),
      ...rangeParams({ after, before, size }),
    };
    untrack(() => feed.reset(params));
  });

  const withParams = (changes) => filterUrl("/search", changes);

  const actions = [
    { icon: "link", title: "Copy link", run: (r) => copyToClipboard(`${location.origin}/${r.id}`, "Link copied") },
    { icon: "copy", title: "Copy content", run: (r) => copyRelicContent(r.id) },
    { icon: "raw", title: "View raw", run: (r) => window.open(`/${r.id}/raw`, "_blank", "noopener") },
    { icon: "fork", title: "Fast fork", run: (r) => fastForkRelic(r) },
    { icon: "download", title: "Download", run: (r) => downloadRelic(r.id, r.name, r.content_type) },
  ];

  const filtered = $derived(!!(search || tagFilter || typeFilter || ownerFilter || source || after || before || size));
  // "All" counts every reason, before the source filter.
  const allCount = $derived(source ? null : feed.total);
</script>

<RelicWorkbench
  {feed}
  grouped={!bestMatch && sort.key === "date"}
  highlight={search || ""}
  {actions}
  sort={bestMatch ? null : sort}
  showSource
  onsort={(key) => navigate(withParams({ sort: sortQuery(nextSort(sort ?? { key: null }, key)) ?? "date-desc" }), { replace: true })}
  emptyText={filtered ? "Nothing you can see matches these filters." : "Nothing here yet: relics you make, bookmark or are given show up here, with every public one."}
  emptyAction={filtered ? { href: "/search", label: "Clear filters" } : { href: "/", label: "Create a relic" }}
  ontag={(tag) => navigate(withParams({ tag, search: null }))}
  onowner={(r) => navigate(withParams({ owner: r.owner_public_id }))}
  ontype={(r) => navigate(withParams({ type: baseType(r.content_type) }))}
>
  {#snippet pagebar({ inspectorOpen, toggleInspector })}
    <PageBar title="Everywhere" count={feed.total} {inspectorOpen} ontoggleinspector={toggleInspector}>
      {#snippet filters()}
        {#if search}
          <span class="r-chip-filter">{search}<button onclick={() => navigate(withParams({ search: null }))} aria-label="Clear search"><Icon name="x" /></button></span>
        {/if}
        {#if tagFilter}
          <span class="r-chip-filter">#{tagFilter}<button onclick={() => navigate(withParams({ tag: null }))} aria-label="Clear tag filter"><Icon name="x" /></button></span>
        {/if}
        <FilterChips owner={ownerFilter} type={typeFilter} relics={feed.items} {after} {before} {size} hrefFor={withParams} />
        {#if filtered}<CopyResultsLink />{/if}
        <span class="r-pagebar-sep"></span>
        <WhereFacets active={source} counts={feed.facets?.sources} total={source ? null : allCount} hrefFor={(s) => withParams({ source: s })} />
      {/snippet}
      {#snippet options()}
        <TypeFacets compact active={facetKeyOf(typeFilter)} types={feed.facets?.types} showCounts={filtered} hrefFor={(type) => withParams({ type })} />
        <TagPicker active={tagFilter} tags={feed.facets?.tags} hrefFor={(tag) => withParams({ tag })} />
        {#if search}
          {#if bestMatch}
            <span class="r-pagebar-opt" title="Best name matches first; a column header sorts by it instead">sort <b>best match</b></span>
          {:else}
            <a class="r-pagebar-opt best" href={withParams({ sort: null })} title="Order by best match again">sort <b>best match</b></a>
          {/if}
        {/if}
      {/snippet}
    </PageBar>
  {/snippet}

  {#snippet status()}
    <span><Icon name="globe" />{feed.total == null ? "…" : feed.total.toLocaleString("en-US")} {search || filtered ? "matches in" : "relics:"} everything you can see</span>
    <span>{feed.items.length.toLocaleString("en-US")} loaded</span>
    {#if feed.error}<span class="status-error">Couldn’t load more. <button class="r-link" onclick={() => feed.reload()}>Retry</button></span>{/if}
    <span class="r-gap"></span>
    <span class="r-hints"><span><kbd class="r-kbd">/</kbd>search</span><span><kbd class="r-kbd">↑</kbd><kbd class="r-kbd">↓</kbd>move</span><span><kbd class="r-kbd">]</kbd>inspector</span></span>
  {/snippet}
</RelicWorkbench>

<style>
  .best {
    color: var(--ink-3);
    text-decoration: none;
  }
  .best:hover b {
    color: var(--accent);
  }
</style>
