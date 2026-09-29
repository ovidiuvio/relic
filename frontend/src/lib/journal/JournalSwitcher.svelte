<script>
  // The journal's name in the page bar, as a menu: your journals with their entry counts, and a
  // form to start another. Picking one opens it (/journal/:id); the page remembers your choice.
  import Icon from "../ui/Icon.svelte";
  import { createJournal, listMyJournals } from "../../services/api";
  import { showToast } from "../../stores/toastStore";
  import { navigate } from "../../utils/navigation";
  import { pinnedJournals } from "./pinnedJournals.svelte.js";

  let {
    journal, // the open journal: { id, name, can_edit }
    canSwitch = true, // false when reading somebody else's journal (the menu is still useful for yours)
  } = $props();

  let open = $state(false);
  let el = $state();
  let btn = $state();
  let pos = $state({ top: 0, left: 0 });
  let journals = $state.raw(null); // null while loading
  let error = $state(false);
  let adding = $state(false);
  let name = $state("");
  let busy = $state(false);

  async function load() {
    error = false;
    try {
      journals = await listMyJournals();
    } catch (e) {
      console.error("[journal] list failed", e);
      error = true;
    }
  }

  // The page bar clips what overflows it, so the menu is placed against the window.
  function toggle() {
    if (!open) {
      const r = btn.getBoundingClientRect();
      pos = { top: r.bottom + 6, left: Math.max(8, Math.min(r.left, window.innerWidth - 288)) };
      adding = false;
      name = "";
      load();
    }
    open = !open;
  }

  /** Open the menu with the new-journal form showing (the sidebar's "+"). */
  export function openWithForm() {
    if (!open) toggle();
    adding = true;
  }

  function pick(id) {
    open = false;
    if (id !== journal.id) navigate(`/journal/${id}`);
  }

  async function add(event) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed || busy) return;
    busy = true;
    try {
      const made = await createJournal(trimmed);
      open = false;
      navigate(`/journal/${made.id}`);
    } catch (e) {
      showToast(e?.response?.data?.detail || "Couldn’t create the journal", "error");
    } finally {
      busy = false;
    }
  }

  function onWindowClick(event) {
    // composedPath, not contains(): a clicked button may already be gone (New journal swaps it for the form).
    if (open && !event.composedPath().includes(el)) open = false;
  }
  function onKeydown(event) {
    if (event.key === "Escape" && open) {
      open = false;
      event.stopPropagation();
      btn?.focus();
    }
  }
</script>

