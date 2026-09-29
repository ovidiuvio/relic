<script>
  // The inspector's Journal tab: the journal itself, which is a relic. Its name, who can read it
  // (changes apply at once), the export, and deleting it. Readers who don't own it see the facts.
  import Icon from "../ui/Icon.svelte";
  import InsSection from "../relics/inspector/InsSection.svelte";
  import AccessSection from "../relics/inspector/AccessSection.svelte";
  import VisibilityField from "../relics/fields/VisibilityField.svelte";
  import { deleteRelic, exportJournal, importJournalEntries, updateRelic } from "../../services/api";
  import { copyToClipboard } from "../../services/relicActions";
  import { triggerDownload } from "../../services/utils/download";
  import { compactBytes, fullDate } from "../relics/format";
  import { showToast } from "../../stores/toastStore";
  import { pinnedJournals } from "./pinnedJournals.svelte.js";

  let {
    journal, // { id, name, access_level, entry_count, size_bytes, created_at, updated_at, can_edit, owner_name }
    readonly = false,
    onchanged, // (patch) => void
    ondeleted, // () => void
    onimported, // () => void: entries were added, so lists should reload
  } = $props();

  let name = $state(journal.name ?? "");
  let vis = $state(journal.access_level);
  let exporting = $state(false);
  let importing = $state(false);
  let picker = $state();
  let dropping = $state(false);
  let confirming = $state(false);
  let deleting = $state(false);

  // Another journal (the switcher) resets the fields.
  $effect(() => {
    journal.id;
    name = journal.name ?? "";
    vis = journal.access_level;
    confirming = false;
  });

  async function save(patch) {
    try {
      await updateRelic(journal.id, patch);
      onchanged?.(patch);
      return true;
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t save that change", "error");
      return false;
    }
  }

  async function rename() {
    const next = name.trim();
    if (!next || next === journal.name) {
      name = journal.name ?? "";
      return;
    }
    if (!(await save({ name: next }))) name = journal.name ?? "";
  }

  // Picking a visibility applies it; a failed change puts the old one back.
  $effect(() => {
    const next = vis;
    if (next === journal.access_level) return;
    save({ access_level: next }).then((ok) => {
      if (!ok) vis = journal.access_level;
    });
  });

  async function download() {
    exporting = true;
    try {
      const { blob, filename } = await exportJournal(journal.id);
      triggerDownload(blob, filename, "application/zip", `Exported ${filename}`);
    } catch (error) {
      showToast(error?.response?.status === 413 ? "This journal is too large to export in one go" : "Couldn’t export the journal", "error");
    } finally {
      exporting = false;
    }
  }

  async function addFiles(fileList) {
    const files = [...fileList].filter((f) => /\.(md|markdown|txt|zip)$/i.test(f.name));
    if (!files.length) {
      showToast("Choose Markdown files (.md, .markdown, .txt) or a .zip of them", "error");
      return;
    }
    importing = true;
    try {
      const result = await importJournalEntries(journal.id, files);
      const skipped = result.skipped.length;
      showToast(`Imported ${result.imported} ${result.imported === 1 ? "entry" : "entries"}${skipped ? `, skipped ${skipped}: ${result.skipped[0].reason}` : ""}`, skipped && !result.imported ? "error" : "success");
      if (result.imported) onimported?.();
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t import those files", "error");
    } finally {
      importing = false;
      if (picker) picker.value = "";
    }
  }

  async function remove() {
    deleting = true;
    try {
      await deleteRelic(journal.id);
      showToast(`Deleted “${journal.name || "journal"}”`);
      ondeleted?.();
    } catch (error) {
      showToast(error?.response?.data?.detail || "Couldn’t delete the journal", "error");
      deleting = false;
    }
  }

  const VISIBILITY_WARNING = {
    private: "Anyone with the link can read every entry, including the ones you write later.",
    public: "Everyone can read every entry, including the ones you write later, and the journal is listed in Recent.",
  };
</script>

