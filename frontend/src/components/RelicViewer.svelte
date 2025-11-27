<script>
  import { onMount } from 'svelte'
  import { getRelic, getRelicRaw, getRelicHistory, addBookmark, removeBookmark, checkBookmark } from '../services/api'
  import { processContent } from '../services/processors'
  import { showToast } from '../stores/toastStore'
  import { shareRelic, copyRelicContent, downloadRelic, viewRaw } from '../services/relicActions'
  import MonacoEditor from './MonacoEditor.svelte'
  import ForkModal from './ForkModal.svelte'

  export let relicId = ''

  let relic = null
  let processed = null
  let loading = true
  let history = []
  let showHistory = false
  let showHtmlSource = false
  let showMarkdownSource = false
  let htmlContainer
  let markdownContainer
  let htmlEditor
  let markdownEditor
  let isBookmarked = false
  let checkingBookmark = false
  let bookmarkLoading = false
  let showForkModal = false
  let forkLoading = false

  async function loadRelic(id) {
    if (!id) return
    loading = true
    relic = null
    processed = null
    history = []

    console.log('[RelicViewer] Loading relic:', id)
    try {
      console.log('[RelicViewer] Fetching relic metadata...')
      const relicResponse = await getRelic(id)
      console.log('[RelicViewer] Relic metadata received:', relicResponse.data)
      relic = relicResponse.data

      // Fetch and process raw content
      console.log('[RelicViewer] Fetching raw content...')
      const rawResponse = await getRelicRaw(id)
      const content = await rawResponse.data.arrayBuffer()
      console.log('[RelicViewer] Raw content received, processing...')

      processed = await processContent(
        new Uint8Array(content),
        relic.content_type,
        relic.language_hint
      )
      console.log('[RelicViewer] Content processed:', processed)

      // Load history if this is part of a version chain
      if (relic.root_id) {
        console.log('[RelicViewer] Loading history...')
        const historyResponse = await getRelicHistory(id)
        history = historyResponse.data.versions
      }

      // Check bookmark status
      await checkBookmarkStatus(id)

      console.log('[RelicViewer] Relic loaded successfully')
    } catch (error) {
      console.error('[RelicViewer] Error loading relic:', error)
      showToast('Failed to load relic: ' + error.message, 'error')
    } finally {
      loading = false
    }
  }

  async function checkBookmarkStatus(id) {
    try {
      checkingBookmark = true
      const response = await checkBookmark(id)
      isBookmarked = response.data.is_bookmarked
    } catch (error) {
      console.error('[RelicViewer] Error checking bookmark status:', error)
      isBookmarked = false
    } finally {
      checkingBookmark = false
    }
  }

  async function toggleBookmark() {
    if (bookmarkLoading) return

    try {
      bookmarkLoading = true
      if (isBookmarked) {
        await removeBookmark(relicId)
        showToast('Bookmark removed', 'success')
        isBookmarked = false
      } else {
        await addBookmark(relicId)
        showToast('Bookmarked!', 'success')
        isBookmarked = true
      }
    } catch (error) {
      console.error('[RelicViewer] Error toggling bookmark:', error)
      if (error.response?.status === 409) {
        showToast('Already bookmarked', 'info')
        isBookmarked = true
      } else if (error.response?.status === 401) {
        showToast('Client key required to bookmark', 'error')
      } else {
        showToast('Failed to update bookmark', 'error')
      }
    } finally {
      bookmarkLoading = false
    }
  }

  $: if (relicId) {
    loadRelic(relicId)
  }

  
  function formatFileSize(bytes) {
    const units = ['B', 'KB', 'MB', 'GB']
    let size = bytes
    let unitIndex = 0

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }

    return `${size.toFixed(2)} ${units[unitIndex]}`
  }

  function navigateToRelic(newId) {
    window.history.pushState({}, '', `/${newId}`)
    window.dispatchEvent(new PopStateEvent('popstate', {}))
    // Update current relic ID
    relicId = newId
  }

  function copyRelicId(id) {
    navigator.clipboard.writeText(id).then(() => {
      // You could add a toast notification here if desired
    })
  }

  function handleLineClicked(event) {
    // No toast needed for line clicks - the URL update is sufficient
  }

  function handleLineCopied(event) {
    const { lineNumber } = event.detail
    showToast(`Line ${lineNumber} URL copied to clipboard!`, 'success')
  }

  function handleLineRangeSelected(event) {
    // No toast needed for range selection - the URL update is sufficient
  }

  function handleMultiLineSelected(event) {
    // No toast needed for multi-line selection - the URL update is sufficient
  }

  // Initialize Monaco editor for HTML source view
  $: if (showHtmlSource && htmlContainer && processed?.html && !htmlEditor) {
    import('monaco-editor').then(monaco => {
      // Setup Monaco environment
      self.MonacoEnvironment = {
        getWorker: () => {
          return {
            postMessage: () => {},
            terminate: () => {}
          }
        }
      }

      try {
        htmlEditor = monaco.editor.create(htmlContainer, {
          value: processed.html,
          language: 'html',
          readOnly: true,
          theme: 'vs',
          automaticLayout: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          lineNumbers: 'on',
          fontSize: 13,
          fontFamily: '"Courier New", monospace',
          padding: { top: 16, bottom: 16 }
        })
        console.log('HTML source editor created successfully')
      } catch (e) {
        console.error('Failed to create HTML source editor:', e)
      }
    })
  }

  // Initialize Monaco editor for Markdown source view
  $: if (showMarkdownSource && markdownContainer && processed?.preview && !markdownEditor) {
    import('monaco-editor').then(monaco => {
      // Setup Monaco environment
      self.MonacoEnvironment = {
        getWorker: () => {
          return {
            postMessage: () => {},
            terminate: () => {}
          }
        }
      }

      try {
        markdownEditor = monaco.editor.create(markdownContainer, {
          value: processed.preview,
          language: 'markdown',
          readOnly: true,
          theme: 'vs',
          automaticLayout: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          lineNumbers: 'on',
          fontSize: 13,
          fontFamily: '"Courier New", monospace',
          padding: { top: 16, bottom: 16 }
        })
        console.log('Markdown source editor created successfully')
      } catch (e) {
        console.error('Failed to create Markdown source editor:', e)
      }
    })
  }

  // Update editor content when HTML changes
  $: if (htmlEditor && processed?.html) {
    const currentValue = htmlEditor.getValue()
    if (currentValue !== processed.html) {
      htmlEditor.setValue(processed.html)
    }
  }

  // Update editor content when Markdown changes
  $: if (markdownEditor && processed?.preview) {
    const currentValue = markdownEditor.getValue()
    if (currentValue !== processed.preview) {
      markdownEditor.setValue(processed.preview)
    }
  }

  // Clean up HTML editor when switching away from HTML source view
  $: if (!showHtmlSource && htmlEditor) {
    htmlEditor.dispose()
    htmlEditor = null
  }

  // Clean up Markdown editor when switching away from Markdown source view
  $: if (!showMarkdownSource && markdownEditor) {
    markdownEditor.dispose()
    markdownEditor = null
  }

  // Cleanup on component destroy
  onMount(() => {
    return () => {
      if (htmlEditor) {
        htmlEditor.dispose()
      }
      if (markdownEditor) {
        markdownEditor.dispose()
      }
    }
  })

  </script>

