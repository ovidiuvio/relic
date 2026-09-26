<script>
  // The 44px bar under the navbar: the page's title and count, its filters, view options,
  // page actions and the inspector toggle. Markup follows the design system's PageBar.
  import Icon from "../ui/Icon.svelte";

  let { title, count = null, filters, options, actions, inspectorOpen = null, ontoggleinspector } = $props();
</script>

<div class="r-pagebar">
  <h1>{title}{#if count != null}<span>{count.toLocaleString("en-US")}</span>{/if}</h1>
  {#if filters}{@render filters()}{/if}
  <span class="r-gap"></span>
  {#if options}{@render options()}{/if}
  {#if actions}{@render actions()}{/if}
  {#if inspectorOpen != null}
    <button
      class="r-btn r-btn-ghost r-btn-icon"
      aria-pressed={inspectorOpen}
      onclick={ontoggleinspector}
      title="Inspector ( ] )"
      aria-label="Toggle inspector"
    >
      <Icon name="panel" />
    </button>
  {/if}
</div>

<style>
  /* A container, so what's in it (the type facets) can fold up when the bar is narrow. */
  .r-pagebar {
    flex: none;
    overflow: hidden;
    container: pagebar / inline-size;
  }
  /* Phones: filters and page actions can outgrow the width; the bar scrolls sideways. */
  @media (max-width: 767px) {
    .r-pagebar {
      overflow-x: auto;
      scrollbar-width: none;
    }
    .r-pagebar :global(.r-gap) {
      flex: 1 0 var(--space-3);
    }
  }
  /* View options are real selects dressed as the design's sentence-style options. */
  .r-pagebar :global(.r-pagebar-opt select) {
    padding: 0 14px 0 0;
    border: 0;
    background: transparent url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23877d85' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E") no-repeat right center / 12px;
    color: var(--ink);
    font: 500 12.5px var(--font-sans);
    cursor: pointer;
    appearance: none;
    field-sizing: content;
  }
  .r-pagebar :global(.r-pagebar-opt select:focus) {
    box-shadow: none;
  }
  .r-pagebar :global(.r-chip-filter button) {
    display: grid;
    place-items: center;
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    cursor: pointer;
  }
</style>
