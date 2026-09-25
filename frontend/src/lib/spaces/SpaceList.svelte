<script>
  // The list of spaces, in the same style as the relic list: a header row that sorts, 30px rows,
  // a selection the inspector follows, hover actions, and more rows as you scroll.
  //   click the name: open · click the row: select · ↑↓ / j k: move · ↵ or double-click: open
  // Dropping files on a row you can add to hands them to `ondropfiles(space, dataTransfer)`.
  import Icon from "../ui/Icon.svelte";
  import { roleLabel, canAddRelics } from "./roles";
  import { copyToClipboard } from "../../services/relicActions";
  import { shortDate, compactNumber } from "../relics/format";

  let {
    spaces = [],
    loading = false,
    hasMore = false,
    selectedId = null,
    sort, // { key: "name" | "relics" | "created", dir }
    highlight = "",
    actions = [], // [{ icon, title, run(space), when?(space) }]
    emptyText = "No spaces yet",
    emptyAction = null,
    onsort,
    onselect,
    onopen,
    onloadmore,
    ondropfiles = null,
  } = $props();

  let listEl = $state();
  let sentinel = $state();
  let dropTarget = $state(null);

  function nameParts(name) {
    const term = highlight.trim();
    const i = term ? name.toLowerCase().indexOf(term.toLowerCase()) : -1;
    if (i < 0) return [{ text: name }];
    return [{ text: name.slice(0, i) }, { text: name.slice(i, i + term.length), mark: true }, { text: name.slice(i + term.length) }];
  }

  function onRowClick(event, space) {
    if (event.target.closest("a, button")) return;
    onselect?.(space);
  }

  function move(delta) {
    if (!spaces.length) return;
    const i = spaces.findIndex((s) => s.id === selectedId);
    const next = spaces[Math.min(spaces.length - 1, Math.max(0, i < 0 ? 0 : i + delta))];
    onselect?.(next);
    requestAnimationFrame(() => {
      const row = listEl?.querySelector(`[data-id="${next.id}"]`);
      row?.focus({ preventScroll: true });
      row?.scrollIntoView({ block: "nearest" });
    });
  }

  function onKeydown(event) {
    if (event.target.closest("button, input")) return;
    if (event.key === "ArrowDown" || event.key === "j") (event.preventDefault(), move(1));
    else if (event.key === "ArrowUp" || event.key === "k") (event.preventDefault(), move(-1));
    else if (event.key === "Enter") {
      const space = spaces.find((s) => s.id === selectedId);
      if (space) (event.preventDefault(), onopen?.(space));
    }
  }

  $effect(() => {
    if (!sentinel || !hasMore) return;
    const io = new IntersectionObserver((e) => e[0].isIntersecting && !loading && onloadmore?.(), { root: listEl, rootMargin: "400px" });
    io.observe(sentinel);
    return () => io.disconnect();
  });

  const hasFiles = (event) => event.dataTransfer?.types?.includes("Files");
  function onDragOver(event, space) {
    if (!ondropfiles || !hasFiles(event) || !canAddRelics(space)) return;
    event.preventDefault();
    event.stopPropagation();
    dropTarget = space.id;
  }
  function onDrop(event, space) {
    if (!ondropfiles || dropTarget !== space.id) return;
    event.preventDefault();
    event.stopPropagation();
    dropTarget = null;
    ondropfiles(space, event.dataTransfer);
  }

  const focusId = $derived(spaces.some((s) => s.id === selectedId) ? selectedId : spaces[0]?.id);
  const sortedBy = (key) => sort?.key === key;
</script>

