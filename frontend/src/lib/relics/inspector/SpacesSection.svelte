<script>
  // Add this relic to a space you can edit: search your spaces, pick one, add. The API can't list
  // the spaces a relic is already in, so this only adds (and says so if it's already there).
  import Combobox from "../../ui/Combobox.svelte";
  import { spaces as spacesApi } from "../../../services/api";
  import { showToast } from "../../../stores/toastStore";
  import { refreshSidebar } from "../../shell/sidebarData";

  let { relicId } = $props();

  const EDITABLE = ["owner", "admin", "editor"];
  let options = $state([]);
  let loaded = $state(false);
  let spaceId = $state(null);
  let adding = $state(false);

  async function load() {
    try {
      const [mine, shared] = await Promise.all([
        spacesApi.list({ category: "my", sort_by: "name", sort_order: "asc", limit: 100 }),
        spacesApi.list({ category: "shared", sort_by: "name", sort_order: "asc", limit: 100 }),
      ]);
      options = [...mine.spaces, ...shared.spaces]
        .filter((s) => EDITABLE.includes(s.role))
        .map((s) => ({ value: s.id, label: `${s.name}${s.visibility === "private" ? " (private)" : ""}` }));
    } catch {
      showToast("Couldn’t load your spaces", "error");
    } finally {
      loaded = true;
    }
  }
  load();

  async function add() {
    if (!spaceId || adding) return;
    adding = true;
    try {
      await spacesApi.addRelic(spaceId, relicId);
      const name = options.find((o) => o.value === spaceId)?.label;
      showToast(`Added to ${name}`, "success");
      spaceId = null;
      refreshSidebar();
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t add it to that space", "error");
    } finally {
      adding = false;
    }
  }
</script>

{#if loaded && !options.length}
  <p class="ins-note">You don’t have a space you can add to. <a class="r-link" href="/spaces?create=1">Create a space</a></p>
{:else}
  <div class="spaces-add">
    <div class="spaces-pick"><Combobox options={options} bind:value={spaceId} placeholder={loaded ? "Find a space" : "Loading…"} /></div>
    <button class="r-btn r-btn-secondary r-btn-md" onclick={add} disabled={!spaceId || adding}>{adding ? "Adding…" : "Add"}</button>
  </div>
  <p class="ins-note spaces-hint">Private relics can only go into private spaces.</p>
{/if}

<style>
  .spaces-add {
    display: flex;
    gap: var(--space-1\.5);
  }
  .spaces-pick {
    flex: 1;
    min-width: 0;
  }
  .spaces-hint {
    margin-top: var(--space-1\.5);
  }
</style>
