<script>
  // A database backup in the admin inspector: its details, Download, and Restore. Restoring
  // replaces every row in the database, so the confirmation asks for RESTORE to be typed; the
  // restore's logs then show here, to copy, download or keep as a restricted relic.
  // `target` is a listed backup ({ source: "s3", filename, timestamp, size_bytes }) or a file
  // picked from this computer ({ source: "upload", filename, size_bytes, file }).
  import Icon from "../ui/Icon.svelte";
  import AdminInspector from "./AdminInspector.svelte";
  import InsSection from "../relics/inspector/InsSection.svelte";
  import { downloadAdminBackup, restoreAdminBackup, restoreFromUpload, createRelic } from "../../services/api";
  import { copyToClipboard } from "../../services/relicActions";
  import { triggerDownload } from "../../services/utils/download";
  import { showToast } from "../../stores/toastStore";
  import { formatBytes } from "../../services/typeUtils";
  import { fullDate, relativeTime } from "../relics/format";

  let {
    target = null,
    confirm = null, // { n } from the row's Restore action
    onrestored, // () after a restore finishes (the list reloads)
    oncancelupload, // () drop a picked file
    onclose = null,
  } = $props();

  let confirming = $state(false);
  let typed = $state("");
  let restoring = $state(false);
  let logs = $state(null); // { filename, log, stdout, stderr, failed }
  let downloading = $state(false);

  // A picked file opens straight at the confirmation; a different backup starts closed. The list
  // reloads after a restore (new row objects, same file), which keeps the logs showing.
  let shownFile = null;
  $effect(() => {
    const key = target ? `${target.source}:${target.filename}` : null;
    if (key === shownFile) return;
    shownFile = key;
    confirming = target?.source === "upload";
    typed = "";
    logs = null;
  });
  $effect(() => {
    if (!confirm || !target) return;
    confirm.n;
    confirming = true;
  });

  const isUpload = $derived(target?.source === "upload");

  async function download() {
    downloading = true;
    try {
      await downloadAdminBackup(target.filename);
    } catch (error) {
      showToast("Couldn’t download the backup", "error");
    } finally {
      downloading = false;
    }
  }

  async function restore() {
    restoring = true;
    const filename = target.filename;
    try {
      const { data } = isUpload ? await restoreFromUpload(target.file) : await restoreAdminBackup(filename);
      logs = { filename, log: data.log || "", stdout: data.stdout || "", stderr: data.stderr || "", failed: false };
      showToast("Database restored", "success");
    } catch (error) {
      const detail = error.response?.data?.detail || "Restore failed";
      logs = { filename, log: "", stdout: "", stderr: detail, failed: true };
      showToast(detail, "error");
    } finally {
      restoring = false;
      confirming = false;
      typed = "";
      onrestored?.();
    }
  }

  function fullLog() {
    const parts = [];
    if (logs.log) parts.push(`=== Process log ===\n${logs.log}`);
    if (logs.stdout) parts.push(`=== psql output ===\n${logs.stdout}`);
    if (logs.stderr) parts.push(`=== Errors and warnings ===\n${logs.stderr}`);
    return parts.join("\n\n");
  }

  const logName = () => `restore-log-${logs.filename}-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.txt`;

  async function saveAsRelic() {
    const name = logName();
    try {
      const file = new File([fullLog()], name, { type: "text/plain" });
      const { data } = await createRelic({ file, name, access_level: "restricted" });
      showToast("Logs saved as a restricted relic", "success");
      window.open(`/${data.id}`, "_blank", "noopener");
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t save the logs", "error");
    }
  }
</script>

<AdminInspector
  label="Backup details"
  icon={isUpload ? "upload" : "database"}
  badgeClass="r-t-data"
  title={logs ? (logs.failed ? "Restore failed" : "Restore complete") : target ? target.filename : null}
  titleClass="backup-title"
  emptyText="Select a backup to download or restore it."
  {onclose}
