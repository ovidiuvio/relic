<script>
  // Inspector mode for a space: "New space" (space = null) or "Space settings". Settings also
  // hold ownership transfer and deleting, each confirmed in place. Ctrl+Enter saves, Esc cancels.
  import Icon from "../ui/Icon.svelte";
  import { spaces as spacesApi } from "../../services/api";
  import { showToast } from "../../stores/toastStore";

  let {
    space = null,
    transferable = false, // owner or Relic admin (the API refuses everyone else)
    startDelete = false, // open with the delete confirmation showing
    onsaved,
    ondeleted,
    oncancel,
  } = $props();

  const VISIBILITY = [
    { value: "public", icon: "globe", label: "Public", hint: "Anyone can find and view it" },
    { value: "private", icon: "lock", label: "Private", hint: "Only people you add" },
  ];

  const initial = () => ({ name: space?.name ?? "", visibility: space?.visibility ?? "public" });
  let form = $state(initial());
  let saving = $state(false);
  let transferTo = $state("");
  let confirming = $state(null); // "transfer" | "delete"
  $effect(() => {
    if (startDelete) confirming = "delete";
  });
  let busy = $state(false);

  const creating = $derived(!space);

  async function save() {
    if (saving) return;
    if (!form.name.trim()) return showToast("Give the space a name", "error");
    saving = true;
    try {
      const payload = { name: form.name.trim(), visibility: form.visibility };
      const saved = creating ? await spacesApi.create(payload) : await spacesApi.update(space.id, payload);
      showToast(creating ? `Created “${saved.name}”` : "Space updated", "success");
      onsaved?.(saved);
    } catch (error) {
      showToast(error.response?.data?.detail || (creating ? "Couldn’t create the space" : "Couldn’t save the space"), "error");
    } finally {
      saving = false;
    }
  }

  async function transfer() {
    busy = true;
    try {
      const saved = await spacesApi.transferOwnership(space.id, transferTo.trim());
      showToast("Ownership transferred", "success");
      transferTo = "";
      confirming = null;
      onsaved?.(saved);
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t transfer ownership", "error");
    } finally {
      busy = false;
    }
  }

  async function remove() {
    busy = true;
    try {
      await spacesApi.delete(space.id);
      showToast(`Deleted “${space.name}”`, "success");
      ondeleted?.(space);
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t delete the space", "error");
      busy = false;
    }
  }

  function onKeydown(event) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      save();
    } else if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      if (confirming) confirming = null;
      else oncancel?.();
    }
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<form class="space-form" onsubmit={(e) => (e.preventDefault(), save())} onkeydown={onKeydown}>
  <div class="r-ins-mode">
    <div>
      <h2>{creating ? "New space" : "Space settings"}</h2>
      <p>{creating ? "A shared collection of relics" : space.name}</p>
    </div>
    <button type="button" class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={oncancel} aria-label="Close"><Icon name="x" /></button>
  </div>

  <div class="r-ins-form">
    <label class="r-field">
      <span class="r-label">Name</span>
      <!-- svelte-ignore a11y_autofocus -->
      <span class="r-input"><input bind:value={form.name} placeholder="Platform team" autofocus={creating} /></span>
    </label>

    <div class="r-field" role="radiogroup" aria-labelledby="space-vis">
      <span class="r-label" id="space-vis">Visibility</span>
      <div class="r-options space-options">
        {#each VISIBILITY as v (v.value)}
          <label class="r-option">
            <input type="radio" class="r-radio" name="space-visibility" value={v.value} bind:group={form.visibility} />
            <b><Icon name={v.icon} />{v.label}</b>
            <small>{v.hint}</small>
          </label>
        {/each}
      </div>
    </div>

    {#if !creating}
      <div class="r-field danger-zone">
        {#if transferable}
          <span class="r-label">Transfer ownership</span>
          <span class="space-row">
            <span class="r-input r-input-sm space-pid"><input bind:value={transferTo} placeholder="New owner’s public ID" spellcheck="false" aria-label="New owner’s public ID" /></span>
            <button type="button" class="r-btn r-btn-secondary r-btn-md" disabled={!transferTo.trim() || !!confirming} onclick={() => (confirming = "transfer")}>Transfer</button>
          </span>
          {#if confirming === "transfer"}
            <div class="r-confirm">
              <b>Transfer “{space.name}” to {transferTo.trim()}?</b>
              <span>They become the owner. The current owner stays in the space as an admin.</span>
              <div class="r-confirm-actions">
                <button type="button" class="r-btn r-btn-secondary r-btn-sm" onclick={() => (confirming = null)}>Cancel</button>
                <button type="button" class="r-btn r-btn-danger r-btn-sm" onclick={transfer} disabled={busy}>{busy ? "Transferring…" : "Transfer ownership"}</button>
              </div>
            </div>
          {/if}
        {/if}

        <button type="button" class="r-btn r-btn-danger-text r-btn-md space-delete" onclick={() => (confirming = "delete")} disabled={!!confirming}>
          <Icon name="trash" />Delete space
        </button>
        {#if confirming === "delete"}
          <div class="r-confirm">
            <b>Delete “{space.name}”?</b>
            <span>The space and its member list go for everyone. The relics in it are kept. This can’t be undone.</span>
            <div class="r-confirm-actions">
              <button type="button" class="r-btn r-btn-secondary r-btn-sm" onclick={() => (confirming = null)}>Cancel</button>
              <button type="button" class="r-btn r-btn-danger r-btn-sm" onclick={remove} disabled={busy}>{busy ? "Deleting…" : "Delete space"}</button>
            </div>
          </div>
        {/if}
      </div>
    {/if}
  </div>

  <div class="r-ins-save">
    <span class="r-help space-hint">Ctrl ↵ saves</span>
    <button type="button" class="r-btn r-btn-secondary" onclick={oncancel}>Cancel</button>
    <button type="submit" class="r-btn r-btn-primary" disabled={saving || !form.name.trim()}>{saving ? "Saving…" : creating ? "Create space" : "Save"}</button>
  </div>
</form>

<style>
  .space-form {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }
  .space-options {
    grid-template-columns: repeat(2, 1fr);
  }
  .danger-zone {
    gap: var(--space-2);
    padding-top: var(--space-3);
    border-top: 1px solid var(--line);
  }
  .space-row {
    display: flex;
    gap: var(--space-1\.5);
  }
  .space-pid {
    flex: 1;
    font-family: var(--font-mono);
  }
  .space-delete {
    justify-self: start;
    padding-left: 0;
  }
  .space-hint {
    margin-right: auto;
  }
</style>
