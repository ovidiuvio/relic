<script>
  // Expiry as a select of presets plus Custom (a number and a unit). The value is the API's duration
  // string ("24h", "90d", "never"), or "keep" when `allowKeep` offers leaving it unchanged.
  import Icon from "../../ui/Icon.svelte";
  import { EXPIRY, EXPIRY_UNITS } from "./options";

  let { value = $bindable("never"), allowKeep = false, current = "" } = $props();

  const presets = $derived(allowKeep ? [["keep", "Keep"], ...EXPIRY] : EXPIRY);
  const isPreset = (v) => presets.some(([p]) => p === v);

  // Start from the value passed in; after that the pills and inputs drive it.
  const start = () => ({
    custom: !isPreset(value),
    amount: parseInt(value) || 2,
    unit: /^\d+[mhdwy]$/.test(value) ? value.slice(-1) : "d",
  });
  const initial = start();
  let custom = $state(initial.custom);
  let amount = $state(initial.amount);
  let unit = $state(initial.unit);

  // The select shows "custom" while a number and unit are being typed.
  const choice = $derived(custom ? "custom" : value);
  function pick(v) {
    custom = v === "custom";
    if (!custom) value = v;
  }
  $effect(() => {
    if (custom) value = `${Math.max(1, Math.round(amount) || 1)}${unit}`;
  });
</script>

<div class="r-field">
  <span class="r-label">Expires{#if current}<span class="r-label-aside">now {current}</span>{/if}</span>
  <div class="expiry-row">
    <span class="expiry-pick">
      <select class="expiry-select" value={choice} onchange={(e) => pick(e.currentTarget.value)} aria-label="Expires">
        {#each presets as [v, label] (v)}<option value={v}>{label}</option>{/each}
        <option value="custom">Custom…</option>
      </select>
      <Icon name="chev" />
    </span>
    {#if custom}
      <span class="r-input r-input-sm"><input type="number" min="1" bind:value={amount} aria-label="How many" /></span>
      <span class="expiry-pick expiry-unit">
        <select class="expiry-select" bind:value={unit} aria-label="Unit">
          {#each EXPIRY_UNITS as [u, label] (u)}<option value={u}>{label}</option>{/each}
        </select>
        <Icon name="chev" />
      </span>
    {/if}
  </div>
</div>

<style>
  .expiry-row {
    display: flex;
    align-items: center;
    gap: var(--space-1\.5);
  }
  .expiry-pick {
    position: relative;
    display: flex;
    flex: 1;
    min-width: 0;
  }
  .expiry-pick :global(.r-icon) {
    position: absolute;
    top: 50%;
    right: 9px;
    width: 13px;
    height: 13px;
    color: var(--ink-3);
    transform: translateY(-50%);
    pointer-events: none;
  }
  .expiry-select {
    appearance: none;
    width: 100%;
    min-width: 0;
    height: var(--field);
    padding: 0 28px 0 10px;
    border: 1px solid var(--line-2);
    border-radius: var(--radius-sm);
    background: var(--surface);
    color: var(--ink);
    font: 13px var(--font-sans);
    cursor: pointer;
  }
  .expiry-select:focus-visible {
    border-color: var(--accent);
    box-shadow: var(--ring-accent);
    outline: 0;
  }
  .expiry-unit {
    flex: none;
    width: 104px;
  }
  .expiry-row .r-input {
    flex: none;
    width: 72px;
    min-height: var(--field);
  }
</style>
