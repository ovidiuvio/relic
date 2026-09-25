<script>
  // Who can open a restricted relic: add people by public ID, remove them. Changes apply at
  // once (no Save), as the design system asks for access changes.
  import Icon from "../../ui/Icon.svelte";
  import { getRelicAccess, addRelicAccess, removeRelicAccess } from "../../../services/api";
  import { showToast } from "../../../stores/toastStore";
  import { shortDate } from "../format";

  let { relicId } = $props();

  let people = $state([]);
  let total = $state(0);
  let loading = $state(false);
  let failed = $state(false);
  let draft = $state("");
  let adding = $state(false);

  async function load(offset = 0) {
    const id = relicId;
    loading = true;
    failed = false;
    try {
      const { data } = await getRelicAccess(id, { limit: 25, offset });
      if (id !== relicId) return;
      people = offset ? [...people, ...data.access] : data.access;
      total = data.total;
    } catch {
      if (id === relicId) failed = true;
    } finally {
      if (id === relicId) loading = false;
    }
  }

  $effect(() => {
    relicId;
    people = [];
    load(0);
  });

  async function add(event) {
    event.preventDefault();
    const publicId = draft.trim();
    if (!publicId || adding) return;
    adding = true;
    try {
      await addRelicAccess(relicId, publicId);
      draft = "";
      showToast("Access granted", "success");
      await load(0);
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t add that person", "error");
    } finally {
      adding = false;
    }
  }

  async function remove(person) {
    try {
      await removeRelicAccess(relicId, person.public_id);
      people = people.filter((p) => p.public_id !== person.public_id);
      total -= 1;
      showToast(`Removed ${person.user_name || person.public_id}`, "success", 3000, {
        label: "Undo",
        run: async () => {
          await addRelicAccess(relicId, person.public_id);
          load(0);
        },
      });
    } catch {
      showToast("Couldn’t remove access", "error");
    }
  }
</script>

<form class="ins-access-add" onsubmit={add}>
  <span class="r-input r-input-sm"><input bind:value={draft} placeholder="Public ID to add" aria-label="Public ID to add" spellcheck="false" /></span>
  <button class="r-btn r-btn-secondary r-btn-md" disabled={!draft.trim() || adding}>Add</button>
</form>
<p class="ins-note access-hint">People find their public ID in their profile. Changes apply immediately.</p>

{#if failed}
  <p class="ins-note">Couldn’t load who has access. <button class="r-link" onclick={() => load(0)}>Try again</button></p>
{:else if !people.length}
  <p class="ins-note">{loading ? "Loading…" : "Only you can open it. Add someone above."}</p>
{:else}
  <ul class="ins-people">
    {#each people as p (p.public_id)}
      <li>
        <span class="ins-person">{p.user_name || "Anonymous"}</span>
        <span class="ins-pid">{p.public_id}</span>
        <span class="ins-when">{shortDate(p.created_at)}</span>
        <button class="ins-remove" onclick={() => remove(p)} title="Remove access" aria-label="Remove access for {p.user_name || p.public_id}"><Icon name="x" size={13} /></button>
      </li>
    {/each}
  </ul>
  {#if people.length < total}
    <button class="r-link ins-more" disabled={loading} onclick={() => load(people.length)}>Show more</button>
  {/if}
{/if}

<style>
  .ins-access-add {
    display: flex;
    gap: var(--space-1\.5);
    margin-bottom: var(--space-1\.5);
  }
  .ins-access-add .r-input {
    flex: 1;
    font-family: var(--font-mono);
  }
  .access-hint {
    margin-bottom: var(--space-3);
  }
  .ins-remove {
    display: grid;
    place-items: center;
    padding: 2px;
    border: 0;
    border-radius: var(--radius-xs);
    background: none;
    color: var(--ink-3);
    cursor: pointer;
  }
  .ins-remove:hover {
    background: var(--danger-soft);
    color: var(--danger);
  }
</style>
