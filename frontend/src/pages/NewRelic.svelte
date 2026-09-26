<script>
  // New relic: write in the editor, upload files (dropped anywhere, here or on any list page),
  // or reopen an autosaved draft. The options and the command-line help are in the inspector.
  // Ctrl+Enter creates. After creating, the link is copied and the relic opens.
  import { onMount, untrack } from "svelte";
  import Icon from "../lib/ui/Icon.svelte";
  import FontSizeSelect from "../lib/ui/FontSizeSelect.svelte";
  import PageBar from "../lib/shell/PageBar.svelte";
  import Workbench from "../lib/shell/Workbench.svelte";
  import ComposeInspector from "../lib/compose/ComposeInspector.svelte";
  import UploadList from "../lib/compose/UploadList.svelte";
  import RelicList from "../lib/relics/RelicList.svelte";
  import { Drafts } from "../lib/compose/drafts.svelte.js";
  import { takePendingUpload } from "../lib/compose/pendingUpload";
  import { createFromText, createFromFile, createZip } from "../lib/compose/create";
  import { InspectorPanel } from "../lib/shell/inspectorPanel.svelte.js";
  import { layout } from "../lib/shell/layout";
  import { refreshSidebar } from "../lib/shell/sidebarData";
  import { getFilesFromDrop } from "../services/utils/fileProcessing";
  import { shouldAutoOpen, getTypeLabel, getContentType } from "../services/typeUtils";
  import { showToast } from "../stores/toastStore";
  import { navigate } from "../utils/navigation";

  let { spaceId = null, upload: startInUpload = false } = $props();

  const panel = new InspectorPanel();
  const drafts = new Drafts();
  const MAX_SEPARATE = 100; // the old form's limit for one-relic-per-file uploads

  let mode = $state(untrack(() => (startInUpload ? "upload" : "write")));
  let form = $state({ title: "", syntax: "auto", visibility: "public", expiry: "never", tags: [], spaceId: untrack(() => spaceId) });
  let content = $state("");
  let entries = $state([]);
  let upload = $state({ count: 0, zip: true });
  let busy = $state(false);

  $effect(() => {
    upload.count = entries.length;
  });

  // Editor display settings, remembered under the old form's keys.
  const pref = (key, fallback) => {
    try {
      const v = localStorage.getItem(key);
      return v == null ? fallback : typeof fallback === "number" ? Number(v) || fallback : v === "true";
    } catch {
      return fallback;
    }
  };
  let editorPrefs = $state({
    syntax: pref("relic_form_syntax_highlighting", true),
    lineNumbers: pref("relic_form_line_numbers", true),
    fontSize: pref("relic_form_font_size", 13),
  });
  function setPref(name, key, value) {
    editorPrefs[name] = value;
    try {
      localStorage.setItem(key, String(value));
    } catch {
      // Not remembered without storage.
    }
  }

  // Files dropped on another page arrive here.
  onMount(() => {
    const pending = takePendingUpload();
    if (pending) {
      addFiles(pending.files);
      if (pending.spaceId) form.spaceId = pending.spaceId;
    }
  });

  function addFiles(files) {
    const fresh = files.map(({ file, path }) => ({ id: Math.random().toString(36).slice(2, 11), file, path: path || "", status: null }));
    entries = [...entries.filter((e) => e.status !== "done"), ...fresh];
    mode = "upload";
    if (entries.length === 1 && !form.title) form.title = entries[0].file.name.replace(/\.[^/.]+$/, "");
  }

  async function onDropFiles(dataTransfer) {
    const files = await getFilesFromDrop(dataTransfer);
    if (files.length) addFiles(files);
  }

  // Autosave the editor as a draft two seconds after the last change.
  let saveTimer;
  $effect(() => {
    const snapshot = { title: form.title, content, syntax: form.syntax, tags: [...form.tags] };
    clearTimeout(saveTimer);
    if (snapshot.content.trim()) saveTimer = setTimeout(() => drafts.save(snapshot), 2000);
    return () => clearTimeout(saveTimer);
  });

  function openDraft(draft) {
    form.title = draft.title === "Untitled draft" || draft.title === "Untitled Draft" ? "" : draft.title;
    form.syntax = draft.syntax || "auto";
    form.tags = Array.isArray(draft.tags) ? draft.tags : (draft.tags || "").split(",").map((t) => t.trim()).filter(Boolean);
    content = draft.content;
    drafts.open(draft);
    mode = "write";
    showToast("Draft opened", "success");
  }

  function deleteDraft(draft) {
    const wasOpen = draft.id === drafts.currentId;
    // Deleting the draft that's in the editor must not be undone by the pending autosave.
    if (wasOpen) clearTimeout(saveTimer);
    drafts.remove(draft.id);
    showToast(`Deleted draft “${draft.title}”`, "success", 3000, {
      label: "Undo",
      run: () => {
        drafts.restoreRemoved(draft);
        if (wasOpen) drafts.open(draft);
      },
    });
  }

  // Drafts shown as rows of the relic list (they aren't relics yet, so no owner, id or counters).
  const draftRows = $derived(
    drafts.list.map((d) => ({
      id: d.id,
      name: d.title,
      content_type: d.syntax && d.syntax !== "auto" ? getContentType(d.syntax) : "text/plain",
      language_hint: d.syntax,
      size_bytes: new Blob([d.content]).size,
      updatedAt: d.updatedAt,
      tags: Array.isArray(d.tags) ? d.tags : (d.tags || "").split(",").map((t) => t.trim()).filter(Boolean),
    }))
  );
  const draftById = (row) => drafts.list.find((d) => d.id === row.id);
  const draftActions = [
    { icon: "edit", title: "Open in the editor", run: (row) => openDraft(draftById(row)) },
    { icon: "trash", title: "Delete draft", run: (row) => deleteDraft(draftById(row)) },
  ];

  async function copyLink(relic) {
    try {
      await navigator.clipboard.writeText(`${location.origin}/${relic.id}`);
      return true;
    } catch {
      return false;
    }
  }

  async function createWritten() {
    if (!content.trim()) return showToast("Write or paste something first", "warning");
    busy = true;
    try {
      const relic = await createFromText({ content, ...form, spaceId: form.spaceId });
      if (drafts.currentId) drafts.remove(drafts.currentId);
      const copied = await copyLink(relic);
      showToast(copied ? "Created. Link copied" : "Created", "success");
      refreshSidebar();
      navigate(`/${relic.id}`);
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t create the relic", "error");
    } finally {
      busy = false;
    }
  }

  const setEntry = (id, patch) => (entries = entries.map((e) => (e.id === id ? { ...e, ...patch } : e)));

  async function createUploaded() {
    const todo = entries.filter((e) => e.status !== "done");
    if (!todo.length) return showToast("Add some files first", "warning");
    if (todo.length > MAX_SEPARATE && !upload.zip) {
      return showToast(`Up to ${MAX_SEPARATE} files can become separate relics. Zip them, or upload fewer.`, "error");
    }
    busy = true;
    const made = [];
    try {
      if (todo.length > 1 && upload.zip) {
        todo.forEach((e) => setEntry(e.id, { status: "uploading" }));
        try {
          const relic = await createZip(todo, form);
          todo.forEach((e) => setEntry(e.id, { status: "done", relic }));
          made.push(relic);
        } catch (error) {
          const reason = error.response?.data?.detail || "Upload failed";
          todo.forEach((e) => setEntry(e.id, { status: "failed", error: reason }));
        }
      } else {
        for (const e of todo) {
          setEntry(e.id, { status: "uploading", error: null });
          try {
            const relic = await createFromFile(e.file, { ...form, name: todo.length === 1 ? form.title : null });
            setEntry(e.id, { status: "done", relic });
            made.push(relic);
          } catch (error) {
            setEntry(e.id, { status: "failed", error: error.response?.data?.detail || "Upload failed" });
          }
        }
      }
    } finally {
      busy = false;
    }
    const failed = entries.filter((e) => e.status === "failed").length;
    if (made.length) refreshSidebar();
    // One relic that can be viewed: open it, like writing does. Otherwise stay on the list.
    if (made.length === 1 && !failed && shouldAutoOpen(made[0].content_type, made[0].size_bytes)) {
      const copied = await copyLink(made[0]);
      showToast(copied ? "Uploaded. Link copied" : "Uploaded", "success");
      return navigate(`/${made[0].id}`);
    }
    if (failed) showToast(`${made.length ? `${made.length} uploaded, ` : ""}${failed} failed. Try again to retry the failed ones.`, "error");
    else showToast(`Uploaded ${made.length} ${made.length === 1 ? "relic" : "relics"}`, "success");
  }

  const submit = () => (mode === "upload" ? createUploaded() : createWritten());

  function onWindowKeydown(event) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !busy) {
      event.preventDefault();
      event.stopPropagation();
      submit();
    }
  }

  const lines = $derived(content ? content.split("\n").length : 0);
  const pending = $derived(entries.filter((e) => e.status !== "done").length);
  const submitLabel = $derived(
    mode !== "upload" ? "Create relic" : pending > 1 && upload.zip ? `Create archive (${pending} files)` : pending > 1 ? `Upload ${pending} files` : "Upload"
  );