<div class="r-ins-body">
  <div class="js-block">
    {#if readonly}
      <h3>{journal.name || "Journal"}</h3>
    {:else}
      <label class="r-field">
        <span class="r-label">Name</span>
        <span class="r-input"><input bind:value={name} maxlength="100" onblur={rename} onkeydown={(e) => e.key === "Enter" && e.currentTarget.blur()} aria-label="Journal name" /></span>
      </label>
    {/if}
    <div class="r-ins-actions">
      <button
        class="r-btn r-btn-secondary r-btn-md"
        aria-pressed={pinnedJournals.has(journal.id)}
        onclick={() => pinnedJournals.toggle(journal)}
        title={pinnedJournals.has(journal.id) ? "Unpin from the sidebar" : "Pin to the sidebar"}
      ><Icon name="pin" />{pinnedJournals.has(journal.id) ? "Unpin" : "Pin"}</button>
      <button class="r-btn r-btn-secondary r-btn-md" onclick={download} disabled={exporting}><Icon name="download" />{exporting ? "Exporting…" : "Export .zip"}</button>
      <button class="r-btn r-btn-secondary r-btn-md" onclick={() => copyToClipboard(`${location.origin}/journal/${journal.id}`, "Link copied")}><Icon name="link" />Copy link</button>
    </div>
  </div>

  {#if !readonly}
    <InsSection id="journal-import" title="Import" defaultOpen>
      <div class="js-block">
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="js-drop"
          class:is-over={dropping}
          ondragover={(e) => { e.preventDefault(); dropping = true; }}
          ondragleave={() => (dropping = false)}
          ondrop={(e) => { e.preventDefault(); dropping = false; addFiles(e.dataTransfer.files); }}
        >
          <Icon name="upload" size={18} />
          <span>Drop Markdown files or a .zip here</span>
          <button class="r-btn r-btn-secondary r-btn-sm" onclick={() => picker.click()} disabled={importing}>{importing ? "Importing…" : "Choose files"}</button>
          <input bind:this={picker} type="file" accept=".md,.markdown,.txt,.zip" multiple hidden onchange={(e) => addFiles(e.currentTarget.files)} />
        </div>
        <p class="js-hint">Front matter (title, date, tags) is read. A file named 2026-09-29.md becomes that day’s entry. An export from here imports back in.</p>
      </div>
    </InsSection>

    <InsSection id="journal-visibility" title="Who can read" aside={journal.access_level} defaultOpen>
      <div class="js-block">
        <VisibilityField bind:value={vis} name="journal-visibility" />
        {#if VISIBILITY_WARNING[vis]}
          <div class="r-banner r-banner-warning"><Icon name="info" /><span>{VISIBILITY_WARNING[vis]}</span></div>
        {/if}
      </div>
    </InsSection>

    {#if journal.access_level === "restricted"}
      <InsSection id="journal-people" title="People" defaultOpen>
        <AccessSection relicId={journal.id} />
      </InsSection>
    {/if}
  {/if}

  <InsSection id="journal-facts" title="Details" defaultOpen>
    <dl class="r-kv">
      <dt>Entries</dt><dd>{journal.entry_count.toLocaleString("en-US")}</dd>
      <dt>Size</dt><dd>{compactBytes(journal.size_bytes)}</dd>
      <dt>Created</dt><dd>{journal.created_at ? fullDate(journal.created_at) : "—"}</dd>
      <dt>Updated</dt><dd>{journal.updated_at ? fullDate(journal.updated_at) : "—"}</dd>
      <dt>Owner</dt><dd>{readonly ? journal.owner_name || journal.owner_public_id || "Someone else" : "You"}</dd>
      <dt>ID</dt><dd class="js-id">{journal.id}</dd>
    </dl>
  </InsSection>

  {#if !readonly}
    <InsSection id="journal-delete" title="Delete journal" defaultOpen>
      <div class="js-block">
        {#if confirming}
          <div class="r-confirm">
            <b>Delete “{journal.name || "Journal"}” and its {journal.entry_count.toLocaleString("en-US")} {journal.entry_count === 1 ? "entry" : "entries"}?</b>
            <span>Every file in it is removed. Export it first if you want a copy. This can’t be undone.</span>
            <div class="r-confirm-actions">
              <button class="r-btn r-btn-secondary r-btn-sm" onclick={() => (confirming = false)}>Keep</button>
              <button class="r-btn r-btn-danger r-btn-sm" onclick={remove} disabled={deleting}>{deleting ? "Deleting…" : "Delete journal"}</button>
            </div>
          </div>
        {:else}
          <button class="r-btn r-btn-danger-text r-btn-md js-delete" onclick={() => (confirming = true)}><Icon name="trash" />Delete journal</button>
        {/if}
      </div>
    </InsSection>
  {/if}
</div>

<style>
  .js-block {
    display: grid;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--line);
  }
  .js-block h3 {
    margin: 0;
    font-size: 17px;
    font-weight: 500;
  }
  .js-block .r-ins-actions {
    padding: 0;
  }
  .js-drop {
    display: grid;
    justify-items: center;
    gap: var(--space-2);
    padding: var(--space-4);
    border: 1px dashed var(--line-2);
    border-radius: var(--radius-md);
    color: var(--ink-2);
    text-align: center;
  }
  .js-drop.is-over {
    border-color: var(--accent);
    background: var(--accent-soft);
    color: var(--accent);
  }
  .js-hint {
    margin: 0;
    color: var(--ink-3);
    font-size: 12px;
    line-height: 1.45;
  }
  .js-id {
    font: 12px var(--font-mono);
    overflow-wrap: anywhere;
  }
  .js-delete {
    justify-self: start;
  }
</style>
