<script>
  import { onMount } from 'svelte';
  import { listRelics } from '../services/api';
  import { getDefaultItemsPerPage } from '../services/typeUtils';
  import { createReloader } from '../services/utils/paginationUtils';
  import { showToast } from '../stores/toastStore';
  import { getFilesFromDrop } from '../services/utils/fileProcessing';
  import RelicTable from './RelicTable.svelte';
  import RelicDropModal from './RelicDropModal.svelte';

  export let tagFilter = null

  let relics = []
  let loading = true
  let searchTerm = ''
  let currentPage = 1
  let itemsPerPage = 25
  let total = 0
  let sortBy = 'date'
  let sortOrder = 'desc'

  // Drop handling state
  let showDropModal = false
  let droppedFiles = []
  let isDraggingOver = false

  // Server-side pagination
  $: totalPages = Math.max(1, Math.ceil(total / itemsPerPage))

  function goToPage(page) {
    if (page >= 1 && page <= totalPages) loadRelics(page)
  }

  function handleSort(event) {
    sortBy = event.detail.sortBy
    sortOrder = event.detail.sortOrder
    loadRelics(1)
  }

  const reloader = createReloader()

  $: if (searchTerm !== undefined) reloader.debounce(() => loadRelics(1))
  $: if (reloader.tagChanged(tagFilter)) loadRelics(1)

  async function loadRelics(page = 1) {
    try {
      loading = true
      const response = await listRelics(itemsPerPage, (page - 1) * itemsPerPage, tagFilter, searchTerm || null, sortBy === 'date' ? 'created_at' : sortBy === 'title' ? 'name' : sortBy, sortOrder)
      relics = response.data.relics || []
      total = response.data.total || 0
      currentPage = page
    } catch (error) {
      showToast('Failed to load recent relics', 'error')
      console.error('Error loading relics:', error)
    } finally {
      loading = false
    }
  }

  function handleDragOver(e) {
    e.preventDefault()
    isDraggingOver = true
  }

  function handleDragLeave(e) {
    e.preventDefault()
    isDraggingOver = false
  }

  async function handleDrop(e) {
    e.preventDefault()
    isDraggingOver = false

    const files = await getFilesFromDrop(e.dataTransfer)
    if (files.length > 0) {
      droppedFiles = files
      showDropModal = true
    }
  }

  function handleUploadSuccess() {
    showDropModal = false
    loadRelics(1)
  }

  onMount(async () => {
    itemsPerPage = getDefaultItemsPerPage()
    await loadRelics(1)
    reloader.setReady()
  })
</script>

<div 
  class="mb-8 relative min-h-[400px]"
  on:dragover={handleDragOver}
  on:dragleave={handleDragLeave}
  on:drop={handleDrop}
  role="region"
  aria-label="Recent Relics Drop Zone"
>
  {#if isDraggingOver}
    <div class="absolute inset-0 z-[100] bg-blue-50/80 backdrop-blur-[2px] border-4 border-dashed border-blue-400 rounded-lg flex flex-col items-center justify-center animate-in fade-in duration-200">
      <div class="w-20 h-20 bg-white rounded-full shadow-xl flex items-center justify-center text-blue-500 mb-6 border-4 border-blue-100">
        <i class="fas fa-cloud-upload-alt text-4xl animate-bounce"></i>
      </div>
      <h3 class="text-2xl font-bold text-blue-700">Drop files to upload</h3>
      <p class="text-blue-500 font-medium mt-2">Uploading as global relics</p>
    </div>
  {/if}
  <RelicTable
    data={relics}
    {loading}
    bind:searchTerm
    bind:currentPage
    bind:itemsPerPage
    {sortBy}
    {sortOrder}
    {totalPages}
    total={total}
    paginatedData={relics}
    title="Recent Relics"
    titleIcon="fa-clock"
    titleIconColor="text-blue-600"
    {tagFilter}
    emptyMessage="No relics yet"
    emptyMessageWithSearch="No relics found"
    emptyIcon="fa-inbox"
    tableId="recent-relics"
    showForkButton={false}
    on:sort={handleSort}
    on:tag-click
    on:clear-tag-filter={() => {
      window.history.pushState({}, "", "/recent");
      window.dispatchEvent(new PopStateEvent('popstate'));
    }}
    {goToPage}
  />
</div>

{#if showDropModal}
  <RelicDropModal
    files={droppedFiles}
    on:close={() => showDropModal = false}
    on:success={handleUploadSuccess}
  />
{/if}
