<script>
  // Journal: your notes as Markdown entries in one private journal (itself a relic). The entry
  // list sits beside the document, the inspector docks at the right. Edits save on their own.
  // /journal opens your journal; /journal/:id opens one by its link (read-only unless it's yours).
  // Search comes from the navbar (?search=), tag filters from ?tag=.
  import { onDestroy, onMount, tick, untrack } from "svelte";
  import Icon from "../lib/ui/Icon.svelte";
  import Workbench from "../lib/shell/Workbench.svelte";
  import PageBar from "../lib/shell/PageBar.svelte";
  import EntryList from "../lib/journal/EntryList.svelte";
  import EntryEditor from "../lib/journal/EntryEditor.svelte";
  import EntryInspector from "../lib/journal/EntryInspector.svelte";
  import EntryFacets from "../lib/journal/EntryFacets.svelte";
  import EntryTable from "../lib/journal/EntryTable.svelte";
  import EntryTimeline from "../lib/journal/EntryTimeline.svelte";
  import EntryCalendar from "../lib/journal/EntryCalendar.svelte";
  import JournalSwitcher from "../lib/journal/JournalSwitcher.svelte";
  import { InspectorPanel } from "../lib/shell/inspectorPanel.svelte.js";
  import { PagedFeed } from "../lib/data/PagedFeed.svelte.js";
  import { layout } from "../lib/shell/layout";
  import { longDate, monthKey, todayLocal } from "../lib/journal/dates";
  import { outline } from "../lib/journal/text";
  import { linkTargets } from "../lib/journal/links";
  import { pageTitle } from "../stores/pageTitle";
  import { showToast } from "../stores/toastStore";
  import { navigate } from "../utils/navigation";
  import {
    createJournal, createJournalEntry, deleteJournalEntry, getEntryBacklinks, getJournal, getJournalDays, getJournalEntry,
    keepEntryVersion, listEntryRevisions, listJournalEntries, listMyJournals, openDailyEntry, resolveJournalLinks,
    restoreEntryRevision, updateJournalEntry,
  } from "../services/api";

  // view: null (entries beside the editor) | "list" | "timeline" | "calendar"; filter: "pinned" | "tasks"
  // entry: an entry to open (from a search result), used once.
  let { journalId = null, search = null, tag = null, view = null, filter = null, entry: entryParam = null, newjournal = null } = $props();
  // The layout is remembered: a link without ?view= opens the one you used last. The layout
  // switcher always writes ?view= (entries included), so opening an entry from the list layout
  // doesn't change what is remembered.
  const LAYOUTS = ["entries", "list", "timeline", "calendar"];
  let remembered = $state(readKey("relic_journal_view"));
  const layoutView = $derived(LAYOUTS.includes(view) ? view : LAYOUTS.includes(remembered) ? remembered : "entries");

  function readKey(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }
  const KEY_JOURNAL = "relic_journal_id";
  const KEY_VIEW = "relic_journal_view";
  const KEY_SORT = "relic_journal_sort";
  const KEY_MODE = "relic_journal_mode";
  const read = (key) => {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  };
  const write = (key, value) => {
    try {
      localStorage.setItem(key, value);
    } catch {
      // Not remembered without storage.
    }
  };

  const panel = new InspectorPanel();
  // One feed per journal, so rows loaded for another journal can never show up (or be opened) here.
  const makeFeed = (id) => new PagedFeed((params) => (id ? listJournalEntries(id, params).then((r) => r.data) : Promise.resolve({ entries: [], total: 0 })), { rows: "entries", facets: true });
  let feed = $state.raw(makeFeed(null));
  let feedFor = null;

  // "loading" | "ready" | "empty" (no journal yet) | "missing" | "error"
  let phase = $state("loading");
  let journal = $state.raw(null);
  let selectedId = $state(null);
  let entry = $state.raw(null); // the selected entry with its body, as loaded
  let draft = $state({ title: "", body: "" }); // what the editor holds now
  let saveState = $state(""); // "" | "saving" | "saved" | "error"
  // Write (live), Source (plain Markdown) or Read. The old Split view is gone: it becomes Write.
  let mode = $state(["write", "source", "read"].includes(read(KEY_MODE)) ? read(KEY_MODE) : "write");
  let editor = $state();
  let newName = $state("Work log");
  let creating = $state(false);
  let phoneOpen = $state(false); // phones show the list or the document, not both
  const savedSort = (() => {
    try {
      const v = JSON.parse(readKey(KEY_SORT) || "null");
      return ["date", "title", "words", "tasks"].includes(v?.key) && ["asc", "desc"].includes(v?.dir) ? v : null;
    } catch {
      return null;
    }
  })();
  let sort = $state(savedSort ?? { key: "date", dir: "desc" }); // the list layout's column sort, remembered
  let days = $state.raw([]); // entry counts per day, for the timeline's month strip
  let daysKey = $state(0);
  let calMonth = $state(null);
  let calDate = $state(null);
  let calReload = $state(0);
  let emptyDay = $state(null); // a calendar day with no entry, selected
  let switcher = $state();
  let insTab = $state("entry"); // the inspector's tab: the entry or the journal itself
  let resolved = $state.raw({}); // what the [[links]] in the text point at
  let backlinks = $state.raw([]); // other entries linking to the open one
  let revisions = $state.raw(null); // earlier versions of the open entry (owner only)

  const readonly = $derived(!journal?.can_edit);
  const shown = $derived(entry ? { ...entry, title: draft.title, body: draft.body } : null);

  // ---- the journal ----
  // Changing the layout or a filter re-sends every prop, so only a different journal reloads.
  let loadedFor;
  $effect(() => {
    const id = journalId;
    untrack(() => {
      if (id === loadedFor && journal) return;
      loadedFor = id;
      load(id);
    });
  });

  async function load(id) {
    // Leaving a journal (the switcher, a link) saves what was typed first, into that journal.
    if (journal) await settle();
    clearSelection();
    phase = "loading";
    try {
      if (id) {
        journal = await getJournal(id);
      } else {
        const mine = await listMyJournals();
        journal = mine.find((j) => j.id === read(KEY_JOURNAL)) ?? mine[0] ?? null;
      }
      if (!journal) {
        phase = "empty";
        return;
      }
      if (journal.can_edit) write(KEY_JOURNAL, journal.id);
      pageTitle.set(journal.name || "Journal");
      phase = "ready";
    } catch (error) {
      console.error("[journal] load failed", error);
      const status = error?.response?.status;
      phase = status === 404 ? "missing" : status === 403 ? "restricted" : "error";
    }
  }

  async function startJournal(event) {
    event.preventDefault();
    if (!newName.trim() || creating) return;
    creating = true;
    try {
      const made = await createJournal(newName.trim());
      write(KEY_JOURNAL, made.id);
      await load(null);
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t create the journal", "error");
    } finally {
      creating = false;
    }
  }

  // ---- the entry list ----
  $effect(() => {
    const id = phase === "ready" ? journal?.id : null;
    const listed = layoutView === "list";
    const params = {
      search: search || undefined,
      tag: tag || undefined,
      pinned: filter === "pinned" ? true : undefined,
      has_tasks: filter === "tasks" ? true : undefined,
      sort_by: listed ? sort.key : undefined,
      sort_order: listed ? sort.dir : undefined,
    };
    if (!id) return;
    untrack(async () => {
      if (feedFor !== id) {
        feedFor = id;
        feed = makeFeed(id);
      }
      const mine = feed;
      await mine.reset(params);
      // Another journal, or a newer search, took over while the list loaded.
      if (mine !== feed || journal?.id !== id || phase !== "ready") return;
      // An entry asked for by a search result opens first, wherever it is in the journal.
      if (wantedEntry) {
        const id = wantedEntry;
        wantedEntry = null;
        const url = new URL(location.href);
        url.searchParams.delete("entry");
        history.replaceState({}, "", url.pathname + url.search);
        await select({ id }, { open: true });
        if (entry?.id === id) return;
      }
      // Open the newest entry when nothing (or something the filter hides) is selected.
      if (mine.items.length && !mine.items.some((e) => e.id === selectedId)) select(mine.items[0]);
      else if (!mine.items.length) clearSelection();
    });
  });

  let wantedEntry = entryParam;

  // The sidebar's "+" opens the switcher's new-journal form, once the page is up.
  let wantsNewJournal = !!newjournal;
  $effect(() => {
    if (!wantsNewJournal || phase !== "ready" || !switcher) return;
    wantsNewJournal = false;
    const url = new URL(location.href);
    url.searchParams.delete("newjournal");
    history.replaceState({}, "", url.pathname + url.search);
    tick().then(() => switcher?.openWithForm());
  });

  // The timeline's month strip counts every entry of the journal, not just the loaded page.
  $effect(() => {
    const id = phase === "ready" && layoutView === "timeline" ? journal?.id : null;
    daysKey;
    if (!id) return;
    getJournalDays(id)
      .then((list) => {
        if (journal?.id === id) days = list;
      })
      .catch((error) => console.error("[journal] days failed", error));
  });
  const refreshViews = () => {
    daysKey++;
    calReload++;
  };

  // Resolve [[links]] when the set of targets in the text changes (not on every keystroke).
  const targetsKey = $derived(entry ? linkTargets(draft.body).join("\n") : "");
  $effect(() => {
    const jid = journal?.id;
    const key = targetsKey;
    if (!jid) return;
    if (!key) {
      resolved = {};
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const map = await resolveJournalLinks(jid, key.split("\n"));
        if (journal?.id === jid && targetsKey === key) resolved = map;
      } catch (error) {
        console.error("[journal] resolving links failed", error);
      }
    }, 300);
    return () => clearTimeout(timer);
  });
  const linkItems = $derived((entry ? linkTargets(draft.body) : []).map((t) => ({ target: t, res: resolved[t.toLowerCase()] ?? null })));

  async function loadBacklinks() {
    const jid = journal?.id;
    const id = entry?.id;
    if (!jid || !id || !entry.title?.trim()) {
      backlinks = [];
      return;
    }
    try {
      const list = await getEntryBacklinks(jid, id);
      if (entry?.id === id) backlinks = list;
    } catch {
      if (entry?.id === id) backlinks = [];
    }
  }
  async function loadRevisions() {
    const jid = journal?.id;
    const id = entry?.id;
    if (!jid || !id || readonly) {
      revisions = null;
      return;
    }
    try {
      const list = await listEntryRevisions(jid, id);
      if (entry?.id === id) revisions = list;
    } catch {
      if (entry?.id === id) revisions = [];
    }
  }
  // Both follow the open entry (and its title, which backlinks match on).
  $effect(() => {
    entry?.id;
    untrack(() => {
      backlinks = [];
      revisions = null;
      loadBacklinks();
      loadRevisions();
    });
  });

  async function keepVersion() {
    try {
      await settle();
      await keepEntryVersion(journal.id, entry.id);
      showToast("Version kept");
      loadRevisions();
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t keep a version", "error");
    }
  }
  async function restoreVersion(revisionId) {
    try {
      await settle();
      const saved = await restoreEntryRevision(journal.id, entry.id, revisionId);
      entry = saved;
      draft = { title: saved.title, body: saved.body };
      editorKey++; // the editor reloads its text
      feed.update({ id: saved.id, title: saved.title, excerpt: saved.excerpt, word_count: saved.word_count, tags: saved.tags });
      showToast("Version restored. The text it replaced is in History.");
      loadRevisions();
      loadBacklinks();
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t restore that version", "error");
    }
  }

  let selectGen = 0;
  async function select(summary, { open = false } = {}) {
    if (open && $layout.phone) phoneOpen = true;
    if (summary.id === selectedId && entry) return;
    await flush();
    const jid = journal?.id;
    if (!jid) return;
    selectedId = summary.id;
    const gen = ++selectGen;
    try {
      const detail = await getJournalEntry(jid, summary.id);
      if (gen !== selectGen || jid !== journal?.id) return;
      entry = detail;
      draft = { title: detail.title, body: detail.body };
      saveState = "";
      if (!$layout.dock) panel.hide();
    } catch (error) {
      if (gen !== selectGen) return;
      console.error("[journal] entry load failed", error);
      showToast("Couldn’t open that entry", "error");
    }
  }

  function clearSelection() {
    selectGen++; // a load still in flight is for an entry that is no longer wanted
    selectedId = null;
    entry = null;
    draft = { title: "", body: "" };
  }

  // ---- saving ----
  let pending = null; // { journal, id, title, body }
  let timer;
  let saving = false;

  function onchange({ title, body }) {
    if (readonly || !entry) return;
    draft = { title, body };
    pending = { journal: journal.id, id: entry.id, title, body };
    saveState = "saving";
    feed.update({ id: entry.id, title });
    clearTimeout(timer);
    timer = setTimeout(flush, 800);
  }

  async function flush() {
    clearTimeout(timer);
    if (saving || !pending) return;
    const job = pending;
    pending = null;
    saving = true;
    try {
      const saved = await updateJournalEntry(job.journal, job.id, { title: job.title, body: job.body });
      const { body: _body, created: _created, ...summary } = saved;
      feed.update(summary);
      if (entry?.id === saved.id && entry.title !== saved.title) loadBacklinks();
      if (entry?.id === saved.id) entry = { ...entry, ...summary };
      saveState = pending ? "saving" : "saved";
    } catch (error) {
      console.error("[journal] save failed", error);
      pending = pending ?? job;
      saveState = "error";
      showToast(error?.response?.data?.detail || "Couldn’t save. Your text is still here; it will retry.", "error");
    } finally {
      saving = false;
      if (pending) timer = setTimeout(flush, saveState === "error" ? 4000 : 300);
    }
  }

  async function settle() {
    // Waits for a save in flight, then saves what is left.
    for (let i = 0; i < 20 && (saving || pending); i++) {
      await flush();
      if (saving) await new Promise((r) => setTimeout(r, 100));
    }
  }

  // Quick capture (Ctrl+J, anywhere) added to this journal: show it without losing what is typed.
  let editorKey = $state(0);
  async function onCaptured(event) {
    if (!journal || event.detail?.journalId !== journal.id) return;
    await settle();
    await feed.reload();
    refreshViews();
    if (entry && entry.id === event.detail.entryId && !pending) {
      try {
        const detail = await getJournalEntry(journal.id, entry.id);
        entry = detail;
        draft = { title: detail.title, body: detail.body };
        editorKey++; // the editor reloads its text from the entry
      } catch (error) {
        console.error("[journal] refresh failed", error);
      }
    } else if (!selectedId && feed.items.length) {
      select(feed.items[0]);
    }
  }
  onMount(() => {
    window.addEventListener("journal:changed", onCaptured);
    return () => window.removeEventListener("journal:changed", onCaptured);
  });

  const onHidden = () => document.visibilityState === "hidden" && flush();
  document.addEventListener("visibilitychange", onHidden);
  onDestroy(() => {
    document.removeEventListener("visibilitychange", onHidden);
    flush();
  });

  // ---- actions ----
  async function newEntry() {
    if (readonly) return;
    await settle();
    try {
      const created = await createJournalEntry(journal.id, { title: "", body: "", entry_date: todayLocal() });
      await feed.reload();
      refreshViews();
      selectedId = created.id;
      entry = created;
      draft = { title: "", body: "" };
      saveState = "";
      emptyDay = null;
      mode = mode === "read" ? "write" : mode;
      await showEditor();
      editor?.focusTitle();
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t create the entry", "error");
    }
  }

  async function openToday() {
    if (readonly) return;
    await settle();
    try {
      const daily = await openDailyEntry(journal.id, todayLocal());
      if (daily.created) {
        await feed.reload();
        refreshViews();
      }
      emptyDay = null;
      await select(daily);
      if (mode === "read") mode = "write";
      await showEditor();
      editor?.focusBody();
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t open today’s entry", "error");
    }
  }

  async function setPinned(pinned) {
    try {
      await settle();
      const saved = await updateJournalEntry(journal.id, entry.id, { pinned });
      entry = { ...entry, pinned: saved.pinned };
      await feed.reload();
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t change the pin", "error");
    }
  }

  async function removeEntry() {
    const id = entry.id;
    const index = feed.items.findIndex((e) => e.id === id);
    pending = null;
    clearTimeout(timer);
    try {
      await deleteJournalEntry(journal.id, id);
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t delete the entry", "error");
      return;
    }
    feed.remove(id);
    refreshViews();
    const next = feed.items[Math.min(index, feed.items.length - 1)];
    selectedId = null;
    entry = null;
    if (next) await select(next);
    else clearSelection();
    showToast("Entry deleted");
  }

  // The other layouts have no editor: opening an entry goes back to the entries layout.
  async function showEditor() {
    if (layoutView !== "entries") {
      navigate(withParams({ view: "entries" }));
      await tick();
      await tick();
    }
  }

  async function openInEditor(summary) {
    if (!summary) return;
    await select(summary, { open: true });
    await showEditor();
  }

  // A row in the list or timeline: the inspector on desktop, the editor itself on phones.
  const pickRow = (summary) => ($layout.phone ? openInEditor(summary) : select(summary));

  function sortBy(key) {
    sort = sort.key === key ? { key, dir: sort.dir === "desc" ? "asc" : "desc" } : { key, dir: key === "title" ? "asc" : "desc" };
    write(KEY_SORT, JSON.stringify(sort));
  }

  function pickDay(date, list) {
    calDate = date;
    if (list.length) {
      emptyDay = null;
      select(list[0]);
    } else {
      emptyDay = date;
      clearSelection();
    }
  }

  async function openDay(date, list) {
    if (list.length) return openInEditor(list[0]);
    await createForDay(date);
  }

  async function createForDay(date) {
    if (readonly) return;
    await settle();
    try {
      const daily = await openDailyEntry(journal.id, date);
      await feed.reload();
      refreshViews();
      emptyDay = null;
      await select(daily);
      await openInEditor(daily);
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t create the entry", "error");
    }
  }

  function setView(next) {
    if (next === "calendar") {
      const date = entry?.entry_date ?? calDate ?? todayLocal();
      calDate = date;
      calMonth = monthKey(date);
    }
    remembered = next;
    write(KEY_VIEW, next);
    navigate(withParams({ view: next }));
  }

  // The journal tab renamed it or changed who can read it.
  function journalChanged(patch) {
    journal = { ...journal, ...patch };
    if (patch.name) pageTitle.set(patch.name);
  }
  // Files were imported: the lists and the counts are stale.
  async function journalImported() {
    await feed.reload();
    refreshViews();
    try {
      journal = await getJournal(journal.id);
    } catch {
      // The counts refresh on the next visit.
    }
  }
  function journalDeleted() {
    try {
      localStorage.removeItem(KEY_JOURNAL);
    } catch {
      // Nothing was remembered without storage.
    }
    // Stop asking for the deleted journal's entries before anything re-runs, then open another.
    phase = "loading";
    journal = null;
    clearSelection();
    loadedFor = null; // this reload is ours; the route effect must not repeat it
    navigate("/journal");
    load(null);
  }

  function setMode(next) {
    mode = next;
    write(KEY_MODE, next);
  }

  function gotoHeading(h) {
    editor?.goto(h, outline(draft.body).findIndex((x) => x.line === h.line));
  }

  const withParams = (changes) => {
    const params = new URLSearchParams(location.search);
    for (const [key, value] of Object.entries(changes)) value ? params.set(key, value) : params.delete(key);
    const q = params.toString();
    return location.pathname + (q ? `?${q}` : "");
  };
  const filtered = $derived(!!(search || tag || filter));
  const VIEWS = [
    ["entries", "split", "Entries and editor"],
    ["list", "list", "List"],
    ["timeline", "timeline", "Timeline"],
    ["calendar", "calendar", "Calendar"],
  ];

  function onKeydown(event) {
    if (event.key === "n" && !readonly) {
      event.preventDefault();
      newEntry();
    } else if (event.key === "t" && !readonly) {
      event.preventDefault();
      openToday();
    }
  }