</script>

<svelte:window onkeydowncapture={onWindowKeydown} />

<Workbench
  {panel}
  phoneDrawer
  label="New relic"
  ondropfiles={onDropFiles}
  dropLabel="Drop files to upload them"
  inspector={composeInspector}
>
  {#snippet pagebar({ inspectorOpen, toggleInspector })}
    <PageBar title="New relic" {inspectorOpen} ontoggleinspector={toggleInspector}>
      {#snippet filters()}
        <span class="r-pagebar-sep"></span>
        <nav class="r-facets" aria-label="How">
          <a href="/" aria-current={mode === "write" ? "true" : undefined} onclick={(e) => (e.preventDefault(), (mode = "write"))}>Write</a>
          <a href="/?upload=1" aria-current={mode === "upload" ? "true" : undefined} onclick={(e) => (e.preventDefault(), (mode = "upload"))}>
            Upload{#if entries.length}<em>{entries.length}</em>{/if}
          </a>
          <a href="/" aria-current={mode === "drafts" ? "true" : undefined} onclick={(e) => (e.preventDefault(), (mode = "drafts"))}>
            Drafts{#if drafts.list.length}<em>{drafts.list.length}</em>{/if}
          </a>
        </nav>
      {/snippet}
    </PageBar>
  {/snippet}

  {#if mode === "write"}
    <div class="compose-editor">
      {#await import("../components/MonacoEditor.svelte")}
        <p class="compose-loading">Loading the editor…</p>
      {:then { default: MonacoEditor }}
        <MonacoEditor
          value={content}
          language={form.syntax === "auto" ? "plaintext" : form.syntax}
          readOnly={false}
          height="100%"
          showSyntaxHighlighting={editorPrefs.syntax}
          showLineNumbers={editorPrefs.lineNumbers}
          fontSize={editorPrefs.fontSize}
          darkMode={false}
          showComments={false}
          placeholder="Write or paste here, or drop files anywhere to upload them…"
          noWrapper={true}
          on:change={(e) => (content = e.detail)}
        />
      {/await}
    </div>
    <div class="r-statusbar compose-status">
      <span>{form.syntax === "auto" ? "Plain text" : getTypeLabel(getContentType(form.syntax))}</span>
      <span>{lines} {lines === 1 ? "line" : "lines"} · {content.length.toLocaleString("en-US")} characters</span>
      <span class="r-gap"></span>
      <button aria-pressed={editorPrefs.syntax} onclick={() => setPref("syntax", "relic_form_syntax_highlighting", !editorPrefs.syntax)} title="Syntax highlighting"><Icon name="palette" /></button>
      <button aria-pressed={editorPrefs.lineNumbers} onclick={() => setPref("lineNumbers", "relic_form_line_numbers", !editorPrefs.lineNumbers)} title="Line numbers"><Icon name="list" /></button>
      <FontSizeSelect value={editorPrefs.fontSize} onchange={(n) => setPref("fontSize", "relic_form_font_size", n)} />
      {#if !$layout.dock}
        <button onclick={() => panel.toggle(false)} title="Options"><Icon name="sliders" />Options</button>
      {/if}
    </div>
  {:else if mode === "drafts"}
    <RelicList
      relics={draftRows}
      local
      dateField="updatedAt"
      dateLabel="Saved"
      selectedId={drafts.currentId}
      actions={draftActions}
      emptyText="No drafts yet. What you write in the editor is saved here every few seconds, in this browser."
      onselect={(row) => openDraft(draftById(row))}
      onopen={(row) => openDraft(draftById(row))}
    />
  {:else}
    <UploadList
      {entries}
      {busy}
      onadd={addFiles}
      onremove={(entry) => (entries = entries.filter((e) => e.id !== entry.id))}
      onclear={() => (entries = [])}
    />
  {/if}

</Workbench>

{#snippet composeInspector({ close })}
  <ComposeInspector
    title={mode === "upload" ? "Upload" : "New relic"}
    subtitle={mode === "upload" ? "Files become relics with these options" : "Everything but the content can be changed later"}
    bind:form
    bind:upload
    showType={mode !== "upload"}
    {busy}
    {submitLabel}
    disabled={mode === "upload" && !pending}
    onsubmit={submit}
    savedAt={mode === "write" ? drafts.savedAt : null}
    showCli
    onclose={close}
  />
{/snippet}

<style>
  .compose-editor {
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .compose-editor :global(> *) {
    flex: 1;
    min-height: 0;
  }
  .compose-loading {
    margin: 0;
    padding: var(--space-5);
    color: var(--ink-3);
  }
  .compose-status {
    flex: none;
  }
</style>
