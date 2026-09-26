<script>
  // The 28px bar under a relic: where it is and what it is on the left, the current renderer's
  // view toggles on the right (only the ones that apply), then the inspector toggle.
  import Icon from "../ui/Icon.svelte";
  import FontSizeSelect from "../ui/FontSizeSelect.svelte";
  import { compactBytes } from "../relics/format";
  import { getTypeLabel } from "../../services/typeUtils";

  let {
    relic,
    processed,
    prefs, // ViewerPrefs
    showSource = $bindable(false),
    archive = null, // { archiveId, archiveName, filePath } for a file opened from an archive
    treeSupported = false,
    formattable = false,
    pdf = null, // { currentPage, numPages, scale } while a PDF is open
    pdfViewer = null,
    treeRenderer = null,
    inspectorOpen = null, // null hides the toggle (phones)
    ontoggleinspector,
    listNav = null, // { label, path, index, count, prev, canNext, onprev, onnext } for the list this relic was opened from
  } = $props();

  const TREE_PAGES = [25, 50, 100, 250, 500];

  const type = $derived(processed?.type);
  const hasSource = $derived(type === "markdown" || type === "html" || type === "diff");
  const inTree = $derived(treeSupported && prefs.treeMode === "tree" && (type === "code" || type === "text"));
  const editorLike = $derived(
    !inTree && (type === "code" || type === "text" || type === "diff" || ((type === "markdown" || type === "html") && showSource))
  );
  const hasText = $derived(editorLike || inTree);
</script>

