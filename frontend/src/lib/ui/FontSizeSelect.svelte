<script>
  // Font size for editors and viewers: common sizes, or Custom… to type any size from 8 to 72
  // (as the old controls allowed). Styled for the status bar.
  import Icon from "./Icon.svelte";

  let { value = 13, onchange } = $props();

  const SIZES = [11, 12, 13, 14, 15, 16, 18, 20, 24];
  let custom = $state(false);
  let draft = $state(0);

  function pick(event) {
    const v = event.currentTarget.value;
    if (v === "custom") {
      draft = value;
      custom = true;
    } else onchange?.(Number(v));
  }

  function commit() {
    const n = Math.round(Number(draft));
    if (n >= 8 && n <= 72) onchange?.(n);
    custom = false;
  }
</script>

<label class="font-size" title="Font size">
  <Icon name="type" />
  {#if custom}
    <!-- svelte-ignore a11y_autofocus -->
    <input
      type="number"
      min="8"
      max="72"
      bind:value={draft}
      aria-label="Font size in pixels, 8 to 72"
      autofocus
      onkeydown={(e) => (e.key === "Enter" ? commit() : e.key === "Escape" && (custom = false))}
      onblur={commit}
    />px
  {:else}
    <select value={SIZES.includes(value) ? value : "current"} onchange={pick} aria-label="Font size">
      {#if !SIZES.includes(value)}<option value="current">{value}px</option>{/if}
      {#each SIZES as n (n)}<option value={n}>{n}px</option>{/each}
      <option value="custom">Custom…</option>
    </select>
  {/if}
</label>

<style>
  .font-size select,
  .font-size input {
    padding: 0 2px;
    border: 0;
    background: transparent;
    color: inherit;
    font: inherit;
  }
  .font-size select {
    cursor: pointer;
  }
  .font-size input {
    width: 3.2em;
    border-bottom: 1px solid var(--accent);
  }
  .font-size select:focus,
  .font-size input:focus {
    box-shadow: none;
    outline: 0;
  }
</style>