{#snippet head(key, label, cls = "")}
  <button class="head-sort {cls}" class:is-on={sortedBy(key)} onclick={() => onsort?.(key)} aria-label={sortedBy(key) ? `${label}, sorted ${sort.dir === "asc" ? "ascending" : "descending"}` : `Sort by ${label.toLowerCase()}`}>
    {label}{#if sortedBy(key)}<span class="head-dir" class:is-asc={sort.dir === "asc"}><Icon name="arrowup" /></span>{/if}
  </button>
{/snippet}

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div class="list" bind:this={listEl} role="list" aria-busy={loading} onkeydown={onKeydown} ondragleave={(e) => !listEl.contains(e.relatedTarget) && (dropTarget = null)}>
  {#if spaces.length}
    <div class="list-head cols" role="presentation">
      <span></span>
      {@render head("name", "Name")}
      <span>Your role</span>
      {@render head("relics", "Relics", "head-num")}
      {@render head("created", "Created", "head-num")}
      <span class="head-id">ID</span>
      <span></span>
    </div>
  {/if}

  {#each spaces as space (space.id)}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_no_noninteractive_tabindex, a11y_click_events_have_key_events -->
    <div
      class="row cols"
      class:is-selected={space.id === selectedId}
      class:is-drop={dropTarget === space.id}
      data-id={space.id}
      role="listitem"
      aria-current={space.id === selectedId ? "true" : undefined}
      tabindex={space.id === focusId ? 0 : -1}
      onclick={(e) => onRowClick(e, space)}
      ondblclick={() => onopen?.(space)}
      ondragover={(e) => onDragOver(e, space)}
      ondrop={(e) => onDrop(e, space)}
    >
      <span class="row-vis" title={space.visibility === "public" ? "Public" : "Private"}>
        <Icon name={space.visibility === "public" ? "globe" : "lock"} size={13} />
      </span>
      <a class="row-name" href="/spaces/{space.id}" tabindex="-1">
        {#each nameParts(space.name) as part}{#if part.mark}<mark>{part.text}</mark>{:else}{part.text}{/if}{/each}
      </a>
      <span class="row-role" class:is-none={!space.role}>{space.role ? roleLabel(space.role) : "—"}</span>
      <span class="row-num">{compactNumber(space.relic_count)}</span>
      <span class="row-num">{shortDate(space.created_at)}</span>
      <button class="row-id" tabindex="-1" title="Copy ID {space.id}" aria-label="Copy space ID" onclick={() => copyToClipboard(space.id, "Space ID copied")} ondblclick={(e) => e.stopPropagation()}>
        {space.id.slice(0, 8)}<Icon name="copy" />
      </button>
      {#if actions.length}
        <span class="r-row-actions row-actions">
          {#each actions.filter((a) => !a.when || a.when(space)) as action (action.title)}
            <button class="r-btn r-btn-ghost" title={action.title} aria-label={action.title} tabindex="-1" onclick={(e) => (e.stopPropagation(), action.run(space))} ondblclick={(e) => e.stopPropagation()}>
              <Icon name={action.icon} />
            </button>
          {/each}
        </span>
      {/if}
      {#if dropTarget === space.id}<span class="row-drop">Drop to upload into this space</span>{/if}
    </div>
  {:else}
    {#if !loading}
      <p class="list-empty">{emptyText}{#if emptyAction}<a class="r-link" href={emptyAction.href}>{emptyAction.label}</a>{/if}</p>
    {/if}
  {/each}

  {#if loading}<p class="list-status" role="status">Loading…</p>{/if}
  {#if hasMore}<div bind:this={sentinel} class="list-sentinel"></div>{/if}
</div>

<style>
  .list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-bottom: var(--space-4);
    outline: 0;
  }
  .cols {
    display: grid;
    /* vis, name, role, relics, created, id, then a column for the hover actions */
    grid-template-columns: 18px minmax(0, 1fr) 90px 64px 90px 84px 78px;
    align-items: center;
    gap: var(--space-2\.5);
    padding: 0 var(--space-4);
  }
  .list-head {
    position: sticky;
    top: 0;
    z-index: 2;
    height: 26px;
    border-bottom: 1px solid var(--line);
    background: var(--surface);
    color: var(--ink-3);
    font: 700 10.5px var(--font-mono);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    white-space: nowrap;
  }
  .head-sort {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    letter-spacing: inherit;
    text-transform: inherit;
    cursor: pointer;
  }
  .head-sort:hover,
  .head-sort.is-on {
    color: var(--accent);
  }
  .head-num {
    justify-content: flex-end;
  }
  .head-dir {
    display: inline-flex;
  }
  .head-dir :global(.r-icon) {
    width: 11px;
    height: 11px;
    transform: rotate(180deg);
  }
  .head-dir.is-asc :global(.r-icon) {
    transform: none;
  }

  .row {
    position: relative;
    height: 30px;
    font-size: 13px;
    white-space: nowrap;
    cursor: default;
  }
  .row:hover {
    background: var(--hover);
  }
  .row.is-selected {
    background: var(--accent-soft);
    box-shadow: inset 2px 0 var(--accent);
  }
  .row.is-selected .row-name {
    font-weight: 500;
  }
  .row:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }
  .row.is-drop {
    background: var(--accent-soft);
    box-shadow: inset 0 0 0 2px var(--accent);
  }
  .row-vis {
    display: inline-flex;
    color: var(--ink-3);
  }
  .row-name {
    min-width: 0;
    overflow: hidden;
    color: var(--ink);
    text-overflow: ellipsis;
    text-decoration: none;
  }
  .row-name:hover {
    color: var(--accent);
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  .row-name mark {
    padding: 0 1px;
    border-radius: 2px;
    background: var(--mark);
    color: inherit;
  }
  .row-role,
  .row-num,
  .row-id {
    color: var(--ink-3);
    font: 12.5px var(--font-mono);
  }
  .row-role.is-none {
    color: var(--line-2);
  }
  .row-num {
    text-align: right;
  }
  .row-id {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 0;
    border: 0;
    background: none;
    text-align: left;
    cursor: pointer;
  }
  .row-id :global(.r-icon) {
    width: 11px;
    height: 11px;
    visibility: hidden;
  }
  .row-id:hover {
    color: var(--accent);
  }
  .row:hover .row-id :global(.r-icon) {
    visibility: visible;
  }
  /* Actions sit in their own last column, shown on hover, selection and keyboard focus. */
  .row .row-actions {
    position: static;
    display: flex;
    justify-content: flex-end;
    padding: 0;
    background: none;
    visibility: hidden;
  }
  .row:hover .row-actions,
  .row.is-selected .row-actions,
  .row:focus-within .row-actions {
    visibility: visible;
  }
  .row-drop {
    position: absolute;
    right: var(--space-4);
    color: var(--accent);
    font-weight: 500;
  }
  .list-empty {
    display: flex;
    gap: var(--space-2);
  }
  .list-empty,
  .list-status {
    margin: 0;
    padding: var(--space-5) var(--space-4);
    color: var(--ink-3);
  }
  .list-sentinel {
    height: 1px;
  }
  @media (max-width: 1180px) {
    .cols {
      grid-template-columns: 18px minmax(0, 1fr) 80px 56px 80px 78px;
    }
    .row-id,
    .head-id {
      display: none;
    }
  }
  @media (max-width: 767px) {
    .cols {
      grid-template-columns: 18px minmax(0, 1fr) 56px;
    }
    .row {
      height: 40px;
    }
    .list-head,
    .row-role,
    .row-num + .row-num,
    .row-id,
    .row .row-actions {
      display: none !important;
    }
  }
</style>
