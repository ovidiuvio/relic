<script>
  // The relic inspector's "In your journals": the entries in your own journals that link to or
  // embed this relic, with the heading each sits under (only you see this), and a way to write one.
  import Icon from "../ui/Icon.svelte";
  import { createJournalEntry, getJournalMentions } from "../../services/api";
  import { showToast } from "../../stores/toastStore";
  import { navigate } from "../../utils/navigation";
  import { currentJournalId } from "./current";
  import { longDate, todayLocal } from "./dates";

  let { relic } = $props(); // { id, name }

  let entries = $state.raw(null); // null while loading
  let failed = $state(false);
  let busy = $state(false);

  $effect(() => {
    const id = relic.id;
    entries = null;
    failed = false;
    getJournalMentions(id)
      .then((list) => {
        if (id === relic.id) entries = list;
      })
      .catch(() => {
        if (id === relic.id) failed = true;
      });
  });

  async function writeAbout() {
    busy = true;
    try {
      const journalId = await currentJournalId();
      if (!journalId) {
        showToast("Start a journal first", "info");
        navigate("/journal");
        return;
      }
      const made = await createJournalEntry(journalId, { title: relic.name || "", body: `![[${relic.id}]]\n\n`, entry_date: todayLocal() });
      navigate(`/journal/${journalId}?view=entries&entry=${made.id}`);
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t create the entry", "error");
    } finally {
      busy = false;
    }
  }
</script>

<div class="ms">
  {#if failed}
    <p class="ins-note">Couldn’t load your journal entries.</p>
  {:else if entries === null}
    <p class="ins-note">Loading…</p>
  {:else}
    {#each entries as e (e.id)}
      <a class="ms-row" href="/journal/{e.journal_id}?view=entries&entry={e.id}">
        <Icon name="book" size={14} />
        <span>{e.title || "Untitled"}<small>{e.journal_name} · {longDate(e.entry_date)}{e.section ? ` · under ${e.section}` : ""}</small></span>
      </a>
    {:else}
      <p class="ins-note">No entry in your journals mentions this yet.</p>
    {/each}
  {/if}
  <button class="r-btn r-btn-secondary r-btn-md ms-write" onclick={writeAbout} disabled={busy}><Icon name="plus" />Write about this relic</button>
</div>

<style>
  .ms {
    display: grid;
    gap: 2px;
    padding: 0 var(--space-4) var(--space-3);
  }
  .ms-row {
    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
    padding: 5px 6px;
    margin-inline: -6px;
    border-radius: var(--radius-sm);
    color: var(--ink);
    text-decoration: none;
  }
  .ms-row:hover {
    background: var(--hover);
  }
  .ms-row :global(.r-icon) {
    flex: none;
    margin-top: 3px;
    color: var(--ink-3);
  }
  .ms-row span {
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .ms-row small {
    display: block;
    color: var(--ink-3);
    font-size: 11px;
  }
  .ms-write {
    justify-self: start;
    margin-top: var(--space-2);
  }
  .ins-note {
    margin: 0;
    color: var(--ink-3);
    font-size: 12.5px;
  }
</style>
