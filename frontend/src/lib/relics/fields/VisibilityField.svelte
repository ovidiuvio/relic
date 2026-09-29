<script>
  // Public / Private / Restricted as a segmented control, with the chosen option's hint below.
  import Icon from "../../ui/Icon.svelte";
  import { VISIBILITY } from "./options";

  let { value = $bindable("public"), name = "visibility", note = "", options = VISIBILITY } = $props();
</script>

<div class="r-field">
  <span class="r-label" id="{name}-label">Visibility</span>
  <div class="r-seg r-seg-block" role="radiogroup" aria-labelledby="{name}-label">
    {#each options as v (v.value)}
      <label title={v.hint}>
        <input type="radio" {name} value={v.value} bind:group={value} />
        <Icon name={v.icon} />{v.label}
      </label>
    {/each}
  </div>
  <span class="r-help">{options.find((v) => v.value === value)?.hint}{#if note && value === "restricted"}. {note}{/if}</span>
</div>
