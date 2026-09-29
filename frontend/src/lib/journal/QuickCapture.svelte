<script>
  // Quick capture, from any page: Ctrl+J opens a strip above the tab bar with a box that adds a
  // timestamped line to today's Log in your journal ("- 14:41 text"), creating today's entry if
  // needed. Enter adds, Shift+Enter starts a new line, Esc closes and returns to where you were.
  // The strip is docked (it takes space, nothing is covered) rather than a dialog.
  import { onMount, tick } from "svelte";
  import Icon from "../ui/Icon.svelte";
  import { appendToJournal, createJournal, listMyJournals } from "../../services/api";
  import { showToast } from "../../stores/toastStore";
  import { navigate } from "../../utils/navigation";
  import { timeLocal, todayLocal } from "./dates";
  import { layout } from "../shell/layout";

  const KEY = "relic_journal_id";

  let open = $state(false);
  let text = $state("");
  let journals = $state.raw(null); // null while loading
  let targetId = $state(null);
  let busy = $state(false);
  let notice = $state(null); // { id, name } after an add
  let box = $state();
  let returnTo = null;
  let path = $state(location.pathname); // the phone button steps aside on the journal itself, where it would cover the text
  onMount(() => {
    const update = () => (path = location.pathname);
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  });
  let addWhenLoaded = false; // Enter pressed before the journals arrived

  const target = $derived(journals?.find((j) => j.id === targetId) ?? null);

  const remembered = () => {
    try {
      return localStorage.getItem(KEY);
    } catch {
      return null;
    }
  };

  async function show() {
    returnTo = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    open = true;
    notice = null;
    await tick();
    box?.focus();
    try {
      journals = await listMyJournals();
      targetId = journals.find((j) => j.id === (targetId ?? remembered()))?.id ?? journals[0]?.id ?? null;
    } catch (error) {
      console.error("[capture] journals failed", error);
      journals = [];
    }
    if (addWhenLoaded) {
      addWhenLoaded = false;
      add();
    }
  }

  function close() {
    open = false;
    if (returnTo?.isConnected) returnTo.focus();
    returnTo = null;
  }

  function onWindowKeydown(event) {
    if (event.key !== "j" || !(event.ctrlKey || event.metaKey) || event.shiftKey || event.altKey) return;
    event.preventDefault(); // Ctrl+J is the browser's downloads shortcut
    if (open && document.activeElement === box) close();
    else if (open) box?.focus();
    else show();
  }

  function fit() {
    if (!box) return;
    box.style.height = "auto";
    box.style.height = `${Math.min(box.scrollHeight, 140)}px`;
  }
  $effect(() => {
    text;
    tick().then(fit);
  });

  async function add() {
    const line = text.trim();
    if (!line || busy) return;
    if (!journals) {
      addWhenLoaded = true; // send it as soon as we know where it goes
      return;
    }
    if (!target) return;
    busy = true;
    try {
      const entry = await appendToJournal(target.id, { text: line, entryDate: todayLocal(), time: timeLocal() });
      text = "";
      notice = { id: target.id, name: target.name || "Journal" };
      try {
        localStorage.setItem(KEY, target.id);
      } catch {
        // Not remembered without storage.
      }
      // A journal page showing this journal reloads its list and today's entry.
      window.dispatchEvent(new CustomEvent("journal:changed", { detail: { journalId: target.id, entryId: entry.id } }));
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t add the note. It is still in the box.", "error");
    } finally {
      busy = false;
      box?.focus();
    }
  }

  async function startJournal() {
    busy = true;
    try {
      const made = await createJournal("Work log");
      journals = await listMyJournals();
      targetId = made.id;
      await tick();
      box?.focus();
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t create the journal", "error");
    } finally {
      busy = false;
    }
  }

  function onBoxKeydown(event) {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      add();
    } else if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close();
    }
  }
</script>

<svelte:window onkeydown={onWindowKeydown} />

