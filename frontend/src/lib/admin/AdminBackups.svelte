<script>
  // Admin · Backups: the database backups in storage, newest first. Back up now, download one,
  // or restore from one of them or from a .sql.gz file on this computer, all in the inspector.
  import Icon from "../ui/Icon.svelte";
  import DataList from "../ui/DataList.svelte";
  import PageBar from "../shell/PageBar.svelte";
  import Workbench from "../shell/Workbench.svelte";
  import BackupInspector from "./BackupInspector.svelte";
  import { PagedFeed } from "../data/PagedFeed.svelte.js";
  import { InspectorPanel } from "../shell/inspectorPanel.svelte.js";
  import { layout } from "../shell/layout";
  import { refreshAdminStats, refreshLastBackup, backupTime } from "./adminState";
  import { getAdminBackups, createAdminBackup, downloadAdminBackup } from "../../services/api";
  import { showToast } from "../../stores/toastStore";
  import { formatBytes } from "../../services/typeUtils";
  import { fullDate, relativeTime } from "../relics/format";

  const COLUMNS = [
    { key: "filename", label: "Backup", width: "minmax(0, 1fr)", mono: true },
    { key: "timestamp", label: "Taken", width: "150px", hide: "phone" },
    { key: "age", label: "Age", width: "90px", num: true, hide: "narrow" },
    { key: "size_bytes", label: "Size", width: "80px", num: true },
  ];

  let totalSize = $state(0);
  const feed = new PagedFeed(
    (p) =>
      getAdminBackups(p.limit, p.offset).then(({ data }) => {
        totalSize = data.total_size_bytes || 0;
        if (data.error) showToast("Couldn’t list the backups", "error");
        return data;
      }),
    { rows: "backups" }
  );
  feed.reset();

  const panel = new InspectorPanel();
  let selectedName = $state(null);
  let upload = $state(null); // a .sql.gz picked from this computer
  let confirm = $state(null);
  let backingUp = $state(false);
  let fileInput = $state();

  const selected = $derived(feed.items.find((b) => b.filename === selectedName) ?? null);
  $effect(() => {
    if ($layout.dock && feed.items.length && !selected) selectedName = feed.items[0].filename;
  });
  const target = $derived(upload ?? (selected ? { source: "s3", ...selected } : null));

  function select(backup) {
    upload = null;
    selectedName = backup.filename;
    confirm = null;
    if (!$layout.dock) panel.show(false);
  }

  function askRestore(backup) {
    select(backup);
    panel.show($layout.dock);
    confirm = { n: (confirm?.n ?? 0) + 1 };
  }

  async function backUpNow() {
    backingUp = true;
    try {
      const { data } = await createAdminBackup();
      if (data.success) {
        showToast("Backup created", "success");
        await feed.reload();
        selectedName = feed.items[0]?.filename ?? null;
        upload = null;
        refreshLastBackup();
      } else {
        showToast(data.message || "Backup failed", "error");
      }
    } catch (error) {
      showToast(error.response?.data?.detail || "Backup failed", "error");
    } finally {
      backingUp = false;
    }
  }

  function onPick(event) {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) return;
    if (!file.name.endsWith(".sql.gz")) {
      showToast("Choose a .sql.gz backup file", "error");
      return;
    }
    upload = { source: "upload", filename: file.name, size_bytes: file.size, file };
    panel.show($layout.dock);
  }

  function onRestored() {
    feed.reload();
    refreshAdminStats();
    refreshLastBackup();
  }

  const actions = [
    { icon: "download", title: "Download", run: (b) => downloadAdminBackup(b.filename).catch(() => showToast("Couldn’t download the backup", "error")) },
    { icon: "history", title: "Restore from this backup", run: askRestore },
  ];
</script>

<input type="file" accept=".sql.gz,.gz" class="file-input" bind:this={fileInput} onchange={onPick} />

<Workbench {panel} hasSelection={!!target} label="Backups" phoneDrawer>
  {#snippet pagebar({ inspectorOpen, toggleInspector })}
    <PageBar title="Backups" count={feed.total} {inspectorOpen} ontoggleinspector={toggleInspector}>
      {#snippet actions()}
        <button class="r-btn r-btn-ghost r-btn-md" onclick={() => fileInput.click()} title="Restore from a .sql.gz file"><Icon name="upload" />Restore from file</button>
        <button class="r-btn r-btn-secondary r-btn-md" onclick={backUpNow} disabled={backingUp}><Icon name="database" />{backingUp ? "Backing up…" : "Back up now"}</button>
      {/snippet}
    </PageBar>
  {/snippet}

  <DataList
    label="Backups"
    rows={feed.items}
    rowId={(b) => b.filename}
    columns={COLUMNS}
    loading={feed.loading}
    hasMore={feed.hasMore}
    selectedId={upload ? null : selectedName}
    {actions}
    emptyText="No backups yet."
    emptyAction={{ label: "Back up now", run: backUpNow }}
    onselect={select}
    onloadmore={() => feed.more()}
  >
    {#snippet cell(backup, c)}
      {#if c.key === "filename"}
        <Icon name="database" size={13} />{backup.filename}
      {:else if c.key === "timestamp"}
        {fullDate(backupTime(backup))}
      {:else if c.key === "age"}
        {relativeTime(backupTime(backup))}
      {:else if c.key === "size_bytes"}
        {formatBytes(backup.size_bytes)}
      {/if}
    {/snippet}
  </DataList>

  {#snippet inspector({ close })}
    <BackupInspector {target} {confirm} onrestored={onRestored} oncancelupload={() => (upload = null)} onclose={close} />
  {/snippet}

  {#snippet status()}
    <span><Icon name="database" />{feed.total == null ? "…" : `${feed.total.toLocaleString("en-US")} ${feed.total === 1 ? "backup" : "backups"}`}</span>
    <span>{formatBytes(totalSize)} in all</span>
    {#if feed.error}<span class="status-error">Couldn’t load. <button class="r-link" onclick={() => feed.reload()}>Retry</button></span>{/if}
    <span class="r-gap"></span>
    <span class="r-hints"><span><kbd class="r-kbd">]</kbd>inspector</span></span>
  {/snippet}
</Workbench>

<style>
  .file-input {
    display: none;
  }
</style>
