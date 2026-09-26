<script>
  // Expiry as preset pills plus Custom (a number and a unit). The value is the API's duration
  // string ("24h", "90d", "never"), or "keep" when `allowKeep` offers leaving it unchanged.
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

  function pick(v) {
    custom = false;
    value = v;
  }
  $effect(() => {
    if (custom) value = `${Math.max(1, Math.round(amount) || 1)}${unit}`;
  });
</script>

<div class="r-field">
  <span class="r-label">Expires{#if current}<span class="r-label-aside">now {current}</span>{/if}</span>
  <div class="r-pills">
    {#each presets as [v, label] (v)}
      <button type="button" aria-pressed={!custom && value === v} onclick={() => pick(v)}>{label}</button>
    {/each}
    <button type="button" aria-pressed={custom} onclick={() => (custom = true)}>Custom…</button>
  </div>
  {#if custom}
    <span class="expiry-custom">
      in
      <span class="r-input r-input-sm"><input type="number" min="1" bind:value={amount} aria-label="How many" /></span>
      <select bind:value={unit} aria-label="Unit">
        {#each EXPIRY_UNITS as [u, label] (u)}<option value={u}>{label}</option>{/each}
      </select>
    </span>
  {/if}
</div>

<style>
  .expiry-custom {
    display: flex;
    align-items: center;
    gap: var(--space-1\.5);
    color: var(--ink-2);
    font-size: 12.5px;
  }
  .expiry-custom .r-input {
    width: 80px;
  }
  .expiry-custom select {
    height: var(--control-md);
    padding: 0 22px 0 8px;
    border: 1px solid var(--line-2);
    border-radius: var(--radius-sm);
    font-size: 12.5px;
  }
</style>
