<script>
  // Spaces: every space you can see, filtered to yours, shared with you or public. The inspector
  // shows the selected space (details, people) and holds New space and Space settings.
  import { untrack } from "svelte";
  import Icon from "../lib/ui/Icon.svelte";
  import PageBar from "../lib/shell/PageBar.svelte";
  import Workbench from "../lib/shell/Workbench.svelte";
  import SpaceList from "../lib/spaces/SpaceList.svelte";
  import SpaceInspector from "../lib/spaces/SpaceInspector.svelte";
  import RelicDropModal from "../components/RelicDropModal.svelte";
  import { PagedFeed } from "../lib/data/PagedFeed.svelte.js";
  import { InspectorPanel } from "../lib/shell/inspectorPanel.svelte.js";
  import { filterUrl } from "../lib/relics/filters";
  import { refreshSidebar } from "../lib/shell/sidebarData";
  import { layout } from "../lib/shell/layout";
  import { canAddRelics, canConfigure } from "../lib/spaces/roles";
  import { session } from "../stores/session";
  import { spaces as spacesApi } from "../services/api";
  import { copyToClipboard } from "../services/relicActions";
  import { getFilesFromDrop } from "../services/utils/fileProcessing";
  import { navigate } from "../utils/navigation";

  let { search = null, create = false } = $props();

  const CATEGORIES = [
    { key: "all", label: "All" },
    { key: "my", label: "Mine" },
    { key: "shared", label: "Shared with me" },
    { key: "public", label: "Public" },
  ];
  const SORTS = { name: ["name", "asc"], relics: ["relic_count", "desc"], created: ["created_at", "desc"] };

  const feed = new PagedFeed((params) => spacesApi.list(params), { rows: "spaces" });
  const panel = new InspectorPanel();
  let category = $state("all");
  let sort = $state({ key: "created", dir: "desc" });
  let selectedId = $state(null);
  let mode = $state("view");
  let confirm = $state(null);

  $effect(() => {
    const params = {
      category: category === "all" ? undefined : category,
      search: search || undefined,
      sort_by: SORTS[sort.key][0],
      sort_order: sort.dir,
    };
    untrack(() => feed.reset(params));
  });

  // ?create=1 (the sidebar's +) opens New space.
  $effect(() => {
    if (create) untrack(startCreate);
  });

  function startCreate() {
    mode = "create";
    panel.show($layout.dock);
  }

  function onSort(key) {
    sort = sort.key === key ? { key, dir: sort.dir === "asc" ? "desc" : "asc" } : { key, dir: SORTS[key][1] };
  }

  const selected = $derived(feed.items.find((s) => s.id === selectedId) ?? null);

  $effect(() => {
    if ($layout.dock && feed.items.length && !feed.items.some((s) => s.id === selectedId)) selectedId = feed.items[0].id;
  });

  function select(space) {
    if ($layout.phone) return open(space);
    selectedId = space.id;
    mode = "view";
    confirm = null;
    if (!$layout.dock) panel.show(false);
  }

  const open = (space) => navigate(`/spaces/${space.id}`);

  function onSaved(space) {
    if (feed.items.some((s) => s.id === space.id)) feed.update(space);
    else feed.reload().then(() => (selectedId = space.id));
    if (create) navigate(filterUrl("/spaces", { create: null }), { replace: true });
    refreshSidebar();
  }

  function onDeleted(space) {
    const i = feed.items.findIndex((s) => s.id === space.id);
    feed.remove(space.id);
    selectedId = feed.items[Math.min(i, feed.items.length - 1)]?.id ?? null;
    mode = "view";
    refreshSidebar();
  }

  const actions = [
    { icon: "link", title: "Copy link", run: (s) => copyToClipboard(`${location.origin}/spaces/${s.id}`, "Space link copied") },
    { icon: "plus", title: "New relic here", run: (s) => navigate(`/?space=${s.id}`), when: canAddRelics },
    { icon: "trash", title: "Delete space", run: askDelete, when: (s) => canConfigure(s, $session.isAdmin) },
  ];

  // Delete from the row: select it and open Settings with the confirmation.
  function askDelete(space) {
    selectedId = space.id;
    panel.show($layout.dock);
    confirm = { what: "delete", n: (confirm?.n ?? 0) + 1 };
  }

  // Files dropped on a space's row upload into that space.
  let drop = $state(null);
  async function onDropFiles(space, dataTransfer) {
    const files = await getFilesFromDrop(dataTransfer);
    if (files.length) drop = { space, files };
  }

  function onKeydown(event) {
    if (event.key === "n") {
      event.preventDefault();
      startCreate();
    }
  }
</script>

<Workbench {panel} hasSelection={!!selected || mode === "create"} label="Spaces" onkeydown={onKeydown}>
  {#snippet pagebar({ inspectorOpen, toggleInspector })}
    <PageBar title={search ? "Results" : "Spaces"} count={feed.total} {inspectorOpen} ontoggleinspector={toggleInspector}>
      {#snippet filters()}
        {#if search}
          <span class="r-chip-filter">{search}<button onclick={() => navigate(filterUrl("/spaces", { search: null }))} aria-label="Clear search"><Icon name="x" /></button></span>
        {/if}
        <span class="r-pagebar-sep"></span>
        <nav class="r-facets" aria-label="Show">
          {#each CATEGORIES as c (c.key)}
            <a href="/spaces" aria-current={category === c.key ? "true" : undefined} onclick={(e) => (e.preventDefault(), (category = c.key))}>{c.label}</a>
          {/each}
        </nav>
      {/snippet}
      {#snippet actions()}
        <button class="r-btn r-btn-secondary r-btn-md" onclick={startCreate} title="New space (n)"><Icon name="plus" />New space</button>
      {/snippet}
    </PageBar>
  {/snippet}

  <SpaceList
    spaces={feed.items}
    loading={feed.loading}
    hasMore={feed.hasMore}
    selectedId={mode === "create" ? null : selectedId}
    {sort}
    highlight={search || ""}
    {actions}
    emptyText={search ? "No spaces match your search." : category === "all" ? "No spaces yet." : "No spaces here yet."}
    emptyAction={search ? { href: "/spaces", label: "Clear search" } : { href: "/spaces?create=1", label: "Create a space" }}
    onsort={onSort}
    onselect={select}
    onopen={open}
    onloadmore={() => feed.more()}
    ondropfiles={onDropFiles}
  />

  {#snippet inspector({ close })}
    <SpaceInspector space={selected} bind:mode {confirm} showOpen onsaved={onSaved} ondeleted={onDeleted} onclose={close} />
  {/snippet}

  {#snippet status()}
    <span><Icon name="layers" />{feed.total == null ? "…" : `${feed.total.toLocaleString("en-US")} ${feed.total === 1 ? "space" : "spaces"}`}</span>
    <span>{feed.items.length.toLocaleString("en-US")} loaded</span>
    {#if feed.error}<span class="status-error">Couldn’t load more. <button class="r-link" onclick={() => feed.reload()}>Retry</button></span>{/if}
    <span class="r-gap"></span>
    <span class="r-hints"><span><kbd class="r-kbd">n</kbd>new space</span><span><kbd class="r-kbd">↵</kbd>open</span><span><kbd class="r-kbd">]</kbd>inspector</span></span>
  {/snippet}
</Workbench>

{#if drop}
  <RelicDropModal
    files={drop.files}
    spaceId={drop.space.id}
    spaceName={drop.space.name}
    on:close={() => (drop = null)}
    on:success={() => {
      drop = null;
      feed.reload();
      refreshSidebar();
    }}
  />
{/if}
