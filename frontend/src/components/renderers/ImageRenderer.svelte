<script>
  // An image relic, centred on a checkerboard so transparency shows. It fits the view; click it
  // (or press 1) for actual size, and again to fit. The corner shows its size in pixels.
  let { processed, relicName = "" } = $props();

  let fit = $state(true);
  let natural = $state(null); // { w, h }
  let img = $state();

  function onLoad() {
    natural = { w: img.naturalWidth, h: img.naturalHeight };
  }

  // Only worth toggling when the image is bigger than the view.
  const canZoom = $derived(!!natural);

  function onKeydown(event) {
    if (event.key === "1" && !event.target.closest?.("input, textarea, [contenteditable]")) fit = !fit;
  }
</script>

<svelte:window onkeydown={onKeydown} />

<div class="img-frame">
<div class="img-view" class:is-actual={!fit}>
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events -->
  <img
    bind:this={img}
    src={processed.url}
    alt={relicName}
    onload={onLoad}
    onclick={() => canZoom && (fit = !fit)}
    title={fit ? "Actual size (1)" : "Fit to the view (1)"}
  />
</div>
{#if natural}
  <span class="img-meta">{natural.w} × {natural.h} px · {fit ? "fit" : "actual size"}</span>
{/if}
</div>

<style>
  .img-frame {
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
  }
  /* One cell the size of the view, so "fit" can size the image against it. */
  .img-view {
    flex: 1;
    min-width: 0;
    display: grid;
    grid-template: minmax(0, 1fr) / minmax(0, 1fr);
    place-items: center;
    padding: var(--space-4);
    overflow: auto;
    background-color: var(--surface);
    background-image:
      linear-gradient(45deg, var(--chip) 25%, transparent 25%),
      linear-gradient(-45deg, var(--chip) 25%, transparent 25%),
      linear-gradient(45deg, transparent 75%, var(--chip) 75%),
      linear-gradient(-45deg, transparent 75%, var(--chip) 75%);
    background-size: 16px 16px;
    background-position: 0 0, 0 8px, 8px -8px, -8px 0;
  }
  img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    cursor: zoom-in;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
  .is-actual {
    grid-template: auto / auto;
    place-items: start center;
  }
  .is-actual img {
    max-width: none;
    max-height: none;
    cursor: zoom-out;
  }
  .img-meta {
    position: absolute;
    right: var(--space-3);
    bottom: var(--space-3);
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--surface) 88%, transparent);
    color: var(--ink-3);
    font: 11.5px var(--font-mono);
    pointer-events: none;
  }
</style>