<!-- Phones have no Ctrl+J: a small button above the tab bar opens the same strip. -->
{#if !open && $layout.phone && !path.startsWith("/journal")}
  <button class="qc-fab" onclick={show} aria-label="Quick note" title="Quick note"><Icon name="plus" size={20} /></button>
{/if}

{#if open}
  <section class="qc" aria-label="Quick note">
    <div class="qc-row">
      <span class="qc-mark" aria-hidden="true"><Icon name="book" size={13} /></span>
      {#if journals && journals.length === 0}
        <span class="qc-none">You don’t have a journal yet.</span>
        <button class="r-btn r-btn-primary r-btn-md" onclick={startJournal} disabled={busy}>{busy ? "Creating…" : "Start a journal"}</button>
      {:else}
        {#if journals && journals.length > 1}
          <select class="qc-select" bind:value={targetId} aria-label="Journal" title="Which journal">
            {#each journals as j (j.id)}<option value={j.id}>{j.name || "Journal"}</option>{/each}
          </select>
        {:else if target}
          <span class="qc-name" title="Your journal">{target.name || "Journal"}</span>
        {/if}
        <textarea
          bind:this={box}
          bind:value={text}
          rows="1"
          placeholder="Add to today’s log…"
          aria-label="Note"
          onkeydown={onBoxKeydown}
        ></textarea>
        <button class="r-btn r-btn-primary r-btn-md" onclick={add} disabled={busy || !text.trim() || !target}>{busy ? "Adding…" : "Add"}</button>
      {/if}
      <button class="r-btn r-btn-ghost r-btn-md r-btn-icon" onclick={close} title="Close ( Esc )" aria-label="Close quick note"><Icon name="x" /></button>
    </div>
    <p class="qc-hint" aria-live="polite">
      {#if notice}
        <span class="qc-ok"><Icon name="check" size={13} />Added to {notice.name}.</span>
        <button class="r-link" onclick={() => { navigate(`/journal/${notice.id}`); close(); }}>Open journal</button>
      {:else}
        <span><kbd class="r-kbd">↵</kbd>add</span><span><kbd class="r-kbd">⇧</kbd><kbd class="r-kbd">↵</kbd>new line</span><span><kbd class="r-kbd">Esc</kbd>close</span>
      {/if}
    </p>
  </section>
{/if}

<style>
  .qc {
    flex: none;
    padding: var(--space-2) var(--space-3) var(--space-1\.5);
    border-top: 1px solid var(--line);
    background: var(--draft);
    color: var(--ink-2);
  }
  .qc-row {
    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
  }
  .qc-mark {
    display: grid;
    flex: none;
    place-items: center;
    width: 26px;
    height: var(--control-md);
    color: var(--accent);
  }
  .qc-name,
  .qc-none {
    flex: none;
    max-width: 180px;
    overflow: hidden;
    line-height: var(--control-md);
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .qc-none {
    max-width: none;
    font-weight: 400;
  }
  .qc-select {
    flex: none;
    max-width: 180px;
    height: var(--control-md);
    padding: 0 var(--space-2);
    border: 1px solid var(--line-2);
    border-radius: var(--radius-sm);
    background: var(--surface);
    color: var(--ink);
    font: 500 13px var(--font-sans);
  }
  textarea {
    flex: 1;
    min-width: 0;
    min-height: var(--control-md);
    max-height: 140px;
    padding: 4px var(--space-2);
    border: 1px solid var(--line-2);
    border-radius: var(--radius-sm);
    outline: 0;
    background: var(--surface);
    color: var(--ink);
    font: 14px/20px var(--font-sans);
    resize: none;
  }
  textarea:focus {
    border-color: var(--accent);
    box-shadow: var(--ring-accent);
  }
  .qc-hint {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-3);
    margin: 4px 0 0 34px;
    color: var(--ink-3);
    font-size: 12px;
  }
  .qc-hint > span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .qc-ok {
    color: var(--success);
  }
  .qc-fab {
    position: fixed;
    right: var(--space-4);
    bottom: calc(56px + var(--space-4) + env(safe-area-inset-bottom, 0px));
    z-index: 40;
    display: grid;
    place-items: center;
    width: 48px;
    height: 48px;
    padding: 0;
    border: 0;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: var(--shadow-float);
    color: var(--on-accent);
    cursor: pointer;
  }
  @media (max-width: 767px) {
    .qc-row {
      flex-wrap: wrap;
    }
    textarea {
      flex-basis: 100%;
      order: 5;
    }
    .qc-hint {
      display: none;
    }
  }
</style>
