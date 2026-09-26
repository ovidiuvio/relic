<script>
  import { navigate } from '../../utils/navigation';
  import { onDestroy } from 'svelte';
  import { processContent } from '../../services/processors/index.js';
  import CodeRenderer from './CodeRenderer.svelte';
  import ImageRenderer from './ImageRenderer.svelte';
  import MarkdownRenderer from './MarkdownRenderer.svelte';
  import HtmlRenderer from './HtmlRenderer.svelte';
  import CsvRenderer from './CsvRenderer.svelte';
  import ExcalidrawRenderer from './ExcalidrawRenderer.svelte';
  import DiffRenderer from './DiffRenderer.svelte';
  import PDFViewer from '../PDFViewer.svelte';
  import TreeRenderer from './TreeRenderer.svelte';
  import { createEventDispatcher } from 'svelte';
  import { getFileTypeDefinition, getSyntaxFromExtension } from '../../services/typeUtils.js';
  import { triggerDownload } from '../../services/utils/download';
  import Icon from '../../lib/ui/Icon.svelte';
  import { compactBytes } from '../../lib/relics/format';
  import { showToast } from '../../stores/toastStore';

  export let processed
  export let relicId
  export let showSyntaxHighlighting = true
  export let showLineNumbers = true
  export let fontSize = 13
  export let darkMode = true

  const dispatch = createEventDispatcher()

  let selectedFile = null
  let previewedFile = null
  let loading = false
  let error = null
  let expandedDirs = new Set(['', '/']) // Support both empty string and '/' for root

  // Resizable panel state
  let sidebarWidth = parseInt(localStorage.getItem('archiveSidebarWidth') || '400')
  let isDragging = false
  let containerRef
  let treeRendererRef = null

  let treeViewMode = (() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("relic_viewer_tree_mode") ?? "code";
    }
    return "code";
  })();

  let treePageSize = (() => {
    if (typeof window !== "undefined") {
      const saved = parseInt(localStorage.getItem("relic_viewer_tree_page_size"), 10);
      return isNaN(saved) ? 100 : saved;
    }
    return 100;
  })();

  $: if (typeof window !== "undefined") {
    localStorage.setItem("relic_viewer_tree_mode", treeViewMode);
  }

  $: if (typeof window !== "undefined") {
    localStorage.setItem("relic_viewer_tree_page_size", treePageSize.toString());
  }

  const TREE_LANGS = new Set(['json', 'yaml', 'yml', 'toml', 'xml'])
  let effectiveLang = null
  $: {
    if (previewedFile) {
      const metaLang = previewedFile.processed?.metadata?.language
      const nameExt = previewedFile.name?.split('.').pop()?.toLowerCase()
      const extLang = getSyntaxFromExtension(nameExt)
      effectiveLang = TREE_LANGS.has(metaLang) ? metaLang : (TREE_LANGS.has(extLang) ? extLang : metaLang)
    } else {
      effectiveLang = null
    }
  }
  $: isTreeSupported = TREE_LANGS.has(effectiveLang)
  $: isFormattable = effectiveLang === 'json'

  // Handle resize divider drag
  function startDrag(e) {
    isDragging = true
    e.preventDefault()
  }

  function handleDrag(e) {
    if (!isDragging || !containerRef) return

    const containerRect = containerRef.getBoundingClientRect()
    const newWidth = Math.max(200, Math.min(e.clientX - containerRect.left, containerRect.width - 300))
    sidebarWidth = newWidth
    localStorage.setItem('archiveSidebarWidth', newWidth.toString())
  }

  function stopDrag() {
    isDragging = false
  }

  // Handle keyboard resize (accessibility)
  function handleKeydown(e) {
    if (e.key === 'ArrowLeft') {
      sidebarWidth = Math.max(200, sidebarWidth - 20)
      localStorage.setItem('archiveSidebarWidth', sidebarWidth.toString())
      e.preventDefault()
    } else if (e.key === 'ArrowRight') {
      const maxWidth = containerRef ? containerRef.getBoundingClientRect().width - 300 : 800
      sidebarWidth = Math.min(maxWidth, sidebarWidth + 20)
      localStorage.setItem('archiveSidebarWidth', sidebarWidth.toString())
      e.preventDefault()
    }
  }

  // Attach global listeners for drag
  $: if (typeof window !== 'undefined') {
    if (isDragging) {
      window.addEventListener('mousemove', handleDrag)
      window.addEventListener('mouseup', stopDrag)
    } else {
      window.removeEventListener('mousemove', handleDrag)
      window.removeEventListener('mouseup', stopDrag)
    }
  }

  // Cleanup on component destroy
  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('mousemove', handleDrag)
      window.removeEventListener('mouseup', stopDrag)
    }
  })

  // Toggle directory expansion
  function toggleDirectory(path) {
    if (expandedDirs.has(path)) {
      expandedDirs.delete(path)
    } else {
      expandedDirs.add(path)
    }
    expandedDirs = expandedDirs
  }

  // Select and preview a file inline (no navigation)
  async function selectFile(file) {
    if (file.type === 'directory') {
      toggleDirectory(file.path)
      return
    }

    selectedFile = file
    previewedFile = null
    loading = true
    error = null

    try {
      // Extract the file from the archive
      const content = await processed.extractFile(file.path)

      // Process the extracted content using existing processors
      const processedContent = await processContent(
        content,
        file.contentType,
        file.languageHint
      )

      previewedFile = {
        ...file,
        processed: processedContent
      }
    } catch (err) {
      console.error('Error extracting file:', err)
      error = err.message
    } finally {
      loading = false
    }
  }

  // Download individual file
  async function downloadFile(file) {
    try {
      const content = await processed.extractFile(file.path)
      triggerDownload(content, file.name, file.contentType)
    } catch (err) {
      console.error('Error downloading file:', err)
      showToast(`Couldn’t extract ${file.name}: ${err.message}`, 'error')
    }
  }

  // Open file in full viewer mode (navigates to dedicated URL)
  function openInFullView(file) {
    const newUrl = `/${relicId}/${file.path}`
    navigate(newUrl);
  }

  // Render file tree recursively
  function renderTree(node, depth = 0) {
    const nodePath = node.path || ''
    return {
      node,
      depth,
      isExpanded: expandedDirs.has(nodePath) || expandedDirs.has('/'),
      children: node.children || []
    }
  }

  // Flatten tree for rendering
  function flattenTree(node, depth = 0, result = []) {
    const item = renderTree(node, depth)
    result.push(item)

    if (item.isExpanded && item.children.length > 0) {
      item.children.forEach(child => flattenTree(child, depth + 1, result))
    }

    return result
  }

  $: flatTree = flattenTree(processed.fileTree)

  // A file's icon and colour, from the design system's icons and type colours.
  const EXT_KIND = {
    code: ['js', 'ts', 'jsx', 'tsx', 'py', 'java', 'cpp', 'c', 'h', 'go', 'rs', 'rb', 'php', 'css', 'scss', 'sh', 'sql', 'swift', 'kt'],
    data: ['json', 'xml', 'yaml', 'yml', 'toml', 'csv', 'xlsx', 'xls'],
    doc: ['md', 'txt', 'log', 'pdf', 'rst'],
    web: ['html', 'htm', 'svg'],
    image: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'ico'],
    archive: ['zip', 'tar', 'gz', 'tgz', 'bz2', 'xz', '7z'],
  }
  const KIND_ICON = { code: 'code', data: 'braces', doc: 'file', web: 'code', image: 'image', archive: 'archive' }

  function fileIcon(node) {
    if (node.type === 'directory') return { name: 'folder', color: 'var(--ink-3)' }
    const ext = node.name.split('.').pop()?.toLowerCase()
    if (ext === 'diff' || ext === 'patch') return { name: 'split', color: 'var(--type-code)' }
    if (ext === 'csv' || ext === 'xlsx' || ext === 'xls') return { name: 'table', color: 'var(--type-data)' }
    for (const [kind, exts] of Object.entries(EXT_KIND)) {
      if (exts.includes(ext)) return { name: KIND_ICON[kind], color: `var(--type-${kind})` }
    }
    return { name: 'file', color: 'var(--ink-3)' }
  }

  $: previewType = previewedFile?.processed?.type
  $: isTextLike = previewType === 'code' || previewType === 'text'
  $: fileCount = flatTree.filter((i) => i.node.type === 'file').length