<div class="r-statusbar viewer-status">
  {#if listNav}
    <span class="vs-list">
      <button class="vs-step" onclick={listNav.onprev} disabled={!listNav.prev} title="Previous in {listNav.label} (k)" aria-label="Previous relic"><Icon name="chevl" /></button>
      <a href={listNav.path} title="Back to {listNav.label}">{listNav.label}</a>
      <span class="vs-pos">{listNav.index + 1} of {listNav.count}{listNav.hasMore ? "+" : ""}</span>
      <button class="vs-step" onclick={listNav.onnext} disabled={!listNav.canNext} title="Next in {listNav.label} (j)" aria-label="Next relic"><Icon name="chevr" /></button>
    </span>
  {/if}
  {#if archive}
    <a class="vs-crumb" href="/{archive.archiveId}" title="Back to the archive">
      <Icon name="archive" />{archive.archiveName || "Archive"}
    </a>
    <span class="vs-path" title={archive.filePath}>{archive.filePath}</span>
  {:else if type === "archive"}
    <span><Icon name="archive" />{processed.metadata.archiveType?.toUpperCase()} · {processed.metadata.totalFiles} files</span>
  {/if}
  <span title={relic.content_type}>{relic.language_hint && relic.language_hint !== "auto" ? relic.language_hint : getTypeLabel(relic.content_type)}</span>
  <span>{compactBytes(relic.size_bytes)}</span>
  {#if type === "pdf" && pdf?.numPages}
    <span>page {pdf.currentPage} of {pdf.numPages}</span>
  {/if}

  <span class="r-gap"></span>

  {#if hasSource}
    <div class="vs-seg" role="group" aria-label="View">
      <button aria-pressed={!showSource} onclick={() => (showSource = false)} title="Rendered preview">Preview</button>
      <button aria-pressed={showSource} onclick={() => (showSource = true)} title="Source">Source</button>
    </div>
    {#if type === "diff" && !showSource}
      <div class="vs-seg" role="group" aria-label="Diff layout">
        <button aria-pressed={prefs.diffView === "unified"} onclick={() => prefs.set("diffView", "unified")}>Unified</button>
        <button aria-pressed={prefs.diffView === "split"} onclick={() => prefs.set("diffView", "split")}><Icon name="split" />Split</button>
      </div>
    {/if}
  {/if}

  {#if treeSupported && (type === "code" || type === "text")}
    <div class="vs-seg" role="group" aria-label="View">
      <button aria-pressed={prefs.treeMode !== "tree"} onclick={() => prefs.set("treeMode", "code")}><Icon name="code" />Code</button>
      <button aria-pressed={prefs.treeMode === "tree"} onclick={() => prefs.set("treeMode", "tree")}><Icon name="tree" />Tree</button>
    </div>
  {/if}

  {#if inTree}
    <button onclick={() => treeRenderer?.expandAll()} title="Expand all"><Icon name="expand" /></button>
    <button onclick={() => treeRenderer?.collapseAll()} title="Collapse all"><Icon name="collapse" /></button>
    <label class="vs-select" title="Nodes per page">
      <select value={prefs.treePageSize} onchange={(e) => prefs.set("treePageSize", Number(e.currentTarget.value))} aria-label="Nodes per page">
        {#each TREE_PAGES as n (n)}<option value={n}>{n} / page</option>{/each}
      </select>
    </label>
  {/if}

  {#if editorLike}
    <button aria-pressed={prefs.syntax} onclick={() => prefs.toggle("syntax")} title="Syntax highlighting"><Icon name="palette" /></button>
    <button aria-pressed={prefs.lineNumbers} onclick={() => prefs.toggle("lineNumbers")} title="Line numbers"><Icon name="list" /></button>
    <button aria-pressed={prefs.comments} onclick={() => prefs.toggle("comments")} title="Comments"><Icon name="msg" /></button>
    {#if formattable}
      <button aria-pressed={prefs.beautify} onclick={() => prefs.toggle("beautify")} title="Pretty print"><Icon name="braces" /></button>
    {/if}
    {#if type === "code" || type === "text"}
      <button aria-pressed={prefs.lineFilter} onclick={() => prefs.toggle("lineFilter")} title="Filter lines"><Icon name="filter" /></button>
    {/if}
  {/if}

  {#if type === "pdf"}
    <button onclick={() => pdfViewer?.zoomOutMethod()} title="Zoom out (−)" aria-label="Zoom out">−</button>
    <button onclick={() => pdfViewer?.resetZoomMethod()} title="Reset zoom (0)">{Math.round((pdf?.scale ?? 1.5) / 1.5 * 100)}%</button>
    <button onclick={() => pdfViewer?.zoomInMethod()} title="Zoom in (+)" aria-label="Zoom in">+</button>
  {/if}

  {#if hasText || type === "archive"}
    <FontSizeSelect value={prefs.fontSize} onchange={(n) => prefs.set("fontSize", n)} />
    <button aria-pressed={prefs.darkMode} onclick={() => prefs.toggle("darkMode")} title={prefs.darkMode ? "Dark theme (on)" : "Dark theme"}><Icon name="moon" /></button>
  {/if}

  {#if inspectorOpen != null}
    <button aria-pressed={inspectorOpen} onclick={ontoggleinspector} title="Inspector ( ] )"><Icon name="panel" /></button>
  {/if}
</div>

<style>
  .viewer-status {
    flex: none;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .viewer-status > button {
    min-width: 30px;
    justify-content: center;
  }
  .vs-crumb {
    color: var(--accent);
    font-weight: 500;
    text-decoration: none;
  }
  .vs-crumb:hover {
    text-decoration: underline;
  }
  .vs-path {
    max-width: 320px;
    overflow: hidden;
    font-family: var(--font-mono);
    text-overflow: ellipsis;
  }
  .vs-seg {
    display: flex;
    gap: 0;
    padding: 0 var(--space-1\.5);
  }
  .vs-seg button {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    height: 20px;
    padding: 0 8px;
    border: 1px solid var(--line-2);
    background: var(--surface);
    color: var(--ink-3);
    font: 500 11.5px var(--font-sans);
    cursor: pointer;
  }
  .vs-seg button + button {
    border-left: 0;
  }
  .vs-seg button:first-child {
    border-radius: var(--radius-xs) 0 0 var(--radius-xs);
  }
  .vs-seg button:last-child {
    border-radius: 0 var(--radius-xs) var(--radius-xs) 0;
  }
  .vs-seg button[aria-pressed="true"] {
    background: var(--accent-soft);
    color: var(--accent);
  }
  .vs-seg :global(.r-icon) {
    width: 12px;
    height: 12px;
  }
  .vs-select select {
    padding: 0 2px;
    border: 0;
    background: transparent;
    color: inherit;
    font: inherit;
    cursor: pointer;
  }
  .vs-select select:focus {
    box-shadow: none;
  }
  .vs-list {
    gap: 2px !important;
    padding: 0 var(--space-1) !important;
  }
  .vs-list a {
    max-width: 180px;
    overflow: hidden;
    color: inherit;
    text-decoration: none;
    text-overflow: ellipsis;
  }
  .vs-list a:hover {
    color: var(--accent);
    text-decoration: underline;
  }
  .vs-pos {
    margin: 0 2px 0 6px;
    color: var(--ink-3);
    font-family: var(--font-mono);
  }
  .vs-step {
    display: grid;
    place-items: center;
    width: 22px;
    height: 22px;
    padding: 0;
    border: 0;
    border-radius: var(--radius-xs);
    background: none;
    color: var(--ink-2);
    cursor: pointer;
  }
  .vs-step:hover:not(:disabled) {
    background: var(--hover);
    color: var(--accent);
  }
  .vs-step:disabled {
    opacity: 0.35;
    cursor: default;
  }
</style>
