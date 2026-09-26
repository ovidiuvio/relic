<script>
  // A relic's content: picks the renderer for the processed type and passes it the viewer's
  // settings and comments. The renderers themselves are unchanged from the old viewer.
  import MarkdownRenderer from "../../components/renderers/MarkdownRenderer.svelte";
  import HtmlRenderer from "../../components/renderers/HtmlRenderer.svelte";
  import CodeRenderer from "../../components/renderers/CodeRenderer.svelte";
  import ImageRenderer from "../../components/renderers/ImageRenderer.svelte";
  import CsvRenderer from "../../components/renderers/CsvRenderer.svelte";
  import ArchiveRenderer from "../../components/renderers/ArchiveRenderer.svelte";
  import ExcalidrawRenderer from "../../components/renderers/ExcalidrawRenderer.svelte";
  import RelicIndexView from "./RelicIndexView.svelte";
  import DiffRenderer from "../../components/renderers/DiffRenderer.svelte";
  import TreeRenderer from "../../components/renderers/TreeRenderer.svelte";
  import PDFViewer from "../../components/PDFViewer.svelte";
  import Icon from "../ui/Icon.svelte";
  import { downloadRelic } from "../../services/relicActions";
  import { showToast } from "../../stores/toastStore";

  let {
    processed,
    relic,
    relicId,
    prefs, // ViewerPrefs
    showSource = false,
    comments = [],
    isAdmin = false,
    lang = null, // effective language, for the tree view
    treeSupported = false,
    formattable = false,
    pdfViewer = $bindable(null),
    treeRenderer = $bindable(null),
    oncomment, // { create, update, delete } handlers taking the renderer's event
    indexView = $bindable(null), // the .rix list, so the viewer can update or remove its rows
    indexSelectedId = null, // the .rix row the viewer's inspector shows
    onindexselect, // (relic, section?) a .rix row was selected
  } = $props();

  const lineCopied = (e) => showToast(`Line ${e.detail.lineNumber} link copied`, "success");
  const toggleComments = () => prefs.toggle("comments");
</script>

<div class="content">
  {#if processed.type === "markdown"}
    <MarkdownRenderer
      {processed}
      {relicId}
      {showSource}
      showSyntaxHighlighting={prefs.syntax}
      showLineNumbers={prefs.lineNumbers}
      showComments={prefs.comments}
      fontSize={prefs.fontSize}
      {comments}
      {isAdmin}
      darkMode={prefs.darkMode}
      on:line-copied={lineCopied}
      on:createComment={oncomment.create}
      on:deleteComment={oncomment.delete}
      on:toggle-comments={toggleComments}
    />
  {:else if processed.type === "html"}
    <HtmlRenderer
      {processed}
      {relicId}
      {showSource}
      showSyntaxHighlighting={prefs.syntax}
      showLineNumbers={prefs.lineNumbers}
      showComments={prefs.comments}
      fontSize={prefs.fontSize}
      {comments}
      {isAdmin}
      darkMode={prefs.darkMode}
      on:line-copied={lineCopied}
      on:createComment={oncomment.create}
      on:updateComment={oncomment.update}
      on:deleteComment={oncomment.delete}
      on:toggle-comments={toggleComments}
    />
  {:else if processed.type === "code" || processed.type === "text"}
    {#if treeSupported && prefs.treeMode === "tree"}
      <TreeRenderer
        bind:this={treeRenderer}
        {processed}
        darkMode={prefs.darkMode}
        fontSize={prefs.fontSize}
        {lang}
        pageSize={prefs.treePageSize}
        on:parse-error={() => prefs.set("treeMode", "code")}
      />
    {:else}
      <CodeRenderer
        {processed}
        {relicId}
        showSyntaxHighlighting={prefs.syntax}
        showLineNumbers={prefs.lineNumbers}
        showComments={prefs.comments}
        fontSize={prefs.fontSize}
        {comments}
        {isAdmin}
        darkMode={prefs.darkMode}
        beautify={prefs.beautify}
        isFormattable={formattable}
        showLineFilter={prefs.lineFilter}
        on:line-copied={lineCopied}
        on:createComment={oncomment.create}
        on:updateComment={oncomment.update}
        on:deleteComment={oncomment.delete}
        on:toggle-comments={toggleComments}
      />
    {/if}
  {:else if processed.type === "image"}
    <ImageRenderer {processed} relicName={relic.name} />
  {:else if processed.type === "pdf"}
    <PDFViewer
      bind:this={pdfViewer}
      pdfDocument={processed.pdfDocument}
      metadata={processed.metadata}
      passwordRequired={processed.passwordRequired}
      {relicId}
    />
  {:else if processed.type === "csv"}
    <CsvRenderer {processed} />
  {:else if processed.type === "archive"}
    <ArchiveRenderer
      {processed}
      {relicId}
      showSyntaxHighlighting={prefs.syntax}
      showLineNumbers={prefs.lineNumbers}
      fontSize={prefs.fontSize}
      darkMode={prefs.darkMode}
      on:toggle-dark-mode={(e) => prefs.set("darkMode", e.detail)}
    />
  {:else if processed.type === "relicindex"}
    <RelicIndexView bind:this={indexView} {processed} selectedId={indexSelectedId} onselect={onindexselect} />
  {:else if processed.type === "diff"}
    <DiffRenderer
      {processed}
      {relicId}
      {showSource}
      showSyntaxHighlighting={prefs.syntax}
      showLineNumbers={prefs.lineNumbers}
      showComments={prefs.comments}
      fontSize={prefs.fontSize}
      {comments}
      {isAdmin}
      darkMode={prefs.darkMode}
      diffViewMode={prefs.diffView}
      on:line-copied={lineCopied}
      on:createComment={oncomment.create}
      on:updateComment={oncomment.update}
      on:deleteComment={oncomment.delete}
      on:toggle-comments={toggleComments}
    />
  {:else if processed.type === "excalidraw"}
    <ExcalidrawRenderer {processed} {relicId} {relic} />
  {:else}
    <div class="no-preview">
      <Icon name="file" size={28} />
      <p>There’s no preview for this type of file.</p>
      <button class="r-btn r-btn-primary r-btn-md" onclick={() => downloadRelic(relicId, relic.name, relic.content_type)}>
        <Icon name="download" />Download it
      </button>
    </div>
  {/if}
</div>

<style>
  .content {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: auto;
  }
  .no-preview {
    display: grid;
    justify-items: center;
    align-content: center;
    gap: var(--space-2\.5);
    flex: 1;
    color: var(--ink-3);
  }
  .no-preview p {
    margin: 0;
  }
</style>
