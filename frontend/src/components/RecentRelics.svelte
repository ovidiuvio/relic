<script>
  import { onMount } from 'svelte';
  import { listRelics } from '../services/api';
  import { getDefaultItemsPerPage, getTypeLabel } from '../services/typeUtils';
  import { filterRelics, sortData, calculateTotalPages, paginateData, clampPage } from '../services/utils/paginationUtils';
  import { showToast } from '../stores/toastStore';
  import RelicTable from './RelicTable.svelte';

  export let tagFilter = null

  let relics = []
  let loading = true
  let searchTerm = ''
  let currentPage = 1
  let itemsPerPage = 25
  let sortBy = 'date'
  let sortOrder = 'desc'

  // Use shared filter utility
  $: filteredRelics = filterRelics(relics, searchTerm, getTypeLabel)
  
  // Apply sorting
  $: sortedRelics = sortData(filteredRelics, sortBy, sortOrder)

  // Calculate pagination using shared utilities
  $: totalPages = calculateTotalPages(sortedRelics, itemsPerPage)
  $: paginatedRelics = paginateData(sortedRelics, currentPage, itemsPerPage)

  function goToPage(page) {
    currentPage = clampPage(page, totalPages)
  }

  async function loadRelics() {
    try {
      loading = true
      const response = await listRelics(1000, tagFilter)
      relics = response.data.relics || []
      currentPage = 1
    } catch (error) {
      showToast('Failed to load recent relics', 'error')
      console.error('Error loading relics:', error)
    } finally {
      loading = false
    }
  }

  $: if (tagFilter !== undefined) {
    loadRelics()
  }

  onMount(async () => {
    itemsPerPage = getDefaultItemsPerPage()
    await loadRelics()
  })
</script>

<div class="mb-8">
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
    title="Recent Relics"
    titleIcon="fa-clock"
    titleIconColor="text-blue-600"
    {tagFilter}
    emptyMessage="No relics yet"
    emptyMessageWithSearch="No relics found"
    emptyIcon="fa-inbox"
    tableId="recent-relics"
    showForkButton={false}
    on:tag-click
    on:clear-tag-filter={() => {
      window.history.pushState({}, "", "/recent");
      window.dispatchEvent(new PopStateEvent('popstate'));
    }}
    {goToPage}
  />
</div>