>
  {#snippet actions()}
    {#if logs}
      <button class="r-btn r-btn-secondary r-btn-md" onclick={() => copyToClipboard(fullLog(), "Logs copied")}><Icon name="copy" />Copy</button>
      <button class="r-btn r-btn-secondary r-btn-md" onclick={() => triggerDownload(fullLog(), logName(), "text/plain")}><Icon name="download" />Download</button>
      <button class="r-btn r-btn-secondary r-btn-md" onclick={saveAsRelic}><Icon name="file" />Save as relic</button>
      <button class="r-btn r-btn-ghost r-btn-md" onclick={() => (logs = null)}>Done</button>
    {:else if isUpload}
      <button class="r-btn r-btn-secondary r-btn-md" onclick={oncancelupload} disabled={restoring}>Choose another backup</button>
    {:else}
      <button class="r-btn r-btn-primary r-btn-md" onclick={download} disabled={downloading}><Icon name="download" />{downloading ? "Downloading…" : "Download"}</button>
      <button class="r-btn r-btn-danger-text r-btn-md" onclick={() => (confirming = true)} disabled={confirming || restoring}><Icon name="history" />Restore</button>
    {/if}
  {/snippet}
  {#snippet meta()}
    {#if logs}
      <span class="r-mono">{logs.filename}</span>
    {:else}
      {#if isUpload}<span class="r-pill"><Icon name="upload" />From this computer</span>{:else}<span>{relativeTime(target.timestamp)}</span>{/if}
      <span>{formatBytes(target.size_bytes)}</span>
    {/if}
  {/snippet}

  {#if logs}
    {#if logs.log}
      <InsSection id="admin-restore-log" title="Process log" defaultOpen><pre class="ins-log">{logs.log}</pre></InsSection>
    {/if}
    {#if logs.stdout}
      <InsSection id="admin-restore-stdout" title="psql output" defaultOpen><pre class="ins-log">{logs.stdout}</pre></InsSection>
    {/if}
    {#if logs.stderr}
      <InsSection id="admin-restore-stderr" title="Errors and warnings" defaultOpen><pre class="ins-log is-error">{logs.stderr}</pre></InsSection>
    {/if}
    {#if !logs.log && !logs.stdout && !logs.stderr}<p class="ins-note ins-pad">The restore produced no output.</p>{/if}
  {:else}
    {#if confirming}
      <div class="r-confirm ins-pad-confirm">
        <b>Restore the database from {target.filename}?</b>
        <span>
          Everything in the database now is replaced with this backup’s contents{#if !isUpload}, from {fullDate(target.timestamp)}{/if}.
          Open connections are closed; the service stays up and shows the restored data straight away. This can’t be undone.
        </span>
        <label class="restore-type">
          <span>Type <b>RESTORE</b> to confirm</span>
          <span class="r-input r-input-sm"><input bind:value={typed} autocomplete="off" spellcheck="false" disabled={restoring} /></span>
        </label>
        <div class="r-confirm-actions">
          <button class="r-btn r-btn-secondary r-btn-sm" onclick={() => (isUpload ? oncancelupload?.() : (confirming = false))} disabled={restoring}>Cancel</button>
          <button class="r-btn r-btn-danger r-btn-sm" onclick={restore} disabled={typed !== "RESTORE" || restoring}>{restoring ? "Restoring…" : "Restore database"}</button>
        </div>
      </div>
    {/if}

    <InsSection id="admin-backup-details" title="Details" defaultOpen>
      <dl class="r-kv">
        <dt>File</dt><dd class="r-mono" title={target.filename}>{target.filename}</dd>
        {#if !isUpload}<dt>Taken</dt><dd>{fullDate(target.timestamp)}</dd>{/if}
        <dt>Size</dt><dd>{formatBytes(target.size_bytes)}</dd>
        <dt>Stored</dt><dd>{isUpload ? "This computer" : "Backup storage (S3)"}</dd>
      </dl>
    </InsSection>
  {/if}
</AdminInspector>

<style>
  :global(.r-ins-name h2.backup-title) {
    font-family: var(--font-mono);
    font-size: 14px;
  }
  .ins-pad-confirm {
    margin: var(--space-3) var(--space-4) 0;
  }
  .ins-pad {
    padding: var(--space-3) var(--space-4);
  }
  .restore-type {
    display: grid;
    gap: 4px;
  }
  .restore-type .r-input {
    background: var(--surface);
  }
  .restore-type input {
    font-family: var(--font-mono);
  }
  :global(.ins-log.is-error) {
    color: var(--night-amber);
  }
</style>