</script>

<div class="arc" bind:this={containerRef} style:user-select={isDragging ? 'none' : null}>
  <nav class="arc-side" style:width="{sidebarWidth}px" aria-label="Files in the archive">
    <div class="arc-side-head">Files <span>{processed.metadata?.totalFiles ?? fileCount}</span></div>
    <div class="arc-tree">
      {#each flatTree as item (item.node.path || '/')}
        {@const icon = fileIcon(item.node)}
        {@const dir = item.node.type === 'directory'}
        <button
          class="arc-item"
          class:is-selected={selectedFile?.path === item.node.path}
          class:is-dir={dir}
          style:padding-left="{item.depth * 14 + 8}px"
          aria-expanded={dir ? item.isExpanded : undefined}
          on:click={() => selectFile(item.node)}
        >
          <span class="arc-chev" class:is-open={item.isExpanded}>{#if dir}<Icon name="chevr" size={12} />{/if}</span>
          <span class="arc-icon" style:color={icon.color}><Icon name={icon.name} size={14} /></span>
          <span class="arc-name">{item.node.name}</span>
          {#if !dir && item.node.size}<span class="arc-size">{compactBytes(item.node.size)}</span>{/if}
        </button>
      {/each}
    </div>
  </nav>

  <!-- svelte-ignore a11y-no-noninteractive-tabindex a11y-no-noninteractive-element-interactions -->
  <div
    class="arc-divider"
    class:is-dragging={isDragging}
    on:mousedown={startDrag}
    on:keydown={handleKeydown}
    role="separator"
    aria-orientation="vertical"
    aria-label="Resize the file list (← →)"
    tabindex="0"
  ></div>

  <section class="arc-main">
    {#if !selectedFile}
      <div class="arc-state">
        <Icon name="archive" size={26} />
        <p>Select a file to preview it.</p>
        <small>{fileCount} {fileCount === 1 ? 'file' : 'files'} in this archive</small>
      </div>
    {:else if loading}
      <div class="arc-state" role="status"><p>Extracting {selectedFile.name}…</p></div>
    {:else if error}
      <div class="r-banner r-banner-danger arc-error" role="alert">
        <Icon name="info" />
        <span>Couldn’t extract {selectedFile.name}: {error}</span>
        <button class="r-btn r-btn-secondary" on:click={() => downloadFile(selectedFile)}><Icon name="download" />Download it instead</button>
      </div>
    {:else if previewedFile}
      {@const icon = fileIcon(selectedFile)}
      <header class="arc-file">
        <span class="arc-icon" style:color={icon.color}><Icon name={icon.name} size={16} /></span>
        <div class="arc-file-name">
          <b title={selectedFile.name}>{selectedFile.name}</b>
          <span title={selectedFile.path}>{selectedFile.path}</span>
        </div>
        <span class="r-gap"></span>
        {#if isTreeSupported && isTextLike}
          {#if treeViewMode === 'tree'}
            <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" on:click={() => treeRendererRef?.expandAll()} title="Expand all" aria-label="Expand all"><Icon name="expand" /></button>
            <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" on:click={() => treeRendererRef?.collapseAll()} title="Collapse all" aria-label="Collapse all"><Icon name="collapse" /></button>
            <select class="arc-select" value={treePageSize} on:change={(e) => (treePageSize = parseInt(e.currentTarget.value, 10))} aria-label="Nodes per page">
              {#each [25, 50, 100, 250, 500] as size}<option value={size}>{size} / page</option>{/each}
            </select>
          {/if}
          <div class="arc-seg" role="group" aria-label="View">
            <button aria-pressed={treeViewMode === 'code'} on:click={() => (treeViewMode = 'code')}><Icon name="code" />Code</button>
            <button aria-pressed={treeViewMode === 'tree'} on:click={() => (treeViewMode = 'tree')}><Icon name="tree" />Tree</button>
          </div>
        {/if}
        {#if isTextLike || previewType === 'markdown' || previewType === 'html' || previewType === 'diff'}
          <button
            class="r-btn r-btn-ghost r-btn-sm r-btn-icon"
            aria-pressed={darkMode}
            on:click={() => { darkMode = !darkMode; dispatch('toggle-dark-mode', darkMode) }}
            title={darkMode ? 'Dark theme (on)' : 'Dark theme'}
            aria-label="Dark theme"
          ><Icon name="moon" /></button>
        {/if}
        <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" on:click={() => openInFullView(selectedFile)} title="Open on its own page" aria-label="Open on its own page"><Icon name="max" /></button>
        <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" on:click={() => downloadFile(selectedFile)} title="Download this file" aria-label="Download this file"><Icon name="download" /></button>
      </header>

      <div class="arc-content">
        {#if isTextLike && isTreeSupported && treeViewMode === 'tree'}
          <TreeRenderer
            bind:this={treeRendererRef}
            processed={previewedFile.processed}
            {darkMode}
            {fontSize}
            lang={effectiveLang}
            pageSize={treePageSize}
            on:parse-error={() => (treeViewMode = 'code')}
          />
        {:else if isTextLike}
          <CodeRenderer processed={previewedFile.processed} {relicId} {showSyntaxHighlighting} {showLineNumbers} {fontSize} {darkMode} />
        {:else if previewType === 'markdown'}
          <MarkdownRenderer processed={previewedFile.processed} {relicId} {showSyntaxHighlighting} {showLineNumbers} {darkMode} />
        {:else if previewType === 'html'}
          <HtmlRenderer processed={previewedFile.processed} {relicId} {showSyntaxHighlighting} {showLineNumbers} {darkMode} />
        {:else if previewType === 'csv'}
          <CsvRenderer processed={previewedFile.processed} name={selectedFile.name} />
        {:else if previewType === 'image'}
          <ImageRenderer processed={previewedFile.processed} relicName={selectedFile.name} />
        {:else if previewType === 'excalidraw'}
          <ExcalidrawRenderer processed={previewedFile.processed} />
        {:else if previewType === 'diff'}
          <DiffRenderer processed={previewedFile.processed} {relicId} {showSyntaxHighlighting} {showLineNumbers} {fontSize} {darkMode} />
        {:else if previewType === 'pdf'}
          <PDFViewer
            pdfDocument={previewedFile.processed.pdfDocument}
            metadata={previewedFile.processed.metadata}
            passwordRequired={previewedFile.processed.passwordRequired}
            {relicId}
          />
        {:else}
          <div class="arc-state">
            <Icon name="eyeoff" size={24} />
            <p>There’s no preview for this type of file.</p>
            <button class="r-btn r-btn-primary r-btn-md" on:click={() => downloadFile(selectedFile)}><Icon name="download" />Download it</button>
          </div>
        {/if}
      </div>
    {/if}
  </section>
</div>

<style>
  .arc {
    flex: 1;
    min-height: 0;
    display: flex;
    overflow: hidden;
    background: var(--surface);
    color: var(--ink);
    font: 13px/1.45 var(--font-sans);
  }
  .arc-side {
    flex: none;
    display: flex;
    flex-direction: column;
    min-width: 0;
    background: var(--subtle);
  }
  .arc-side-head {
    flex: none;
    display: flex;
    align-items: center;
    gap: var(--space-2);
    height: 36px;
    padding: 0 var(--space-3);
    border-bottom: 1px solid var(--line);
    color: var(--ink-3);
    font: 700 11px var(--font-mono);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .arc-side-head span {
    font-weight: 400;
    letter-spacing: 0;
  }
  .arc-tree {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: var(--space-1) 0 var(--space-3);
  }
  .arc-item {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    height: 28px;
    padding-right: var(--space-3);
    border: 0;
    background: none;
    color: var(--ink);
    font: 13px var(--font-sans);
    text-align: left;
    cursor: pointer;
  }
  .arc-item:hover {
    background: var(--hover);
  }
  .arc-item.is-selected {
    background: var(--accent-soft);
    box-shadow: inset 2px 0 var(--accent);
    font-weight: 500;
  }
  .arc-item.is-dir {
    color: var(--ink-2);
  }
  .arc-chev {
    display: inline-flex;
    flex: none;
    width: 12px;
    color: var(--ink-3);
    transition: transform 0.1s;
  }
  .arc-chev.is-open {
    transform: rotate(90deg);
  }
  .arc-icon {
    display: inline-flex;
    flex: none;
  }
  .arc-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .arc-size {
    flex: none;
    color: var(--ink-3);
    font: 12px var(--font-mono);
  }
  .arc-divider {
    flex: none;
    width: 5px;
    margin: 0 -2px;
    z-index: 1;
    background: linear-gradient(to right, transparent 2px, var(--line) 2px, var(--line) 3px, transparent 3px);
    cursor: col-resize;
    outline: 0;
  }
  .arc-divider:hover,
  .arc-divider:focus-visible,
  .arc-divider.is-dragging {
    background: linear-gradient(to right, transparent 1px, var(--accent) 1px, var(--accent) 4px, transparent 4px);
  }
  .arc-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .arc-file {
    flex: none;
    display: flex;
    align-items: center;
    gap: var(--space-1);
    height: 44px;
    padding: 0 var(--space-2) 0 var(--space-4);
    border-bottom: 1px solid var(--line);
  }
  .arc-file .arc-icon {
    margin-right: var(--space-1\.5);
  }
  .arc-file-name {
    display: grid;
    min-width: 0;
    line-height: 1.25;
  }
  .arc-file-name b,
  .arc-file-name span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .arc-file-name b {
    font-weight: 600;
  }
  .arc-file-name span {
    color: var(--ink-3);
    font: 11.5px var(--font-mono);
  }
  .arc-select {
    height: var(--control-sm);
    padding: 0 6px;
    border: 1px solid var(--line-2);
    border-radius: var(--radius-sm);
    background: var(--surface);
    color: var(--ink-2);
    font: 12px var(--font-sans);
  }
  .arc-seg {
    display: inline-flex;
    margin: 0 var(--space-1);
    border: 1px solid var(--line-2);
    border-radius: var(--radius-sm);
    overflow: hidden;
  }
  .arc-seg button {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    height: var(--control-sm);
    padding: 0 8px;
    border: 0;
    background: var(--surface);
    color: var(--ink-2);
    font: 12px var(--font-sans);
    cursor: pointer;
  }
  .arc-seg button + button {
    border-left: 1px solid var(--line-2);
  }
  .arc-seg button[aria-pressed='true'] {
    background: var(--accent-soft);
    color: var(--accent);
    font-weight: 500;
  }
  .arc-seg :global(.r-icon) {
    width: 13px;
    height: 13px;
  }
  .arc-file [aria-pressed='true'].r-btn {
    color: var(--accent);
  }
  .arc-content {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: auto;
  }
  .arc-state {
    flex: 1;
    display: grid;
    place-content: center;
    justify-items: center;
    gap: var(--space-2);
    padding: var(--space-5);
    color: var(--ink-3);
    text-align: center;
  }
  .arc-state p {
    margin: 0;
    color: var(--ink-2);
  }
  .arc-error {
    flex: none;
  }
  .arc-error .r-btn {
    margin-left: auto;
  }
  @media (max-width: 767px) {
    .arc {
      flex-direction: column;
    }
    .arc-side {
      width: auto !important;
      max-height: 40%;
      border-bottom: 1px solid var(--line);
    }
    .arc-divider {
      display: none;
    }
  }
</style>
