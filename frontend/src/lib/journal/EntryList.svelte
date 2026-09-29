<script>
  // The journal's entry list: pinned first, then month by month, each row a date block, the
  // title, an excerpt and its tags. Loads more as you reach the end; ↑ ↓ move the selection.
  import { onMount } from "svelte";
  import Icon from "../ui/Icon.svelte";
  import { dayParts, groupEntries } from "./dates";

  let {
    feed, // PagedFeed of entry summaries
    selectedId = null,
    onselect, // (entry) => void
    ontag, // (name) => void
    emptyText = "No entries yet.",
    emptyAction = null, // { label, run }
  } = $props();

  const groups = $derived(groupEntries(feed.items));
  let scroller = $state();
  let sentinel = $state();

  onMount(() => {
    const observer = new IntersectionObserver((seen) => seen[0].isIntersecting && feed.more(), { root: scroller, rootMargin: "240px" });
    observer.observe(sentinel);
    return () => observer.disconnect();
  });

  function onkeydown(event) {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    const rows = feed.items;
    if (!rows.length) return;
    event.preventDefault();
    const i = rows.findIndex((r) => r.id === selectedId);
    const next = rows[Math.max(0, Math.min(rows.length - 1, i + (event.key === "ArrowDown" ? 1 : -1)))];
    onselect(next);
    requestAnimationFrame(() => scroller?.querySelector(`[data-id="${next.id}"]`)?.scrollIntoView({ block: "nearest" }));
  }

  const excerptOf = (e) => e.excerpt || "Empty entry";
</script>

<div class="jl" bind:this={scroller} role="listbox" aria-label="Entries" tabindex="-1" {onkeydown}>
  {#each groups as group (group.key)}
    <div class="r-day"><span>{group.label}</span><span class="r-day-rule"></span><span class="r-day-count">{group.entries.length}</span></div>
    {#each group.entries as entry (entry.id)}
      {@const d = dayParts(entry.entry_date)}
      <div class="jl-row" class:is-selected={entry.id === selectedId} data-id={entry.id} role="option" aria-selected={entry.id === selectedId} tabindex={entry.id === selectedId ? 0 : -1} onclick={() => onselect(entry)} onkeydown={(e) => e.key === "Enter" && onselect(entry)}>
        <div class="jl-date"><b>{d.day}</b><span>{d.weekday}</span></div>
        <div class="jl-main">
          <div class="jl-title" class:is-untitled={!entry.title}>
            <span>{entry.title || "Untitled"}</span>
            {#if entry.pinned}<Icon name="pin" size={13} />{/if}
          </div>
          <div class="jl-excerpt">{excerptOf(entry)}</div>
          <div class="jl-meta">
            {#each entry.tags.slice(0, 3) as tag}
              <button class="jl-tag" onclick={(e) => { e.stopPropagation(); ontag?.(tag); }}>#{tag}</button>
            {/each}
            {#if entry.open_tasks}<span class="r-badge jl-open">{entry.open_tasks} open</span>{/if}
            <span class="jl-words">{entry.word_count.toLocaleString("en-US")} words</span>
          </div>
        </div>
      </div>
    {/each}
  {/each}

  {#if feed.items.length === 0 && !feed.loading}
    <div class="jl-empty">
      <p>{emptyText}</p>
      {#if emptyAction}<button class="r-btn r-btn-secondary r-btn-md" onclick={emptyAction.run}>{emptyAction.label}</button>{/if}
    </div>
  {/if}
  <div bind:this={sentinel} class="jl-end">
    {#if feed.loading}Loading…{:else if feed.error}Couldn’t load entries. <button class="r-link" onclick={() => feed.reload()}>Retry</button>{/if}
  </div>
</div>

<style>
  .jl {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    outline: 0;
    background: var(--subtle);
  }
  .jl :global(.r-day) {
    position: sticky;
    top: 0;
    z-index: 1;
    margin: 0;
    background: var(--subtle);
  }
  .jl-row {
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr);
    gap: 10px;
    padding: 10px 14px;
    border-bottom: 1px solid var(--line);
    cursor: default;
  }
  .jl-row:hover {
    background: var(--hover);
  }
  .jl-row.is-selected {
    background: var(--accent-soft);
    box-shadow: inset 2px 0 var(--accent);
  }
  .jl-row:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }
  .jl-date {
    display: grid;
    align-content: start;
    justify-items: center;
    line-height: 1;
  }
  .jl-date b {
    font-size: 20px;
    font-weight: 500;
  }
  .jl-date span {
    margin-top: 3px;
    color: var(--ink-3);
    font-size: 10px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .jl-title {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    font-size: 13.5px;
    font-weight: 500;
  }
  .jl-title span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .jl-title.is-untitled span {
    color: var(--ink-3);
    font-style: italic;
    font-weight: 400;
  }
  .jl-title :global(.r-icon) {
    flex: none;
    color: var(--accent);
  }
  .jl-excerpt {
    display: -webkit-box;
    margin-top: 2px;
    overflow: hidden;
    color: var(--ink-3);
    font-size: 12px;
    line-height: 1.45;
    overflow-wrap: anywhere;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }
  .jl-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 5px;
    overflow: hidden;
    color: var(--ink-3);
    font-size: 11px;
    white-space: nowrap;
  }
  .jl-tag {
    padding: 0;
    border: 0;
    background: none;
    color: var(--accent);
    font: 500 11px var(--font-sans);
    cursor: pointer;
  }
  .jl-tag:hover {
    text-decoration: underline;
  }
  .jl-open {
    background: var(--accent-soft);
    color: var(--accent);
  }
  .jl-words {
    font-family: var(--font-mono);
  }
  .jl-empty {
    display: grid;
    justify-items: start;
    gap: var(--space-3);
    padding: 24px 16px;
    color: var(--ink-3);
  }
  .jl-empty p {
    margin: 0;
  }
  .jl-end {
    min-height: 24px;
    padding: 4px 16px 12px;
    color: var(--ink-3);
    font-size: 12px;
  }
</style>
