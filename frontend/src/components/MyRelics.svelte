<script>
  import { onMount } from 'svelte';
  import { showToast } from '../stores/toastStore';
  import { getClientRelics, deleteRelic } from '../services/api';
  import { getDefaultItemsPerPage, getTypeLabel } from '../services/typeUtils';
  import { filterRelics } from '../services/utils/paginationUtils';
  import RelicTable from './RelicTable.svelte';

  let relics = []
  let loading = true
  let searchTerm = ''
  let currentPage = 1
  let itemsPerPage = 20

  // Use the shared filter utility
  $: filteredRelics = filterRelics(relics, searchTerm, getTypeLabel)

  // Calculate pagination
  $: totalPages = Math.ceil(filteredRelics.length / itemsPerPage)
  $: paginatedRelics = (() => {
    const start = (currentPage - 1) * itemsPerPage
    const end = start + itemsPerPage
    return filteredRelics.slice(start, end)
  })()

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
    currentPage = Math.max(1, Math.min(page, totalPages))
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
    onDelete={handleDeleteRelic}
    {goToPage}
  />
</div>
