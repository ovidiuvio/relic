<script>
  // A list in the relic list's style for other records (users, reports, backups, jobs): a header
  // row that sorts, 30px rows, a selection the inspector follows, hover actions in the last
  // column, and more rows as you scroll.
  //   click a row: select · ↑↓ / j k: move · ↵ or double-click: open (when `onopen` is set)
  //
  // columns: [{ key, label, width, sort?: first-click direction, num?, mono?, hide?: "narrow" | "phone" }]
  //   width is a grid track ("minmax(0, 1fr)", "90px"); hide drops the column below 1180px
  //   ("narrow") or on phones ("phone"). `cell(row, column)` renders a cell's contents.
  import Icon from "./Icon.svelte";

  let {
    rows = [],
    columns,
    cell, // snippet(row, column)
    rowId = (row) => row.id,
    label = "List",
    loading = false,
    hasMore = false,
    selectedId = null,
    sort = null, // { key, dir }
    actions = [], // [{ icon, title, run(row), when?(row), disabled?(row) }]
    emptyText = "Nothing here yet",
    emptyAction = null, // { label, run } or { label, href }
    rowClass = () => "",
    onsort, // (key) => void
    onselect,
    onopen = null,
    onloadmore,
  } = $props();

  let listEl = $state();
  let sentinel = $state();

  const actionsWidth = $derived(actions.length ? `${actions.length * 28 + 6}px` : null);
  const template = (hidden, withActions = true) => {
    const tracks = columns.filter((c) => !hidden.includes(c.hide)).map((c) => c.width);
    if (actionsWidth && withActions) tracks.push(actionsWidth);
    return tracks.join(" ");
  };
  const gridStyle = $derived(
    `--cols: ${template([])}; --cols-narrow: ${template(["narrow"])}; --cols-phone: ${template(["narrow", "phone"], false)}`
  );

  function onRowClick(event, row) {
    if (event.target.closest("a, button, input")) return;
    onselect?.(row);
  }

  function move(delta) {
    if (!rows.length) return;
    const i = rows.findIndex((r) => rowId(r) === selectedId);
    const next = rows[Math.min(rows.length - 1, Math.max(0, i < 0 ? 0 : i + delta))];
    onselect?.(next);
    requestAnimationFrame(() => {
      const row = listEl?.querySelector(`[data-id="${CSS.escape(String(rowId(next)))}"]`);
      row?.focus({ preventScroll: true });
      row?.scrollIntoView({ block: "nearest" });
    });
  }

  function onKeydown(event) {
    if (event.target.closest("button, input, a")) return;
    if (event.key === "ArrowDown" || event.key === "j") (event.preventDefault(), move(1));
    else if (event.key === "ArrowUp" || event.key === "k") (event.preventDefault(), move(-1));
    else if (event.key === "Enter" && onopen) {
      const row = rows.find((r) => rowId(r) === selectedId);
      if (row) (event.preventDefault(), onopen(row));
    }
  }

  $effect(() => {
    if (!sentinel || !hasMore) return;
    const io = new IntersectionObserver((e) => e[0].isIntersecting && !loading && onloadmore?.(), { root: listEl, rootMargin: "400px" });
    io.observe(sentinel);
    return () => io.disconnect();
  });

  const sortedBy = (key) => sort?.key === key;
  const focusId = $derived(rows.some((r) => rowId(r) === selectedId) ? selectedId : rows[0] && rowId(rows[0]));
  const hideClass = (c) => (c.hide ? `hide-${c.hide}` : "");
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div class="list" bind:this={listEl} style={gridStyle} role="list" aria-label={label} aria-busy={loading} onkeydown={onKeydown}>
  {#if rows.length}
    <div class="list-head cols" role="presentation">
      {#each columns as c (c.key)}
        {#if c.sort}
          <button
            class="head-sort {hideClass(c)}"
            class:is-num={c.num}
            class:is-on={sortedBy(c.key)}
            onclick={() => onsort?.(c.key)}
            aria-label={sortedBy(c.key) ? `${c.label}, sorted ${sort.dir === "asc" ? "ascending" : "descending"}` : `Sort by ${c.label.toLowerCase()}`}
          >
            {c.label}{#if sortedBy(c.key)}<span class="head-dir" class:is-asc={sort.dir === "asc"}><Icon name="arrowup" /></span>{/if}
          </button>
        {:else}
          <span class={hideClass(c)} class:is-num={c.num}>{c.label}</span>
        {/if}
      {/each}
      {#if actions.length}<span class="hide-phone"></span>{/if}
    </div>
  {/if}

  {#each rows as row (rowId(row))}
    {@const id = rowId(row)}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_no_noninteractive_tabindex, a11y_click_events_have_key_events -->
    <div
      class="row cols {rowClass(row)}"
      class:is-selected={id === selectedId}
      data-id={id}
      role="listitem"
      aria-current={id === selectedId ? "true" : undefined}
      tabindex={id === focusId ? 0 : -1}
      onclick={(e) => onRowClick(e, row)}
      ondblclick={() => onopen?.(row)}
    >
      {#each columns as c (c.key)}
        <span class="cell {hideClass(c)}" class:is-num={c.num} class:is-mono={c.mono}>{@render cell(row, c)}</span>
      {/each}
      {#if actions.length}
        <span class="r-row-actions row-actions hide-phone">
          {#each actions.filter((a) => !a.when || a.when(row)) as action (action.title)}
            <button
              class="r-btn r-btn-ghost"
              title={action.title}
              aria-label={action.title}
              tabindex="-1"
              disabled={action.disabled?.(row)}
              onclick={(e) => (e.stopPropagation(), action.run(row))}
              ondblclick={(e) => e.stopPropagation()}
            >
              <Icon name={action.icon} />
            </button>
          {/each}
        </span>
      {/if}
    </div>
  {:else}
    {#if !loading}
      <p class="list-empty">
        {emptyText}
        {#if emptyAction?.href}<a class="r-link" href={emptyAction.href}>{emptyAction.label}</a>
        {:else if emptyAction}<button class="r-link" onclick={emptyAction.run}>{emptyAction.label}</button>{/if}
      </p>
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
    grid-template-columns: var(--cols);
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
  .list-head .is-num {
    justify-content: flex-end;
    text-align: right;
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
  .row:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }
  .cell {
    display: flex;
    align-items: center;
    gap: var(--space-1\.5);
    min-width: 0;
    overflow: hidden;
    color: var(--ink);
    text-overflow: ellipsis;
  }
  .cell.is-mono {
    color: var(--ink-3);
    font: 12.5px var(--font-mono);
  }
  .cell.is-num {
    justify-content: flex-end;
    color: var(--ink-3);
    font: 12.5px var(--font-mono);
  }
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
  .list-empty button.r-link {
    padding: 0;
    border: 0;
    background: none;
    font: inherit;
    cursor: pointer;
  }
  .list-sentinel {
    height: 1px;
  }
  @media (max-width: 1180px) {
    .cols {
      grid-template-columns: var(--cols-narrow);
    }
    .hide-narrow {
      display: none !important;
    }
  }
  @media (max-width: 767px) {
    .cols {
      grid-template-columns: var(--cols-phone);
    }
    .row {
      height: 40px;
    }
    .list-head,
    .hide-phone {
      display: none !important;
    }
  }
</style>
