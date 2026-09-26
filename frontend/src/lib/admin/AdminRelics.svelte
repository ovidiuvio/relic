<script>
  // Admin · Relics: every relic on the instance, private and restricted included. Filter by
  // visibility, tag and search (in the URL) or by owner (click an owner; kept in memory, since
  // a user's ID is their key). The inspector is the relic inspector, with Delete for any relic.
  import { untrack } from "svelte";
  import Icon from "../ui/Icon.svelte";
  import PageBar from "../shell/PageBar.svelte";
  import TypeFacets from "../relics/TypeFacets.svelte";
  import TagPicker from "../relics/TagPicker.svelte";
  import FilterChips from "../relics/FilterChips.svelte";
  import { facetTypes, facetKeyOf, baseType } from "../relics/typeFacets";
  import RelicWorkbench from "../relics/RelicWorkbench.svelte";
  import { PagedFeed } from "../data/PagedFeed.svelte.js";
  import { nextSort, sortQuery, parseSort } from "../relics/sort";
  import { filterUrl } from "../relics/filters";
  import { relicOwner, refreshAdminStats } from "./adminState";
  import { getAdminRelics } from "../../services/api";
  import { copyRelicContent, downloadRelic, copyToClipboard } from "../../services/relicActions";
  import { navigate } from "../../utils/navigation";

  let { search = null, tag = null, visibility = null, type = null, sort: sortValue = null } = $props();

  const PATH = "/admin/relics";
  const VISIBILITIES = [
    { key: null, label: "All" },
    { key: "public", label: "Public" },
    { key: "private", label: "Private" },
    { key: "restricted", label: "Restricted" },
  ];
  // What the admin endpoint sorts by: list column → API field.
  const SORT_FIELDS = { date: "created_at", name: "name", size: "size_bytes", views: "access_count" };

  const feed = new PagedFeed(
    (p) =>
      getAdminRelics(p.limit, p.offset, p.visibility, p.user, p.search, p.tag, p.sort_by, p.sort_order, { types: p.types, facets: p.facets }).then(
        (r) => r.data
      ),
    { facets: true }
  );
  const typesParam = $derived(facetTypes(type, feed.facets?.types));
  const sort = $derived(parseSort(sortValue, Object.keys(SORT_FIELDS)));

  $effect(() => {
    const params = {
      visibility: visibility || null,
      user: $relicOwner?.id ?? null,
      search: search || null,
      tag: tag || null,
      types: typesParam,
      sort_by: SORT_FIELDS[sort.key],
      sort_order: sort.dir,
    };
    untrack(() => feed.reset(params));
  });

  const withParams = (changes) => filterUrl(PATH, changes);

  const actions = [
    { icon: "link", title: "Copy link", run: (r) => copyToClipboard(`${location.origin}/${r.id}`, "Link copied") },
    { icon: "copy", title: "Copy content", run: (r) => copyRelicContent(r.id) },
    { icon: "raw", title: "View raw", run: (r) => window.open(`/${r.id}/raw`, "_blank", "noopener") },
    { icon: "download", title: "Download", run: (r) => downloadRelic(r.id, r.name, r.content_type) },
    { icon: "trash", title: "Delete", request: "delete" },
  ];

  function showOwner(relic) {
    relicOwner.set({ id: relic.user_id, publicId: relic.user_public_id, label: relic.owner_name || "—" });
  }

  const filtered = $derived(!!(search || tag || $relicOwner || visibility || type));
</script>

<RelicWorkbench
  {feed}
  grouped={sort.key === "date"}
  highlight={search || ""}
  {actions}
  {sort}
  sortable={Object.keys(SORT_FIELDS)}
  onsort={(key) => navigate(withParams({ sort: sortQuery(nextSort(sort, key)) }), { replace: true })}
  deletable
  showPublic
  onowner={showOwner}
  ondeleted={refreshAdminStats}
  emptyText={filtered ? "No relics match these filters." : "No relics on this instance yet."}
  emptyAction={filtered ? { href: PATH, label: "Clear filters" } : null}
  ontag={(t) => navigate(withParams({ tag: t }))}
  ontype={(r) => navigate(withParams({ type: baseType(r.content_type) }))}
>
  {#snippet pagebar({ inspectorOpen, toggleInspector })}
    <PageBar title="Relics" count={feed.total} {inspectorOpen} ontoggleinspector={toggleInspector}>
      {#snippet filters()}
        {#if $relicOwner}
          <span class="r-chip-filter"><Icon name="user" />{$relicOwner.label}{#if $relicOwner.publicId}<button class="owner-id" onclick={() => copyToClipboard($relicOwner.publicId, "Owner ID copied")} title="Copy owner ID {$relicOwner.publicId}">{$relicOwner.publicId.slice(0, 8)}<Icon name="copy" /></button>{/if}<button onclick={() => relicOwner.set(null)} aria-label="Show every owner"><Icon name="x" /></button></span>
        {/if}
        {#if search}
          <span class="r-chip-filter">{search}<button onclick={() => navigate(withParams({ search: null }))} aria-label="Clear search"><Icon name="x" /></button></span>
        {/if}
        {#if tag}
          <span class="r-chip-filter">#{tag}<button onclick={() => navigate(withParams({ tag: null }))} aria-label="Clear tag filter"><Icon name="x" /></button></span>
        {/if}
        <FilterChips {type} hrefFor={withParams} />
        <span class="r-pagebar-sep"></span>
        <TypeFacets active={facetKeyOf(type)} types={feed.facets?.types} showCounts={filtered} hrefFor={(t) => withParams({ type: t })} />
      {/snippet}
      {#snippet options()}
        <label class="r-pagebar-opt">visibility
          <select value={visibility ?? ""} onchange={(e) => navigate(withParams({ visibility: e.currentTarget.value || null }))} aria-label="Visibility">
            {#each VISIBILITIES as v (v.label)}<option value={v.key ?? ""}>{v.key ? v.label.toLowerCase() : "any"}</option>{/each}
          </select>
        </label>
        <TagPicker active={tag} tags={feed.facets?.tags} hrefFor={(t) => withParams({ tag: t })} />
      {/snippet}
      {#snippet actions()}
        <button class="r-btn r-btn-ghost r-btn-icon" onclick={() => feed.reload()} title="Refresh" aria-label="Refresh"><Icon name="history" /></button>
      {/snippet}
    </PageBar>
  {/snippet}

  {#snippet status()}
    <span><Icon name="file" />{feed.total == null ? "…" : `${feed.total.toLocaleString("en-US")} ${feed.total === 1 ? "relic" : "relics"}`}</span>
    <span>{feed.items.length.toLocaleString("en-US")} loaded</span>
    {#if feed.error}<span class="status-error">Couldn’t load more. <button class="r-link" onclick={() => feed.reload()}>Retry</button></span>{/if}
    <span class="r-gap"></span>
    <span class="r-hints"><span><kbd class="r-kbd">/</kbd>search</span><span><kbd class="r-kbd">↵</kbd>open</span><span><kbd class="r-kbd">]</kbd>inspector</span></span>
  {/snippet}
</RelicWorkbench>

<style>
  .owner-id {
    display: inline-flex !important;
    align-items: center;
    gap: 2px !important;
    margin-left: 4px;
    color: var(--ink-3) !important;
    font: 11.5px var(--font-mono) !important;
  }
  .owner-id:hover {
    color: var(--accent) !important;
  }
</style>
