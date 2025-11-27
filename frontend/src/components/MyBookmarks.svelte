<script>
  import { onMount } from 'svelte'
  import { showToast } from '../stores/toastStore'
  import { getClientBookmarks, removeBookmark } from '../services/api'
  import { shareRelic, copyRelicContent, downloadRelic, viewRaw } from '../services/relicActions'
  import { getTypeLabel, formatBytes } from '../services/typeUtils'

  let bookmarks = []
  let loading = true
  let searchTerm = ''
  let currentPage = 1
  let itemsPerPage = 20

  function getDefaultItemsPerPage() {
    if (typeof window === 'undefined') return 20
    const width = window.innerWidth
    if (width < 768) return 10      // Mobile
    return 20                        // Tablet & Desktop
  }

  function formatTimeAgo(dateString) {
    const now = new Date()
    const date = new Date(dateString)
    const diffInSeconds = Math.floor((now - date) / 1000)

    if (diffInSeconds < 60) return 'just now'
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
    return `${Math.floor(diffInSeconds / 86400)}d ago`
  }

  async function loadBookmarks() {
    try {
      loading = true
      const response = await getClientBookmarks()
      bookmarks = response.data.bookmarks || []
    } catch (error) {
      console.error('Failed to load bookmarks:', error)
      showToast('Failed to load bookmarks', 'error')
      bookmarks = []
    } finally {
      loading = false
    }
  }

  async function handleRemoveBookmark(relicId, relicName) {
    if (!confirm(`Remove bookmark for "${relicName || 'Untitled'}"?`)) {
      return
    }

    try {
      await removeBookmark(relicId)
      showToast('Bookmark removed', 'success')
      // Reload the bookmarks list
      await loadBookmarks()
    } catch (error) {
      console.error('Failed to remove bookmark:', error)
      showToast('Failed to remove bookmark', 'error')
    }
  }

  function copyRelicId(relicId) {
    navigator.clipboard.writeText(relicId).then(() => {
      // You could add a toast notification here if desired
    })
  }

  $: filteredBookmarks = bookmarks.filter(bookmark => {
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return (
      (bookmark.name && bookmark.name.toLowerCase().includes(term)) ||
      bookmark.id.toLowerCase().includes(term) ||
      (bookmark.content_type && getTypeLabel(bookmark.content_type).toLowerCase().includes(term))
    )
  })

  $: totalPages = Math.ceil(filteredBookmarks.length / itemsPerPage)

  $: paginatedBookmarks = (() => {
    const start = (currentPage - 1) * itemsPerPage
    const end = start + itemsPerPage
    return filteredBookmarks.slice(start, end)
  })()

  function goToPage(page) {
    currentPage = Math.max(1, Math.min(page, totalPages))
  }

  onMount(() => {
    itemsPerPage = getDefaultItemsPerPage()
    loadBookmarks()
  })
</script>

