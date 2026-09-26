<script>
  // Tags as chips: type and press Enter or comma to add, × or Backspace to remove. Tags are
  // lowercased and de-duplicated, as the API stores them.
  import Icon from "../../ui/Icon.svelte";

  let { tags = $bindable([]), id = "tags" } = $props();
  let draft = $state("");

  function add(raw) {
    const names = raw.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean);
    tags = [...new Set([...tags, ...names])];
    draft = "";
  }

  function onKeydown(event) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      if (draft.trim()) add(draft);
    } else if (event.key === "Backspace" && !draft && tags.length) {
      tags = tags.slice(0, -1);
    }
  }

  /** Commit a half-typed tag (call before saving). */
  export function flush() {
    if (draft.trim()) add(draft);
  }
</script>

<div class="r-field">
  <label class="r-label" for={id}>Tags</label>
  <span class="r-input">
    {#each tags as tag (tag)}
      <span class="r-chip-tag">
        {tag}
        <button type="button" class="untag" onclick={() => (tags = tags.filter((t) => t !== tag))} aria-label="Remove tag {tag}"><Icon name="x" /></button>
      </span>
    {/each}
    <input {id} bind:value={draft} onkeydown={onKeydown} onblur={() => draft.trim() && add(draft)} placeholder={tags.length ? "Add a tag…" : "config, nginx, production"} />
  </span>
</div>

<style>
  .untag {
    display: grid;
    place-items: center;
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink-3);
    cursor: pointer;
  }
  .untag:hover {
    color: var(--danger);
  }
</style>
