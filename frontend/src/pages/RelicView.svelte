<script>
  // Viewing a relic: its content with the status bar under it and the inspector beside it (no
  // header; the inspector is the relic's header, actions and details). With the inspector hidden
  // (]) a floating toolbar keeps the main actions. Also shows files opened from inside archives.
  import { untrack, onDestroy } from "svelte";
  import Icon from "../lib/ui/Icon.svelte";
  import Workbench from "../lib/shell/Workbench.svelte";
  import RelicInspector from "../lib/relics/inspector/RelicInspector.svelte";
  import ContentView from "../lib/viewer/ContentView.svelte";
  import ViewerStatusBar from "../lib/viewer/ViewerStatusBar.svelte";
  import ArchiveFileInspector from "../lib/viewer/ArchiveFileInspector.svelte";
  import ForkModal from "../components/ForkModal.svelte";
  import { ViewerPrefs } from "../lib/viewer/viewerPrefs.svelte.js";
  import { InspectorPanel } from "../lib/shell/inspectorPanel.svelte.js";
  import { layout } from "../lib/shell/layout";
  import { refreshSidebar } from "../lib/shell/sidebarData";
  import { getRelic, getRelicRaw, getCommentsPaginated, createComment, updateComment, deleteComment } from "../services/api";
  import { processContent } from "../services/processors/index.js";
  import { processArchive } from "../services/processors/archiveProcessor";
  import { copyRelicContent, downloadRelic, copyToClipboard } from "../services/relicActions";
  import { getFileTypeDefinition, getSyntaxFromExtension, isBinaryType } from "../services/typeUtils";
  import { getCurrentLineNumberFragment } from "../utils/lineNumbers";
  import { session } from "../stores/session";
  import { showToast } from "../stores/toastStore";
  import { pageTitle } from "../stores/pageTitle";
  import { navigate } from "../utils/navigation";

  let { relicId, filePath = null } = $props();

  const prefs = new ViewerPrefs();
  const panel = new InspectorPanel();

  // Raw state: these hold parsed content (archive readers, PDF documents, byte arrays). Deep
  // proxies would wrap every object the parsers touch and make archives crawl; both are only
  // ever replaced whole, never mutated in place.
  let relic = $state.raw(null);
  let processed = $state.raw(null);
  let archive = $state(null); // { archiveId, archiveName, filePath } for a file inside an archive
  let error = $state(null); // HTTP status or "unknown"
  let loading = $state(true);
  let showSource = $state(false);
  let comments = $state([]);
  let forking = $state(false);
  let pdfViewer = $state(null);
  let treeRenderer = $state(null);
  let pdf = $state(null);

  // Navigating between relics reuses this page, so a slow response for the previous one is dropped.
  let gen = 0;

  async function loadRelic(id) {
    const g = ++gen;
    const data = (await getRelic(id)).data;
    const raw = await (await getRelicRaw(id)).data.arrayBuffer();
    if (g !== gen) return;
    const result = await processContent(new Uint8Array(raw), data.content_type, data.language_hint);
    if (g !== gen) return;
    relic = data;
    processed = result;
    loadComments(id, g);
  }

  async function loadArchiveFile(id, path) {
    const g = ++gen;
    const archiveRelic = (await getRelic(id)).data;
    const raw = await (await getRelicRaw(id)).data.arrayBuffer();
    const unpacked = await processArchive(new Uint8Array(raw), archiveRelic.content_type);
    const content = await unpacked.extractFile(path);
    const meta = unpacked.files.find((f) => f.path === path);
    if (!meta) throw Object.assign(new Error("File not found in archive"), { response: { status: 404 } });
    const result = await processContent(content, meta.contentType, meta.languageHint);
    if (g !== gen) return;
    relic = {
      id,
      name: meta.name,
      content_type: meta.contentType,
      language_hint: meta.languageHint,
      size_bytes: meta.size,
      created_at: archiveRelic.created_at,
      access_level: archiveRelic.access_level,
      _extractedContent: content,
    };
    archive = { archiveId: id, archiveName: archiveRelic.name, filePath: path };
    processed = result;
  }

  async function loadComments(id, g) {
    const LIMIT = 1000;
    try {
      const first = await getCommentsPaginated(id, { limit: LIMIT });
      if (g !== gen) return;
      comments = first.comments;
      for (let offset = LIMIT; offset < first.total; offset += LIMIT) {
        const page = await getCommentsPaginated(id, { limit: LIMIT, offset });
        if (g !== gen) return;
        comments = [...comments, ...page.comments];
      }
    } catch (e) {
      console.error("[RelicView] comments failed", e);
    }
  }

  $effect(() => {
    const id = relicId;
    const path = filePath;
    untrack(async () => {
      loading = true;
      error = null;
      relic = null;
      processed = null;
      archive = null;
      comments = [];
      showSource = false;
      try {
        await (path ? loadArchiveFile(id, path) : loadRelic(id));
      } catch (e) {
        console.error("[RelicView] load failed", e);
        error = e.response?.status ?? "unknown";
        if (path && !e.response) showToast(`Couldn’t open that file: ${e.message}`, "error");
      } finally {
        loading = false;
      }
    });
  });

  $effect(() => {
    if (relic) pageTitle.set(archive ? `${archive.filePath.split("/").pop()} · ${archive.archiveName || "Archive"}` : relic.name || "Untitled relic");
  });

  // A link to a line (#L12) opens text content as source, so the line is there to see.
  $effect(() => {
    if (!relic || !processed || !getCurrentLineNumberFragment()) return;
    const category = getFileTypeDefinition(relic.content_type).category;
    if (["text", "code", "markdown", "html"].includes(category)) untrack(() => (showSource = true));
  });

  // The tree view and pretty print depend on the language.
  const TREE_LANGS = new Set(["json", "yaml", "yml", "toml", "xml"]);
  const lang = $derived.by(() => {
    const meta = processed?.metadata?.language;
    const ext = getSyntaxFromExtension(relic?.name?.split(".").pop()?.toLowerCase());
    return TREE_LANGS.has(meta) ? meta : TREE_LANGS.has(ext) ? ext : meta;
  });
  const treeSupported = $derived(TREE_LANGS.has(lang));
  const formattable = $derived(lang === "json");

  // The PDF viewer keeps its own page and zoom; read them for the status bar.
  const pdfTimer = setInterval(() => {
    if (processed?.type === "pdf" && pdfViewer?.getState) pdf = pdfViewer.getState();
  }, 250);
  onDestroy(() => clearInterval(pdfTimer));

  const oncomment = {
    async create(event) {
      const { lineNumber, content, parentId } = event.detail;
      try {
        comments = [...comments, await createComment(relicId, lineNumber, content, parentId)];
        relic = { ...relic, comments_count: (relic.comments_count ?? 0) + 1 };
        showToast("Comment added", "success");
      } catch (e) {
        showToast(e.response?.data?.detail || "Couldn’t add the comment", "error");
      }
    },
    async update(event) {
      const { commentId, content } = event.detail;
      try {
        const updated = await updateComment(relicId, commentId, content);
        comments = comments.map((c) => (c.id === commentId ? updated : c));
        showToast("Comment updated", "success");
      } catch {
        showToast("Couldn’t update the comment", "error");
      }
    },
    async delete(event) {
      try {
        await deleteComment(relicId, event.detail);
        comments = comments.filter((c) => c.id !== event.detail);
        relic = { ...relic, comments_count: Math.max(0, (relic.comments_count ?? 1) - 1) };
        showToast("Comment deleted", "success");
      } catch {
        showToast("Couldn’t delete the comment", "error");
      }
    },
  };

  function onUpdated(updated) {
    const retype = updated.content_type !== relic.content_type || updated.language_hint !== relic.language_hint;
    relic = { ...relic, ...updated };
    // A new type or language re-renders the content with it.
    if (retype) loadRelic(relicId).catch(() => {});
  }

  function onDeleted() {
    refreshSidebar();
    navigate("/my-relics");
  }

  const inspectorOpen = $derived(panel.isOpen($layout.dock, true));
  const binary = $derived(relic ? isBinaryType(relic.content_type) : false);

  function onKeydown(event) {
    if (event.key === "y" && relic && !archive) {
      copyToClipboard(`${location.origin}/${relic.id}`, "Link copied");
    }
  }