</script>

{#if phase === "loading"}
  <div class="jp-note" role="status">Loading your journal…</div>
{:else if phase === "empty"}
  <div class="jp-start">
    <form class="jp-card" onsubmit={startJournal}>
      <span class="jp-mark"><Icon name="book" size={20} /></span>
      <h1>Start a journal</h1>
      <p>A journal is a relic that holds your notes as Markdown files, one per entry. It starts out restricted: only you can read it until you add people or change its visibility.</p>
      <label class="r-field">
        <span class="r-label">Name</span>
        <span class="r-input"><input bind:value={newName} maxlength="100" required /></span>
      </label>
      <button class="r-btn r-btn-primary r-btn-md" disabled={creating || !newName.trim()}>{creating ? "Creating…" : "Create journal"}</button>
    </form>
  </div>
{:else if phase === "missing" || phase === "restricted" || phase === "error"}
  <div class="jp-note" role="alert">
    {phase === "missing" ? "That journal doesn’t exist." : phase === "restricted" ? "That journal is restricted. Ask its owner to add you." : "Couldn’t load the journal."}
    <button class="r-btn r-btn-secondary r-btn-md" onclick={() => (phase === "error" ? load(journalId) : navigate("/journal"))}>{phase === "error" ? "Try again" : "Go to your journal"}</button>
  </div>
{:else}
  <Workbench {panel} hasSelection={!!entry || !!emptyDay} label="Journal" onkeydown={onKeydown}>
    {#snippet pagebar({ inspectorOpen, toggleInspector })}
      <PageBar title={journal.name || "Journal"} count={feed.total} {inspectorOpen} ontoggleinspector={toggleInspector}>
        {#snippet heading()}<JournalSwitcher bind:this={switcher} {journal} />{/snippet}
        {#snippet filters()}
          {#if search}
            <span class="r-chip-filter">{search}<button onclick={() => navigate(withParams({ search: null }))} aria-label="Clear search"><Icon name="x" /></button></span>
          {/if}
          {#if filter}
            <span class="r-chip-filter">{filter === "pinned" ? "Pinned" : "Open tasks"}<button onclick={() => navigate(withParams({ filter: null }))} aria-label="Clear filter"><Icon name="x" /></button></span>
          {/if}
          {#if tag}
            <span class="r-chip-filter">#{tag}<button onclick={() => navigate(withParams({ tag: null }))} aria-label="Clear tag filter"><Icon name="x" /></button></span>
          {/if}
        {/snippet}
        {#snippet actions()}
          {#if layoutView === "entries"}
            {#if saveState}
              <span class="jp-save" class:is-error={saveState === "error"} aria-live="polite">
                {#if saveState === "saving"}Saving…{:else if saveState === "saved"}<Icon name="check" size={13} />Saved{:else}Not saved{/if}
              </span>
            {/if}
            <div class="r-seg" role="group" aria-label="Editor view">
              {#each [["write", "Write"], ["source", "Source"], ["read", "Read"]] as [id, label]}
                <button class:is-on={mode === id} aria-pressed={mode === id} onclick={() => setMode(id)} disabled={readonly && id !== "read"}>{label}</button>
              {/each}
            </div>
          {/if}
          <div class="r-seg" role="group" aria-label="Layout">
            {#each VIEWS as [id, icon, label]}
              <button class:is-on={layoutView === id} aria-pressed={layoutView === id} onclick={() => setView(id)} title={label} aria-label={label}><Icon name={icon} /></button>
            {/each}
          </div>
          {#if !readonly}
            <button class="r-btn r-btn-secondary r-btn-md" onclick={openToday} title="Open today’s entry ( t )"><Icon name="calendar" />Today</button>
            <button class="r-btn r-btn-primary r-btn-md" onclick={newEntry} title="New entry ( n )"><Icon name="plus" />New entry</button>
          {/if}
        {/snippet}
      </PageBar>
    {/snippet}

    {#if layoutView !== "entries"}
      <div class="jp-view">
        {#if layoutView !== "calendar"}
          <EntryFacets {filter} {tag} tags={feed.facets?.tags} hrefFor={(changes) => withParams(changes)} />
        {/if}
        {#if layoutView === "list"}
          <EntryTable
            {feed}
            {selectedId}
            {sort}
            onselect={pickRow}
            onopen={openInEditor}
            onsort={sortBy}
            ontag={(name) => navigate(withParams({ tag: name, filter: null }))}
            emptyText={filtered ? "No entries match these filters." : readonly ? "This journal has no entries." : "No entries yet."}
          />
        {:else if layoutView === "timeline"}
          <EntryTimeline
            {feed}
            {days}
            {selectedId}
            onselect={pickRow}
            onopen={openInEditor}
            ontag={(name) => navigate(withParams({ tag: name, filter: null }))}
            emptyText={filtered ? "No entries match these filters." : readonly ? "This journal has no entries." : "No entries yet."}
          />
        {:else}
          <EntryCalendar journalId={journal.id} bind:month={calMonth} selectedDate={calDate} reloadKey={calReload} {filter} {tag} onpickday={pickDay} onopen={openDay} />
        {/if}
      </div>
    {:else}
    <div class="jp-panes" class:phone-open={phoneOpen}>
      <div class="jp-list">
        <EntryList
          {feed}
          selectedId={selectedId}
          onselect={(e) => select(e, { open: true })}
          ontag={(name) => navigate(withParams({ tag: name }))}
          emptyText={filtered ? "No entries match these filters." : readonly ? "This journal has no entries." : "No entries yet. Write your first one."}
          emptyAction={filtered ? { label: "Clear filters", run: () => navigate(location.pathname) } : readonly ? null : { label: "New entry", run: newEntry }}
        />
      </div>
      <div class="jp-doc">
        <button class="jp-back r-btn r-btn-ghost r-btn-md" onclick={() => (phoneOpen = false)}><Icon name="chevl" />Entries</button>
        {#key editorKey}
          <EntryEditor bind:this={editor} {entry} mode={readonly ? "read" : mode} {readonly} {onchange} oncreate={readonly ? null : newEntry} {resolved} onopenentry={(id) => openInEditor({ id })} />
        {/key}
      </div>
    </div>
    {/if}

    {#snippet inspector({ close })}
      {#if layoutView === "calendar" && emptyDay && !entry}
        <aside class="r-inspector" aria-label="Day">
          <div class="ins-empty">
            <Icon name="calendar" size={22} />
            <p>No entry on {longDate(emptyDay)}.</p>
            {#if !readonly && emptyDay <= todayLocal()}
              <button class="r-btn r-btn-primary r-btn-md" onclick={() => createForDay(emptyDay)}><Icon name="plus" />Create entry</button>
            {/if}
          </div>
        </aside>
      {:else}
        <EntryInspector entry={shown} {journal} {readonly} tab={insTab} ontab={(t) => (insTab = t)} onjournalchanged={journalChanged} onjournaldeleted={journalDeleted} onjournalimported={journalImported} links={linkItems} {backlinks} {revisions} onopenentry={(id) => openInEditor({ id })} onkeep={keepVersion} onrestore={restoreVersion} onpin={setPinned} ondelete={removeEntry} ongoto={gotoHeading} onclose={close} onopen={layoutView === "entries" ? null : () => openInEditor(feed.items.find((e) => e.id === entry?.id) ?? entry)} />
      {/if}
    {/snippet}

    {#snippet status()}
      <span><Icon name="book" />{feed.total == null ? "…" : feed.total.toLocaleString("en-US")} {feed.total === 1 ? "entry" : "entries"}</span>
      <span><Icon name={journal.access_level === "public" ? "globe" : "lock"} />{journal.access_level === "public" ? "Public" : journal.access_level === "private" ? "Private (link)" : "Restricted"}</span>
      {#if feed.error}<span class="status-error">Couldn’t load more. <button class="r-link" onclick={() => feed.reload()}>Retry</button></span>{/if}
      <span class="r-gap"></span>
      <span class="r-hints">{#if !readonly}<span><kbd class="r-kbd">n</kbd>new</span><span><kbd class="r-kbd">t</kbd>today</span>{/if}<span><kbd class="r-kbd">Ctrl</kbd><kbd class="r-kbd">J</kbd>note</span><span><kbd class="r-kbd">/</kbd>blocks</span><span><kbd class="r-kbd">]</kbd>inspector</span></span>
    {/snippet}
  </Workbench>
{/if}

<style>
  .jp-panes {
    flex: 1;
    min-height: 0;
    display: flex;
  }
  .jp-list {
    flex: none;
    width: 300px;
    min-height: 0;
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--line);
  }
  .jp-view {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .jp-doc {
    flex: 1;
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .jp-back {
    display: none;
  }
  .jp-save {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: var(--ink-3);
    font-size: 12px;
    white-space: nowrap;
  }
  .jp-save.is-error {
    color: var(--danger);
  }
  .jp-note {
    flex: 1;
    display: grid;
    place-content: center;
    justify-items: center;
    gap: var(--space-3);
    color: var(--ink-3);
  }
  .jp-start {
    flex: 1;
    display: grid;
    place-items: center;
    padding: var(--space-5);
    background: var(--subtle);
  }
  .jp-card {
    display: grid;
    gap: var(--space-3);
    width: min(420px, 100%);
    padding: 28px;
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
    background: var(--surface);
    box-shadow: var(--shadow-float);
  }
  .jp-card h1 {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }
  .jp-card p {
    margin: 0;
    color: var(--ink-2);
    line-height: 1.5;
  }
  .jp-mark {
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: var(--accent);
    color: var(--on-accent);
  }
  @media (max-width: 767px) {
    .jp-list {
      width: 100%;
      border-right: 0;
    }
    .jp-panes.phone-open .jp-list,
    .jp-panes:not(.phone-open) .jp-doc {
      display: none;
    }
    .jp-back {
      display: inline-flex;
      align-self: flex-start;
      margin: 4px 6px 0;
    }
  }
</style>
