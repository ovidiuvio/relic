<script>
  // My relics: everything you created, any visibility, with editing and deleting in the
  // inspector (no dialogs). Search comes from the navbar (?search=), tag filters from ?tag=.
  import { untrack } from "svelte";
  import Icon from "../lib/ui/Icon.svelte";
  import PageBar from "../lib/shell/PageBar.svelte";
  import TypeFacets from "../lib/relics/TypeFacets.svelte";
  import TagPicker from "../lib/relics/TagPicker.svelte";
  import FilterChips from "../lib/relics/FilterChips.svelte";
  import CopyResultsLink from "../lib/relics/CopyResultsLink.svelte";
  import { rangeParams } from "../lib/search/ranges";
  import { facetTypes, facetKeyOf, baseType } from "../lib/relics/typeFacets";
  import RelicWorkbench from "../lib/relics/RelicWorkbench.svelte";
  import { PagedFeed } from "../lib/data/PagedFeed.svelte.js";
  import { nextSort, sortParams, sortQuery, parseSort } from "../lib/relics/sort";
  import { filterUrl } from "../lib/relics/filters";
  import { refreshSidebar } from "../lib/shell/sidebarData";
  import { getUserRelics } from "../services/api";
  import { copyRelicContent, downloadRelic, fastForkRelic, copyToClipboard } from "../services/relicActions";
  import { getFilesFromDrop } from "../services/utils/fileProcessing";
  import { uploadFiles } from "../lib/compose/pendingUpload";
  import { navigate } from "../utils/navigation";

  let { tagFilter = null, search = null, typeFilter = null, sort: sortValue = null, after = null, before = null, size = null } = $props();

  const feed = new PagedFeed((params) => getUserRelics(params).then((r) => r.data), { facets: true });

  // The type facet as the content types to send; derived, so new counts don't reload the same list.
  const typesParam = $derived(facetTypes(typeFilter, feed.facets?.types));
  // The sort lives in the URL (?sort=size-desc) so links and search history keep it.
  const sort = $derived(parseSort(sortValue));

  $effect(() => {
    const params = { tag: tagFilter || undefined, search: search || undefined, types: typesParam, ...sortParams(sort), ...rangeParams({ after, before, size }) };
    untrack(() => feed.reset(params));
  });

  const withParams = (changes) => filterUrl("/my-relics", changes);

  const actions = [
    { icon: "link", title: "Copy link", run: (r) => copyToClipboard(`${location.origin}/${r.id}`, "Link copied") },
    { icon: "copy", title: "Copy content", run: (r) => copyRelicContent(r.id) },
    { icon: "raw", title: "View raw", run: (r) => window.open(`/${r.id}/raw`, "_blank", "noopener") },
    { icon: "fork", title: "Fast fork", run: (r) => fastForkRelic(r) },
    { icon: "download", title: "Download", run: (r) => downloadRelic(r.id, r.name, r.content_type) },
    { icon: "edit", title: "Edit details", request: "edit" },
    { icon: "trash", title: "Delete", request: "delete" },
  ];

  // Dropped files go to the New relic page to upload.
  async function onDropFiles(dataTransfer) {
    const files = await getFilesFromDrop(dataTransfer);
    if (files.length) uploadFiles(files);
  }

  const filtered = $derived(!!(search || tagFilter || typeFilter || after || before || size));
</script>

<RelicWorkbench
  {feed}
  grouped={sort.key === "date"}
  highlight={search || ""}
  {actions}
  {sort}
  onsort={(key) => navigate(withParams({ sort: sortQuery(nextSort(sort, key)) }), { replace: true })}
  editable
  showPublic
  showOwner={false}
  emptyText={filtered ? "None of your relics match these filters." : "You haven’t made any relics yet."}
  emptyAction={filtered ? { href: "/my-relics", label: "Clear filters" } : { href: "/", label: "Create your first relic" }}
  ontag={(tag) => navigate(withParams({ tag, search: null }))}
  ontype={(r) => navigate(withParams({ type: baseType(r.content_type) }))}
  ondropfiles={onDropFiles}
  dropLabel="Drop files to add them to your relics"
>
  {#snippet pagebar({ inspectorOpen, toggleInspector })}
    <PageBar title={search || tagFilter ? "Results" : "My relics"} count={feed.total} {inspectorOpen} ontoggleinspector={toggleInspector}>
      {#snippet filters()}
        {#if search}
          <span class="r-chip-filter">{search}<button onclick={() => navigate(withParams({ search: null }))} aria-label="Clear search"><Icon name="x" /></button></span>
        {/if}
        {#if tagFilter}
          <span class="r-chip-filter">#{tagFilter}<button onclick={() => navigate(withParams({ tag: null }))} aria-label="Clear tag filter"><Icon name="x" /></button></span>
        {/if}
        <FilterChips type={typeFilter} {after} {before} {size} hrefFor={withParams} />
        {#if filtered}<CopyResultsLink />{/if}
      <span class="r-pagebar-sep"></span>
        <TypeFacets active={facetKeyOf(typeFilter)} types={feed.facets?.types} showCounts={filtered} hrefFor={(type) => withParams({ type })} />
      {/snippet}
      {#snippet options()}
        <TagPicker active={tagFilter} tags={feed.facets?.tags} hrefFor={(tag) => withParams({ tag })} />
      {/snippet}
    </PageBar>
  {/snippet}

  {#snippet status()}
    <span><Icon name="user" />{feed.total == null ? "…" : feed.total.toLocaleString("en-US")} of your relics</span>
    <span>{feed.items.length.toLocaleString("en-US")} loaded</span>
    {#if feed.error}<span class="status-error">Couldn’t load more. <button class="r-link" onclick={() => feed.reload()}>Retry</button></span>{/if}
    <span class="r-gap"></span>
    <span class="r-hints"><span><kbd class="r-kbd">/</kbd>search</span><span><kbd class="r-kbd">e</kbd>edit</span><span><kbd class="r-kbd">]</kbd>inspector</span></span>
  {/snippet}
</RelicWorkbench>