</script>

{#if error}
  <div class="view-state">
    <Icon name={error === 403 ? "lock" : error === 410 ? "clock" : "file"} size={28} />
    <h1>
      {error === 403 ? "You don’t have access to this relic" : error === 404 ? "This relic doesn’t exist" : error === 410 ? "This relic has expired" : "Couldn’t load this relic"}
    </h1>
    <p>
      {#if error === 403}It’s restricted. Ask its owner to add you, using the public ID from your profile.
      {:else if error === 404}It may have been deleted, or the link is wrong.
      {:else if error === 410}Expired relics are deleted and can’t be brought back.
      {:else}Check your connection and try again.{/if}
    </p>
    <div class="view-state-actions">
      <a class="r-btn r-btn-secondary r-btn-md" href="/recent">Recent relics</a>
    </div>
  </div>
{:else if loading || !relic || !processed}
  <div class="view-state" role="status"><p>Loading…</p></div>
{:else}
  <Workbench {panel} phoneDrawer label={relic.name || "Relic"} onkeydown={onKeydown}>
    <div class="view-main">
      <ContentView
        {processed}
        {relic}
        {relicId}
        {prefs}
        {showSource}
        {comments}
        isAdmin={$session.isAdmin}
        {lang}
        {treeSupported}
        {formattable}
        bind:pdfViewer
        bind:treeRenderer
        {oncomment}
      />

      {#if !inspectorOpen}
        <div class="r-float view-float" role="toolbar" aria-label="Relic actions">
          {#if !archive}
            <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={() => copyToClipboard(`${location.origin}/${relic.id}`, "Link copied")} title="Copy link (y)" aria-label="Copy link"><Icon name="link" /></button>
            <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={() => copyRelicContent(relic.id)} disabled={binary} title="Copy content" aria-label="Copy content"><Icon name="copy" /></button>
            <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={() => downloadRelic(relic.id, relic.name, relic.content_type)} title="Download" aria-label="Download"><Icon name="download" /></button>
          {/if}
          <button class="r-btn r-btn-ghost r-btn-sm" onclick={() => panel.toggle($layout.dock)} title="Show the inspector ( ] )"><Icon name="panel" />Details</button>
        </div>
      {/if}

      <ViewerStatusBar
        {relic}
        {processed}
        {prefs}
        bind:showSource
        {archive}
        {treeSupported}
        {formattable}
        {pdf}
        {pdfViewer}
        {treeRenderer}
        {inspectorOpen}
        ontoggleinspector={() => panel.toggle($layout.dock)}
      />
    </div>

    {#snippet inspector({ close })}
      {#if archive}
        <ArchiveFileInspector file={relic} {archive} onclose={close} />
      {:else}
        <RelicInspector
          {relic}
          editable={!!relic.can_edit}
          deletable={!!relic.can_edit || $session.isAdmin}
          ontag={(tag) => navigate(`/recent?tag=${encodeURIComponent(tag)}`)}
          onfork={() => (forking = true)}
          onupdated={onUpdated}
          ondeleted={onDeleted}
          onclose={close}
        />
      {/if}
    {/snippet}
  </Workbench>
{/if}

{#if relic && !archive}
  <ForkModal bind:open={forking} {relicId} {relic} darkMode={prefs.darkMode} />
{/if}

<style>
  .view-main {
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .view-float {
    position: absolute;
    top: var(--space-2\.5);
    right: var(--space-4);
    z-index: 10;
  }
  .view-state {
    display: grid;
    justify-items: center;
    align-content: center;
    gap: var(--space-2);
    flex: 1;
    padding: var(--space-5);
    color: var(--ink-3);
    text-align: center;
  }
  .view-state h1 {
    margin: var(--space-2) 0 0;
    color: var(--ink);
    font-size: 17px;
    font-weight: 500;
  }
  .view-state p {
    margin: 0;
    max-width: 46ch;
  }
  .view-state-actions {
    display: flex;
    gap: var(--space-2);
    margin-top: var(--space-2);
  }
</style>
