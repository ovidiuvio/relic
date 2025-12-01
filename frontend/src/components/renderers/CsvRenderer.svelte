<script>
  import { onMount } from 'svelte'

  export let processed

  let tableRef
  let filterText = ''
  let currentPage = 1
  let itemsPerPage = 50
  let sortColumn = null
  let sortDirection = 'asc'

  // Computed data with filtering and sorting
  $: filteredAndSortedData = processData(processed?.rows || [], filterText, sortColumn, sortDirection)

  function processData(rows, filter, sortCol, sortDir) {
    if (!rows || !Array.isArray(rows)) return []

    let filtered = rows

    // Apply text filter
    if (filter && filter.trim()) {
      const searchTerm = filter.toLowerCase().trim()
      console.log('CSV Filter Debug: Applying filter:', searchTerm)
      filtered = rows.filter(row => {
        return processed.metadata.columns.some(col => {
          const value = row[col]?.toString().toLowerCase() || ''
          return value.includes(searchTerm)
        })
      })
      console.log('CSV Filter Debug: Filter result:', filtered.length, 'rows')
    }

    // Apply sorting
    if (sortCol) {
      filtered = [...filtered].sort((a, b) => {
        const aVal = a[sortCol] || ''
        const bVal = b[sortCol] || ''

        // Try to compare as numbers
        const aNum = parseFloat(aVal)
        const bNum = parseFloat(bVal)
        if (!isNaN(aNum) && !isNaN(bNum)) {
          return sortDir === 'asc' ? aNum - bNum : bNum - aNum
        }

        // Compare as strings
        const aStr = aVal.toString().toLowerCase()
        const bStr = bVal.toString().toLowerCase()
        if (sortDir === 'asc') {
          return aStr.localeCompare(bStr)
        } else {
          return bStr.localeCompare(aStr)
        }
      })
    }

    return filtered
  }

  // Pagination
  $: totalPages = Math.ceil(filteredAndSortedData.length / itemsPerPage)
  $: paginatedData = filteredAndSortedData.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  // Sort handler
  function handleSort(column) {
    if (sortColumn === column) {
      sortDirection = sortDirection === 'asc' ? 'desc' : 'asc'
    } else {
      sortColumn = column
      sortDirection = 'asc'
    }
    currentPage = 1 // Reset to first page
  }

  // Pagination functions
  function goToPage(page) {
    currentPage = page
  }

  function changePageSize() {
    // Reset to first page when page size changes
    currentPage = 1
  }

  // Export function
  function exportToCSV() {
    const headers = processed.metadata.columns
    const csvContent = [
      headers.join(','),
      ...filteredAndSortedData.map(row =>
        headers.map(col => {
          const value = row[col] || ''
          // Escape commas and quotes
          if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
            return `"${value.replace(/"/g, '""')}"`
          }
          return value
        }).join(',')
      )
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = processed.fileName || 'data.csv'
    a.click()
    window.URL.revokeObjectURL(url)
  }

  function exportAllToCSV() {
    const headers = processed.metadata.columns
    const csvContent = [
      headers.join(','),
      ...processed.rows.map(row =>
        headers.map(col => {
          const value = row[col] || ''
          // Escape commas and quotes
          if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
            return `"${value.replace(/"/g, '""')}"`
          }
          return value
        }).join(',')
      )
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = (processed.fileName || 'all-data').replace(/\.[^/.]+$/, '') + '.csv'
    a.click()
    window.URL.revokeObjectURL(url)
  }

  // Utility functions for cell styling
  function getCellClass(value) {
    if (!value || value === '') return 'empty-cell'

    const strValue = value.toString()

    // Check if it's a number
    if (!isNaN(parseFloat(strValue)) && !isNaN(strValue)) {
      return 'numeric-cell'
    }

    // Check if it's a date
    if (strValue.match(/^\d{4}-\d{2}-\d{2}/) || strValue.match(/^\d{2}\/\d{2}\/\d{4}/)) {
      return 'date-cell'
    }

    return 'text-cell'
  }

  function getSortIcon(column) {
    if (sortColumn !== column) return ''
    return sortDirection === 'asc' ? ' ↑' : ' ↓'
  }

  onMount(() => {
    if (!tableRef || !processed) return

    // Add keyboard navigation
    tableRef.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft' && currentPage > 1) {
        goToPage(currentPage - 1)
      } else if (e.key === 'ArrowRight' && currentPage < totalPages) {
        goToPage(currentPage + 1)
      }
    })

    // Focus the table for keyboard events
    tableRef.focus()
  })

  // Reset filters
  function clearAll() {
    filterText = ''
    sortColumn = null
    sortDirection = 'asc'
    currentPage = 1
  }
