<script>
  // The list layout: the compact log of the relic lists, one row per entry with day rules, and
  // sortable columns. Sorting by anything but date drops the day rules. ↑ ↓ move, ↵ opens.
  import { onMount } from "svelte";
  import Icon from "../ui/Icon.svelte";
  import { relativeTime } from "../relics/format";
  import { dayLabel } from "./dates";

  let {
    feed,
    selectedId = null,
    sort = { key: "date", dir: "desc" },
    onselect, // (entry) => void: moving with the arrow keys
    onopen, // (entry) => void: a click or Enter
    onsort, // (key) => void
    ontag, // (name) => void
    emptyText = "No entries yet.",
  } = $props();

  let scroller = $state();
  let sentinel = $state();

  const byDate = $derived(sort.key === "date");
  const rows = $derived.by(() => {
    const out = [];
    let last = null;
    for (const entry of feed.items) {
      if (byDate && entry.entry_date !== last) {
        last = entry.entry_date;
        const count = feed.items.filter((e) => e.entry_date === last).length;
        out.push({ kind: "day", key: `d${last}`, label: dayLabel(last), count });
      }
      out.push({ kind: "row", key: entry.id, entry });
    }
    return out;
  });

  onMount(() => {
    const observer = new IntersectionObserver((seen) => seen[0].isIntersecting && feed.more(), { root: scroller, rootMargin: "240px" });
    observer.observe(sentinel);
    return () => observer.disconnect();
  });

  function onkeydown(event) {
    const list = feed.items;
    if (!list.length) return;
    if (event.key === "Enter" && selectedId) {
      event.preventDefault();
      onopen?.(list.find((e) => e.id === selectedId));
      return;
    }
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const i = list.findIndex((e) => e.id === selectedId);
    const next = list[Math.max(0, Math.min(list.length - 1, i + (event.key === "ArrowDown" ? 1 : -1)))];
    onselect(next);
    requestAnimationFrame(() => scroller?.querySelector(`[data-id="${next.id}"]`)?.scrollIntoView({ block: "nearest" }));
  }

  const COLUMNS = [
    { key: "title", label: "Title" },
    { key: "tasks", label: "Tasks", small: true },
    { key: "words", label: "Words", right: true, small: true },
    { key: "date", label: "Updated", right: true },
  ];
</script>

<div class="jt-head" role="row">
  <span></span>
  {#each COLUMNS as c (c.key)}
    <button class="jt-h" class:is-on={sort.key === c.key} class:is-right={c.right} class:hide-sm={c.small} onclick={() => onsort?.(c.key)} aria-label="Sort by {c.label}">
      {c.label}{#if sort.key === c.key}<Icon name={sort.dir === "desc" ? "chev" : "arrowup"} size={12} />{/if}
    </button>
  {/each}
</div>

<div class="jt" bind:this={scroller} role="listbox" aria-label="Entries" tabindex="-1" {onkeydown}>
  {#each rows as item (item.key)}
    {#if item.kind === "day"}
      <div class="r-day"><span>{item.label}</span><span class="r-day-rule"></span><span class="r-day-count">{item.count}</span></div>
    {:else}
      {@const e = item.entry}
      <div class="jt-row" class:is-selected={e.id === selectedId} data-id={e.id} role="option" aria-selected={e.id === selectedId} tabindex={e.id === selectedId ? 0 : -1} onclick={() => onopen?.(e)} onkeydown={(ev) => ev.key === "Enter" && onopen?.(e)}>
        <span class="jt-icon"><Icon name={e.daily ? "calendar" : "file"} size={14} /></span>
        <span class="jt-title">
          <span class="jt-name" class:is-untitled={!e.title}>{e.title || "Untitled"}</span>
          {#if e.pinned}<Icon name="pin" size={13} />{/if}
          {#each e.tags.slice(0, 2) as t}<button class="jt-tag" onclick={(ev) => { ev.stopPropagation(); ontag?.(t); }}>#{t}</button>{/each}
        </span>
        <span class="jt-tasks">{#if e.open_tasks}<span class="r-badge jt-open">{e.open_tasks} open</span>{:else if e.total_tasks}<Icon name="check" size={13} />done{/if}</span>
        <span class="jt-num jt-words">{e.word_count.toLocaleString("en-US")}</span>
        <span class="jt-num">{e.updated_at ? relativeTime(e.updated_at) : ""}</span>
      </div>
    {/if}
  {/each}

  {#if feed.items.length === 0 && !feed.loading}
    <p class="jt-empty">{emptyText}</p>
  {/if}
  <div bind:this={sentinel} class="jt-end">
    {#if feed.loading}Loading…{:else if feed.error}Couldn’t load entries. <button class="r-link" onclick={() => feed.reload()}>Retry</button>{/if}
  </div>
</div>

<style>
  .jt-head,
  .jt-row {
    display: grid;
    grid-template-columns: 20px minmax(0, 1fr) 84px 64px 100px;
    align-items: center;
    gap: var(--space-2\.5);
    padding: 0 var(--space-4);
  }
  .jt-head {
    flex: none;
    height: var(--day-height);
    border-bottom: 1px solid var(--line);
    background: var(--subtle);
  }
  .jt-h {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink-3);
    font: 700 10.5px var(--font-mono);
    letter-spacing: 0.07em;
    text-align: left;
    text-transform: uppercase;
    cursor: pointer;
  }
  .jt-h.is-right {
    justify-content: flex-end;
  }
  .jt-h.is-on {
    color: var(--accent);
  }
  .jt {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    outline: 0;
  }
  .jt :global(.r-day) {
    position: sticky;
    top: 0;
    z-index: 1;
    background: var(--surface);
  }
  .jt-row {
    height: var(--row-height);
    font-size: 13px;
    cursor: default;
  }
  .jt-row:hover {
    background: var(--hover);
  }
  .jt-row.is-selected {
    background: var(--accent-soft);
    box-shadow: inset 2px 0 var(--accent);
  }
  .jt-row:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }
  .jt-icon {
    display: grid;
    color: var(--ink-3);
  }
  .jt-title {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    min-width: 0;
    white-space: nowrap;
  }
  .jt-name {
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .jt-row.is-selected .jt-name {
    font-weight: 500;
  }
  .jt-name.is-untitled {
    color: var(--ink-3);
    font-style: italic;
  }
  .jt-title :global(.r-icon) {
    flex: none;
    color: var(--accent);
  }
  .jt-tag {
    padding: 0;
    border: 0;
    background: none;
    color: var(--accent);
    font: 12px var(--font-sans);
    cursor: pointer;
  }
  .jt-tag:hover {
    text-decoration: underline;
  }
  .jt-tasks {
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--ink-3);
    font-size: 12px;
  }
  .jt-tasks :global(.r-icon) {
    color: var(--ink-3);
  }
  .jt-open {
    background: var(--accent-soft);
    color: var(--accent);
  }
  .jt-num {
    color: var(--ink-3);
    font: 12px var(--font-mono);
    text-align: right;
    white-space: nowrap;
  }
  .jt-empty {
    margin: 0;
    padding: 24px var(--space-4);
    color: var(--ink-3);
  }
  .jt-end {
    min-height: 24px;
    padding: 4px var(--space-4) var(--space-3);
    color: var(--ink-3);
    font-size: 12px;
  }
  @media (max-width: 767px) {
    .jt-head,
    .jt-row {
      grid-template-columns: 20px minmax(0, 1fr) 64px;
    }
    .hide-sm,
    .jt-tasks,
    .jt-words {
      display: none;
    }
  }
</style>
