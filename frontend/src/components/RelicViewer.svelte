<script>
  import { onMount } from 'svelte'
  import { getRelic, getRelicRaw, addBookmark, removeBookmark, checkBookmark } from '../services/api'
  import { processContent } from '../services/processors'
  import { showToast } from '../stores/toastStore'
  import { shareRelic, copyRelicContent, downloadRelic, viewRaw } from '../services/relicActions'
  import { getTypeLabel, getTypeIcon, getTypeIconColor } from '../services/typeUtils'
  import MonacoEditor from './MonacoEditor.svelte'
  import ForkModal from './ForkModal.svelte'
  import { createEventDispatcher } from 'svelte'
  import { getCurrentLineNumberFragment } from '../utils/lineNumbers'

  const dispatch = createEventDispatcher()

  export let relicId = ''

  let relic = null
  let processed = null
  let loading = true
  let showHtmlSource = false
  let showMarkdownSource = false
  let isBookmarked = false
  let checkingBookmark = false
  let bookmarkLoading = false
  let showForkModal = false
  let forkLoading = false

  // Initialize from localStorage immediately
  let isFullWidth = (() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('relic_viewer_fullwidth')
      return saved === 'true'
    }
    return false
  })()

  let showSyntaxHighlighting = (() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('relic_editor_syntax_highlighting')
      return saved === 'false' ? false : true
    }
    return true
  })()

  let showLineNumbers = (() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('relic_editor_line_numbers')
      return saved === 'false' ? false : true
    }
    return true
  })()

  // Dispatch initial state to parent on mount
  onMount(() => {
    dispatch('fullwidth-toggle', { isFullWidth })
  })

  // Save full-width preference and dispatch to parent
  $: {
    if (typeof window !== 'undefined') {
      localStorage.setItem('relic_viewer_fullwidth', isFullWidth.toString())
    }
    dispatch('fullwidth-toggle', { isFullWidth })
  }

  // Save editor preferences
  $: if (typeof window !== 'undefined') {
    localStorage.setItem('relic_editor_syntax_highlighting', showSyntaxHighlighting.toString())
  }

  $: if (typeof window !== 'undefined') {
    localStorage.setItem('relic_editor_line_numbers', showLineNumbers.toString())
  }

  async function loadRelic(id) {
    if (!id) return
    loading = true
    relic = null
    processed = null
    
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

      // Check if URL has line number fragment - if so, show source view
      const lineFragment = getCurrentLineNumberFragment()
      if (lineFragment) {
        if (processed.type === 'markdown') {
          showMarkdownSource = true
        } else if (processed.type === 'html') {
          showHtmlSource = true
        }
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
  <div class="{isFullWidth ? 'w-full px-0' : 'max-w-7xl mx-auto px-4'} py-6 transition-all duration-300">
    <!-- Unified Container -->
    <div class="bg-white shadow-sm border border-gray-200 overflow-hidden {isFullWidth ? 'rounded-none' : 'rounded-lg'}">
      <!-- Compact Header -->
      <div class="px-6 py-4 border-b border-gray-200">
        <!-- Title Row with Actions -->
        <div class="flex items-center justify-between gap-4 mb-2">
          <div class="flex items-center gap-3 flex-1 min-w-0">
            <i class="fas {getTypeIcon(relic.content_type)} {getTypeIconColor(relic.content_type)} text-base flex-shrink-0"></i>
            <h2 class="text-base font-semibold text-gray-900 truncate leading-none">{relic.name || 'Untitled'}</h2>

            <!-- Type Badge -->
            <span class="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs flex-shrink-0">{getTypeLabel(relic.content_type)}</span>
          </div>

          <!-- Action Toolbar -->
          <div class="flex items-center gap-1 flex-shrink-0">
            <button
              on:click={toggleBookmark}
              disabled={checkingBookmark || bookmarkLoading}
              class="p-2 rounded transition-colors {isBookmarked
                ? 'text-amber-600 hover:text-amber-700 hover:bg-amber-50'
                : 'text-gray-400 hover:text-amber-600 hover:bg-amber-50'}"
              title={isBookmarked ? 'Remove bookmark' : 'Bookmark this relic'}
            >
              {#if bookmarkLoading}
                <i class="fas fa-spinner fa-spin text-sm"></i>
              {:else if isBookmarked}
                <i class="fas fa-bookmark text-sm"></i>
              {:else}
                <i class="far fa-bookmark text-sm"></i>
              {/if}
            </button>
            <button
              on:click={() => shareRelic(relicId)}
              class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
              title="Share relic"
            >
              <i class="fas fa-share text-sm"></i>
            </button>
            <button
              on:click={() => copyRelicContent(relicId)}
              class="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
              title="Copy content to clipboard"
            >
              <i class="fas fa-copy text-sm"></i>
            </button>
            <button
              on:click={() => viewRaw(relicId)}
              class="p-2 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors"
              title="View raw content"
            >
              <i class="fas fa-code text-sm"></i>
            </button>
            <button
              on:click={() => showForkModal = true}
              disabled={forkLoading}
              class="p-2 text-gray-400 hover:text-teal-600 hover:bg-teal-50 rounded transition-colors"
              title="Create fork"
            >
              {#if forkLoading}
                <i class="fas fa-spinner fa-spin text-sm"></i>
              {:else}
                <i class="fas fa-code-branch text-sm"></i>
              {/if}
            </button>
            <button
              on:click={() => downloadRelic(relicId, relic.name, relic.content_type)}
              class="p-2 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
              title="Download relic"
            >
              <i class="fas fa-download text-sm"></i>
            </button>
          </div>
        </div>

        <!-- Status Badges Row -->
        <div class="flex items-center flex-wrap gap-2 mb-3">
          <!-- Status Badges -->
          {#if relic.access_level === 'private'}
            <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium leading-none" style="background-color: #fce3eb; color: #76306c;" title="Private - accessible only via URL">
              <i class="fas fa-lock text-[10px]"></i>
              <span class="hidden sm:inline">Private</span>
            </span>
          {:else if relic.access_level === 'public'}
            <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium leading-none" style="background-color: #e2f2fd; color: #217db1;" title="Public - discoverable">
              <i class="fas fa-globe text-[10px]"></i>
              <span class="hidden sm:inline">Public</span>
            </span>
          {/if}
          {#if relic.fork_of}
            <a href="/{relic.fork_of}" class="inline-flex items-center gap-1.5 px-2 py-1 bg-teal-100 text-teal-700 rounded text-xs font-medium leading-none hover:bg-teal-200 transition-colors" title="Fork of {relic.fork_of}">
              <i class="fas fa-code-branch text-[10px]"></i>
              <span>Fork of <span class="font-mono">{relic.fork_of.substring(0, 8)}</span></span>
            </a>
          {/if}
          {#if relic.password_hash}
            <span class="inline-flex items-center gap-1.5 px-2 py-1 bg-amber-100 text-amber-700 rounded text-xs font-medium leading-none" title="Password protected">
              <i class="fas fa-key text-[10px]"></i>
            </span>
          {/if}
          {#if relic.expires_at}
            <span class="inline-flex items-center gap-1.5 px-2 py-1 bg-orange-100 text-orange-700 rounded text-xs font-medium leading-none" title="Expires {new Date(relic.expires_at).toLocaleDateString()}">
              <i class="fas fa-clock text-[10px]"></i>
              <span class="hidden sm:inline text-[11px]">{new Date(relic.expires_at).toLocaleDateString()}</span>
            </span>
          {/if}
        </div>

        <!-- Compact Metadata Row -->
        <div class="flex items-center justify-between flex-wrap gap-3">
          <div class="flex items-center flex-wrap gap-3 text-sm text-gray-700 font-mono">
            <!-- ID with copy -->
            <div class="flex items-center gap-1.5 group">
              <i class="fas fa-fingerprint text-gray-400"></i>
              <span>{relicId}</span>
              <button
                on:click={() => copyRelicId(relicId)}
                class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-gray-600 transition-opacity"
                title="Copy ID"
              >
                <i class="fas fa-copy text-xs"></i>
              </button>
            </div>

            <!-- Size -->
            <span class="flex items-center gap-1.5">
              <i class="fas fa-weight text-gray-400"></i>
              <span>{formatFileSize(relic.size_bytes)}</span>
            </span>

            <!-- Views -->
            <span class="flex items-center gap-1.5">
              <i class="fas fa-eye text-gray-400"></i>
              <span>{relic.access_count}</span>
            </span>

            <!-- Created -->
            <span class="flex items-center gap-1.5">
              <i class="fas fa-clock text-gray-400"></i>
              <span>{new Date(relic.created_at).toLocaleDateString()}</span>
            </span>
          </div>

          <!-- View Controls (Full-Width Toggle and Preview/Source Tabs) -->
          <div class="flex items-center gap-2">
            <!-- Full-Width Toggle -->
            <button
              on:click={() => isFullWidth = !isFullWidth}
              class="px-2 py-1 rounded text-xs font-medium transition-colors {isFullWidth ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
              title={isFullWidth ? 'Normal width' : 'Full width'}
            >
              <i class="fas {isFullWidth ? 'fa-compress' : 'fa-expand'}"></i>
            </button>

            <!-- Editor Controls (for code, text, markdown/html source) -->
            {#if processed && (processed.type === 'code' || processed.type === 'text' || (processed.type === 'markdown' && showMarkdownSource) || (processed.type === 'html' && showHtmlSource))}
              <div class="flex items-center gap-1 border-l border-gray-300 pl-2 ml-2">
                <button
                  on:click={() => showSyntaxHighlighting = !showSyntaxHighlighting}
                  class="px-2 py-1 rounded text-xs font-medium transition-colors {showSyntaxHighlighting ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
                  title="Toggle syntax highlighting"
                >
                  <i class="fas fa-palette text-xs"></i>
                </button>
                <button
                  on:click={() => showLineNumbers = !showLineNumbers}
                  class="px-2 py-1 rounded text-xs font-medium transition-colors {showLineNumbers ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
                  title="Toggle line numbers"
                >
                  <i class="fas fa-list-ol text-xs"></i>
                </button>
              </div>
            {/if}

            <!-- Preview/Source Tabs (for Markdown and HTML) -->
            {#if processed?.type === 'markdown'}
              <div class="flex items-center gap-1">
                <button
                  on:click={() => showMarkdownSource = false}
                  class="px-2 py-1 rounded text-xs font-medium transition-colors {!showMarkdownSource ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
                  title="Show preview"
                >
                  <i class="fas fa-eye"></i>
                </button>
                <button
                  on:click={() => showMarkdownSource = true}
                  class="px-2 py-1 rounded text-xs font-medium transition-colors {showMarkdownSource ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
                  title="Show source"
                >
                  <i class="fas fa-file-code"></i>
                </button>
              </div>
            {:else if processed?.type === 'html'}
              <div class="flex items-center gap-1">
                <button
                  on:click={() => showHtmlSource = false}
                  class="px-2 py-1 rounded text-xs font-medium transition-colors {!showHtmlSource ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
                  title="Show preview"
                >
                  <i class="fas fa-eye"></i>
                </button>
                <button
                  on:click={() => showHtmlSource = true}
                  class="px-2 py-1 rounded text-xs font-medium transition-colors {showHtmlSource ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
                  title="Show source"
                >
                  <i class="fas fa-file-code"></i>
                </button>
              </div>
            {/if}
          </div>
        </div>

        <!-- Optional Description -->
        {#if relic.description}
          <div class="mt-3 pt-3 border-t border-gray-100">
            <p class="text-sm text-gray-700 leading-relaxed">{relic.description}</p>
          </div>
        {/if}
      </div>

      <!-- Content -->
      {#if processed}
        {#if processed.type === 'markdown'}
          <div class="border-t border-gray-200">
            {#if !showMarkdownSource}
              <!-- Rendered Markdown - natural height -->
              <div class="p-6 prose prose-sm max-w-none">
                {@html processed.html}
              </div>
            {:else}
              <!-- Markdown Source Editor - fixed height for editor -->
              <MonacoEditor
                value={processed.preview || ''}
                language="markdown"
                readOnly={true}
                height="calc(100vh - 300px)"
                relicId={relicId}
                noWrapper={true}
                {showSyntaxHighlighting}
                {showLineNumbers}
                on:line-clicked={handleLineClicked}
                on:line-range-selected={handleLineRangeSelected}
                on:multi-line-selected={handleMultiLineSelected}
                on:line-copied={handleLineCopied}
              />
            {/if}
          </div>
        {:else if processed.type === 'html'}
          <div class="border-t border-gray-200">
            {#if !showHtmlSource}
              <!-- HTML Preview Frame -->
              <div style="height: calc(100vh - 300px);">
                <iframe
                  srcdoc={processed.html}
                  class="w-full h-full border-0"
                  sandbox="allow-same-origin allow-scripts allow-forms"
                  title="HTML Content Preview"
                ></iframe>
              </div>
            {:else}
              <!-- HTML Source Editor -->
              <MonacoEditor
                value={processed.html || ''}
                language="html"
                readOnly={true}
                height="calc(100vh - 300px)"
                relicId={relicId}
                noWrapper={true}
                {showSyntaxHighlighting}
                {showLineNumbers}
                on:line-clicked={handleLineClicked}
                on:line-range-selected={handleLineRangeSelected}
                on:multi-line-selected={handleMultiLineSelected}
                on:line-copied={handleLineCopied}
              />
            {/if}
          </div>
        {:else if processed.type === 'code'}
          <div class="border-t border-gray-200">
            <MonacoEditor
              value={processed.preview || ''}
              language={processed.metadata?.language || 'plaintext'}
              readOnly={true}
              height="calc(100vh - 300px)"
              relicId={relicId}
              noWrapper={true}
              {showSyntaxHighlighting}
              {showLineNumbers}
              on:line-clicked={handleLineClicked}
              on:line-range-selected={handleLineRangeSelected}
              on:multi-line-selected={handleMultiLineSelected}
              on:line-copied={handleLineCopied}
            />
          </div>
        {:else if processed.type === 'text'}
          <div class="border-t border-gray-200">
            <MonacoEditor
              value={processed.preview || ''}
              language="plaintext"
              readOnly={true}
              height="calc(100vh - 300px)"
              relicId={relicId}
              noWrapper={true}
              {showSyntaxHighlighting}
              {showLineNumbers}
              on:line-clicked={handleLineClicked}
              on:line-range-selected={handleLineRangeSelected}
              on:multi-line-selected={handleMultiLineSelected}
              on:line-copied={handleLineCopied}
            />
          </div>
          {#if processed.truncated}
            <div class="bg-blue-50 border-t border-gray-200 px-6 py-4 text-center text-sm text-blue-700 rounded-b-lg">
              Content truncated. <a href="/{relicId}/raw" class="font-semibold hover:underline">Download full file</a>
            </div>
          {/if}
        {:else if processed.type === 'image'}
          <div class="border-t border-gray-200 p-6">
            <img src={processed.url} alt={relic.name} class="max-w-full h-auto rounded" />
          </div>
        {:else if processed.type === 'csv'}
          <div class="border-t border-gray-200 p-6">
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
          <div class="border-t border-gray-200 p-6 text-center">
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
        <div class="border-t border-gray-200 p-6 text-center">
          <i class="fas fa-file text-gray-400 text-6xl mb-4"></i>
          <p class="text-gray-600">Loading preview...</p>
        </div>
      {/if}
    </div>
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