<svelte:window onclick={onWindowClick} onresize={() => (open = false)} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="js" bind:this={el} onkeydown={onKeydown}>
  <button bind:this={btn} class="js-btn" aria-expanded={open} aria-haspopup="true" onclick={toggle} title="Switch journal">
    <strong class="js-name">{journal.name || "Journal"}</strong><Icon name="chev" />
  </button>
  {#if open}
    <div class="js-menu" style:top="{pos.top}px" style:left="{pos.left}px">
      <p class="js-head">Your journals</p>
      {#each pinnedJournals.sorted(journals ?? []) as j (j.id)}
        <div class="js-row">
          <button class="js-item" class:is-on={j.id === journal.id} onclick={() => pick(j.id)} aria-current={j.id === journal.id ? "true" : undefined}>
            <span class="js-mark"><Icon name="book" size={11} /></span>
            <strong class="js-name">{j.name || "Journal"}</strong>
            {#if j.access_level === "public"}<Icon name="globe" size={13} />{/if}
            <em>{j.entry_count.toLocaleString("en-US")}</em>
          </button>
          <button
            class="js-pin"
            class:is-pinned={pinnedJournals.has(j.id)}
            aria-pressed={pinnedJournals.has(j.id)}
            onclick={() => pinnedJournals.toggle(j)}
            title={pinnedJournals.has(j.id) ? "Unpin: stop showing it in the sidebar" : "Pin: show it in the sidebar (only pinned journals are listed there)"}
            aria-label={pinnedJournals.has(j.id) ? `Unpin ${j.name}` : `Pin ${j.name}`}
          ><Icon name="pin" size={14} /></button>
        </div>
      {:else}
        <p class="js-empty">{error ? "Couldn’t load your journals." : journals ? "You have no journals yet." : "Loading…"}</p>
      {/each}
      <div class="js-foot">
        {#if adding}
          <form class="js-add" onsubmit={add}>
            <!-- svelte-ignore a11y_autofocus -->
            <input bind:value={name} maxlength="100" placeholder="Journal name" aria-label="New journal name" autofocus required />
            <button class="r-btn r-btn-primary r-btn-sm" disabled={busy || !name.trim()}>{busy ? "Creating…" : "Create"}</button>
          </form>
        {:else}
          <button class="js-new" onclick={() => (adding = true)}><Icon name="plus" size={14} />New journal</button>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .js {
    position: relative;
    display: inline-flex;
    min-width: 0;
  }
  .js-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    min-width: 0;
    max-width: 240px;
    height: var(--control-md);
    padding: 0 6px 0 4px;
    border: 0;
    border-radius: var(--radius-sm);
    background: none;
    color: inherit;
    font: inherit;
    letter-spacing: inherit;
    cursor: pointer;
  }
  .js-btn:hover,
  .js-btn[aria-expanded="true"] {
    background: var(--hover);
  }
  .js-btn :global(.r-icon) {
    flex: none;
    color: var(--ink-3);
  }
  .js-name {
    font-weight: inherit;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .js-menu {
    position: fixed;
    z-index: 60;
    display: grid;
    width: 280px;
    max-height: 380px;
    padding: var(--space-1) 0 0;
    overflow-y: auto;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    background: var(--surface);
    box-shadow: var(--shadow-popover);
    color: var(--ink);
    font: 13px var(--font-sans);
    letter-spacing: 0;
  }
  .js-head {
    margin: 0;
    padding: var(--space-1) var(--space-3) var(--space-1\.5);
    color: var(--ink-3);
    font: 700 10.5px var(--font-mono);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .js-row {
    position: relative;
    display: flex;
    align-items: center;
  }
  .js-pin {
    flex: none;
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    margin-right: var(--space-2);
    padding: 0;
    border: 0;
    border-radius: var(--radius-sm);
    background: none;
    color: var(--ink-4);
    cursor: pointer;
  }
  .js-pin:hover {
    background: var(--chip);
    color: var(--ink);
  }
  .js-pin.is-pinned {
    color: var(--accent);
  }
  .js-item {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex: 1;
    min-width: 0;
    padding: 6px var(--space-3);
    border: 0;
    background: none;
    color: var(--ink);
    font: inherit;
    text-align: left;
    cursor: pointer;
  }
  .js-item:hover {
    background: var(--hover);
  }
  .js-item.is-on {
    color: var(--accent);
    font-weight: 500;
  }
  .js-item :global(.r-icon) {
    flex: none;
    color: var(--ink-3);
  }
  .js-item .js-name {
    flex: 1;
    font-weight: 400;
  }
  .js-item.is-on .js-name {
    font-weight: 500;
  }
  .js-item em {
    color: var(--ink-3);
    font: 12px var(--font-mono);
    font-style: normal;
  }
  .js-mark {
    display: grid;
    flex: none;
    place-items: center;
    width: 20px;
    height: 20px;
    border-radius: 6px;
    background: var(--accent);
    color: var(--on-accent);
  }
  .js-item .js-mark :global(.r-icon) {
    color: inherit;
  }
  .js-empty {
    margin: 0;
    padding: var(--space-2) var(--space-3);
    color: var(--ink-3);
    font-size: 12.5px;
  }
  .js-foot {
    margin-top: var(--space-1);
    padding: var(--space-1\.5) var(--space-2);
    border-top: 1px solid var(--line);
    background: var(--subtle);
  }
  .js-new {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    width: 100%;
    padding: 5px var(--space-1);
    border: 0;
    border-radius: var(--radius-sm);
    background: none;
    color: var(--ink-2);
    font: inherit;
    cursor: pointer;
  }
  .js-new:hover {
    background: var(--hover);
    color: var(--ink);
  }
  .js-add {
    display: flex;
    gap: var(--space-2);
  }
  .js-add input {
    flex: 1;
    min-width: 0;
    height: var(--control-md);
    padding: 0 var(--space-2);
    border: 1px solid var(--line-2);
    border-radius: var(--radius-sm);
    background: var(--surface);
    color: var(--ink);
    font: inherit;
  }
  .js-add input:focus {
    outline: 0;
    border-color: var(--accent);
    box-shadow: var(--ring-accent);
  }
</style>
