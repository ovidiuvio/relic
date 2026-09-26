<script>
  // The panel under the focused search bar: the filters you can type here (each inserts itself),
  // values for the word or token under the caret, or with an empty bar an example query.
  // The bar keeps focus; ↑↓ choose, Tab or Enter take a suggestion (see NavSearch).
  import { KEY_HELP } from "./suggest";

  let {
    keys = [], // the filter keys this scope takes, then in:
    scopeLabel = "",
    heading = null,
    items = [],
    note = null,
    active = -1,
    empty = false, // nothing typed yet
    onpick, // (item) a suggestion was chosen
    oninsert, // (text) a filter key or the example was clicked
  } = $props();

  // A click here mustn't take focus from the bar.
  const keep = (event) => event.preventDefault();
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="r-dropdown search-panel" onmousedown={keep}>
  <div class="r-dropdown-filters">
    <span>Narrow with</span>
    {#each keys as key (key)}
      <button type="button" class="key" onclick={() => oninsert(`${key}:`)} title="Add {KEY_HELP[key].example.split(':')[0]}: to the search">
        <code>{key}:</code><em>{KEY_HELP[key].text}</em>
      </button>
    {/each}
  </div>

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
  {:else if note}
    <p class="panel-note">{note}</p>
  {:else if empty}
    <div class="panel-help">
      <p>Words match names, descriptions, IDs and tags in {scopeLabel}. Add filters to narrow it down, for example</p>
      <button type="button" class="example" onclick={() => oninsert("queue handler type:py tag:work")}>
        <code>queue handler <span class="tok">type:py</span> <span class="tok">tag:work</span></code>
      </button>
    </div>
  {/if}

  <div class="r-dropdown-foot panel-keys">
    <span><kbd class="r-kbd">↵</kbd>search</span>
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