<style>
  :global(.monaco-container .line-numbers) {
    color: #6b7280 !important;
  }

  :global(.monaco-editor .line-numbers) {
    color: #6b7280 !important;
  }

  :global(.monaco-editor .view-line .line-number) {
    color: #6b7280 !important;
  }
</style>

{#if loading}
  <div class="flex items-center justify-center py-12">
    <i class="fas fa-spinner fa-spin text-blue-600 text-4xl"></i>
  </div>
{:else if relic}
  <div class="max-w-7xl mx-auto px-4 py-6">
    <!-- Header -->
    <div class="bg-white shadow-sm rounded-lg border border-gray-200 mb-6">
      <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <div class="flex items-center">
          <h2 class="text-lg font-semibold text-gray-900 flex items-center">
            <i class="fas fa-file text-blue-600 mr-2"></i>
            {relic.name || 'Untitled'}
          </h2>
          <div class="flex items-center group gap-1">
            <span class="ml-3 text-xs bg-gray-100 px-2 py-1 rounded text-gray-600 font-mono">{relicId}</span>
            <button
              on:click={() => copyRelicId(relicId)}
              class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-gray-600 transition-all duration-200 -mt-0.5"
              title="Copy ID"
            >
              <i class="fas fa-copy text-xs"></i>
            </button>
          </div>
        </div>
        <div class="flex items-center gap-1">
          <button
            on:click={toggleBookmark}
            disabled={checkingBookmark || bookmarkLoading}
            class="p-1.5 rounded transition-colors {isBookmarked
              ? 'text-amber-600 hover:text-amber-700 hover:bg-amber-50'
              : 'text-gray-400 hover:text-amber-600 hover:bg-amber-50'}"
            title={isBookmarked ? 'Remove bookmark' : 'Bookmark this relic'}
          >
            {#if bookmarkLoading}
              <i class="fas fa-spinner fa-spin text-xs"></i>
            {:else if isBookmarked}
              <i class="fas fa-bookmark text-xs"></i>
            {:else}
              <i class="far fa-bookmark text-xs"></i>
            {/if}
          </button>
          <button
            on:click={() => shareRelic(relicId)}
            class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
            title="Share relic"
          >
            <i class="fas fa-share text-xs"></i>
          </button>
          <button
            on:click={() => copyRelicContent(relicId)}
            class="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
            title="Copy content to clipboard"
          >
            <i class="fas fa-copy text-xs"></i>
          </button>
          <button
            on:click={() => viewRaw(relicId)}
            class="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors"
            title="View raw content"
          >
            <i class="fas fa-code text-xs"></i>
          </button>
          <button
            on:click={() => showForkModal = true}
            disabled={forkLoading}
            class="p-1.5 text-gray-400 hover:text-teal-600 hover:bg-teal-50 rounded transition-colors"
            title="Create fork"
          >
            {#if forkLoading}
              <i class="fas fa-spinner fa-spin text-xs"></i>
            {:else}
              <i class="fas fa-code-branch text-xs"></i>
            {/if}
          </button>
          <button
            on:click={() => downloadRelic(relicId, relic.name, relic.content_type)}
            class="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
            title="Download relic"
          >
            <i class="fas fa-download text-xs"></i>
          </button>
        </div>
      </div>

      <!-- Extended Metadata -->
      <div class="p-6">
        <!-- Fork Attribution -->
        {#if relic.fork_of}
          <div class="flex items-center gap-2 text-sm text-gray-600 mb-4">
            <i class="fas fa-code-branch text-teal-600"></i>
            <span>Forked from
              <a href="/{relic.fork_of}" class="text-teal-600 hover:underline ml-1">relic/{relic.fork_of}</a>
            </span>
          </div>
        {/if}

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span class="text-xs text-gray-500 block mb-1">Type</span>
            <span class="block font-mono text-gray-900 text-xs">{relic.content_type}</span>
          </div>
          <div>
            <span class="text-xs text-gray-500 block mb-1">Size</span>
            <span class="block font-mono text-gray-900 text-xs">{formatFileSize(relic.size_bytes)}</span>
          </div>
          <div>
            <span class="text-xs text-gray-500 block mb-1">Views</span>
            <span class="block font-mono text-gray-900 text-xs">{relic.access_count}</span>
          </div>
          <div>
            <span class="text-xs text-gray-500 block mb-1">Version</span>
            <span class="block font-mono text-gray-900 text-xs">v{relic.version_number}</span>
          </div>
        </div>
        {#if relic.description}
          <div class="mt-4 pt-4 border-t border-gray-100">
            <span class="text-xs text-gray-500 block mb-1">Description</span>
            <p class="text-sm text-gray-700">{relic.description}</p>
          </div>
        {/if}
      </div>
    </div>

    <!-- Content -->
    {#if processed}
      {#if processed.type === 'markdown'}
        <div class="bg-white shadow-sm rounded-lg border border-gray-200 mb-6 p-6">
          <!-- Header with toggle -->
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-lg font-semibold text-gray-900 flex items-center">
              <i class="fas fa-file-alt text-blue-600 mr-2"></i>
              Markdown Content
            </h3>
            <div class="flex items-center gap-2">
              <!-- Preview Button -->
              <button
                type="button"
                on:click={() => showMarkdownSource = false}
                class="p-2 rounded transition-colors {showMarkdownSource ? 'bg-gray-100 text-gray-600' : 'bg-blue-100 text-blue-600 hover:bg-blue-200'}"
                title="Rendered preview"
              >
                <i class="fas fa-eye"></i>
              </button>

              <!-- Code Button -->
              <button
                type="button"
                on:click={() => showMarkdownSource = true}
                class="p-2 rounded transition-colors {showMarkdownSource ? 'bg-blue-100 text-blue-600 hover:bg-blue-200' : 'bg-gray-100 text-gray-600'}"
                title="Source code"
              >
                <i class="fas fa-code"></i>
              </button>
            </div>
          </div>

          <!-- Markdown Content Container -->
          <div class="border border-gray-200 rounded-lg overflow-hidden">
            {#if !showMarkdownSource}
              <!-- Rendered Markdown - natural height -->
              <div class="p-6 prose prose-sm max-w-none">
                {@html processed.html}
              </div>
            {:else}
              <!-- Markdown Source Editor - fixed height for editor -->
              <div style="height: calc(100vh - 400px);">
                <div bind:this={markdownContainer} style="height: 100%; width: 100%;" class="monaco-container"></div>
              </div>
            {/if}
          </div>
        </div>
      {:else if processed.type === 'html'}
        <div class="bg-white shadow-sm rounded-lg border border-gray-200 mb-6 p-6">
          <!-- Header with toggle -->
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-lg font-semibold text-gray-900 flex items-center">
              <i class="fas fa-code text-orange-600 mr-2"></i>
              HTML Content
            </h3>
            <div class="flex items-center gap-2">
              <!-- Preview Button -->
              <button
                type="button"
                on:click={() => showHtmlSource = false}
                class="p-2 rounded transition-colors {showHtmlSource ? 'bg-gray-100 text-gray-600' : 'bg-blue-100 text-blue-600 hover:bg-blue-200'}"
                title="Rendered preview"
              >
                <i class="fas fa-eye"></i>
              </button>

              <!-- Code Button -->
              <button
                type="button"
                on:click={() => showHtmlSource = true}
                class="p-2 rounded transition-colors {showHtmlSource ? 'bg-blue-100 text-blue-600 hover:bg-blue-200' : 'bg-gray-100 text-gray-600'}"
                title="Source code"
              >
                <i class="fas fa-code"></i>
              </button>
            </div>
          </div>

          <!-- HTML Content Container -->
          <div class="border border-gray-200 rounded-lg overflow-hidden" style="height: calc(100vh - 400px);">
            {#if !showHtmlSource}
              <!-- HTML Preview Frame -->
              <iframe
                srcdoc={processed.html}
                class="w-full h-full border-0"
                sandbox="allow-same-origin allow-scripts allow-forms"
                title="HTML Content Preview"
              ></iframe>
            {:else}
              <!-- HTML Source Editor - directly use Monaco without extra wrapper -->
              <div bind:this={htmlContainer} style="height: 100%; width: 100%;" class="monaco-container"></div>
            {/if}
          </div>
        </div>
      {:else if processed.type === 'code'}
        <MonacoEditor
          value={processed.preview || ''}
          language={processed.metadata?.language || 'plaintext'}
          readOnly={true}
          height="calc(100vh - 300px)"
          relicId={relicId}
          on:line-clicked={handleLineClicked}
          on:line-range-selected={handleLineRangeSelected}
          on:multi-line-selected={handleMultiLineSelected}
          on:line-copied={handleLineCopied}
        />
      {:else if processed.type === 'text'}
        <MonacoEditor
          value={processed.preview || ''}
          language="plaintext"
          readOnly={true}
          height="calc(100vh - 300px)"
          relicId={relicId}
          on:line-clicked={handleLineClicked}
          on:line-range-selected={handleLineRangeSelected}
          on:multi-line-selected={handleMultiLineSelected}
          on:line-copied={handleLineCopied}
        />
        {#if processed.truncated}
          <div class="bg-blue-50 border-t border-gray-200 px-6 py-4 text-center text-sm text-blue-700 mb-6 rounded-b-lg">
            Content truncated. <a href="/{relicId}/raw" class="font-semibold hover:underline">Download full file</a>
          </div>
        {/if}
      {:else if processed.type === 'image'}
        <div class="bg-white shadow-sm rounded-lg border border-gray-200 mb-6 p-6">
          <img src={processed.url} alt={relic.name} class="max-w-full h-auto rounded" />
        </div>
      {:else if processed.type === 'csv'}
        <div class="bg-white shadow-sm rounded-lg border border-gray-200 mb-6 p-6">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-gray-200">
                  <th class="px-4 py-2 text-left font-semibold text-gray-900">Row</th>
                  {#each processed.metadata.columns as col}
                    <th class="px-4 py-2 text-left font-semibold text-gray-900">{col}</th>
                  {/each}
                </tr>
              </thead>
              <tbody>
                {#each processed.rows as row, idx}
                  <tr class="border-b border-gray-100 hover:bg-gray-50">
                    <td class="px-4 py-2 text-gray-600">{idx + 1}</td>
                    {#each processed.metadata.columns as col}
                      <td class="px-4 py-2 text-gray-900">{row[col] || ''}</td>
                    {/each}
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {:else}
        <div class="bg-white shadow-sm rounded-lg border border-gray-200 mb-6 p-6 text-center">
          <i class="fas fa-file text-gray-400 text-6xl mb-4"></i>
          <p class="text-gray-600 mb-4">Preview not available for this file type</p>
          <button
            on:click={downloadRelic}
            class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            <i class="fas fa-download mr-2"></i>
            Download File
          </button>
        </div>
      {/if}
    {:else}
      <div class="bg-white shadow-sm rounded-lg border border-gray-200 mb-6 p-6 text-center">
        <i class="fas fa-file text-gray-400 text-6xl mb-4"></i>
        <p class="text-gray-600">Loading preview...</p>
      </div>
    {/if}

    <!-- History -->
    {#if history.length > 0}
      <div class="bg-white shadow-sm rounded-lg border border-gray-200">
        <div class="px-6 py-4 border-b border-gray-200">
          <button
            on:click={() => (showHistory = !showHistory)}
            class="flex items-center text-lg font-semibold text-gray-900 hover:text-blue-600"
          >
            <i class="fas fa-code-branch mr-2"></i>
            Version History
            <i class="fas fa-chevron-down ml-2 transition-transform" class:rotate-180={showHistory}></i>
          </button>
        </div>
        {#if showHistory}
          <div class="divide-y divide-gray-200">
            {#each history as version (version.id)}
              <button
                on:click={() => navigateToRelic(version.id)}
                class="w-full p-4 hover:bg-gray-50 transition-colors block text-left border-0 bg-transparent cursor-pointer"
              >
                <div class="flex items-center justify-between">
                  <div>
                    <span class="font-medium text-gray-900">v{version.version}</span>
                    <span class="text-sm text-gray-500 ml-2">{version.name || 'Untitled'}</span>
                  </div>
                  <span class="text-sm text-gray-500">{new Date(version.created_at).toLocaleString()}</span>
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  </div>
{:else}
  <div class="flex items-center justify-center py-12">
    <div class="text-center">
      <i class="fas fa-search text-gray-400 text-6xl mb-4"></i>
      <p class="text-gray-600">Relic not found</p>
    </div>
  </div>
{/if}

<!-- Fork Modal -->
{#if relic}
  <ForkModal
    bind:open={showForkModal}
    relicId={relicId}
    {relic}
  />
{/if}
