<script>
  import { onMount } from 'svelte';
  import { showToast } from '../stores/toastStore';
  import { getClientRelics, deleteRelic } from '../services/api';
  import { getDefaultItemsPerPage, getTypeLabel } from '../services/typeUtils';
  import { filterRelics, calculateTotalPages, paginateData, clampPage } from '../services/utils/paginationUtils';
  import RelicTable from './RelicTable.svelte';
  import EditRelicModal from './EditRelicModal.svelte';

  let relics = []
  let loading = true
  let searchTerm = ''
  let currentPage = 1
  let itemsPerPage = 20
  let showEditModal = false
  let selectedRelic = null

  // Use the shared filter utility
  $: filteredRelics = filterRelics(relics, searchTerm, getTypeLabel)

  // Calculate pagination using shared utilities
  $: totalPages = calculateTotalPages(filteredRelics, itemsPerPage)
  $: paginatedRelics = paginateData(filteredRelics, currentPage, itemsPerPage)

  async function loadMyRelics() {
    try {
      loading = true
      const response = await getClientRelics()
      relics = response.data.relics || []
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

  function goToPage(page) {
    currentPage = clampPage(page, totalPages)
  }

  onMount(() => {
    itemsPerPage = getDefaultItemsPerPage()
    loadMyRelics()
  })
</script>

<div class="px-4 sm:px-0">
  <RelicTable
    data={filteredRelics}
    {loading}
    bind:searchTerm
    bind:currentPage
    bind:itemsPerPage
    {totalPages}
    paginatedData={paginatedRelics}
    title="My Relics"
    titleIcon="fa-user"
    titleIconColor="text-blue-600"
    emptyMessage="No relics yet"
    emptyMessageWithSearch="No relics found"
    emptyIcon="fa-inbox"
    emptyAction="Create your first relic to get started!"
    tableId="my-relics"
    onEdit={handleEditRelic}
    onDelete={handleDeleteRelic}
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
