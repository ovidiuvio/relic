<script>
  // A CSV relic as a table: search across every column, sort by any column (numbers as numbers),
  // pages of 25–500 rows, and export of all rows or just the filtered ones.
  //   ← → change page while the table has focus
  import Icon from "../../lib/ui/Icon.svelte";
  import FilterStrip from "../../lib/viewer/FilterStrip.svelte";
  import { triggerDownload } from "../../services/utils/download";
  import { formatBytes } from "../../services/typeUtils";

  let { processed, name = "" } = $props(); // name: the relic's, for exported files

  const PAGE_SIZES = [25, 50, 100, 200, 500];

  let search = $state("");
  let sortColumn = $state(null);
  let sortDir = $state("asc");
  let page = $state(1);
  let pageSize = $state(50);
  let exportOpen = $state(false);
  let exportEl = $state();

  const columns = $derived(processed?.metadata?.columns ?? []);
  // A trailing newline parses as an empty row; rows with nothing in them aren't data.
  const allRows = $derived((processed?.rows ?? []).filter((row) => columns.some((c) => row[c] !== undefined && row[c] !== null && row[c] !== "")));
  const total = $derived(allRows.length);

  const rows = $derived.by(() => {
    let out = allRows;
    const term = search.trim().toLowerCase();
    if (term) out = out.filter((row) => columns.some((c) => String(row[c] ?? "").toLowerCase().includes(term)));
    if (sortColumn) {
      const dir = sortDir === "asc" ? 1 : -1;
      out = [...out].sort((a, b) => {
        const x = a[sortColumn] ?? "";
        const y = b[sortColumn] ?? "";
        const nx = parseFloat(x);
        const ny = parseFloat(y);
        if (!isNaN(nx) && !isNaN(ny)) return (nx - ny) * dir;
        return String(x).toLowerCase().localeCompare(String(y).toLowerCase()) * dir;
      });
    }
    return out;
  });

  // Columns whose filled cells are mostly numbers get a right-aligned header, over their numbers.
  const numericCols = $derived.by(() => {
    const sample = allRows.slice(0, 200);
    return new Set(
      columns.filter((c) => {
        const filled = sample.filter((r) => cellKind(r[c]) !== "empty");
        return filled.length > 0 && filled.filter((r) => cellKind(r[c]) === "num").length / filled.length > 0.8;
      })
    );
  });

  const pages = $derived(Math.max(1, Math.ceil(rows.length / pageSize)));
  const pageRows = $derived(rows.slice((page - 1) * pageSize, page * pageSize));
  const firstShown = $derived(rows.length ? (page - 1) * pageSize + 1 : 0);
  const lastShown = $derived(Math.min(page * pageSize, rows.length));
  const filtered = $derived(!!search.trim());

  // Page numbers around the current one (up to seven).
  const pageNumbers = $derived.by(() => {
    const start = Math.max(1, Math.min(page - 3, pages - 6));
    return Array.from({ length: Math.min(7, pages) }, (_, i) => start + i);
  });

  function sortBy(column) {
    if (sortColumn === column) sortDir = sortDir === "asc" ? "desc" : "asc";
    else {
      sortColumn = column;
      sortDir = "asc";
    }
    page = 1;
  }

  function reset() {
    search = "";
    sortColumn = null;
    sortDir = "asc";
    page = 1;
  }

  function go(n) {
    page = Math.min(pages, Math.max(1, n));
  }

  function cellKind(value) {
    if (value === undefined || value === null || value === "") return "empty";
    const s = String(value);
    if (!isNaN(parseFloat(s)) && !isNaN(s)) return "num";
    if (/^\d{4}-\d{2}-\d{2}/.test(s) || /^\d{2}\/\d{2}\/\d{4}/.test(s)) return "date";
    return "text";
  }

  function toCsv(list) {
    const esc = (v) => {
      const s = String(v ?? "");
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    return [columns.map(esc).join(","), ...list.map((row) => columns.map((c) => esc(row[c])).join(","))].join("\n");
  }

  function exportRows(which) {
    exportOpen = false;
    const base = (name || processed.fileName || "data").replace(/\.csv$/i, "");
    const file = which === "all" ? `${base}.csv` : `${base}-filtered.csv`;
    triggerDownload(toCsv(which === "all" ? allRows : rows), file, "text/csv");
  }

  function onTableKey(event) {
    if (event.key === "ArrowLeft" && page > 1) (event.preventDefault(), go(page - 1));
    else if (event.key === "ArrowRight" && page < pages) (event.preventDefault(), go(page + 1));
  }

  function onWindowClick(event) {
    if (exportOpen && !exportEl?.contains(event.target)) exportOpen = false;
  }
</script>

<svelte:window onclick={onWindowClick} />

<div class="csv">
  <FilterStrip bind:value={search} placeholder="Search all columns" oninput={() => (page = 1)} count={filtered ? { matched: rows.length, total } : null}>
    <label class="csv-opt" title="Rows per page">
      <select bind:value={pageSize} onchange={() => (page = 1)} aria-label="Rows per page">
        {#each PAGE_SIZES as n (n)}<option value={n}>{n} rows</option>{/each}
      </select>
    </label>
    <div class="csv-export" bind:this={exportEl}>
      <button class="r-btn r-btn-secondary r-btn-md" aria-expanded={exportOpen} onclick={() => (exportOpen = !exportOpen)}><Icon name="download" />Export<Icon name="chev" /></button>
      {#if exportOpen}
        <div class="csv-menu" role="menu">
          <button role="menuitem" onclick={() => exportRows("all")}>All {total.toLocaleString("en-US")} rows<small>as CSV</small></button>
          <button role="menuitem" onclick={() => exportRows("filtered")} disabled={!filtered}>
            The {rows.length.toLocaleString("en-US")} filtered rows<small>{filtered ? "as CSV" : "search first"}</small>
          </button>
        </div>
      {/if}
    </div>
    <button class="r-btn r-btn-ghost r-btn-md" onclick={reset} disabled={!filtered && !sortColumn && page === 1} title="Clear the search and sorting">Reset</button>
  </FilterStrip>

  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
  <div class="csv-scroll" tabindex="0" role="region" aria-label="Table, ← → change page" onkeydown={onTableKey}>
    <table>
      <thead>
        <tr>
          <th class="csv-n">#</th>
          {#each columns as col (col)}
            <th class:is-num={numericCols.has(col)}>
              <button class="csv-head" class:is-on={sortColumn === col} onclick={() => sortBy(col)} title="Sort by {col}">
                <span>{col}</span>
                {#if sortColumn === col}<span class="csv-dir" class:is-asc={sortDir === "asc"}><Icon name="arrowup" /></span>{/if}
              </button>
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each pageRows as row, i}
          <tr>
            <td class="csv-n">{(firstShown + i).toLocaleString("en-US")}</td>
            {#each columns as col (col)}
              {@const kind = cellKind(row[col])}
              <td class="is-{kind}"><span title={row[col] ?? ""}>{row[col] ?? ""}</span></td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
    {#if !pageRows.length}
      <p class="csv-empty">
        {filtered ? "No rows match your search." : "This file has no rows."}
        {#if filtered}<button class="r-link" onclick={() => (search = "")}>Clear search</button>{/if}
      </p>
    {/if}
  </div>

  <div class="csv-foot">
    <span>
      {#if rows.length}Rows {firstShown.toLocaleString("en-US")}–{lastShown.toLocaleString("en-US")} of {rows.length.toLocaleString("en-US")}{:else}No rows{/if}
      {#if filtered}<em>· {total.toLocaleString("en-US")} in all</em>{/if}
      <em>· {columns.length} {columns.length === 1 ? "column" : "columns"}</em>
      {#if processed.metadata?.fileSize}<em>· {formatBytes(processed.metadata.fileSize)}</em>{/if}
      {#if sortColumn}<em>· sorted by {sortColumn}, {sortDir === "asc" ? "ascending" : "descending"}</em>{/if}
    </span>
    {#if pages > 1}
      <nav class="csv-pager" aria-label="Pages">
        <button onclick={() => go(1)} disabled={page === 1} title="First page" aria-label="First page"><Icon name="chevl" /><Icon name="chevl" /></button>
        <button onclick={() => go(page - 1)} disabled={page === 1} title="Previous page (←)" aria-label="Previous page"><Icon name="chevl" /></button>
        {#each pageNumbers as n (n)}
          <button class:is-on={n === page} aria-current={n === page ? "page" : undefined} onclick={() => go(n)}>{n}</button>
        {/each}
        <button onclick={() => go(page + 1)} disabled={page === pages} title="Next page (→)" aria-label="Next page"><Icon name="chevr" /></button>
        <button onclick={() => go(pages)} disabled={page === pages} title="Last page" aria-label="Last page"><Icon name="chevr" /><Icon name="chevr" /></button>
      </nav>
    {/if}
  </div>
</div>

<style>
  .csv {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    background: var(--surface);
    color: var(--ink);
    font: 13px/1.45 var(--font-sans);
  }
  .csv-opt select {
    height: var(--control-md);
    padding: 0 22px 0 8px;
    border: 1px solid var(--line-2);
    border-radius: var(--radius-sm);
    background: var(--surface) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23877d85' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E") no-repeat right 6px center / 12px;
    color: var(--ink);
    font: 12.5px var(--font-sans);
    appearance: none;
    cursor: pointer;
  }
  .csv-export {
    position: relative;
  }
  .csv-export :global(.r-icon) {
    width: 13px;
    height: 13px;
  }
  .csv-menu {
    position: absolute;
    top: calc(100% + 4px);
    right: 0;
    z-index: 30;
    display: grid;
    min-width: 220px;
    padding: var(--space-1) 0;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    background: var(--surface);
    box-shadow: var(--shadow-popover);
  }
  .csv-menu button {
    display: flex;
    justify-content: space-between;
    gap: var(--space-3);
    padding: 7px var(--space-3);
    border: 0;
    background: none;
    color: var(--ink);
    font: 13px var(--font-sans);
    text-align: left;
    cursor: pointer;
  }
  .csv-menu button:hover:not(:disabled) {
    background: var(--hover);
  }
  .csv-menu button:disabled {
    color: var(--ink-3);
    cursor: not-allowed;
  }
  .csv-menu small {
    color: var(--ink-3);
    font-size: 11.5px;
  }
  .csv-scroll {
    flex: 1;
    min-height: 0;
    overflow: auto;
    outline: 0;
  }
  .csv-scroll:focus-visible {
    box-shadow: inset 0 0 0 2px var(--accent);
  }
  table {
    min-width: 100%;
    border-collapse: separate;
    border-spacing: 0;
  }
  th,
  td {
    height: 30px;
    padding: 0 var(--space-3);
    border-bottom: 1px solid var(--line);
    white-space: nowrap;
  }
  thead th {
    position: sticky;
    top: 0;
    z-index: 2;
    height: 28px;
    background: var(--surface);
    color: var(--ink-3);
    font: 700 10.5px var(--font-mono);
    letter-spacing: 0.06em;
    text-align: left;
    text-transform: uppercase;
  }
  .csv-head {
    display: flex;
    align-items: center;
    gap: 2px;
    max-width: 240px;
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    letter-spacing: inherit;
    text-transform: inherit;
    cursor: pointer;
  }
  th.is-num .csv-head {
    flex-direction: row-reverse;
    margin-left: auto;
  }
  .csv-head span:first-child {
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .csv-head:hover,
  .csv-head.is-on {
    color: var(--accent);
  }
  .csv-dir {
    display: inline-flex;
  }
  .csv-dir :global(.r-icon) {
    width: 11px;
    height: 11px;
    transform: rotate(180deg);
  }
  .csv-dir.is-asc :global(.r-icon) {
    transform: none;
  }
  .csv-n {
    position: sticky;
    left: 0;
    z-index: 1;
    width: 1%;
    border-right: 1px solid var(--line);
    background: var(--subtle);
    color: var(--ink-3);
    font: 12px var(--font-mono);
    text-align: right;
  }
  thead .csv-n {
    z-index: 3;
    background: var(--surface);
  }
  tbody tr:hover td {
    background: var(--hover);
  }
  td span {
    display: block;
    max-width: 320px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  td.is-num {
    font: 12.5px var(--font-mono);
    font-variant-numeric: tabular-nums;
    text-align: right;
  }
  td.is-num span {
    margin-left: auto;
  }
  td.is-date {
    color: var(--ink-2);
    font: 12.5px var(--font-mono);
  }
  .csv-empty {
    display: flex;
    gap: var(--space-2);
    margin: 0;
    padding: var(--space-5) var(--space-4);
    color: var(--ink-3);
  }
  .csv-empty button {
    padding: 0;
    border: 0;
    background: none;
    font: inherit;
    cursor: pointer;
  }
  .csv-foot {
    flex: none;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    min-height: 36px;
    padding: 0 var(--space-3);
    border-top: 1px solid var(--line);
    background: var(--subtle);
    color: var(--ink-2);
    font-size: 12.5px;
  }
  .csv-foot em {
    margin-left: 4px;
    color: var(--ink-3);
    font-style: normal;
  }
  .csv-pager {
    display: flex;
    gap: 2px;
  }
  .csv-pager button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 26px;
    height: 26px;
    padding: 0 6px;
    border: 0;
    border-radius: var(--radius-xs);
    background: none;
    color: var(--ink-2);
    font: 12px var(--font-mono);
    cursor: pointer;
  }
  .csv-pager button :global(.r-icon) {
    width: 13px;
    height: 13px;
  }
  .csv-pager button :global(.r-icon + .r-icon) {
    margin-left: -8px;
  }
  .csv-pager button:hover:not(:disabled) {
    background: var(--hover);
  }
  .csv-pager button.is-on {
    background: var(--accent-soft);
    color: var(--accent);
    font-weight: 700;
  }
  .csv-pager button:disabled {
    opacity: 0.35;
    cursor: default;
  }
  @media (max-width: 767px) {
    .csv-foot {
      flex-wrap: wrap;
      padding: var(--space-1\.5) var(--space-3);
    }
    .csv-opt {
      display: none;
    }
  }
</style>