<div class="px-4 sm:px-0">
  <div class="bg-white shadow-sm rounded-lg border border-gray-200">
    <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
      <h2 class="text-lg font-semibold text-gray-900 flex items-center">
        <i class="fas fa-bookmark text-amber-600 mr-2"></i>
        My Bookmarks
      </h2>
      <div class="relative flex-1 max-w-md ml-4">
        <i class="fa-solid fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
        <input
          type="text"
          bind:value={searchTerm}
          placeholder="Filter by name, type, or id..."
          class="w-full pl-9 pr-3 py-1.5 text-sm maas-input"
        />
      </div>
    </div>

    {#if loading}
      <div class="p-8 text-center">
        <div class="inline-block">
          <i class="fas fa-spinner fa-spin text-[#772953] text-2xl"></i>
        </div>
        <p class="text-sm text-gray-500 mt-2">Loading bookmarks...</p>
      </div>
    {:else if filteredBookmarks.length === 0}
      <div class="p-8 text-center text-gray-500">
        <i class="fas fa-bookmark text-4xl mb-2"></i>
        <p>
          {searchTerm ? `No bookmarks found matching "${searchTerm}"` : 'No bookmarks yet'}
        </p>
        {#if !searchTerm}
          <p class="text-sm mt-2">Bookmark relics you want to save for later!</p>
        {/if}
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full maas-table text-sm">
          <thead>
            <tr class="text-gray-500 uppercase text-xs tracking-wider bg-gray-50">
              <th>Title / ID</th>
              <th>Type</th>
              <th>Bookmarked</th>
              <th>Size</th>
              <th class="w-40">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each paginatedBookmarks as bookmark (bookmark.id)}
              <tr class="hover:bg-gray-50 cursor-pointer">
                <td>
                  <a href="/{bookmark.id}" class="font-medium text-[#0066cc] hover:underline block">
                    {bookmark.name || 'Untitled'}
                  </a>
                  <div class="flex items-center group gap-1">
                    <span class="text-xs text-gray-400 font-mono">{bookmark.id}</span>
                    <button
                      on:click|stopPropagation={() => copyRelicId(bookmark.id)}
                      class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-gray-600 transition-all duration-200 -mt-0.5"
                      title="Copy ID"
                    >
                      <i class="fas fa-copy text-xs"></i>
                    </button>
                  </div>
                </td>
                <td>
                  <span class="text-sm">{getTypeLabel(bookmark.content_type)}</span>
                </td>
                <td class="text-gray-500 text-xs">
                  {formatTimeAgo(bookmark.bookmarked_at)}
                </td>
                <td class="font-mono text-xs">
                  {formatBytes(bookmark.size_bytes || 0)}
                </td>
                <td>
                  <div class="flex items-center gap-1">
                    <button
                      on:click|stopPropagation={() => shareRelic(bookmark.id)}
                      class="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                      title="Share relic"
                    >
                      <i class="fas fa-share text-xs"></i>
                    </button>
                    <button
                      on:click|stopPropagation={() => copyRelicContent(bookmark.id)}
                      class="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors"
                      title="Copy content to clipboard"
                    >
                      <i class="fas fa-copy text-xs"></i>
                    </button>
                    <button
                      on:click|stopPropagation={() => viewRaw(bookmark.id)}
                      class="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
                      title="View raw content"
                    >
                      <i class="fas fa-code text-xs"></i>
                    </button>
                    <button
                      on:click|stopPropagation={() => downloadRelic(bookmark.id, bookmark.name, bookmark.content_type)}
                      class="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                      title="Download relic"
                    >
                      <i class="fas fa-download text-xs"></i>
                    </button>
                    <button
                      on:click|stopPropagation={() => handleRemoveBookmark(bookmark.id, bookmark.name)}
                      class="p-1.5 text-amber-600 hover:text-amber-700 hover:bg-amber-50 rounded transition-colors"
                      title="Remove bookmark"
                    >
                      <i class="fas fa-bookmark-slash text-xs"></i>
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <div class="px-6 py-3 border-t border-gray-200 bg-gray-50 text-xs text-gray-500 flex justify-between items-center gap-6">
        <div class="flex items-center gap-4">
          <span>{filteredBookmarks.length} bookmark{filteredBookmarks.length !== 1 ? 's' : ''}</span>
          {#if filteredBookmarks.length > 0}
            <div class="flex items-center gap-2">
              <label for="items-per-page-bookmarks" class="text-gray-600">Per page:</label>
              <select
                id="items-per-page-bookmarks"
                bind:value={itemsPerPage}
                on:change={() => { currentPage = 1 }}
                class="pl-3 pr-8 py-1 border border-gray-300 rounded text-gray-700 bg-white hover:border-gray-400 cursor-pointer w-16"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>
          {/if}
        </div>

        {#if totalPages > 1}
          <div class="flex items-center gap-2 whitespace-nowrap">
            <span class="text-gray-600">
              Page {currentPage} of {totalPages}
            </span>
            <button
              on:click={() => goToPage(currentPage - 1)}
              disabled={currentPage === 1}
              class="px-3 py-1 border border-gray-300 rounded text-gray-700 hover:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:hover:bg-gray-50 transition-colors"
              title="Previous page"
            >
              <i class="fas fa-chevron-left text-xs"></i>
            </button>
            <button
              on:click={() => goToPage(currentPage + 1)}
              disabled={currentPage === totalPages}
              class="px-3 py-1 border border-gray-300 rounded text-gray-700 hover:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:hover:bg-gray-50 transition-colors"
              title="Next page"
            >
              <i class="fas fa-chevron-right text-xs"></i>
            </button>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>
