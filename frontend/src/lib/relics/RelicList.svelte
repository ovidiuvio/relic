<script>
  // The compact relic log: day headers, 26px rows, hover actions, a selection the inspector
  // follows, and more rows loaded as you scroll. Markup follows the design system's RelicList.
  //   click the name: open · click elsewhere on the row: select · double-click or ↵: open
  //   ↑↓ / j k: move · ctrl/⌘/middle click on the name: new tab
  import Icon from "../ui/Icon.svelte";
  import { hasViewer } from "../../services/typeUtils";
  import { copyToClipboard } from "../../services/relicActions";
  import { clockTime, dayMonth, dayGroup, typeBadge, tagName, compactBytes, middleTruncate, expiryMarker, counterLevel } from "./format";

  // The four counter columns, as in the old table. Each is coloured by how notable it is,
  // sorts the list from its header, and (all but views) opens its inspector section.
  const COUNTERS = [
    { key: "access_count", icon: "eye", name: "Views", sort: "views", views: true },
    { key: "bookmark_count", icon: "bookmark", name: "Bookmarks", sort: "bookmarks", section: "bookmarkers" },
    { key: "comments_count", icon: "msg", name: "Comments", sort: "comments", section: "comments" },
    { key: "forks_count", icon: "fork", name: "Forks", sort: "forks", section: "lineage" },
  ];
  const counted = (n, name) => `${n} ${n === 1 ? name.slice(0, -1).toLowerCase() : name.toLowerCase()}`;

  let {
    relics = [],
    loading = false,
    hasMore = false,
    grouped = true, // day headers; off when sorted by anything but date
    dateField = "created_at",
    dateLabel = null, // header for the date column when it isn't "Time"/"Date" (e.g. "Bookmarked")
    showPublic = false, // mark public relics too (lists that mix visibilities)
    showOwner = true, // off where every relic is yours
    local = false, // items that live only in this browser (drafts): no owner, id or counters, and the name opens via onopen
    highlight = "", // search term to <mark> in names
    selectedId = null,
    actions = [], // [{ icon, title, run(relic) }] shown on hover
    emptyText = "No relics yet",
    emptyAction = null, // { href, label } link under the empty message
    sort = null, // { key, dir } (see relics/sort.js); the column headers show and change it
    onsort, // (column key) => void
    sortable = null, // the column keys the API can sort by; null: all of them
    onowner = null, // (relic) — the owner's name was clicked (admin: show that user's relics)
    onselect,
    onopen,
    oncounter, // (relic, section) — a counter was clicked; section is "bookmarkers" | "comments" | "lineage" | "tags"
    ontag, // (tag) — a tag was clicked: filter by it
    onloadmore,
  } = $props();

  let listEl = $state();
  let sentinel = $state();

  // Rows with the day header each one starts, if any.
  const items = $derived.by(() => {
    const out = [];
    let lastKey = null;
    const now = new Date();
    for (const relic of relics) {
      let day = null;
      if (grouped) {
        const g = dayGroup(relic[dateField], now);
        if (g.key !== lastKey) {
          day = { ...g, count: 0 };
          lastKey = g.key;
        }
      }
      out.push({ relic, day, dated: grouped && lastKey?.startsWith("m") });
    }
    // Count each day's rows; the last day may continue past the rows loaded so far,
    // so its count waits until everything is in.
    let current = null;
    for (const item of out) {
      if (item.day) current = item.day;
      if (current) current.count++;
    }
    if (current && hasMore) current.count = null;
    return out;
  });

  function nameParts(name) {
    const text = middleTruncate(name, 72);
    const term = highlight.trim();
    if (!term) return [{ text }];
    const i = text.toLowerCase().indexOf(term.toLowerCase());
    if (i < 0) return [{ text }];
    return [
      { text: text.slice(0, i) },
      { text: text.slice(i, i + term.length), mark: true },
      { text: text.slice(i + term.length) },
    ];
  }

  function onRowClick(event, relic) {
    // The name is a real link: the app's link handling opens it (or the browser, in a new tab).
    if (event.target.closest("a, button")) return;
    onselect?.(relic);
  }

  function move(delta) {
    if (!relics.length) return;
    const i = relics.findIndex((r) => r.id === selectedId);
    const next = relics[Math.min(relics.length - 1, Math.max(0, i < 0 ? 0 : i + delta))];
    onselect?.(next);
    requestAnimationFrame(() => {
      const row = listEl?.querySelector(`[data-id="${next.id}"]`);
      row?.focus({ preventScroll: true });
      row?.scrollIntoView({ block: "nearest" });
    });
  }

  function onKeydown(event) {
    if (event.target.closest("button")) return;
    const key = event.key;
    if (key === "ArrowDown" || key === "j") {
      event.preventDefault();
      move(1);
    } else if (key === "ArrowUp" || key === "k") {
      event.preventDefault();
      move(-1);
    } else if (key === "Enter") {
      const relic = relics.find((r) => r.id === selectedId);
      if (relic && hasViewer(relic.content_type)) {
        event.preventDefault();
        onopen?.(relic);
      }
    }
  }

  // Load more when the end of the list scrolls into view.
  $effect(() => {
    if (!sentinel || !hasMore) return;
    const io = new IntersectionObserver(
      (entries) => entries[0].isIntersecting && !loading && onloadmore?.(),
      { root: listEl, rootMargin: "400px" }
    );
    io.observe(sentinel);
    return () => io.disconnect();
  });

  const sortedBy = (key) => sort?.key === key;
  const canSort = (key) => !!onsort && (!sortable || sortable.includes(key));
  // Header buttons say their state: "Size, sorted largest first" style labels for screen readers.
  const sortLabel = (key, title) =>
    sortedBy(key) ? `${title}, sorted ${sort.dir === "asc" ? "ascending" : "descending"}` : `Sort by ${title.toLowerCase()}`;

  // The row that takes Tab focus: the selection, or the first row.
  const focusId = $derived(relics.some((r) => r.id === selectedId) ? selectedId : relics[0]?.id);
