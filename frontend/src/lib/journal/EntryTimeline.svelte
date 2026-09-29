<script>
  // The timeline layout: time runs down a spine, entries on the same day share a node, quiet
  // stretches are marked, and the month strip jumps around and shows how much was written.
  import { onMount, tick } from "svelte";
  import Icon from "../ui/Icon.svelte";
  import { dayParts, daysBetween, monthKey, monthShort, monthTitle, todayLocal } from "./dates";

  let {
    feed,
    days = [], // [{ date, count }] for the whole journal, for the month strip
    selectedId = null,
    onselect,
    onopen,
    ontag,
    emptyText = "No entries yet.",
  } = $props();

  let scroller = $state();
  let sentinel = $state();
  let current = $state(null); // the month heading at the top
  const today = todayLocal();

  // { date, entries[] } in list order (the feed is newest first).
  const nodes = $derived.by(() => {
    const out = [];
    for (const entry of feed.items) {
      const last = out[out.length - 1];
      if (last && last.date === entry.entry_date) last.entries.push(entry);
      else out.push({ date: entry.entry_date, entries: [entry] });
    }
    return out;
  });

  // Months for the strip, newest first, with entry counts across the whole journal.
  const months = $derived.by(() => {
    const counts = {};
    for (const d of days) counts[monthKey(d.date)] = (counts[monthKey(d.date)] ?? 0) + d.count;
    const max = Math.max(1, ...Object.values(counts));
    return Object.keys(counts)
      .sort()
      .reverse()
      .map((key) => ({ key, count: counts[key], width: Math.round((counts[key] / max) * 100) }));
  });

  onMount(() => {
    const observer = new IntersectionObserver((seen) => seen[0].isIntersecting && feed.more(), { root: scroller, rootMargin: "320px" });
    observer.observe(sentinel);
    return () => observer.disconnect();
  });

  function markMonth() {
    if (!scroller) return;
    let now = null;
    for (const h of scroller.querySelectorAll(".jm-head")) if (h.offsetTop <= scroller.scrollTop + 24) now = h.dataset.month;
    current = now ?? scroller.querySelector(".jm-head")?.dataset.month ?? null;
  }
  $effect(() => {
    nodes;
    tick().then(markMonth);
  });

  // Jump to a month, loading pages until its heading exists.
  async function jump(key) {
    for (let i = 0; i < 40 && !scroller.querySelector(`.jm-head[data-month="${key}"]`) && feed.hasMore; i++) {
      await feed.more();
      await tick();
    }
    const head = scroller.querySelector(`.jm-head[data-month="${key}"]`);
    if (head) scroller.scrollTo({ top: head.offsetTop - 2, behavior: "smooth" });
  }

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

  const gapBefore = (i) => (i > 0 ? daysBetween(nodes[i].date, nodes[i - 1].date) - 1 : 0);
  const newMonth = (i) => i === 0 || monthKey(nodes[i].date) !== monthKey(nodes[i - 1].date);
  const monthCount = (key) => nodes.filter((n) => monthKey(n.date) === key).reduce((sum, n) => sum + n.entries.length, 0);
</script>

