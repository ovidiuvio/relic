<script>
  import { onMount } from 'svelte';
  import { showToast } from '../stores/toastStore';
  import { getClientRelics, deleteRelic } from '../services/api';
  import { getDefaultItemsPerPage } from '../services/typeUtils';
  import RelicTable from './RelicTable.svelte';
  import EditRelicModal from './EditRelicModal.svelte';
  import RelicDropModal from './RelicDropModal.svelte'
  import ConfirmModal from './ConfirmModal.svelte';
  import { getFilesFromDrop } from '../services/utils/fileProcessing';

  export let tagFilter = null

  let relics = []
  let loading = true
  let searchTerm = ''
  let currentPage = 1
  let itemsPerPage = 20
  let total = 0
  let showEditModal = false
  let selectedRelic = null
  let sortBy = 'date'
  let sortOrder = 'desc'

  // Drop handling state
  let showDropModal = false
  let droppedFiles = []
  let isDraggingOver = false

  // Confirm modal state
  let showConfirm = false
  let confirmTitle = ''
  let confirmMessage = ''
  let confirmAction = null

  // Server-side pagination
  $: totalPages = Math.max(1, Math.ceil(total / itemsPerPage))

  function goToPage(page) {
    if (page >= 1 && page <= totalPages) loadMyRelics(page)
  }

  function handleSort(event) {
    sortBy = event.detail.sortBy
    sortOrder = event.detail.sortOrder
    loadMyRelics(1)
  }

  let relicsReady = false
  let searchTimer
  let prevTagFilter = tagFilter

  $: if (relicsReady && searchTerm !== undefined) {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(() => loadMyRelics(1), 300)
  }

  $: if (relicsReady && tagFilter !== prevTagFilter) {
    prevTagFilter = tagFilter
    loadMyRelics(1)
  }

  async function loadMyRelics(page = 1) {
    try {
      loading = true
      const response = await getClientRelics({
        tag: tagFilter || undefined,
        search: searchTerm || undefined,
        sort_by: sortBy === 'date' ? 'created_at' : sortBy,
        sort_order: sortOrder,
        limit: itemsPerPage,
        offset: (page - 1) * itemsPerPage,
      })
      relics = response.data.relics || []
      total = response.data.total || 0
      currentPage = page
    } catch (error) {
      console.error('Failed to load client relics:', error)
      showToast('Failed to load your relics', 'error')
      relics = []
    } finally {
      loading = false
    }
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

  function handleDeleteRelic(relic) {
    confirmTitle = 'Delete Relic'
    confirmMessage = `Are you sure you want to delete "${relic.name || 'Untitled'}"? This action cannot be undone.`
    confirmAction = async () => {
      showConfirm = false
      try {
        await deleteRelic(relic.id)
        showToast(`"${relic.name || 'Untitled'}" deleted successfully`, 'success')
        const newPage = relics.length === 1 && currentPage > 1 ? currentPage - 1 : currentPage
        await loadMyRelics(newPage)
      } catch (error) {
        console.error('Failed to delete relic:', error)
        showToast(`Could not delete "${relic.name || 'Untitled'}": ${error.response?.data?.detail || "check your connection and try again"}`, 'error')
      }
    }
    showConfirm = true
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
    loadMyRelics(1)
  }

  onMount(async () => {
    itemsPerPage = getDefaultItemsPerPage()
    await loadMyRelics(1)
    relicsReady = true
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
    on:sort={handleSort}
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

<ConfirmModal
  show={showConfirm}
  title={confirmTitle}
  message={confirmMessage}
  on:confirm={confirmAction}
  on:cancel={() => showConfirm = false}
/>
