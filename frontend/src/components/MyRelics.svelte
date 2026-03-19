<script>
  import { onMount } from 'svelte';
  import { showToast } from '../stores/toastStore';
  import { getClientRelics, deleteRelic } from '../services/api';
  import { getDefaultItemsPerPage, getTypeLabel } from '../services/typeUtils';
  import { filterRelics, sortData, calculateTotalPages, paginateData, clampPage } from '../services/utils/paginationUtils';
  import RelicTable from './RelicTable.svelte';
  import EditRelicModal from './EditRelicModal.svelte';
  import RelicDropModal from './RelicDropModal.svelte';
  import { getFilesFromDrop } from '../services/utils/fileProcessing';

  export let tagFilter = null

  let relics = []
  let loading = true
  let searchTerm = ''
  let currentPage = 1
  let itemsPerPage = 20
  let showEditModal = false
  let selectedRelic = null
  let sortBy = 'date'
  let sortOrder = 'desc'

  // Drop handling state
  let showDropModal = false
  let droppedFiles = []
  let isDraggingOver = false

  // Use the shared filter utility
  $: filteredRelics = filterRelics(relics, searchTerm, getTypeLabel)

  // Apply sorting
  $: sortedRelics = sortData(filteredRelics, sortBy, sortOrder)

  // Calculate pagination using shared utilities
  $: totalPages = calculateTotalPages(sortedRelics, itemsPerPage)
  $: paginatedRelics = paginateData(sortedRelics, currentPage, itemsPerPage)

  async function loadMyRelics() {
    try {
      loading = true
      const response = await getClientRelics(tagFilter)
      relics = response.data.relics || []
    } catch (error) {
      console.error('Failed to load client relics:', error)
      showToast('Failed to load your relics', 'error')
      relics = []
    } finally {
      loading = false
    }
  }

  $: if (tagFilter !== undefined) {
    loadMyRelics()
  }

  function handleEditRelic(relic) {
    selectedRelic = relic
    showEditModal = true
  }

  function handleEditModalClose() {
    showEditModal = false
    selectedRelic = null
  }

  function handleEditModalUpdate(event) {
    const updatedRelic = event.detail
    if (updatedRelic) {
      // Update the relic in the list
      relics = relics.map(r => r.id === updatedRelic.id ? { ...r, ...updatedRelic } : r)
    }
    handleEditModalClose()
  }

  async function handleDeleteRelic(relic) {
    if (!confirm(`Are you sure you want to delete "${relic.name || 'Untitled'}"? This action cannot be undone.`)) {
      return
    }

    try {
      await deleteRelic(relic.id)
      showToast('Relic deleted successfully', 'success')
      // Reload the relics list
      await loadMyRelics()
    } catch (error) {
      console.error('Failed to delete relic:', error)
      showToast('Failed to delete relic', 'error')
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
    loadMyRelics()
  }

  function goToPage(page) {
    currentPage = clampPage(page, totalPages)
  }

  onMount(() => {
    itemsPerPage = getDefaultItemsPerPage()
    loadMyRelics()
  })
</script>

<div 
  class="px-4 sm:px-0 relative min-h-[400px]"
  on:dragover={handleDragOver}
  on:dragleave={handleDragLeave}
  on:drop={handleDrop}
  role="region"
  aria-label="My Relics Drop Zone"
>
  {#if isDraggingOver}
    <div class="absolute inset-0 z-[100] bg-blue-50/80 backdrop-blur-[2px] border-4 border-dashed border-blue-400 rounded-lg flex flex-col items-center justify-center animate-in fade-in duration-200">
      <div class="w-20 h-20 bg-white rounded-full shadow-xl flex items-center justify-center text-blue-500 mb-6 border-4 border-blue-100">
        <i class="fas fa-cloud-upload-alt text-4xl animate-bounce"></i>
      </div>
      <h3 class="text-2xl font-bold text-blue-700">Drop files to upload</h3>
      <p class="text-blue-500 font-medium mt-2">Uploading to your collection</p>
    </div>
  {/if}
  <RelicTable
    data={sortedRelics}
    {loading}
    bind:searchTerm
    bind:currentPage
    bind:itemsPerPage
    bind:sortBy
    bind:sortOrder
    {totalPages}
    paginatedData={paginatedRelics}
    title="My Relics"
    titleIcon="fa-user"
    titleIconColor="text-blue-600"
    {tagFilter}
    emptyMessage="No relics yet"
    emptyMessageWithSearch="No relics found"
    emptyIcon="fa-inbox"
    emptyAction="Create your first relic to get started!"
    tableId="my-relics"
    onEdit={handleEditRelic}
    onDelete={handleDeleteRelic}
    on:tag-click
    on:clear-tag-filter={() => {
      window.history.pushState({}, "", "/my-relics");
      window.dispatchEvent(new PopStateEvent('popstate'));
    }}
    {goToPage}
  />
</div>

{#if selectedRelic}
  <EditRelicModal
    bind:show={showEditModal}
    relic={selectedRelic}
    on:close={handleEditModalClose}
    on:update={handleEditModalUpdate}
  />
{/if}

{#if showDropModal}
    <RelicDropModal
        files={droppedFiles}
        on:close={() => showDropModal = false}
        on:success={handleUploadSuccess}
    />
{/if}
