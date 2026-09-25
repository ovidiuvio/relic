<script>
  // The inspector for a file opened from inside an archive. It isn't a relic of its own, so its
  // actions work on the extracted file, and "Save as relic" makes it one.
  import Icon from "../ui/Icon.svelte";
  import { copyArchiveFileContent, downloadArchiveFile, viewArchiveFileRaw, fastForkArchiveFile } from "../../services/relicActions";
  import { copyToClipboard } from "../../services/relicActions";
  import { isBinaryType } from "../../services/typeUtils";
  import { typeBadge, compactBytes, fullDate } from "../relics/format";

  let { file, archive, onclose } = $props(); // file: the virtual relic; archive: { archiveId, archiveName, filePath }

  const badge = $derived(typeBadge(file));
  const binary = $derived(isBinaryType(file.content_type));
  let saving = $state(false);

  async function saveAsRelic() {
    saving = true;
    try {
      await fastForkArchiveFile(file._extractedContent, file.name, file.content_type);
    } finally {
      saving = false;
    }
  }
</script>

<aside class="r-inspector" aria-label="File details">
  <div class="r-ins-id">
    <div class="r-ins-name">
      <span class="r-badge r-t-{badge.cls}" title={badge.name}>{badge.label}</span>
      <h2>{file.name}</h2>
      {#if onclose}
        <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={onclose} aria-label="Hide inspector"><Icon name="x" /></button>
      {/if}
    </div>
    <p class="r-ins-desc">A file inside an archive. Save it as a relic to share, bookmark or comment on it.</p>

    <div class="r-ins-actions">
      <button class="r-btn r-btn-primary r-btn-md" onclick={() => copyToClipboard(location.href, "Link copied")}><Icon name="link" />Copy link</button>
      <button class="r-btn r-btn-secondary r-btn-md r-btn-icon" onclick={() => copyArchiveFileContent(file._extractedContent)} disabled={binary} title="Copy content" aria-label="Copy content"><Icon name="copy" /></button>
      <button class="r-btn r-btn-secondary r-btn-md r-btn-icon" onclick={() => viewArchiveFileRaw(file._extractedContent, file.name, file.content_type)} title="View raw" aria-label="View raw"><Icon name="raw" /></button>
      <button class="r-btn r-btn-secondary r-btn-md r-btn-icon" onclick={() => downloadArchiveFile(file._extractedContent, file.name, file.content_type)} title="Download" aria-label="Download"><Icon name="download" /></button>
      <button class="r-btn r-btn-secondary r-btn-md" onclick={saveAsRelic} disabled={saving}><Icon name="fork" />{saving ? "Saving…" : "Save as relic"}</button>
    </div>
  </div>

  <div class="r-ins-body">
    <div class="r-ins-sec">
      <dl class="r-kv">
        <dt>Archive</dt><dd><a class="r-link" href="/{archive.archiveId}" title={archive.archiveName}>{archive.archiveName || archive.archiveId.slice(0, 8)}</a></dd>
        <dt>Path</dt><dd title={archive.filePath}>{archive.filePath}</dd>
        <dt>Type</dt><dd>{badge.name}</dd>
        <dt>Size</dt><dd>{compactBytes(file.size_bytes)}</dd>
        <dt>Archive added</dt><dd>{fullDate(file.created_at)}</dd>
      </dl>
    </div>
  </div>
</aside>

<style>
  .r-inspector {
    height: 100%;
  }
  .r-ins-name h2 {
    overflow-wrap: anywhere;
  }
</style>
