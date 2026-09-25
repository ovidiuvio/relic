<script>
  // Recent: every public relic, newest first, as the compact day-grouped log.
  // Search comes from the navbar (?search=), tag filters from ?tag=; both show as chips.
  import { untrack } from "svelte";
  import Icon from "../lib/ui/Icon.svelte";
  import PageBar from "../lib/shell/PageBar.svelte";
  import RelicWorkbench from "../lib/relics/RelicWorkbench.svelte";
  import RelicDropModal from "../components/RelicDropModal.svelte";
  import { PagedFeed } from "../lib/data/PagedFeed.svelte.js";
  import { DEFAULT_SORT, nextSort, sortParams } from "../lib/relics/sort";
  import { listRelics } from "../services/api";
  import { copyRelicContent, downloadRelic, fastForkRelic, copyToClipboard } from "../services/relicActions";
  import { getFilesFromDrop } from "../services/utils/fileProcessing";
  import { navigate } from "../utils/navigation";
  import { filterUrl } from "../lib/relics/filters";

  let { tagFilter = null, search = null } = $props();

  const feed = new PagedFeed((params) => listRelics(params).then((r) => r.data));
  let sort = $state(DEFAULT_SORT);

  $effect(() => {
    const params = {
      tag: tagFilter || undefined,
      search: search || undefined,
      ...sortParams(sort),
    };
    untrack(() => feed.reset(params));
  });

  const withParams = (changes) => filterUrl("/recent", changes);

  const actions = [
    { icon: "link", title: "Copy link", run: (r) => copyToClipboard(`${location.origin}/${r.id}`, "Link copied") },
    { icon: "copy", title: "Copy content", run: (r) => copyRelicContent(r.id) },
    { icon: "raw", title: "View raw", run: (r) => window.open(`/${r.id}/raw`, "_blank", "noopener") },
    { icon: "fork", title: "Fast fork", run: (r) => fastForkRelic(r) },
    { icon: "download", title: "Download", run: (r) => downloadRelic(r.id, r.name, r.content_type) },
  ];

  // Dropped files open the upload form (still a dialog; it moves into the inspector later).
  let droppedFiles = $state(null);
  async function onDropFiles(dataTransfer) {
    const files = await getFilesFromDrop(dataTransfer);
    if (files.length) droppedFiles = files;
  }

  const filtered = $derived(!!(search || tagFilter));
</script>

<RelicWorkbench
  {feed}
  grouped={sort.key === "date"}
  highlight={search || ""}
  {actions}
  {sort}
  onsort={(key) => (sort = nextSort(sort, key))}
  emptyText={filtered ? "No public relics match these filters." : "No public relics yet."}
  emptyAction={filtered ? { href: "/recent", label: "Clear filters" } : { href: "/", label: "Create the first one" }}
  ontag={(tag) => navigate(withParams({ tag, search: null }))}
  ondropfiles={onDropFiles}
  dropLabel="Drop files to upload them as public relics"
>
  {#snippet pagebar({ inspectorOpen, toggleInspector })}
    <PageBar title={filtered ? "Results" : "Recent"} count={feed.total} {inspectorOpen} ontoggleinspector={toggleInspector}>
      {#snippet filters()}
        {#if search}
          <span class="r-chip-filter">{search}<button onclick={() => navigate(withParams({ search: null }))} aria-label="Clear search"><Icon name="x" /></button></span>
        {/if}
        {#if tagFilter}
          <span class="r-chip-filter">#{tagFilter}<button onclick={() => navigate(withParams({ tag: null }))} aria-label="Clear tag filter"><Icon name="x" /></button></span>
        {/if}
      {/snippet}
    </PageBar>
  {/snippet}

  {#snippet status()}
    <span><Icon name="globe" />{feed.total == null ? "…" : feed.total.toLocaleString("en-US")} public relics</span>
    <span>{feed.items.length.toLocaleString("en-US")} loaded</span>
    {#if feed.error}<span class="status-error">Couldn’t load more. <button class="r-link" onclick={() => feed.reload()}>Retry</button></span>{/if}
    <span class="r-gap"></span>
    <span class="r-hints"><span><kbd class="r-kbd">/</kbd>search</span><span><kbd class="r-kbd">↑</kbd><kbd class="r-kbd">↓</kbd>move</span><span><kbd class="r-kbd">]</kbd>inspector</span></span>
  {/snippet}
</RelicWorkbench>

{#if droppedFiles}
  <RelicDropModal
    files={droppedFiles}
    on:close={() => (droppedFiles = null)}
    on:success={() => {
      droppedFiles = null;
      feed.reload();
    }}
  />
{/if}
