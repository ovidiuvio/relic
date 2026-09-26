<script>
  // The panel under the focused search bar: the filters you can type here (each inserts itself),
  // values for the word or token under the caret, or with an empty bar an example query.
  // On pages without a list it also shows the matches, in the Recent rows, with a preview of the
  // highlighted one when there's room. The bar keeps focus; see NavSearch for the keys.
  import Icon from "../ui/Icon.svelte";
  import RelicList from "../relics/RelicList.svelte";
  import SearchPreview from "./SearchPreview.svelte";
  import { KEY_HELP } from "./suggest";
  import { segments } from "./query";

  let {
    keys = [], // the filter keys this scope takes, then in:
    scopeLabel = "",
    heading = null,
    items = [],
    note = null,
    active = -1,
    empty = false, // nothing typed yet
    results = null, // { relics, total } matching the query, on pages without a list
    loading = false,
    highlight = "", // the query's free text, marked in names
    resultIndex = -1, // the match chosen with ↑↓
    width = null, // px, when the panel is wide enough for the preview
    onpick, // (item) a suggestion was chosen
    oninsert, // (text) a filter key or the example was clicked
    onopen, // (relic, newTab) a match was chosen
    onseeall, // show every match on the list page
    history = [], // [{ kind: "pinned" | "recent", id?, name?, query, path, label }]
    historyIndex = -1, // the entry chosen with ↑↓
    pinCurrent = null, // { pinned } on a filtered list: offer to pin (or unpin) it
    onrun, // (entry, newTab) run a history entry
    onpin, // (entry) pin a recent search
    onunpin, // (entry)
    onforget, // (entry) drop a recent search
    onrename, // (entry, name)
    onpincurrent, // pin or unpin the list's current search
    onclearrecent, // forget every recent search
  } = $props();

  let renaming = $state(null); // the pinned entry being renamed
  let draft = $state("");

  function startRename(entry) {
    renaming = entry.id;
    draft = entry.name ?? "";
  }

  function onRenameKeydown(event, entry) {
    event.stopPropagation();
    if (event.key === "Enter") {
      event.preventDefault();
      renaming = null;
      onrename(entry, draft);
    } else if (event.key === "Escape") {
      event.preventDefault();
      renaming = null;
      onrename(entry, null);
    }
  }

  const focusOnMount = (el) => {
    el.focus();
    el.select();
  };

  const chosen = $derived(results?.relics[resultIndex] ?? null);
  const previewed = $derived(width && results?.relics.length ? chosen ?? results.relics[0] : null);

  // A click here mustn't take focus from the bar (except into the rename field).
  const keep = (event) => {
    if (!event.target.closest("input")) event.preventDefault();
  };
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="r-dropdown search-panel" class:has-preview={!!previewed} style:width={previewed ? `${width}px` : null} onmousedown={keep}>
  <div class="r-dropdown-filters">
    <span>Narrow with</span>
    {#each keys as key (key)}
      <button type="button" class="key" onclick={() => oninsert(`${key}:`)} title="Add {KEY_HELP[key].example.split(':')[0]}: to the search">
        <code>{key}:</code><em>{KEY_HELP[key].text}</em>
      </button>
    {/each}
  </div>

  <div class="panel-body">
  <div class="panel-main">
  {#if pinCurrent && !items.length}
    <button type="button" class="pin-current" onclick={onpincurrent}>
      <Icon name="pin" />
      {#if pinCurrent.pinned}<span>Pinned</span><span class="r-gap"></span><span class="pin-undo">Unpin</span>
      {:else}<span>Pin this search</span><span class="r-gap"></span><span class="pin-hint">keeps it in your searches, on every device</span>{/if}
    </button>
  {/if}
  {#if history.length && !items.length}
    <div class="r-dropdown-group history" role="listbox" aria-label="Your searches">
      <div class="r-dropdown-head">
        <b>{empty ? "Your searches" : "From your searches"}</b>
        {#if empty && history.some((h) => h.kind === "recent")}<span class="r-gap"></span><button type="button" class="r-link clear" onclick={onclearrecent}>Clear recent</button>{/if}
      </div>
      {#each history as h, i (h.kind + h.path)}
        <div class="hist" class:is-active={i === historyIndex} role="option" aria-selected={i === historyIndex} id="search-hist-{i}">
          {#if renaming === h.id}
            <Icon name="pin" />
            <input class="hist-rename" bind:value={draft} placeholder="Name this search" use:focusOnMount onkeydown={(e) => onRenameKeydown(e, h)} onblur={() => renaming === h.id && ((renaming = null), onrename(h, draft))} maxlength="100" />
          {:else}
            <button type="button" class="hist-run" onclick={(e) => onrun(h, e.ctrlKey || e.metaKey || e.shiftKey)} title="Search {h.label} for {h.query}">
              <Icon name={h.kind === "pinned" ? "pin" : "history"} />
              {#if h.name}<b class="hist-name">{h.name}</b>{/if}
              <code class="hist-query">{#each segments(h.query) as seg (seg.start)}{#if seg.kind === "token"}<span class="tok">{seg.raw}</span>{:else}{seg.raw}{/if}{/each}</code>
              <span class="hist-scope">{h.label}</span>
            </button>
            <span class="hist-acts">
              {#if h.kind === "pinned"}
                <button type="button" onclick={() => startRename(h)} title="Rename" aria-label="Rename"><Icon name="edit" /></button>
                <button type="button" onclick={() => onunpin(h)} title="Unpin" aria-label="Unpin"><Icon name="x" /></button>
              {:else}
                <button type="button" onclick={() => onpin(h)} title="Pin" aria-label="Pin"><Icon name="pin" /></button>
                <button type="button" onclick={() => onforget(h)} title="Forget" aria-label="Forget"><Icon name="x" /></button>
              {/if}
            </span>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
  {#if items.length}
    <div class="r-dropdown-group" role="listbox" id="search-suggestions" aria-label={heading}>
      <div class="r-dropdown-head"><b>{heading}</b><span class="r-gap"></span><span>Tab to complete</span></div>
      {#each items as item, i (item.label)}
        <button type="button" role="option" id="search-sugg-{i}" class="sugg" class:is-active={i === active} aria-selected={i === active} onclick={() => onpick(item)}>
          <code>{item.label}</code>
          {#if item.detail}<span class="sugg-detail">{item.detail}</span>{/if}
          {#if item.count != null}<span class="sugg-count">{item.count.toLocaleString("en-US")}</span>{/if}
        </button>
      {/each}
    </div>
  {:else if results}
    <div class="r-dropdown-group results">
      <div class="r-dropdown-head">
        <b>{results.total ? `${results.total.toLocaleString("en-US")} ${results.total === 1 ? "match" : "matches"}` : "No matches"}</b>
        <span>in {scopeLabel}</span>
        {#if loading}<span class="r-gap"></span><span>Searching…</span>{/if}
      </div>
      {#if results.relics.length}
        <RelicList
          relics={results.relics}
          head={false}
          showOwner={false}
          grouped={!highlight.trim()}
          {highlight}
          selectedId={chosen?.id ?? null}
          onselect={(r) => onopen(r, false)}
          onopen={(r) => onopen(r, false)}
        />
        <button type="button" class="r-dropdown-all see-all" onclick={onseeall}>
          <Icon name="search" /><span>See all <b>{results.total.toLocaleString("en-US")}</b> in {scopeLabel}</span>
          <span class="r-gap"></span><kbd class="r-kbd">↵</kbd>
        </button>
      {:else}
        <p class="panel-note">Nothing in {scopeLabel} matches. Try fewer words or filters, or another list with <code>in:</code>.</p>
      {/if}
    </div>
  {:else if note}
    <p class="panel-note">{note}</p>
  {:else if empty && !history.length}
    <div class="panel-help">
      <p>Words match names, descriptions, IDs and tags in {scopeLabel}. Add filters to narrow it down, for example</p>
      <button type="button" class="example" onclick={() => oninsert("queue handler type:py tag:work")}>
        <code>queue handler <span class="tok">type:py</span> <span class="tok">tag:work</span></code>
      </button>
    </div>
  {/if}
  </div>
  {#if previewed}<SearchPreview relic={previewed} label={chosen ? "" : "Top match"} />{/if}
  </div>

  <div class="r-dropdown-foot panel-keys">
    {#if (results?.relics.length || history.length) && !items.length}
      <span><kbd class="r-kbd">↑</kbd><kbd class="r-kbd">↓</kbd>choose</span>
      <span><kbd class="r-kbd">↵</kbd>{chosen || historyIndex >= 0 ? "open" : results?.relics.length ? "see all" : "search"}</span>
      <span><kbd class="r-kbd">Ctrl</kbd><kbd class="r-kbd">↵</kbd>new tab</span>
    {:else}
      <span><kbd class="r-kbd">↵</kbd>search</span>
    {/if}
    {#if items.length}<span><kbd class="r-kbd">⇥</kbd>complete</span><span><kbd class="r-kbd">↑</kbd><kbd class="r-kbd">↓</kbd>choose</span>{/if}
    <span><kbd class="r-kbd">Esc</kbd>close</span>
  </div>
</div>

<style>
  .search-panel {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    z-index: 60;
    width: max(100%, 460px);
    max-width: calc(100vw - 16px);
  }
  /* Phones: the bar is narrow, so the panel spans the screen under the navbar. */
  @media (max-width: 767px) {
    .search-panel {
      position: fixed;
      top: calc(var(--nav-height) + 4px);
      right: 8px;
      left: 8px;
      width: auto;
    }
    .panel-keys {
      display: none;
    }
    .has-preview .panel-body {
      grid-template-columns: minmax(0, 1fr);
    }
  }
  .panel-body {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
  }
  .has-preview .panel-body {
    grid-template-columns: minmax(0, 1fr) 340px;
    min-height: 300px;
  }
  .panel-main {
    min-width: 0;
  }
  .results :global(.list) {
    flex: none;
    max-height: 60vh;
    padding-bottom: 0;
  }
  .see-all {
    width: 100%;
    border: 0;
    border-top: 1px solid var(--line);
    background: none;
    font: inherit;
    text-align: left;
    cursor: pointer;
  }
  .see-all:hover {
    background: var(--subtle);
  }
  .see-all :global(.r-icon) {
    width: 14px;
    height: 14px;
    color: var(--ink-3);
  }
  .panel-note code {
    color: var(--accent);
    font-family: var(--font-mono);
  }
  .pin-current {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    width: 100%;
    height: 34px;
    padding: 0 var(--space-4);
    border: 0;
    border-bottom: 1px solid var(--line);
    background: none;
    color: var(--ink);
    font: inherit;
    font-size: 13px;
    text-align: left;
    cursor: pointer;
  }
  .pin-current:hover {
    background: var(--subtle);
  }
  .pin-current :global(.r-icon) {
    width: 14px;
    height: 14px;
    color: var(--accent);
  }
  .pin-hint,
  .pin-undo {
    color: var(--ink-3);
    font-size: 12px;
  }
  .pin-undo {
    color: var(--accent);
  }
  .clear {
    font-size: 11.5px;
  }
  .hist {
    position: relative;
    display: flex;
    align-items: center;
    height: 32px;
    padding: 0 var(--space-4);
  }
  .hist:hover,
  .hist.is-active {
    background: var(--accent-soft);
  }
  .hist > :global(.r-icon) {
    flex: none;
    width: 14px;
    height: 14px;
    margin-right: var(--space-2\.5);
    color: var(--accent);
  }
  .hist-run {
    display: flex;
    flex: 1;
    align-items: center;
    gap: var(--space-2\.5);
    min-width: 0;
    height: 100%;
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink);
    font: inherit;
    text-align: left;
    cursor: pointer;
  }
  .hist-run :global(.r-icon) {
    flex: none;
    width: 14px;
    height: 14px;
    color: var(--ink-3);
  }
  .hist-name {
    flex: none;
    max-width: 40%;
    overflow: hidden;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .hist-query {
    min-width: 0;
    overflow: hidden;
    color: var(--ink-2);
    font: 12.5px var(--font-mono);
    text-overflow: ellipsis;
    white-space: pre;
  }
  .hist-query .tok {
    color: var(--accent);
  }
  .hist-scope {
    flex: none;
    margin-left: auto;
    padding-left: var(--space-2);
    color: var(--ink-3);
    font-size: 12px;
  }
  .hist-acts {
    display: none;
    gap: 2px;
    margin-left: var(--space-2);
  }
  .hist:hover .hist-acts,
  .hist.is-active .hist-acts {
    display: flex;
  }
  .hist-acts button {
    display: grid;
    place-items: center;
    width: 24px;
    height: 24px;
    padding: 0;
    border: 0;
    border-radius: var(--radius-sm);
    background: none;
    color: var(--ink-3);
    cursor: pointer;
  }
  .hist-acts button:hover {
    background: var(--surface);
    color: var(--ink);
  }
  .hist-acts :global(.r-icon) {
    width: 13px;
    height: 13px;
  }
  .hist-rename {
    flex: 1;
    height: 24px;
    padding: 0 var(--space-2);
    border: 1px solid var(--accent);
    border-radius: var(--radius-sm);
    background: var(--surface);
    color: var(--ink);
    font: inherit;
    outline: 0;
  }
  .key {
    display: inline-flex;
    align-items: baseline;
    padding: 0;
    border: 0;
    background: none;
    font: inherit;
    cursor: pointer;
  }
  .key:hover code {
    border-color: var(--accent);
    color: var(--accent);
  }
  .sugg {
    display: flex;
    align-items: baseline;
    gap: var(--space-2\.5);
    width: 100%;
    height: 30px;
    align-items: center;
    padding: 0 var(--space-4);
    border: 0;
    background: none;
    color: var(--ink);
    font: inherit;
    text-align: left;
    cursor: pointer;
  }
  .sugg:hover,
  .sugg.is-active {
    background: var(--accent-soft);
  }
  .sugg code {
    color: var(--accent);
    font: 12.5px var(--font-mono);
  }
  .sugg-detail {
    min-width: 0;
    overflow: hidden;
    color: var(--ink-3);
    font-size: 12.5px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sugg-count {
    margin-left: auto;
    color: var(--ink-3);
    font: 12px var(--font-mono);
  }
  .panel-help,
  .panel-note {
    margin: 0;
    padding: var(--space-3) var(--space-4);
    color: var(--ink-2);
    font-size: 12.5px;
  }
  .panel-help p {
    margin: 0 0 var(--space-2);
  }
  .example {
    padding: 4px 8px;
    border: 1px solid var(--line-2);
    border-radius: var(--radius-sm);
    background: var(--surface);
    cursor: pointer;
  }
  .example:hover {
    border-color: var(--accent);
  }
  .example code {
    color: var(--ink);
    font: 12.5px var(--font-mono);
  }
  .example .tok {
    border-radius: 3px;
    background: var(--accent-soft);
    color: var(--accent);
  }
  .panel-keys {
    display: flex;
    gap: var(--space-4);
    color: var(--ink-3);
    font-size: 11.5px;
  }
  .panel-keys span {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
</style>
