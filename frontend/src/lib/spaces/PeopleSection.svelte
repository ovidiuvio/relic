<script>
  // Who can use a space: the owner, then everyone given a role. Managers (owner, admin) add
  // people by public ID with a role and remove them, with Undo. Changes apply at once.
  import Icon from "../ui/Icon.svelte";
  import { spaces as spacesApi } from "../../services/api";
  import { showToast } from "../../stores/toastStore";
  import { ROLES, GRANTABLE } from "./roles";
  import { shortDate } from "../relics/format";

  let { spaceId, manage = false } = $props();

  let owner = $state(null);
  let people = $state([]);
  let total = $state(0);
  let loading = $state(false);
  let failed = $state(false);
  let query = $state("");
  let draft = $state("");
  let role = $state("viewer");
  let adding = $state(false);
  let timer;

  async function load(offset = 0) {
    const id = spaceId;
    loading = true;
    failed = false;
    try {
      const data = await spacesApi.getAccessList(id, { limit: 25, offset, search: query.trim() || undefined });
      if (id !== spaceId) return;
      owner = data.owner ?? null;
      people = offset ? [...people, ...data.access] : data.access;
      total = data.total;
    } catch {
      if (id === spaceId) failed = true;
    } finally {
      if (id === spaceId) loading = false;
    }
  }

  $effect(() => {
    spaceId;
    people = [];
    query = "";
    load(0);
  });

  function onSearch() {
    clearTimeout(timer);
    timer = setTimeout(() => load(0), 300);
  }

  async function grant(publicId, grantRole) {
    await spacesApi.addAccess(spaceId, { public_id: publicId, role: grantRole });
    await load(0);
  }

  async function add(event) {
    event.preventDefault();
    const publicId = draft.trim();
    if (!publicId || adding) return;
    adding = true;
    try {
      await grant(publicId, role);
      draft = "";
      showToast("Added to the space", "success");
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t add that person", "error");
    } finally {
      adding = false;
    }
  }

  async function remove(person) {
    try {
      await spacesApi.removeAccess(spaceId, person.id);
      people = people.filter((p) => p.id !== person.id);
      total -= 1;
      showToast(`Removed ${person.user_name || person.public_id}`, "success", 3000, {
        label: "Undo",
        run: () => grant(person.public_id, person.role).catch(() => showToast("Couldn’t add them back", "error")),
      });
    } catch {
      showToast("Couldn’t remove them", "error");
    }
  }
</script>

{#if manage}
  <form class="people-add" onsubmit={add}>
    <span class="r-input r-input-sm people-id"><input bind:value={draft} placeholder="Public ID" aria-label="Public ID to add" spellcheck="false" /></span>
    <select class="people-role" bind:value={role} aria-label="Role">
      {#each GRANTABLE as r (r)}<option value={r}>{ROLES[r].label}</option>{/each}
    </select>
    <button class="r-btn r-btn-secondary r-btn-md" disabled={!draft.trim() || adding}>Add</button>
  </form>
  <p class="ins-note people-hint">{ROLES[role].hint}. People find their public ID in their profile.</p>
{/if}

{#if total > 25 || query}
  <span class="r-input r-input-sm people-search">
    <Icon name="search" size={13} />
    <input bind:value={query} oninput={onSearch} placeholder="Filter people" aria-label="Filter people" />
  </span>
{/if}

{#if failed}
  <p class="ins-note">Couldn’t load the people in this space. <button class="r-link" onclick={() => load(0)}>Try again</button></p>
{:else}
  <ul class="ins-people">
    {#if owner && !query}
      <li>
        <span class="ins-person">{owner.user_name || "Anonymous"}</span>
        <span class="r-chip">Owner</span>
        <span class="ins-when">{owner.public_id?.slice(0, 8) ?? ""}</span>
      </li>
    {/if}
    {#each people as p (p.id)}
      <li>
        <span class="ins-person">{p.user_name || "Anonymous"}</span>
        <span class="r-chip">{ROLES[p.role]?.label ?? p.role}</span>
        <span class="ins-when" title="Added {shortDate(p.created_at)}">{p.public_id?.slice(0, 8) ?? ""}</span>
        {#if manage}
          <button class="people-remove" onclick={() => remove(p)} title="Remove from the space" aria-label="Remove {p.user_name || p.public_id}"><Icon name="x" size={13} /></button>
        {/if}
      </li>
    {:else}
      {#if !loading}<li class="ins-note">{query ? "Nobody matches." : "Nobody else has access yet."}</li>{/if}
    {/each}
  </ul>
  {#if people.length < total}
    <button class="r-link ins-more" disabled={loading} onclick={() => load(people.length)}>Show more</button>
  {/if}
{/if}

<style>
  .people-add {
    display: flex;
    gap: var(--space-1\.5);
    margin-bottom: var(--space-1\.5);
  }
  .people-id {
    flex: 1;
    font-family: var(--font-mono);
  }
  .people-role {
    height: var(--control-md);
    padding: 0 22px 0 8px;
    border: 1px solid var(--line-2);
    border-radius: var(--radius-sm);
    background-color: var(--surface);
    font-size: 12.5px;
  }
  .people-hint {
    margin-bottom: var(--space-3);
  }
  .people-search {
    margin-bottom: var(--space-2);
  }
  .people-remove {
    display: grid;
    place-items: center;
    padding: 2px;
    border: 0;
    border-radius: var(--radius-xs);
    background: none;
    color: var(--ink-3);
    cursor: pointer;
  }
  .people-remove:hover {
    background: var(--danger-soft);
    color: var(--danger);
  }
</style>