</script>

<div class="border-t border-gray-200">
  <!-- CSV Controls Bar -->
  <div class="bg-gray-50 border-b border-gray-200 px-4 py-3">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <span class="text-sm font-medium text-gray-700">
          {processed.metadata.rowCount.toLocaleString()} rows × {processed.metadata.columnCount} columns
        </span>
        {#if filteredAndSortedData.length !== processed.metadata.rowCount}
          <span class="text-sm text-blue-600">
            ({filteredAndSortedData.length.toLocaleString()} filtered)
          </span>
        {/if}
        {#if processed.metadata.fileSize}
          <span class="text-sm text-gray-500">
            ({Math.round(processed.metadata.fileSize / 1024)} KB)
          </span>
        {/if}
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <!-- Search -->
        <input
          type="text"
          bind:value={filterText}
          placeholder="Search all columns..."
          class="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        <!-- Page Size Selector -->
        <select
          bind:value={itemsPerPage}
          on:change={changePageSize}
          class="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="25">25 rows</option>
          <option value="50">50 rows</option>
          <option value="100">100 rows</option>
          <option value="200">200 rows</option>
          <option value="500">500 rows</option>
        </select>

        <div class="h-4 w-px bg-gray-300"></div>

        <!-- Export -->
        <div class="relative group">
          <button
            class="inline-flex items-center px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <i class="fas fa-download mr-1.5"></i>
            Export
            <i class="fas fa-chevron-down ml-1.5 text-xs"></i>
          </button>

          <!-- Dropdown Menu -->
          <div class="absolute right-0 mt-1 w-48 bg-white border border-gray-200 rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
            <button
              on:click={exportAllToCSV}
              class="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 text-left"
            >
              <i class="fas fa-file-csv mr-2"></i>
              Export All as CSV
            </button>
            <button
              on:click={exportToCSV}
              class="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 text-left"
            >
              <i class="fas fa-filter mr-2"></i>
              Export Filtered as CSV
            </button>
          </div>
        </div>

        <button
          on:click={clearAll}
          class="inline-flex items-center px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <i class="fas fa-redo mr-1.5"></i>
          Reset All
        </button>
      </div>
    </div>
  </div>

  <!-- Enhanced CSV Table Container -->
  <div class="overflow-x-auto">
    <div class="min-w-full">
      <table
        bind:this={tableRef}
        class="w-full text-sm"
      >
        <thead class="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
          <tr>
            <!-- Row number column -->
            <th class="px-4 py-2 text-left font-semibold text-gray-900 w-16 sticky left-0 bg-gray-50 z-10 border-r border-gray-200">
              #
            </th>

            <!-- Data columns -->
            {#each processed.metadata.columns as col}
              <th
                class="px-4 py-2 text-left font-semibold text-gray-900 cursor-pointer hover:bg-gray-100 transition-colors"
                on:click={() => handleSort(col)}
              >
                <div class="flex items-center justify-between">
                  <span class="truncate max-w-[200px]" title={col}>{col}</span>
                  <span class="text-blue-600 text-xs ml-1">{getSortIcon(col)}</span>
                </div>
              </th>
            {/each}
          </tr>
        </thead>

        <tbody class="bg-white divide-y divide-gray-200">
          {#each paginatedData as row, idx}
            <tr class="hover:bg-gray-50 transition-colors">
              <!-- Row number -->
              <td class="px-4 py-2 text-gray-600 font-medium text-xs sticky left-0 bg-white z-5 border-r border-gray-200">
                {(currentPage - 1) * itemsPerPage + idx + 1}
              </td>

              <!-- Data cells -->
              {#each processed.metadata.columns as col}
                <td class="px-4 py-2 {getCellClass(row[col])}">
                  <div class="truncate max-w-[300px]" title={row[col] || ''}>
                    {row[col] || ''}
                  </div>
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>

      <!-- Empty state -->
      {#if paginatedData.length === 0}
        <div class="text-center py-12">
          <i class="fas fa-search text-gray-400 text-4xl mb-4"></i>
          <p class="text-gray-600">
            {filterText.trim() ? 'No rows match your search criteria' : 'No data available'}
          </p>
          {#if filterText.trim()}
            <button
              on:click={() => filterText = ''}
              class="mt-2 text-blue-600 hover:text-blue-800 text-sm"
            >
              Clear search
            </button>
          {/if}
        </div>
      {/if}

      <!-- Pagination Controls -->
      {#if totalPages > 1}
        <div class="bg-gray-50 border-t border-gray-200 px-4 py-3">
          <div class="flex items-center justify-between">
            <div class="text-sm text-gray-700">
              Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, filteredAndSortedData.length)}
              of {filteredAndSortedData.length} results
              {#if filteredAndSortedData.length !== processed.metadata.rowCount}
                (from {processed.metadata.rowCount.toLocaleString()} total)
              {/if}
            </div>

            <div class="flex items-center gap-2">
              <!-- First/Previous -->
              <button
                on:click={() => goToPage(1)}
                disabled={currentPage === 1}
                class="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <i class="fas fa-angle-double-left"></i>
              </button>
              <button
                on:click={() => goToPage(currentPage - 1)}
                disabled={currentPage === 1}
                class="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <i class="fas fa-angle-left"></i>
              </button>

              <!-- Page numbers -->
              {#each Array(Math.min(7, totalPages)) as _, i}
                {@const startPage = Math.max(1, Math.min(currentPage - 3, totalPages - 6))}
                {@const pageNum = startPage + i}
                {#if pageNum > 0 && pageNum <= totalPages}
                  <button
                    on:click={() => goToPage(pageNum)}
                    class="px-2 py-1 text-xs border {currentPage === pageNum ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 hover:bg-gray-100'} rounded"
                  >
                    {pageNum}
                  </button>
                {/if}
              {/each}

              <!-- Next/Last -->
              <button
                on:click={() => goToPage(currentPage + 1)}
                disabled={currentPage === totalPages}
                class="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <i class="fas fa-angle-right"></i>
              </button>
              <button
                on:click={() => goToPage(totalPages)}
                disabled={currentPage === totalPages}
                class="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <i class="fas fa-angle-double-right"></i>
              </button>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>

  <!-- Status Bar -->
  <div class="bg-gray-50 border-t border-gray-200 px-4 py-2">
    <div class="flex items-center justify-between text-xs text-gray-600">
      <div class="flex items-center gap-4">
        <span>
          <i class="fas fa-table mr-1"></i>
          {processed.metadata.rowCount.toLocaleString()} total rows
        </span>
        {#if filterText.trim()}
          <span class="text-blue-600">
            <i class="fas fa-filter mr-1"></i>
            Filtered by "{filterText}"
          </span>
        {/if}
        {#if sortColumn}
          <span class="text-green-600">
            <i class="fas fa-sort mr-1"></i>
            Sorted by {sortColumn} ({sortDirection})
          </span>
        {/if}
      </div>

      <div class="flex items-center gap-2">
        <span class="text-xs text-gray-500">
          Use ← → arrows to navigate pages
        </span>
      </div>
    </div>
  </div>
</div>

<style>
  .numeric-cell {
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.875em;
  }

  .date-cell {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.875em;
    color: #059669;
  }

  .text-cell {
    text-align: left;
  }

  .empty-cell {
    color: #9ca3af;
    font-style: italic;
    font-size: 0.875em;
  }

  /* Custom scrollbar for better UX */
  .overflow-x-auto::-webkit-scrollbar {
    height: 8px;
    width: 8px;
  }

  .overflow-x-auto::-webkit-scrollbar-track {
    background: #f1f5f9;
  }

  .overflow-x-auto::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 4px;
  }

  .overflow-x-auto::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
  }

  /* Sticky header and row number column */
  :global(thead.sticky th) {
    position: sticky;
    top: 0;
    z-index: 20;
  }

  :global(.sticky) {
    position: sticky;
  }

  /* Table focus for keyboard navigation */
  table:focus {
    outline: 2px solid #3b82f6;
    outline-offset: -2px;
  }

  /* Dropdown animation */
  .group:hover .group-hover\:opacity-100 {
    opacity: 1;
  }

  .group:hover .group-hover\:visible {
    visibility: visible;
  }
</style>