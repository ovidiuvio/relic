<script>
  import { onDestroy } from 'svelte';
  import { processContent } from '../../services/processors/index.js';
  import CodeRenderer from './CodeRenderer.svelte';
  import ImageRenderer from './ImageRenderer.svelte';
  import MarkdownRenderer from './MarkdownRenderer.svelte';
  import HtmlRenderer from './HtmlRenderer.svelte';
  import CsvRenderer from './CsvRenderer.svelte';
  import ExcalidrawRenderer from './ExcalidrawRenderer.svelte';
  import PDFViewer from '../PDFViewer.svelte';

  export let processed
  export let relicId
  export let showSyntaxHighlighting = true
  export let showLineNumbers = true
  export let fontSize = 13

  let selectedFile = null
  let previewedFile = null
  let loading = false
  let error = null
  let expandedDirs = new Set(['', '/']) // Support both empty string and '/' for root

  // Resizable panel state
  let sidebarWidth = parseInt(localStorage.getItem('archiveSidebarWidth') || '400')
  let isDragging = false
  let containerRef

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
      const blob = new Blob([content], { type: file.contentType })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = file.name
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Error downloading file:', err)
      alert('Failed to download file: ' + err.message)
    }
  }

  // Open file in full viewer mode (navigates to dedicated URL)
  function openInFullView(file) {
    const newUrl = `/${relicId}/${file.path}`
    window.history.pushState({}, '', newUrl)
    window.dispatchEvent(new PopStateEvent('popstate'))
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

  // Debug logging
  $: if (processed) {
    console.log('[ArchiveRenderer] Processed archive:', processed)
    console.log('[ArchiveRenderer] File tree:', processed.fileTree)
    console.log('[ArchiveRenderer] Flat tree:', flatTree)
    console.log('[ArchiveRenderer] Total items in flat tree:', flatTree.length)
  }

  // Get FontAwesome icon for file/directory
  function getIcon(item) {
    if (item.node.type === 'directory') {
      return expandedDirs.has(item.node.path || '/') ? 'fa-folder-open' : 'fa-folder'
    }

    const ext = item.node.name.split('.').pop()?.toLowerCase()
    const iconMap = {
      'js': 'fa-file-code', 'ts': 'fa-file-code', 'jsx': 'fa-file-code', 'tsx': 'fa-file-code',
      'py': 'fa-file-code', 'java': 'fa-file-code', 'cpp': 'fa-file-code', 'c': 'fa-file-code',
      'go': 'fa-file-code', 'rs': 'fa-file-code', 'rb': 'fa-file-code', 'php': 'fa-file-code',
      'html': 'fa-file-code', 'css': 'fa-file-code', 'scss': 'fa-file-code',
      'json': 'fa-file-code', 'xml': 'fa-file-code', 'yaml': 'fa-file-code', 'yml': 'fa-file-code',
      'md': 'fa-file-alt', 'txt': 'fa-file-alt', 'log': 'fa-file-alt',
      'png': 'fa-file-image', 'jpg': 'fa-file-image', 'jpeg': 'fa-file-image',
      'gif': 'fa-file-image', 'svg': 'fa-file-image', 'webp': 'fa-file-image',
      'pdf': 'fa-file-pdf',
      'csv': 'fa-file-csv', 'xlsx': 'fa-file-excel', 'xls': 'fa-file-excel',
      'zip': 'fa-file-archive', 'tar': 'fa-file-archive', 'gz': 'fa-file-archive',
      'mp4': 'fa-file-video', 'avi': 'fa-file-video', 'mov': 'fa-file-video',
      'mp3': 'fa-file-audio', 'wav': 'fa-file-audio'
    }

    return iconMap[ext] || 'fa-file'
  }

  // Get icon color
  function getIconColor(item) {
    if (item.node.type === 'directory') {
      return 'text-blue-500'
    }

    const ext = item.node.name.split('.').pop()?.toLowerCase()
    const colorMap = {
      'js': 'text-yellow-500', 'ts': 'text-blue-600', 'jsx': 'text-cyan-500', 'tsx': 'text-cyan-600',
      'py': 'text-blue-400', 'java': 'text-red-500', 'cpp': 'text-blue-700', 'c': 'text-blue-700',
      'go': 'text-cyan-600', 'rs': 'text-orange-600', 'rb': 'text-red-600', 'php': 'text-purple-500',
      'html': 'text-orange-500', 'css': 'text-blue-500', 'scss': 'text-pink-500',
      'json': 'text-yellow-600', 'xml': 'text-orange-400', 'yaml': 'text-purple-400', 'yml': 'text-purple-400',
      'md': 'text-gray-600', 'txt': 'text-gray-500', 'log': 'text-gray-500',
      'png': 'text-green-500', 'jpg': 'text-green-500', 'jpeg': 'text-green-500',
      'gif': 'text-green-500', 'svg': 'text-green-600', 'webp': 'text-green-500',
      'pdf': 'text-red-600',
      'csv': 'text-green-600', 'xlsx': 'text-green-700', 'xls': 'text-green-700',
      'zip': 'text-gray-600', 'tar': 'text-gray-600', 'gz': 'text-gray-600'
    }

    return colorMap[ext] || 'text-gray-400'
  }
</script>

<div class="border-t border-gray-200">
  <div bind:this={containerRef} class="flex divide-x divide-gray-200 relative" style="user-select: {isDragging ? 'none' : 'auto'}">
    <!-- File tree sidebar -->
    <div class="bg-gray-50 max-h-[calc(100vh-300px)] overflow-y-auto flex-shrink-0" style="width: {sidebarWidth}px">
      <!-- Archive metadata header -->
      <div class="sticky top-0 bg-white border-b border-gray-200 px-4 py-3 z-10">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-sm font-semibold text-gray-900">Archive Contents</h3>
          <span class="px-2 py-0.5 bg-gray-200 text-gray-700 rounded text-xs font-bold uppercase">
            {processed.metadata.archiveType}
          </span>
        </div>
        <div class="flex items-center gap-4 text-xs text-gray-600">
          <span class="flex items-center gap-1">
            <i class="fas fa-file text-gray-400"></i>
            {processed.metadata.totalFiles}
          </span>
          <span class="flex items-center gap-1">
            <i class="fas fa-folder text-gray-400"></i>
            {processed.metadata.totalDirectories}
          </span>
          <span class="flex items-center gap-1">
            <i class="fas fa-weight text-gray-400"></i>
            {processed.metadata.totalSizeFormatted}
          </span>
        </div>
      </div>

      <!-- File tree -->
      <div class="py-1">
        {#each flatTree as item}
          <button
            class="w-full text-left px-4 py-1.5 hover:bg-gray-100 transition-colors flex items-center gap-2 text-sm
                   {selectedFile?.path === item.node.path ? 'bg-blue-50 text-blue-700 border-l-2 border-blue-600' : 'text-gray-700'}"
            style="padding-left: {item.depth * 16 + 16}px"
            on:click={() => selectFile(item.node)}
          >
            <i class="fas {getIcon(item)} {getIconColor(item)} text-sm flex-shrink-0"></i>
            <span class="truncate flex-1">{item.node.name}</span>
            {#if item.node.type === 'file' && item.node.size}
              <span class="text-xs text-gray-500 flex-shrink-0">
                {(item.node.size / 1024).toFixed(1)}KB
              </span>
            {/if}
          </button>
        {/each}
      </div>
    </div>

    <!-- Resize divider -->
    <div
      class="w-1 bg-gray-200 hover:bg-blue-500 cursor-col-resize flex-shrink-0 transition-colors relative group"
      on:mousedown={startDrag}
      on:keydown={handleKeydown}
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize sidebar"
      tabindex="0"
    >
      <div class="absolute inset-y-0 -left-1 -right-1 group-hover:bg-blue-500/10"></div>
    </div>

    <!-- File preview area -->
    <div class="flex-1 bg-white min-w-0">
      {#if !selectedFile}
        <div class="flex items-center justify-center h-[calc(100vh-300px)] text-gray-500">
          <div class="text-center">
            <i class="fas fa-file-archive text-gray-300 text-6xl mb-4"></i>
            <p class="text-lg font-medium text-gray-600 mb-2">Select a file to preview</p>
            <p class="text-sm text-gray-500">Click on any file in the tree to view its contents</p>
          </div>
        </div>
      {:else if loading}
        <div class="flex items-center justify-center h-[calc(100vh-300px)] text-gray-500">
          <div class="text-center">
            <i class="fas fa-spinner fa-spin text-blue-600 text-4xl mb-4"></i>
            <p class="text-sm text-gray-600">Extracting file...</p>
          </div>
        </div>
      {:else if error}
        <div class="p-6">
          <div class="bg-red-50 border border-red-200 rounded-lg p-4">
            <div class="flex items-start gap-3">
              <i class="fas fa-exclamation-circle text-red-600 text-xl"></i>
              <div class="flex-1">
                <h4 class="font-semibold text-red-900 mb-1">Failed to extract file</h4>
                <p class="text-sm text-red-700 mb-3">{error}</p>
                <button
                  class="text-sm px-3 py-1.5 bg-red-100 text-red-700 hover:bg-red-200 rounded transition-colors"
                  on:click={() => downloadFile(selectedFile)}
                >
                  <i class="fas fa-download mr-1"></i>
                  Download file instead
                </button>
              </div>
            </div>
          </div>
        </div>
      {:else if previewedFile}
        <div class="flex flex-col h-[calc(100vh-300px)]">
          <!-- File header -->
          <div class="border-b border-gray-200 px-4 py-3 bg-gray-50 flex items-center justify-between flex-shrink-0">
            <div class="flex items-center gap-3 min-w-0">
              <i class="fas {getIcon({ node: selectedFile })} {getIconColor({ node: selectedFile })} text-lg flex-shrink-0"></i>
              <div class="min-w-0">
                <h4 class="font-semibold text-gray-900 truncate">{selectedFile.name}</h4>
                <p class="text-xs text-gray-500 font-mono truncate">{selectedFile.path}</p>
              </div>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <button
                class="p-2 text-[#772953] hover:text-[#5a1f3f] rounded transition-colors"
                on:click={() => openInFullView(selectedFile)}
                title="Open in full view"
              >
                <i class="fas fa-expand-alt text-sm"></i>
              </button>
              <button
                class="p-2 text-[#772953] hover:text-[#5a1f3f] rounded transition-colors"
                on:click={() => downloadFile(selectedFile)}
                title="Download file"
              >
                <i class="fas fa-download text-sm"></i>
              </button>
            </div>
          </div>

          <!-- File content -->
          <div class="flex-1 overflow-auto">
            {#if previewedFile.processed.type === 'code' || previewedFile.processed.type === 'text'}
              <CodeRenderer
                processed={previewedFile.processed}
                {relicId}
                {showSyntaxHighlighting}
                {showLineNumbers}
                {fontSize}
              />
            {:else if previewedFile.processed.type === 'markdown'}
              <MarkdownRenderer
                processed={previewedFile.processed}
                {relicId}
                {showSyntaxHighlighting}
                {showLineNumbers}
              />
            {:else if previewedFile.processed.type === 'html'}
              <HtmlRenderer
                processed={previewedFile.processed}
                {relicId}
                {showSyntaxHighlighting}
                {showLineNumbers}
              />
            {:else if previewedFile.processed.type === 'csv'}
              <CsvRenderer processed={previewedFile.processed} />
            {:else if previewedFile.processed.type === 'image'}
              <ImageRenderer processed={previewedFile.processed} relicName={selectedFile.name} />
            {:else if previewedFile.processed.type === 'excalidraw'}
              <ExcalidrawRenderer processed={previewedFile.processed} />
            {:else if previewedFile.processed.type === 'pdf'}
              <PDFViewer
                pdfDocument={previewedFile.processed.pdfDocument}
                metadata={previewedFile.processed.metadata}
                passwordRequired={previewedFile.processed.passwordRequired}
                {relicId}
              />
            {:else}
              <div class="p-6 text-center text-gray-500">
                <i class="fas fa-eye-slash text-gray-300 text-4xl mb-4"></i>
                <p class="text-gray-600 mb-4">Preview not available for this file type</p>
                <button
                  class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                  on:click={() => downloadFile(selectedFile)}
                >
                  <i class="fas fa-download mr-2"></i>
                  Download to view
                </button>
              </div>
            {/if}
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>
