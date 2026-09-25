<script>
  // One space: its relics as the relic list, with the space itself (details, people, settings)
  // in the inspector when you open it from the page bar. Editors and above can add relics
  // (new, existing by ID, or dropped files) and remove them, with Undo.
  import { untrack } from "svelte";
  import Icon from "../lib/ui/Icon.svelte";
  import PageBar from "../lib/shell/PageBar.svelte";
  import RelicWorkbench from "../lib/relics/RelicWorkbench.svelte";
  import SpaceInspector from "../lib/spaces/SpaceInspector.svelte";
  import RelicDropModal from "../components/RelicDropModal.svelte";
  import { PagedFeed } from "../lib/data/PagedFeed.svelte.js";
  import { InspectorPanel } from "../lib/shell/inspectorPanel.svelte.js";
  import { DEFAULT_SORT, nextSort, sortParams } from "../lib/relics/sort";
  import { filterUrl } from "../lib/relics/filters";
  import { refreshSidebar } from "../lib/shell/sidebarData";
  import { layout } from "../lib/shell/layout";
  import { canAddRelics, roleLabel } from "../lib/spaces/roles";
  import { spaces as spacesApi } from "../services/api";
  import { copyRelicContent, downloadRelic, fastForkRelic, copyToClipboard } from "../services/relicActions";
  import { getFilesFromDrop } from "../services/utils/fileProcessing";
  import { showToast } from "../stores/toastStore";
  import { pageTitle } from "../stores/pageTitle";
  import { navigate } from "../utils/navigation";

  let { spaceId, tagFilter = null, search = null } = $props();

  let space = $state(null);
  let error = $state(null); // HTTP status or "unknown"
  const feed = new PagedFeed((params) => spacesApi.getRelics(spaceId, params));
  const panel = new InspectorPanel();
  let sort = $state(DEFAULT_SORT);
  let showSpace = $state(false); // the inspector shows the space instead of a relic
  let spaceMode = $state("view");

  async function loadSpace(id) {
    error = null;
    try {
      const loaded = await spacesApi.get(id);
      if (id === spaceId) space = loaded;
    } catch (e) {
      if (id === spaceId) error = e.response?.status ?? "unknown";
    }
  }

  $effect(() => {
    const id = spaceId;
    untrack(() => {
      space = null;
      showSpace = false;
      loadSpace(id);
    });
  });

  $effect(() => {
    if (space?.name) pageTitle.set(space.name);
  });

  // Relics load once the space has: a space you can't open shows its error, not a failed list.
  const ready = $derived(space?.id === spaceId);
  $effect(() => {
    const params = { tag: tagFilter || undefined, search: search || undefined, ...sortParams(sort) };
    if (ready) untrack(() => feed.reset(params));
  });

  const canAdd = $derived(canAddRelics(space));
  const withParams = (changes) => filterUrl(`/spaces/${spaceId}`, changes);
  const bump = (n) => space && (space = { ...space, relic_count: Math.max(0, (space.relic_count ?? 0) + n) });

  function openSpacePanel(mode = "view") {
    showSpace = true;
    spaceMode = mode;
    panel.show($layout.dock);
  }

  // Add an existing relic by ID (or a pasted relic link).
  let adding = $state(false);
  let addDraft = $state("");
  let addBusy = $state(false);
  async function addExisting(event) {
    event.preventDefault();
    const id = addDraft.trim().match(/[a-f0-9]{32}/i)?.[0];
    if (!id) return showToast("Paste a relic ID or link (32 hexadecimal characters)", "error");
    addBusy = true;
    try {
      await spacesApi.addRelic(spaceId, id);
      addDraft = "";
      adding = false;
      bump(1);
      feed.reload();
      showToast("Added to the space", "success");
    } catch (e) {
      showToast(e.response?.data?.detail || "Couldn’t add that relic", "error");
    } finally {
      addBusy = false;
    }
  }

  async function removeFromSpace(relic) {
    try {
      await spacesApi.removeRelic(spaceId, relic.id);
      feed.remove(relic.id);
      bump(-1);
      showToast(`Removed “${relic.name || "Untitled"}” from the space`, "success", 3000, {
        label: "Undo",
        run: async () => {
          try {
            await spacesApi.addRelic(spaceId, relic.id);
            bump(1);
            feed.reload();
          } catch {
            showToast("Couldn’t add it back", "error");
          }
        },
      });
    } catch {
      showToast("Couldn’t remove it from the space", "error");
    }
  }

  const actions = $derived([
    { icon: "link", title: "Copy link", run: (r) => copyToClipboard(`${location.origin}/${r.id}`, "Link copied") },
    { icon: "copy", title: "Copy content", run: (r) => copyRelicContent(r.id) },
    { icon: "raw", title: "View raw", run: (r) => window.open(`/${r.id}/raw`, "_blank", "noopener") },
    { icon: "fork", title: "Fast fork", run: (r) => fastForkRelic(r) },
    { icon: "download", title: "Download", run: (r) => downloadRelic(r.id, r.name, r.content_type) },
    ...(canAdd ? [{ icon: "x", title: "Remove from space", run: removeFromSpace }] : []),
  ]);

  let droppedFiles = $state(null);
  async function onDropFiles(dataTransfer) {
    const files = await getFilesFromDrop(dataTransfer);
    if (files.length) droppedFiles = files;
  }

  const filtered = $derived(!!(search || tagFilter));