</script>

<!-- Keys bubble up from the focused row; the rows themselves are the focus targets. -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div class="list" bind:this={listEl} role="list" aria-busy={loading} onkeydown={onKeydown}>
  {#if relics.length}
    <div class="list-head cols" class:no-owner={!showOwner} class:is-local={local} role="presentation">
      {#snippet head(key, label, title, cls = "")}
        {#if !canSort(key)}
          <span class="head-plain {cls}" title={title}>{@render label()}</span>
        {:else}
        <button class="head-sort {cls}" class:is-on={sortedBy(key)} aria-label={sortLabel(key, title)} onclick={() => onsort?.(key)} title="Sort by {title.toLowerCase()}">
          {#if cls.includes("head-num") && sortedBy(key)}<span class="head-dir" class:is-asc={sort.dir === "asc"}><Icon name="arrowup" /></span>{/if}
          {@render label()}
          {#if !cls.includes("head-num") && sortedBy(key)}<span class="head-dir" class:is-asc={sort.dir === "asc"}><Icon name="arrowup" /></span>{/if}
        </button>
        {/if}
      {/snippet}
      {#snippet dateHead()}{dateLabel ?? (grouped ? "Time" : "Date")}{/snippet}
      {#snippet nameLabel()}Name{/snippet}
      {#snippet ownerLabel()}Owner{/snippet}
      {#snippet sizeLabel()}Size{/snippet}
      {@render head("date", dateHead, dateLabel ?? "Date")}
      <span></span>
      {@render head("name", nameLabel, "Name")}
      {#if showOwner && !local}{@render head("owner", ownerLabel, "Owner", "head-owner")}{/if}
      {#if !local}<span class="head-id">ID</span>{/if}
      <span class="head-tags">Tags</span>
      {@render head("size", sizeLabel, "Size", "head-num")}
      {#if !local}
      {#each COUNTERS as c (c.key)}
        {#snippet countLabel()}<Icon name={c.icon} />{/snippet}
        {#if c.sort}
          {@render head(c.sort, countLabel, c.name, "head-num head-count")}
        {:else}
          <span class="head-num head-count" title={c.name} aria-label={c.name}><Icon name={c.icon} /></span>
        {/if}
      {/each}
      {/if}
    </div>
  {/if}
  {#each items as { relic, day, dated } (relic.id)}
    {#if day}
      <div class="r-day" role="presentation">
        <span>{day.label}</span>{#if day.date}<span class="r-day-date">{day.date}</span>{/if}
        <span class="r-day-rule"></span><span class="r-day-count">{day.count ?? ""}</span>
      </div>
    {/if}
    {@const badge = typeBadge(relic)}
    {@const expiry = expiryMarker(relic.expires_at)}
    {@const tags = (relic.tags ?? []).map(tagName)}
    {@const viewable = local || hasViewer(relic.content_type)}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_no_noninteractive_tabindex, a11y_click_events_have_key_events -->
    <div
      class="r-row cols"
      class:no-owner={!showOwner}
      class:is-local={local}
      class:is-selected={relic.id === selectedId}
      data-id={relic.id}
      role="listitem"
      aria-current={relic.id === selectedId ? "true" : undefined}
      tabindex={relic.id === focusId ? 0 : -1}
      onclick={(e) => onRowClick(e, relic)}
      ondblclick={() => viewable && onopen?.(relic)}
    >
      <!-- Under a month header the row needs its day; under a day header, its time. -->
      <span class="r-row-time" title={new Date(relic[dateField]).toLocaleString()}>{grouped && !dated ? clockTime(relic[dateField]) : dayMonth(relic[dateField])}</span>
      <span class="r-type r-t-{badge.cls}" title={badge.name}>{badge.label}</span>
      <span class="r-row-name">
        {#snippet name()}
          {#if relic.access_level === "private"}
            <span class="r-row-vis" title="Private: anyone with the link"><Icon name="lock" /></span>
          {:else if relic.access_level === "restricted"}
            <span class="r-row-vis" title="Restricted: only people you add"><Icon name="users" /></span>
          {:else if showPublic}
            <span class="r-row-vis" title="Public: listed in Recent"><Icon name="globe" /></span>
          {/if}
          {#if relic.name}
            {#each nameParts(relic.name) as part}{#if part.mark}<mark>{part.text}</mark>{:else}{part.text}{/if}{/each}
          {:else}Untitled{/if}
        {/snippet}
        {#if local}
          <button class="r-row-link row-open" class:is-untitled={!relic.name} tabindex="-1" title="Open “{relic.name || 'Untitled'}”" onclick={() => onopen?.(relic)}>{@render name()}</button>
        {:else if viewable}
          <a class="r-row-link" class:is-untitled={!relic.name} href="/{relic.id}" tabindex="-1" title={relic.name || "Untitled"}>{@render name()}</a>
        {:else}
          <!-- No viewer for this type: nothing to open, so the name isn't a link (download it instead). -->
          <span class="r-row-link is-plain" class:is-untitled={!relic.name} title="{relic.name || 'Untitled'}: no viewer for this type, download it instead">{@render name()}</span>
        {/if}
        {#if expiry}
          <span class="r-marker" class:r-marker-warning={expiry.soon}><Icon name="clock" />{expiry.text}</span>
        {/if}
      </span>
      {#if showOwner && !local}
        {#if onowner && relic.user_id}
          <button class="row-owner row-owner-link" tabindex="-1" title="Show relics by {relic.owner_name || relic.user_public_id || 'this user'}" onclick={() => onowner(relic)} ondblclick={(e) => e.stopPropagation()}>{relic.owner_name || "—"}</button>
        {:else}
          <span class="row-owner" class:is-anon={!relic.owner_name} title={relic.owner_name ? `Owner: ${relic.owner_name}` : "No owner"}>{relic.owner_name || "—"}</span>
        {/if}
      {/if}
      {#if !local}
      <button
        class="r-row-id row-id"
        tabindex="-1"
        title="Copy ID {relic.id}"
        aria-label="Copy ID"
        onclick={() => copyToClipboard(relic.id, "Relic ID copied")}
        ondblclick={(e) => e.stopPropagation()}
      >{relic.id.slice(0, 8)}<Icon name="copy" /></button>
      {/if}
      <!-- Two tags as filter links, then "+N" to see the rest in the inspector. -->
      <span class="r-row-tags">
        {#each tags.slice(0, 2) as tag (tag)}
          <button class="row-tag" tabindex="-1" title="Show relics tagged #{tag}" onclick={() => ontag?.(tag)} ondblclick={(e) => e.stopPropagation()}>#{tag}</button>
        {/each}
        {#if tags.length > 2}
          <button class="row-tag" tabindex="-1" title={tags.slice(2).map((t) => `#${t}`).join(" ")} onclick={() => oncounter?.(relic, "tags")} ondblclick={(e) => e.stopPropagation()}>+{tags.length - 2}</button>
        {/if}
      </span>
      <span class="r-row-size">{compactBytes(relic.size_bytes)}</span>
      {#if !local}
      {#each COUNTERS as c (c.key)}
        {@const n = relic[c.key] ?? 0}
        {#if c.section && n > 0}
          <button
            class="row-count"
            data-level={counterLevel(n)}
            title="{counted(n, c.name)}: show in the inspector"
            aria-label={counted(n, c.name)}
            tabindex="-1"
            onclick={() => oncounter?.(relic, c.section)}
            ondblclick={(e) => e.stopPropagation()}
          >{n}</button>
        {:else}
          <span class="row-count" data-level={counterLevel(n, c.views)} title={counted(n, c.name)}>{n || (c.views ? 0 : "")}</span>
        {/if}
      {/each}
      {/if}
      {#if actions.length}
        <span class="r-row-actions">
          {#each actions as action (action.title)}
            <button
              class="r-btn r-btn-ghost"
              title={action.title}
              aria-label={action.title}
              tabindex="-1"
              onclick={(e) => {
                e.stopPropagation();
                action.run(relic);
              }}
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
        {#if emptyAction}<a class="r-link" href={emptyAction.href}>{emptyAction.label}</a>{/if}
      </p>
    {/if}
  {/each}

  {#if loading}
    <p class="list-status" role="status">Loading…</p>
  {/if}
  {#if hasMore}
    <div bind:this={sentinel} class="list-sentinel"></div>
  {/if}
</div>

<style>
  .list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-bottom: var(--space-4);
    outline: 0;
  }
  .r-row {
    cursor: default;
  }
  .r-row:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }
  /* Name cell: the link shrinks with an ellipsis; markers and counters keep their size. */
  .r-row-name {
    display: flex;
    align-items: center;
    min-width: 0;
  }
  .r-row-link {
    min-width: 0;
    overflow: hidden;
    color: var(--ink);
    text-overflow: ellipsis;
    text-decoration: none;
    cursor: pointer;
  }
  .r-row-link:hover {
    color: var(--accent);
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  .r-row-link.is-untitled {
    color: var(--ink-3);
    font-style: italic;
  }
  .r-row-name :global(.r-marker) {
    flex: none;
  }

  /* One grid for the header and every row: time, type, name, id, tags, size, then the four
     counters. Hover actions float over the counters (the design system's default). */
  .cols {
    grid-template-columns: 38px 34px minmax(0, 1fr) 130px 64px 150px 44px repeat(4, 38px);
  }
  .cols.no-owner {
    grid-template-columns: 38px 34px minmax(0, 1fr) 64px 150px 44px repeat(4, 38px);
  }
  /* Local items (drafts): time, type, name, tags, size; actions float over tags and size. */
  .cols.is-local {
    grid-template-columns: 38px 34px minmax(0, 1fr) 180px 64px;
  }
  .row-open {
    padding: 0;
    border: 0;
    background: none;
    font: inherit;
    text-align: left;
  }
  .r-row:focus-within :global(.r-row-actions) {
    display: flex;
  }

  .list-head {
    position: sticky;
    top: 0;
    z-index: 2;
    display: grid;
    align-items: center;
    gap: var(--space-2\.5);
    height: 26px;
    padding: 0 var(--space-4);
    border-bottom: 1px solid var(--line);
    background: var(--surface);
    color: var(--ink-3);
    font: 700 10.5px var(--font-mono);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    white-space: nowrap;
  }
  .head-sort {
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    letter-spacing: inherit;
    text-align: left;
    text-transform: inherit;
    cursor: pointer;
  }
  .head-sort,
  .head-plain {
    display: flex;
    align-items: center;
    gap: 2px;
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
  .head-num {
    text-align: right;
  }
  .head-count {
    display: flex;
    justify-content: flex-end;
  }
  .head-count :global(.r-icon) {
    width: 14px;
    height: 14px;
  }

  /* Counters: grey until notable, then blue, orange, red (bold); zeros stay blank. */
  .row-count {
    --level: var(--ink-3);
    justify-self: end;
    min-width: 0;
    padding: 0 3px;
    margin-right: -3px;
    border: 0;
    border-radius: var(--radius-xs);
    background: none;
    color: var(--level);
    font: 12.5px var(--font-mono);
    text-align: right;
  }
  button.row-count {
    cursor: pointer;
  }
  button.row-count:hover {
    background: var(--hover);
    text-decoration: underline;
  }
  .row-count[data-level] {
    font-weight: 700;
  }
  .row-count[data-level="low"] {
    --level: var(--type-doc);
  }
  .row-count[data-level="medium"] {
    --level: var(--warning);
  }
  .row-count[data-level="high"] {
    --level: var(--danger);
  }
  .r-row-link.is-plain {
    color: var(--ink-2);
    cursor: default;
  }
  .r-row-link.is-plain:hover {
    color: var(--ink-2);
    text-decoration: none;
  }
  /* Metadata like the id and tags beside it: mono-meta in ink-3, so only the name reads as text. */
  .row-owner {
    min-width: 0;
    overflow: hidden;
    color: var(--ink-3);
    font: 12.5px var(--font-mono);
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .row-owner.is-anon {
    color: var(--line-2);
  }
  .row-owner-link {
    padding: 0;
    border: 0;
    background: none;
    text-align: left;
    cursor: pointer;
  }
  .row-owner-link:hover {
    color: var(--accent);
    text-decoration: underline;
    text-underline-offset: 2px;
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
  .r-row:hover .row-id :global(.r-icon) {
    visibility: visible;
  }

  .row-tag {
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    cursor: pointer;
  }
  .row-tag + .row-tag {
    margin-left: 0.5ch;
  }
  .row-tag:hover {
    color: var(--accent);
    text-decoration: underline;
    text-underline-offset: 2px;
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

  /* Narrower lists drop columns from the right-hand metadata first; the name always stays. */
  /* Narrower: tags go; where there's an owner it stays (it filters, in admin) and the ID goes. */
  @media (max-width: 1180px) {
    .cols {
      grid-template-columns: 38px 34px minmax(0, 1fr) 110px 44px repeat(4, 34px);
    }
    .cols.no-owner {
      grid-template-columns: 38px 34px minmax(0, 1fr) 64px 44px repeat(4, 34px);
    }
    .cols.is-local {
      grid-template-columns: 38px 34px minmax(0, 1fr) 64px;
    }
    .r-row-tags,
    .head-tags,
    .cols:not(.no-owner) .row-id,
    .cols:not(.no-owner) .head-id {
      display: none;
    }
  }
  @media (max-width: 767px) {
    .cols,
    .cols.no-owner,
    .cols.is-local {
      grid-template-columns: 44px 34px minmax(0, 1fr) 44px;
    }
    .r-row {
      height: 36px;
    }
    .list-head,
    .row-owner,
    .r-row-id,
    .row-count,
    .r-row-actions {
      display: none !important;
    }
  }
</style>
