<script>
  // The calendar layout: a month of entries, Monday first. Click an entry to open it; click a
  // day to select it (a day with one entry opens it). Days with no entry can be given one from the inspector.
  import Icon from "../ui/Icon.svelte";
  import { listJournalEntries } from "../../services/api";
  import { addDays, monthGrid, monthKey, monthTitle, shiftMonth, todayLocal } from "./dates";

  let {
    journalId,
    selectedDate = null,
    month = $bindable(null), // "2026-09"; null starts on today's month
    reloadKey = 0, // change to reload after an entry was made or removed
    onpickday, // (date, entries) => void
    onopen, // (date, entries) => void
    filter = null, // "pinned" | "tasks"
    tag = null,
  } = $props();

  const today = todayLocal();
  const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const shown = $derived(month ?? monthKey(today));
  const grid = $derived(monthGrid(shown));

  let entries = $state.raw([]);
  let loading = $state(false);
  let failed = $state(false);
  let gen = 0;

  const byDay = $derived.by(() => {
    const map = {};
    for (const e of entries) (map[e.entry_date] ??= []).push(e);
    return map;
  });

  $effect(() => {
    const id = journalId;
    const first = grid[0][0].date;
    const last = grid[grid.length - 1][6].date;
    reloadKey;
    const params = { after: first, before: addDays(last, 1), sort_by: "date", sort_order: "asc", limit: 200, pinned: filter === "pinned" ? true : undefined, has_tasks: filter === "tasks" ? true : undefined, tag: tag || undefined };
    const g = ++gen;
    loading = true;
    failed = false;
    listJournalEntries(id, params)
      .then((r) => {
        if (g === gen) entries = r.data.entries;
      })
      .catch((error) => {
        if (g !== gen) return;
        console.error("[journal] calendar load failed", error);
        failed = true;
        entries = [];
      })
      .finally(() => {
        if (g === gen) loading = false;
      });
  });

  const go = (n) => (month = shiftMonth(shown, n));
  // A day with exactly one entry opens it; otherwise the day is selected (its entries are the chips).
  function pick(cell) {
    const list = byDay[cell.date] ?? [];
    if (list.length === 1) onopen?.(cell.date, list);
    else onpickday?.(cell.date, list);
  }

  function onkeydown(event) {
    const date = selectedDate ?? today;
    const step = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
    if (step) {
      event.preventDefault();
      const next = addDays(date, step);
      if (monthKey(next) !== shown) month = monthKey(next);
      onpickday?.(next, byDay[next] ?? []);
    } else if (event.key === "Enter") {
      event.preventDefault();
      onopen?.(date, byDay[date] ?? []);
    }
  }
</script>

<div class="jc">
  <div class="jc-bar">
    <button class="r-btn r-btn-ghost r-btn-md r-btn-icon" onclick={() => go(-1)} aria-label="Previous month"><Icon name="chevl" /></button>
    <h2>{monthTitle(shown)}</h2>
    <button class="r-btn r-btn-ghost r-btn-md r-btn-icon" onclick={() => go(1)} aria-label="Next month"><Icon name="chevr" /></button>
    <button class="r-btn r-btn-secondary r-btn-md" onclick={() => (month = monthKey(today))} disabled={shown === monthKey(today)}>Today</button>
    {#if loading}<span class="jc-note">Loading…</span>{:else if failed}<span class="jc-note is-error">Couldn’t load this month.</span>{/if}
  </div>
  <div class="jc-grid" style="grid-template-rows: auto repeat({grid.length}, minmax(0, 1fr))" role="grid" aria-label="Entries by day" tabindex="0" {onkeydown}>
    {#each WEEKDAYS as w}<div class="jc-wd" role="columnheader">{w}</div>{/each}
    {#each grid as row}
      {#each row as cell (cell.date)}
        {@const list = byDay[cell.date] ?? []}
        <div class="jc-cell" class:is-off={!cell.inMonth} class:is-today={cell.date === today} class:is-selected={cell.date === selectedDate} role="gridcell" aria-selected={cell.date === selectedDate} aria-label="{cell.date}, {list.length} entries" onclick={() => pick(cell)}>
          <span class="jc-day">{Number(cell.date.slice(8))}</span>
          {#each list.slice(0, 3) as e (e.id)}
            <button class="jc-chip" class:is-pinned={e.pinned} title={e.title || "Untitled"} onclick={(ev) => { ev.stopPropagation(); onopen?.(cell.date, [e]); }}>{e.title || "Untitled"}</button>
          {/each}
          {#if list.length > 3}<span class="jc-more">+{list.length - 3} more</span>{/if}
        </div>
      {/each}
    {/each}
  </div>
</div>

<style>
  .jc {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .jc-bar {
    flex: none;
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    border-bottom: 1px solid var(--line);
  }
  .jc-bar h2 {
    min-width: 150px;
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    text-align: center;
  }
  .jc-note {
    margin-left: var(--space-2);
    color: var(--ink-3);
    font-size: 12px;
  }
  .jc-note.is-error {
    color: var(--danger);
  }
  .jc-grid {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    outline: 0;
  }
  .jc-wd {
    padding: 6px 10px;
    border-right: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    background: var(--subtle);
    color: var(--ink-3);
    font: 700 10.5px var(--font-mono);
    letter-spacing: 0.07em;
    text-transform: uppercase;
  }
  .jc-cell {
    display: grid;
    align-content: start;
    gap: 3px;
    min-width: 0;
    padding: 6px 6px 4px;
    overflow: hidden;
    border-right: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    cursor: default;
  }
  .jc-cell:hover {
    background: var(--hover);
  }
  .jc-cell.is-off {
    background: var(--subtle);
  }
  .jc-cell.is-off .jc-day {
    color: var(--ink-4);
  }
  .jc-cell.is-selected {
    background: var(--accent-soft);
    box-shadow: inset 0 0 0 2px var(--accent);
  }
  .jc-day {
    display: grid;
    place-items: center;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    font-size: 12px;
    font-weight: 500;
  }
  .jc-cell.is-today .jc-day {
    background: var(--accent);
    color: var(--on-accent);
  }
  .jc-chip {
    border: 0;
    text-align: left;
    cursor: pointer;
    font-family: inherit;
    padding: 2px 6px;
    overflow: hidden;
    border-radius: var(--radius-xs);
    background: var(--accent-soft);
    color: var(--accent);
    font-size: 12px;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .jc-cell.is-selected .jc-chip {
    background: var(--surface);
  }
  .jc-chip.is-pinned {
    background: var(--warning-soft);
    color: var(--warning-ink);
  }
  .jc-more {
    padding-left: 6px;
    color: var(--ink-3);
    font-size: 11px;
  }
  @media (max-width: 767px) {
    .jc-chip {
      padding: 0;
      height: 6px;
      font-size: 0;
    }
    .jc-more {
      display: none;
    }
    .jc-wd {
      padding: 6px 2px;
      text-align: center;
    }
  }
</style>