</script>

{#if error}
  <div class="space-state">
    <Icon name={error === 403 ? "lock" : "layers"} size={28} />
    <h1>{error === 403 ? "You don’t have access to this space" : error === 404 ? "This space doesn’t exist" : "Couldn’t load this space"}</h1>
    <p>
      {#if error === 403}Ask its owner to add you, using the public ID from your profile.
      {:else if error === 404}It may have been deleted, or the link is wrong.
      {:else}Check your connection and try again.{/if}
    </p>
    <div class="space-state-actions">
      {#if error !== 403 && error !== 404}<button class="r-btn r-btn-primary r-btn-md" onclick={() => loadSpace(spaceId)}>Try again</button>{/if}
      <a class="r-btn r-btn-secondary r-btn-md" href="/spaces">All spaces</a>
    </div>
  </div>
{:else}
  <RelicWorkbench
    {feed}
    {panel}
    grouped={sort.key === "date"}
    highlight={search || ""}
    {actions}
    {sort}
    onsort={(key) => (sort = nextSort(sort, key))}
    showPublic
    emptyText={filtered ? "No relics in this space match these filters." : "This space is empty."}
    emptyAction={filtered ? { href: `/spaces/${spaceId}`, label: "Clear filters" } : canAdd ? { href: `/?space=${spaceId}`, label: "Create the first relic here" } : null}
    ontag={(tag) => navigate(withParams({ tag, search: null }))}
    onselect={() => (showSpace = false)}
    aside={showSpace && space ? spaceAside : null}
    ondropfiles={canAdd ? onDropFiles : null}
    dropLabel={space ? `Drop files to upload them into ${space.name}` : undefined}
  >
    {#snippet pagebar({ inspectorOpen, toggleInspector })}
      <PageBar title={space?.name ?? "Space"} count={feed.total} {inspectorOpen} ontoggleinspector={toggleInspector}>
        {#snippet filters()}
          {#if space}
            <span class="space-meta" title={space.visibility === "public" ? "Public space" : "Private space"}>
              <Icon name={space.visibility === "public" ? "globe" : "lock"} size={13} />{roleLabel(space.role)}
            </span>
          {/if}
          {#if search}
            <span class="r-chip-filter">{search}<button onclick={() => navigate(withParams({ search: null }))} aria-label="Clear search"><Icon name="x" /></button></span>
          {/if}
          {#if tagFilter}
            <span class="r-chip-filter">#{tagFilter}<button onclick={() => navigate(withParams({ tag: null }))} aria-label="Clear tag filter"><Icon name="x" /></button></span>
          {/if}
        {/snippet}
        {#snippet actions()}
          {#if canAdd}
            <a class="r-btn r-btn-secondary r-btn-md" href="/?space={spaceId}"><Icon name="plus" />New relic</a>
            <button class="r-btn r-btn-secondary r-btn-md" aria-pressed={adding} onclick={() => (adding = !adding)}><Icon name="link" />Add existing</button>
          {/if}
          <button class="r-btn r-btn-secondary r-btn-md" onclick={() => copyToClipboard(`${location.origin}/spaces/${spaceId}`, "Space link copied")}><Icon name="share" />Share</button>
          <button class="r-btn r-btn-secondary r-btn-md" aria-pressed={showSpace} onclick={() => (showSpace ? (showSpace = false) : openSpacePanel())} title="Details, people and settings">
            <Icon name="layers" />Space
          </button>
        {/snippet}
      </PageBar>
      {#if adding}
        <form class="r-strip r-strip-draft" onsubmit={addExisting}>
          <Icon name="link" />
          <!-- svelte-ignore a11y_autofocus -->
          <span class="r-input r-input-sm"><input bind:value={addDraft} placeholder="Paste a relic ID or link to add it" aria-label="Relic ID or link" spellcheck="false" autofocus onkeydown={(e) => e.key === "Escape" && (adding = false)} /></span>
          <button type="button" class="r-btn r-btn-secondary r-btn-sm" onclick={() => (adding = false)}>Cancel</button>
          <button class="r-btn r-btn-primary r-btn-sm" disabled={!addDraft.trim() || addBusy}>{addBusy ? "Adding…" : "Add to space"}</button>
        </form>
      {/if}
    {/snippet}

    {#snippet status()}
      <span><Icon name="layers" />{feed.total == null ? "…" : `${feed.total.toLocaleString("en-US")} ${feed.total === 1 ? "relic" : "relics"}`} in this space</span>
      <span>{feed.items.length.toLocaleString("en-US")} loaded</span>
      {#if feed.error}<span class="status-error">Couldn’t load more. <button class="r-link" onclick={() => feed.reload()}>Retry</button></span>{/if}
      <span class="r-gap"></span>
      <span class="r-hints"><span><kbd class="r-kbd">/</kbd>search this space</span><span><kbd class="r-kbd">]</kbd>inspector</span></span>
    {/snippet}
  </RelicWorkbench>
{/if}

{#snippet spaceAside({ close })}
  <SpaceInspector
    {space}
    bind:mode={spaceMode}
    onsaved={(saved) => {
      space = { ...space, ...saved };
      refreshSidebar();
    }}
    ondeleted={() => {
      refreshSidebar();
      navigate("/spaces");
    }}
    onclose={close ?? (() => (showSpace = false))}
  />
{/snippet}

{#if droppedFiles && space}
  <RelicDropModal
    files={droppedFiles}
    spaceId={space.id}
    spaceName={space.name}
    on:close={() => (droppedFiles = null)}
    on:success={() => {
      droppedFiles = null;
      feed.reload();
      loadSpace(spaceId);
    }}
  />
{/if}

<style>
  .space-meta {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: var(--ink-3);
    font: 12px var(--font-mono);
  }
  .space-state {
    display: grid;
    justify-items: center;
    align-content: center;
    gap: var(--space-2);
    flex: 1;
    padding: var(--space-5);
    color: var(--ink-3);
    text-align: center;
  }
  .space-state h1 {
    margin: var(--space-2) 0 0;
    color: var(--ink);
    font-size: 17px;
    font-weight: 500;
  }
  .space-state p {
    margin: 0;
    max-width: 44ch;
  }
  .space-state-actions {
    display: flex;
    gap: var(--space-2);
    margin-top: var(--space-2);
  }
</style>