<div class="jm">
  <div class="jm-scroll" bind:this={scroller} role="listbox" aria-label="Entries" tabindex="-1" {onkeydown} onscroll={markMonth}>
    <div class="jm-body">
      {#each nodes as node, i (node.date)}
        {#if gapBefore(i) >= 3}
          <div class="jm-node is-gap"><span></span><span class="jm-spine"></span><span class="jm-gap">{gapBefore(i)} days without entries</span></div>
        {/if}
        {#if newMonth(i)}
          <div class="jm-head" data-month={monthKey(node.date)}>{monthTitle(monthKey(node.date))}<span>{monthCount(monthKey(node.date))} entries</span></div>
        {/if}
        {@const d = dayParts(node.date)}
        <div class="jm-node">
          <div class="jm-date"><b>{d.day}</b><span>{d.weekday}</span></div>
          <div class="jm-spine"><i class:is-today={node.date === today}></i></div>
          <div class="jm-cards">
            {#each node.entries as e (e.id)}
              <div class="jm-card" class:is-selected={e.id === selectedId} data-id={e.id} role="option" aria-selected={e.id === selectedId} tabindex={e.id === selectedId ? 0 : -1} onclick={() => onopen?.(e)} onkeydown={(ev) => ev.key === "Enter" && onopen?.(e)}>
                <div class="jm-title"><span class:is-untitled={!e.title}>{e.title || "Untitled"}</span>{#if e.pinned}<Icon name="pin" size={13} />{/if}<em>{e.word_count.toLocaleString("en-US")} words</em></div>
                {#if e.excerpt}<div class="jm-excerpt">{e.excerpt}</div>{/if}
                {#if e.tags.length || e.open_tasks}
                  <div class="jm-meta">
                    {#each e.tags.slice(0, 4) as t}<button class="jm-tag" onclick={(ev) => { ev.stopPropagation(); ontag?.(t); }}>#{t}</button>{/each}
                    {#if e.open_tasks}<span class="r-badge jm-open">{e.open_tasks} open</span>{/if}
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/each}
      {#if feed.items.length === 0 && !feed.loading}<p class="jm-empty">{emptyText}</p>{/if}
      <div bind:this={sentinel} class="jm-end">
        {#if feed.loading}Loading…{:else if feed.error}Couldn’t load entries. <button class="r-link" onclick={() => feed.reload()}>Retry</button>{/if}
      </div>
    </div>
  </div>

  {#if months.length}
    <nav class="jm-months" aria-label="Jump to a month">
      <h6>Jump to</h6>
      {#each months as m (m.key)}
        <button class:is-on={current === m.key} onclick={() => jump(m.key)}>
          <span>{monthShort(m.key)}</span><em>{m.count}</em><i style="width:{m.width}%"></i>
        </button>
      {/each}
    </nav>
  {/if}
</div>

<style>
  .jm {
    flex: 1;
    min-height: 0;
    display: flex;
  }
  .jm-scroll {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
    outline: 0;
    position: relative;
  }
  .jm-body {
    max-width: 900px;
    padding: 0 var(--space-5) 60px var(--space-4);
  }
  .jm-head {
    position: sticky;
    top: 0;
    z-index: 2;
    display: flex;
    align-items: baseline;
    gap: var(--space-2\.5);
    padding: 16px 0 8px 76px;
    background: var(--surface);
    font-size: 15px;
    font-weight: 700;
  }
  .jm-head span {
    color: var(--ink-3);
    font-size: 12px;
    font-weight: 400;
  }
  .jm-node {
    display: grid;
    grid-template-columns: 52px 20px minmax(0, 1fr);
    gap: 0 12px;
  }
  .jm-date {
    display: grid;
    justify-items: end;
    align-content: start;
    padding-top: 9px;
    line-height: 1;
  }
  .jm-date b {
    font-size: 20px;
    font-weight: 500;
  }
  .jm-date span {
    margin-top: 3px;
    color: var(--ink-3);
    font-size: 10px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .jm-spine {
    position: relative;
  }
  .jm-spine::before {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    left: 9px;
    width: 2px;
    background: var(--line);
  }
  .jm-node.is-gap .jm-spine::before {
    width: 0;
    border-left: 2px dotted var(--line-2);
    background: none;
  }
  .jm-spine i {
    position: absolute;
    top: 13px;
    left: 4px;
    z-index: 1;
    width: 12px;
    height: 12px;
    border: 2px solid var(--accent);
    border-radius: 50%;
    background: var(--surface);
  }
  .jm-spine i.is-today {
    background: var(--accent);
    box-shadow: 0 0 0 4px var(--accent-soft);
  }
  .jm-gap {
    padding: 8px 0;
    color: var(--ink-3);
    font-size: 12px;
  }
  .jm-cards {
    display: grid;
    gap: var(--space-2);
    min-width: 0;
    padding-block: 6px;
  }
  .jm-card {
    min-width: 0;
    padding: 10px 14px;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    background: var(--surface);
    cursor: default;
  }
  .jm-card:hover {
    border-color: var(--line-2);
  }
  .jm-card.is-selected {
    border-color: color-mix(in srgb, var(--accent) 35%, var(--line));
    background: var(--accent-soft);
  }
  .jm-card:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }
  .jm-title {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    font-size: 14px;
    font-weight: 500;
  }
  .jm-title > span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .jm-title > span.is-untitled {
    color: var(--ink-3);
    font-style: italic;
    font-weight: 400;
  }
  .jm-title :global(.r-icon) {
    flex: none;
    color: var(--accent);
  }
  .jm-title em {
    margin-left: auto;
    color: var(--ink-3);
    font: 400 11px var(--font-mono);
    font-style: normal;
    white-space: nowrap;
  }
  .jm-excerpt {
    display: -webkit-box;
    margin-top: 3px;
    overflow: hidden;
    color: var(--ink-2);
    font-size: 12.5px;
    line-height: 1.5;
    overflow-wrap: anywhere;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
  }
  .jm-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-2);
    margin-top: 7px;
    font-size: 11px;
  }
  .jm-tag {
    padding: 0;
    border: 0;
    background: none;
    color: var(--accent);
    font: 500 11px var(--font-sans);
    cursor: pointer;
  }
  .jm-tag:hover {
    text-decoration: underline;
  }
  .jm-open {
    background: var(--accent-soft);
    color: var(--accent);
  }
  .jm-card.is-selected .jm-open {
    background: var(--surface);
  }
  .jm-empty {
    margin: 0;
    padding: 24px 0 24px 76px;
    color: var(--ink-3);
  }
  .jm-end {
    min-height: 24px;
    padding-left: 76px;
    color: var(--ink-3);
    font-size: 12px;
  }
  .jm-months {
    display: grid;
    flex: none;
    align-content: start;
    gap: 2px;
    width: 140px;
    padding: var(--space-3) var(--space-2);
    overflow-y: auto;
    border-left: 1px solid var(--line);
    background: var(--subtle);
  }
  .jm-months h6 {
    margin: 0 6px 6px;
    color: var(--ink-3);
    font: 700 10.5px var(--font-mono);
    letter-spacing: 0.07em;
    text-transform: uppercase;
  }
  .jm-months button {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 2px 8px;
    align-items: center;
    padding: 6px;
    border: 0;
    border-radius: var(--radius-sm);
    background: none;
    color: var(--ink);
    font: inherit;
    text-align: left;
    cursor: pointer;
  }
  .jm-months button:hover {
    background: var(--hover);
  }
  .jm-months button.is-on {
    background: var(--checked);
    color: var(--accent);
    font-weight: 500;
  }
  .jm-months em {
    color: var(--ink-3);
    font: 11px var(--font-mono);
    font-style: normal;
  }
  .jm-months i {
    grid-column: 1 / -1;
    display: block;
    height: 4px;
    border-radius: 2px;
    background: var(--chart-bar);
  }
  @media (max-width: 767px) {
    .jm-months {
      display: none;
    }
    .jm-node {
      grid-template-columns: 38px 14px minmax(0, 1fr);
      gap: 0 6px;
    }
    .jm-head {
      padding-left: 58px;
    }
    .jm-spine::before {
      left: 6px;
    }
    .jm-spine i {
      left: 1px;
    }
    .jm-date b {
      font-size: 17px;
    }
    .jm-body {
      padding-inline: var(--space-3);
    }
  }
</style>
