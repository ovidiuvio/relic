<script>
  import { onMount } from 'svelte'
  import { showToast } from '../stores/toastStore'
  import { getClientBookmarks, removeBookmark } from '../services/api'
  import { getDefaultItemsPerPage, getTypeLabel } from '../services/typeUtils'
  import { filterRelics, calculateTotalPages, paginateData, clampPage } from '../services/utils/paginationUtils'
  import RelicTable from './RelicTable.svelte'

  export let tagFilter = null

  let bookmarks = []
  let loading = true
  let searchTerm = ''
  let currentPage = 1
  let itemsPerPage = 20

  // Use shared filter utility
  $: filteredBookmarks = filterRelics(bookmarks, searchTerm, getTypeLabel)
  // Apply tag filter if present
  $: tableBookmarks = tagFilter 
    ? filteredBookmarks.filter(b => b.tags && b.tags.some(t => (typeof t === 'string' ? t : t.name).toLowerCase() === tagFilter.toLowerCase()))
    : filteredBookmarks

  // Calculate pagination using shared utilities
  $: totalPages = calculateTotalPages(tableBookmarks, itemsPerPage)
  $: paginatedBookmarks = paginateData(tableBookmarks, currentPage, itemsPerPage)

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

  async function handleRemoveBookmark(bookmark) {
    if (!confirm(`Remove bookmark for "${bookmark.name || 'Untitled'}"?`)) {
      return
    }

    try {
      await removeBookmark(bookmark.id)
      showToast('Bookmark removed', 'success')
      // Reload the bookmarks list
      await loadBookmarks()
    } catch (error) {
      console.error('Failed to remove bookmark:', error)
      showToast('Failed to remove bookmark', 'error')
    }
  }

  function goToPage(page) {
    currentPage = clampPage(page, totalPages)
  }

  onMount(() => {
    itemsPerPage = getDefaultItemsPerPage()
    loadBookmarks()
  })
</script>

<div class="px-4 sm:px-0">
  <RelicTable
    data={tableBookmarks}
    {loading}
    bind:searchTerm
    bind:currentPage
    bind:itemsPerPage
    {totalPages}
    paginatedData={paginatedBookmarks}
    title="My Bookmarks"
    titleIcon="fa-bookmark"
    titleIconColor="text-amber-600"
    {tagFilter}
    columnHeaders={{
      title: 'Title / ID',
      type: 'Type',
      date: 'Bookmarked',
      size: 'Size',
      actions: 'Actions'
    }}
    emptyMessage="No bookmarks yet"
    emptyMessageWithSearch="No bookmarks found"
    emptyIcon="fa-bookmark"
    emptyAction="Bookmark relics you want to save for later!"
    tableId="my-bookmarks"
    onRemoveBookmark={handleRemoveBookmark}
    on:tag-click
    on:clear-tag-filter={() => {
      window.history.pushState({}, "", "/my-bookmarks");
      window.dispatchEvent(new PopStateEvent('popstate'));
    }}
    {goToPage}
  />
</div>
