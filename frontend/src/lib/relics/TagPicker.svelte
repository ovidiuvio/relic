<script>
  // "tag any ▾" in the page bar: the list's most used tags with how many relics carry each.
  // Picking one filters by it (a link, ?tag=); the filter chip then shows and clears it.
  import Icon from "../ui/Icon.svelte";

  let {
    active = null, // the tag filtered by
    tags = null, // [{ name, count }] from feed.facets.tags
    hrefFor, // (tag | null) => URL with that tag
  } = $props();

  let open = $state(false);
  let el = $state();
  let btn = $state();
  let pos = $state({ top: 0, right: 0 });

  // The page bar clips what overflows it, so the menu is placed against the window.
  function toggle() {
    if (!open) {
      const r = btn.getBoundingClientRect();
      pos = { top: r.bottom + 6, right: Math.max(8, window.innerWidth - r.right) };
    }
    open = !open;
  }

  function onWindowClick(event) {
    if (open && !el?.contains(event.target)) open = false;
  }
  function onKeydown(event) {
    if (event.key === "Escape" && open) {
      open = false;
      event.stopPropagation();
    }
  }
</script>

<svelte:window onclick={onWindowClick} onresize={() => (open = false)} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="tp" bind:this={el} onkeydown={onKeydown}>
  <button bind:this={btn} class="r-pagebar-opt tp-btn" aria-expanded={open} aria-haspopup="true" onclick={toggle} title="Filter by a tag">
    tag <b>{active ? `#${active}` : "any"}</b><Icon name="chev" />
  </button>
  {#if open}
    <div class="tp-menu" style:top="{pos.top}px" style:right="{pos.right}px">
      <p class="tp-head">Most used tags{#if tags?.length}<span>relics</span>{/if}</p>
      {#if active}
        <a class="tp-item" href={hrefFor(null)} onclick={() => (open = false)}><span class="tp-name">Any tag</span></a>
      {/if}
      {#each tags ?? [] as t (t.name)}
        <a class="tp-item" class:is-on={t.name === active} href={hrefFor(t.name)} onclick={() => (open = false)} aria-current={t.name === active ? "true" : undefined}>
          <span class="tp-name">#{t.name}</span><em>{t.count.toLocaleString("en-US")}</em>
        </a>
      {:else}
        <p class="tp-empty">{tags ? "No tags in this list." : "Loading…"}</p>
      {/each}
    </div>
  {/if}
</div>

<style>
  .tp {
    position: relative;
    flex: none;
  }
  .tp-btn {
    height: var(--control-md);
    padding: 0 4px;
    border: 0;
    border-radius: var(--radius-xs);
    background: none;
    color: var(--ink-2);
    font: 12.5px var(--font-sans);
    white-space: nowrap;
    cursor: pointer;
  }
  .tp-btn:hover,
  .tp-btn[aria-expanded="true"] {
    background: var(--hover);
  }
  .tp-btn b {
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .tp-menu {
    position: fixed;
    z-index: 60;
    display: grid;
    width: 240px;
    max-height: 360px;
    padding: var(--space-1) 0;
    overflow-y: auto;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    background: var(--surface);
    box-shadow: var(--shadow-popover);
  }
  .tp-head {
    display: flex;
    justify-content: space-between;
    margin: 0;
    padding: var(--space-1) var(--space-3) var(--space-1\.5);
    color: var(--ink-3);
    font: 700 10.5px var(--font-mono);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .tp-head span {
    font-weight: 400;
  }
  .tp-item {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: 5px var(--space-3);
    color: var(--ink);
    font: 13px var(--font-sans);
    text-decoration: none;
  }
  .tp-item:hover {
    background: var(--hover);
  }
  .tp-item.is-on {
    color: var(--accent);
    font-weight: 500;
  }
  .tp-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .tp-item em {
    color: var(--ink-3);
    font: 12px var(--font-mono);
    font-style: normal;
  }
  .tp-empty {
    margin: 0;
    padding: var(--space-2) var(--space-3);
    color: var(--ink-3);
    font-size: 12.5px;
  }
</style>
