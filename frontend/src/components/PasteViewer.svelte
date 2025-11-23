<script>
  import { onMount } from 'svelte'
  import { getPaste, getPasteRaw, getPasteHistory } from '../services/api'
  import { showToast } from '../stores/toastStore'

  export let pasteId = ''

  let paste = null
  let content = ''
  let loading = true
  let history = []
  let showHistory = false

  onMount(async () => {
    try {
      const pasteResponse = await getPaste(pasteId)
      paste = pasteResponse.data

      // For text content, fetch raw
      if (paste.content_type.startsWith('text/')) {
        const rawResponse = await getPasteRaw(pasteId)
        content = new TextDecoder().decode(rawResponse.data)
      }

      // Load history if this is part of a version chain
      if (paste.root_id) {
        const historyResponse = await getPasteHistory(pasteId)
        history = historyResponse.data.versions
      }
    } catch (error) {
      showToast('Failed to load paste', 'error')
      console.error('Error loading paste:', error)
    } finally {
      loading = false
    }
  })

  function downloadPaste() {
    const element = document.createElement('a')
    element.setAttribute('href', `/${pasteId}/raw`)
    element.setAttribute('download', paste.name || pasteId)
    element.style.display = 'none'
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
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
</script>

{#if loading}
  <div class="flex items-center justify-center py-12">
    <i class="fas fa-spinner fa-spin text-blue-600 text-4xl"></i>
  </div>
{:else if paste}
  <div class="max-w-7xl mx-auto px-4 py-6">
    <!-- Header -->
    <div class="bg-white shadow-sm rounded-lg border border-gray-200 mb-6">
      <div class="px-6 py-4">
        <div class="flex items-start justify-between mb-4">
          <div>
            <h1 class="text-2xl font-bold text-gray-900 mb-2">{paste.name || 'Untitled'}</h1>
            {#if paste.description}
              <p class="text-gray-600">{paste.description}</p>
            {/if}
          </div>
          <button
            on:click={downloadPaste}
            class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <i class="fas fa-download mr-2"></i>
            Download
          </button>
        </div>

        <!-- Metadata -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span class="text-gray-500">Type:</span>
            <span class="block font-mono text-gray-900">{paste.content_type}</span>
          </div>
          <div>
            <span class="text-gray-500">Size:</span>
            <span class="block font-mono text-gray-900">{formatFileSize(paste.size_bytes)}</span>
          </div>
          <div>
            <span class="text-gray-500">Views:</span>
            <span class="block font-mono text-gray-900">{paste.access_count}</span>
          </div>
          <div>
            <span class="text-gray-500">Version:</span>
            <span class="block font-mono text-gray-900">v{paste.version_number}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Content -->
    {#if paste.content_type.startsWith('text/')}
      <div class="bg-white shadow-sm rounded-lg border border-gray-200 mb-6 overflow-hidden">
        <pre class="p-6 bg-gray-900 text-gray-100 font-mono text-sm overflow-x-auto"><code>{content}</code></pre>
      </div>
    {:else if paste.content_type.startsWith('image/')}
      <div class="bg-white shadow-sm rounded-lg border border-gray-200 mb-6 p-6">
        <img src="/{pasteId}/raw" alt={paste.name} class="max-w-full h-auto rounded" />
      </div>
    {:else}
      <div class="bg-white shadow-sm rounded-lg border border-gray-200 mb-6 p-6 text-center">
        <i class="fas fa-file text-gray-400 text-6xl mb-4"></i>
        <p class="text-gray-600 mb-4">Binary file preview not available</p>
        <button
          on:click={downloadPaste}
          class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          <i class="fas fa-download mr-2"></i>
          Download File
        </button>
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
              <a href="/{version.id}" class="p-4 hover:bg-gray-50 transition-colors block">
                <div class="flex items-center justify-between">
                  <div>
                    <span class="font-medium text-gray-900">v{version.version}</span>
                    <span class="text-sm text-gray-500 ml-2">{version.name || 'Untitled'}</span>
                  </div>
                  <span class="text-sm text-gray-500">{new Date(version.created_at).toLocaleString()}</span>
                </div>
              </a>
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
      <p class="text-gray-600">Paste not found</p>
    </div>
  </div>
{/if}
