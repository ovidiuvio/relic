<script>
  // Public / Private / Restricted as the design system's option cards.
  import Icon from "../../ui/Icon.svelte";
  import { VISIBILITY } from "./options";

  let { value = $bindable("public"), name = "visibility", note = "" } = $props();
</script>

<div class="r-field" role="radiogroup" aria-labelledby="{name}-label">
  <span class="r-label" id="{name}-label">Visibility</span>
  <div class="r-options">
    {#each VISIBILITY as v (v.value)}
      <label class="r-option">
        <input type="radio" class="r-radio" {name} value={v.value} bind:group={value} />
        <b><Icon name={v.icon} />{v.label}</b>
        <small>{v.hint}</small>
      </label>
    {/each}
  </div>
  {#if note && value === "restricted"}<span class="r-help">{note}</span>{/if}
</div>
