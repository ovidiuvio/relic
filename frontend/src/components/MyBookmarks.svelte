<script>
  import { onMount } from 'svelte'
  import { showToast } from '../stores/toastStore'
  import { getClientBookmarks, removeBookmark } from '../services/api'
  import { getDefaultItemsPerPage } from '../services/typeUtils'
  import { createReloader } from '../services/utils/paginationUtils'
  import RelicTable from './RelicTable.svelte'

  export let tagFilter = null

  let bookmarks = []
  let loading = true
  let searchTerm = ''
  let currentPage = 1
  let itemsPerPage = 20
  let total = 0
  let sortBy = 'date'
  let sortOrder = 'desc'

  let showConfirm = false
  let bookmarkToRemove = null

  // Server-side pagination
  $: totalPages = Math.max(1, Math.ceil(total / itemsPerPage))

  function goToPage(page) {
    if (page >= 1 && page <= totalPages) loadBookmarks(page)
  }

  function handleSort(event) {
    sortBy = event.detail.sortBy
    sortOrder = event.detail.sortOrder
    loadBookmarks(1)
  }

  const reloader = createReloader()

  $: if (searchTerm !== undefined) reloader.debounce(() => loadBookmarks(1))
  $: if (reloader.tagChanged(tagFilter)) loadBookmarks(1)

  async function loadBookmarks(page = 1) {
    const gen = reloader.gen()
    try {
      loading = true
      const response = await getClientBookmarks({
        tag: tagFilter || undefined,
        search: searchTerm || undefined,
        sort_by: sortBy === 'date' ? 'created_at' : sortBy === 'title' ? 'name' : sortBy,
        sort_order: sortOrder,
        limit: itemsPerPage,
        offset: (page - 1) * itemsPerPage,
      })
      if (reloader.stale(gen)) return
      bookmarks = response.data.bookmarks || []
      total = response.data.total || 0
      currentPage = page
    } catch (error) {
      if (reloader.stale(gen)) return
      console.error('Failed to load bookmarks:', error)
      showToast('Failed to load bookmarks', 'error')
      bookmarks = []
    } finally {
      if (!reloader.stale(gen)) loading = false
    }
  }

  function handleRemoveBookmark(bookmark) {
    bookmarkToRemove = bookmark
    showConfirm = true
  }

  async function executeRemoveBookmark() {
    if (!bookmarkToRemove) return

    showConfirm = false
    try {
      await removeBookmark(bookmarkToRemove.id)
      showToast('Bookmark removed', 'success')
      const newPage = bookmarks.length === 1 && currentPage > 1 ? currentPage - 1 : currentPage
      await loadBookmarks(newPage)
    } catch (error) {
      console.error('Failed to remove bookmark:', error)
      showToast('Failed to remove bookmark', 'error')
    } finally {
      bookmarkToRemove = null
    }
  }

  onMount(async () => {
    itemsPerPage = getDefaultItemsPerPage()
    await loadBookmarks(1)
    reloader.setReady()
  })
</script>

<div class="px-4 sm:px-0">
  <RelicTable
    data={bookmarks}
    {loading}
    bind:searchTerm
    bind:currentPage
    bind:itemsPerPage
    {sortBy}
    {sortOrder}
    {totalPages}
    total={total}
    paginatedData={bookmarks}
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
    on:sort={handleSort}
    on:tag-click
    on:clear-tag-filter={() => {
      window.history.pushState({}, "", "/my-bookmarks");
      window.dispatchEvent(new PopStateEvent('popstate'));
    }}
    {goToPage}
  />
</div>

{#if showConfirm}
  <div class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-lg shadow-xl max-w-sm w-full p-6">
      <p class="text-sm text-gray-700 mb-6">Remove bookmark for "{bookmarkToRemove?.name || 'Untitled'}"?</p>
      <div class="flex justify-end gap-3">
        <button class="maas-btn-secondary" on:click={() => { showConfirm = false; bookmarkToRemove = null; }}>Cancel</button>
        <button class="maas-btn-primary" on:click={executeRemoveBookmark}>Remove</button>
      </div>
    </div>
  </div>
{/if}
