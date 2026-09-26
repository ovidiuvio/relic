<script>
  // The files waiting to upload, each with its status once uploading starts (waiting,
  // uploading, done with a link, or failed with the reason). Choose files or a whole folder,
  // or drop them anywhere on the page.
  import Icon from "../ui/Icon.svelte";
  import { compactBytes, typeBadge } from "../relics/format";
  import { copyToClipboard } from "../../services/relicActions";

  let { entries = [], busy = false, onadd, onremove, onclear } = $props();

  let fileInput = $state();
  let folderInput = $state();

  function picked(event, withPaths) {
    const files = [...event.currentTarget.files].map((file) => ({
      file,
      path: withPaths ? file.webkitRelativePath : "",
    }));
    event.currentTarget.value = "";
    if (files.length) onadd?.(files);
  }

  const STATUS = {
    waiting: { icon: "clock", label: "Waiting" },
    uploading: { icon: "upload", label: "Uploading…" },
    done: { icon: "check", label: "Done" },
    failed: { icon: "info", label: "Failed" },
  };
</script>

<div class="upload">
  <div class="upload-drop">
    <Icon name="upload" size={26} />
    <p><b>Drop files or a folder anywhere on this page</b></p>
    <p class="upload-or">
      or
      <button type="button" class="r-link" onclick={() => fileInput.click()} disabled={busy}>choose files</button>
      ·
      <button type="button" class="r-link" onclick={() => folderInput.click()} disabled={busy}>choose a folder</button>
    </p>
    <input bind:this={fileInput} type="file" multiple hidden onchange={(e) => picked(e, false)} />
    <input bind:this={folderInput} type="file" webkitdirectory hidden onchange={(e) => picked(e, true)} />
  </div>

  {#if entries.length}
    <div class="upload-head">
      <b>{entries.length} {entries.length === 1 ? "file" : "files"}</b>
      <span>{compactBytes(entries.reduce((n, e) => n + e.file.size, 0))}</span>
      <span class="r-gap"></span>
      {#if !busy}
        <button type="button" class="r-link" onclick={onclear}>{entries.every((e) => e.status === "done") ? "Upload more" : "Clear"}</button>
      {/if}
    </div>
    <ul class="upload-list">
      {#each entries as entry (entry.id)}
        {@const badge = typeBadge({ name: entry.file.name, content_type: entry.file.type })}
        {@const st = entry.status ? STATUS[entry.status] : null}
        <li class="upload-row" data-status={entry.status}>
          <span class="r-type r-t-{badge.cls}">{badge.label}</span>
          <span class="upload-name" title={entry.path || entry.file.name}>
            {#if entry.path && entry.path !== entry.file.name}<span class="upload-dir">{entry.path.slice(0, -entry.file.name.length)}</span>{/if}{entry.file.name}
          </span>
          <span class="upload-size">{compactBytes(entry.file.size)}</span>
          {#if st}
            <span class="upload-status" title={entry.error || st.label}>
              <Icon name={st.icon} size={13} />
              {#if entry.status === "done" && entry.relic}
                <button type="button" class="upload-copy" onclick={() => copyToClipboard(`${location.origin}/${entry.relic.id}`, "Link copied")} title="Copy link" aria-label="Copy link to {entry.relic.name || entry.file.name}"><Icon name="link" size={13} /></button>
                <a class="r-link" href="/{entry.relic.id}">Open</a>
              {:else}{entry.status === "failed" ? entry.error || st.label : st.label}{/if}
            </span>
          {:else if !busy}
            <button type="button" class="upload-remove" onclick={() => onremove?.(entry)} aria-label="Remove {entry.file.name}"><Icon name="x" size={13} /></button>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .upload {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-4);
    overflow-y: auto;
  }
  .upload-drop {
    display: grid;
    justify-items: center;
    gap: var(--space-1);
    padding: var(--space-5) var(--space-4);
    border: 1.5px dashed var(--line-2);
    border-radius: var(--radius-lg);
    background: var(--subtle);
    color: var(--ink-3);
    text-align: center;
  }
  .upload-drop p {
    margin: 0;
  }
  .upload-drop b {
    color: var(--ink);
    font-weight: 500;
  }
  .upload-or button {
    padding: 0;
    border: 0;
    background: none;
    cursor: pointer;
  }
  .upload-head {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--ink-3);
    font-size: 12.5px;
  }
  .upload-head b {
    color: var(--ink);
    font-weight: 500;
  }
  .upload-head button {
    padding: 0;
    border: 0;
    background: none;
    cursor: pointer;
  }
  .upload-list {
    margin: 0;
    padding: 0;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    list-style: none;
  }
  .upload-row {
    display: grid;
    grid-template-columns: 40px minmax(0, 1fr) 64px 140px;
    align-items: center;
    gap: var(--space-2\.5);
    height: 30px;
    padding: 0 var(--space-3);
    font-size: 13px;
  }
  .upload-row + .upload-row {
    border-top: 1px solid var(--line);
  }
  .upload-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .upload-dir {
    color: var(--ink-3);
  }
  .upload-size {
    color: var(--ink-3);
    font: 12.5px var(--font-mono);
    text-align: right;
  }
  .upload-status {
    display: inline-flex;
    align-items: center;
    justify-content: flex-end;
    gap: 4px;
    overflow: hidden;
    color: var(--ink-3);
    font-size: 12px;
    white-space: nowrap;
  }
  [data-status="done"] .upload-status {
    color: var(--success-ink);
  }
  [data-status="failed"] .upload-status {
    color: var(--danger);
  }
  [data-status="uploading"] .upload-status {
    color: var(--accent);
  }
  .upload-copy {
    display: grid;
    place-items: center;
    padding: 2px;
    border: 0;
    border-radius: var(--radius-xs);
    background: none;
    color: var(--ink-3);
    cursor: pointer;
  }
  .upload-copy:hover {
    background: var(--hover);
    color: var(--accent);
  }
  .upload-remove {
    justify-self: end;
    display: grid;
    place-items: center;
    padding: 2px;
    border: 0;
    border-radius: var(--radius-xs);
    background: none;
    color: var(--ink-3);
    cursor: pointer;
  }
  .upload-remove:hover {
    background: var(--danger-soft);
    color: var(--danger);
  }
</style>
