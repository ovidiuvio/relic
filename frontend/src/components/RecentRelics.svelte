<script>
  import { onMount } from 'svelte';
  import { listRelics } from '../services/api';
  import { getDefaultItemsPerPage, getTypeLabel } from '../services/typeUtils';
  import { filterRelics, calculateTotalPages, paginateData, clampPage } from '../services/utils/paginationUtils';
  import { showToast } from '../stores/toastStore';
  import RelicTable from './RelicTable.svelte';

  let relics = []
  let loading = true
  let searchTerm = ''
  let currentPage = 1
  let itemsPerPage = 25

  // Use shared filter utility
  $: filteredRelics = filterRelics(relics, searchTerm, getTypeLabel)

  // Calculate pagination using shared utilities
  $: totalPages = calculateTotalPages(filteredRelics, itemsPerPage)
  $: paginatedRelics = paginateData(filteredRelics, currentPage, itemsPerPage)

  function goToPage(page) {
    currentPage = clampPage(page, totalPages)
  }

  onMount(async () => {
    itemsPerPage = getDefaultItemsPerPage()
    try {
      const response = await listRelics()
      relics = response.data.relics || []
      currentPage = 1
    } catch (error) {
      showToast('Failed to load recent relics', 'error')
      console.error('Error loading relics:', error)
    } finally {
      loading = false
    }
  })
</script>

<div class="mb-8">
  <RelicTable
    data={filteredRelics}
    {loading}
    bind:searchTerm
    bind:currentPage
    bind:itemsPerPage
    {totalPages}
    paginatedData={paginatedRelics}
    title="Recent Relics"
    titleIcon="fa-clock"
    titleIconColor="text-blue-600"
    emptyMessage="No relics yet"
    emptyMessageWithSearch="No relics found"
    emptyIcon="fa-inbox"
    tableId="recent-relics"
    showForkButton={false}
    {goToPage}
  />
</div>
