<script>
  import { createEventDispatcher } from 'svelte'
  import { shareRelic, copyRelicContent, downloadRelic, viewRaw, fastForkRelic, copyToClipboard } from '../services/relicActions'
  import { getTypeLabel, getTypeIcon, getTypeIconColor, formatBytes, formatTimeAgo } from '../services/typeUtils'

  // Props
  export let data = [] // Array of relics/bookmarks
  export let loading = false
  export let searchTerm = ''
  export let currentPage = 1
  export let totalPages = 1
  export let itemsPerPage = 20
  export let paginatedData = []
  export let title = 'Relics'
  export let titleIcon = 'fa-clock'
  export let titleIconColor = 'text-blue-600'
  export let emptyMessage = 'No relics yet'
  export let emptyMessageWithSearch = 'No relics found'
  export let showItemsCount = true
  export let emptyIcon = 'fa-inbox'
  export let emptyAction = 'Create your first relic to get started!'
  export let columnHeaders = {
    title: 'Title / ID',
    type: 'Type',
    date: 'Created',
    size: 'Size',
    actions: 'Actions'
  }

  // Sorting
  export let sortBy = 'date'
  export let sortOrder = 'desc'

  const dispatch = createEventDispatcher()

  // Custom action handlers
  export let onEdit = null // function(relic) for edit action
  export let onDelete = null // function(relic) for delete action
  export let onRemoveBookmark = null // function(relic) for remove bookmark action
  export let customActions = [] // Array of { icon, color, title, handler, position }

  // Unique ID for form elements
  export let tableId = 'relics'

  // Display options
  export let showForkButton = true

  // Tag filtering
  export let tagFilter = null

  // Event handlers for pagination
  export let goToPage = () => {}

  function clearTagFilter() {
    dispatch('clear-tag-filter')
  }

  // Helper function to determine date field
  function getDateField(relic) {
    return relic.bookmarked_at || relic.created_at
  }

  // Helper function to get date column header
  function getDateColumnHeader() {
    return columnHeaders.date
  }

  function handleSort(column) {
    if (sortBy === column) {
      sortOrder = sortOrder === 'asc' ? 'desc' : 'asc'
    } else {
      sortBy = column
      // Default to descending for date, size, and statistics
      sortOrder = (column === 'date' || column === 'size' || column === 'access_count' || column === 'bookmark_count') ? 'desc' : 'asc'
    }
    dispatch('sort', { sortBy, sortOrder })
  }
</script>

<div class="maas-card">
  <div class="px-4 py-3 border-b border-[#ccc] flex items-center justify-between bg-[#f5f5f5]">
    <div class="flex items-center gap-3">
      <h2 class="text-sm font-bold text-gray-800 flex items-center uppercase tracking-wide">
        <i class="fas {titleIcon} {titleIconColor} mr-2"></i>
        {title}
      </h2>

      {#if tagFilter}
        <div class="flex items-center animate-fade-in">
          <div class="h-4 w-[1px] bg-gray-300 mx-2"></div>
          <div class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[11px] font-medium bg-[#fdf2f8] text-[#772953] border border-[#fbcfe8] shadow-sm">
            <i class="fas fa-tag text-[9px] opacity-70"></i>
            <span>{tagFilter}</span>
            <button
              on:click|stopPropagation={clearTagFilter}
              class="ml-1 text-[#772953] hover:text-red-700 transition-colors focus:outline-none flex items-center"
              title="Clear tag filter"
            >
              <i class="fas fa-times-circle text-[10px]"></i>
            </button>
          </div>
        </div>
      {/if}
    </div>
    <div class="relative flex-1 max-w-md ml-4">
      <i class="fa-solid fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 text-xs"></i>
      <input
        type="text"
        bind:value={searchTerm}
        placeholder="Filter..."
        class="w-full pl-8 pr-3 py-1 text-sm maas-input"
      />
    </div>
  </div>

  {#if loading}
    <div class="p-8 text-center">
      <div class="inline-block">
        <i class="fas fa-spinner fa-spin text-[#2196f3] text-2xl"></i>
      </div>
      <p class="text-sm text-gray-500 mt-2">Loading...</p>
    </div>
  {:else if data.length === 0}
    <div class="p-8 text-center text-gray-500">
      <i class="fas {emptyIcon} text-4xl mb-2 text-gray-400"></i>
      <p class="text-sm">
        {searchTerm ? `${emptyMessageWithSearch} matching "${searchTerm}"` : emptyMessage}
      </p>
      {#if !searchTerm && emptyAction}
        <p class="text-xs mt-2 text-gray-400">{emptyAction}</p>
      {/if}
    </div>
  {:else}
    <div class="overflow-x-auto">
      <table class="w-full maas-table text-sm">
        <thead>
          <tr>
            <th class="cursor-pointer hover:bg-gray-100 transition-colors group px-4 py-2 text-left select-none" on:click={() => handleSort('title')}>
              <div class="flex items-center gap-1.5">
                <span>{columnHeaders.title}</span>
                <i class="fas fa-arrow-up sort-arrow {sortBy === 'title' ? 'active' : ''} {sortBy === 'title' && sortOrder === 'desc' ? 'desc' : ''}"></i>
              </div>
            </th>
            <th class="cursor-pointer hover:bg-gray-100 transition-colors group px-4 py-2 text-left select-none" on:click={() => handleSort('date')}>
              <div class="flex items-center gap-1.5">
                <span>{getDateColumnHeader()}</span>
                <i class="fas fa-arrow-up sort-arrow {sortBy === 'date' ? 'active' : ''} {sortBy === 'date' && sortOrder === 'desc' ? 'desc' : ''}"></i>
              </div>
            </th>
            <th class="cursor-pointer hover:bg-gray-100 transition-colors group px-4 py-2 text-left select-none" on:click={() => handleSort('size')}>
              <div class="flex items-center gap-1.5">
                <span>{columnHeaders.size}</span>
                <i class="fas fa-arrow-up sort-arrow {sortBy === 'size' ? 'active' : ''} {sortBy === 'size' && sortOrder === 'desc' ? 'desc' : ''}"></i>
              </div>
            </th>
            <th class="px-4 py-2 text-left w-40">{columnHeaders.actions}</th>
          </tr>
        </thead>
        <tbody>
          {#each paginatedData as relic (relic.id)}
            <tr class="hover:bg-gray-50 cursor-pointer transition-colors duration-75">
              <td class="py-2">
                <div class="flex items-center gap-2">
                  <!-- Status indicators -->
                  {#if tableId !== 'recent-relics'}
                    <div class="flex items-center gap-0.5 flex-shrink-0">
                      {#if relic.access_level === 'private'}
                        <i class="fas fa-lock text-[10px]" style="color: #76306c;" title="Private"></i>
                      {:else if relic.access_level === 'public'}
                        <i class="fas fa-globe text-[10px]" style="color: #217db1;" title="Public"></i>
                      {/if}
                    </div>
                  {/if}
                  <i class="fas {getTypeIcon(relic.content_type)} {getTypeIconColor(relic.content_type)} text-sm flex-shrink-0" title={getTypeLabel(relic.content_type)}></i>
                  <div class="flex flex-col min-w-0">
                      <div class="flex items-center gap-2">
                          <a href="/{relic.id}" class="font-bold text-[#333] hover:underline truncate text-sm">
                            {relic.name || 'Untitled'}
                          </a>

                          <!-- Copy ID Button integrated -->
                          <div class="flex items-center group/id gap-1 opacity-50 hover:opacity-100 transition-opacity">
                            <span class="text-[10px] text-gray-500 font-mono">{relic.id}</span>
                            <button
                              on:click|stopPropagation={() => copyToClipboard(relic.id, 'ID copied!')}
                              class="text-gray-400 hover:text-blue-600 -mt-0.5"
                              title="Copy ID"
                            >
                              <i class="fas fa-copy text-[10px]"></i>
                            </button>
                          </div>
                      </div>

                      <div class="flex items-center gap-2 text-[10px] text-gray-500 mt-[1px]">
                        <!-- Tags -->
                        {#if relic.tags && relic.tags.length > 0}
                            <div class="flex items-center flex-wrap gap-1">
                              {#each relic.tags as tag}
                                <button
                                  on:click|stopPropagation={() => dispatch('tag-click', typeof tag === 'string' ? tag : tag.name)}
                                  class="inline-flex items-center px-1 py-0 rounded-sm bg-gray-200 hover:bg-gray-300 text-gray-600 transition-colors"
                                >
                                  <span class="truncate max-w-[80px]">{typeof tag === 'string' ? tag : tag.name}</span>
                                </button>
                              {/each}
                              <span class="text-gray-300">|</span>
                            </div>
                        {/if}

                        <!-- Stats -->
                        <span class="flex items-center gap-1" title="Views">
                          <i class="fas fa-eye text-[9px]"></i> {relic.access_count || 0}
                        </span>
                        <span class="flex items-center gap-1" title="Bookmarks">
                          <i class="fas fa-bookmark text-[9px]"></i> {relic.bookmark_count || 0}
                        </span>
                      </div>
                  </div>
                </div>
              </td>
              <td class="text-gray-600 text-xs py-2">
                {formatTimeAgo(getDateField(relic))}
              </td>
              <td class="font-mono text-xs py-2 text-gray-600">
                {formatBytes(relic.size_bytes || 0)}
              </td>
              <td class="py-2">
                <div class="flex items-center gap-1 opacity-70 hover:opacity-100 transition-opacity">
                  {#if onRemoveBookmark}
                    <button
                      on:click|stopPropagation={() => onRemoveBookmark(relic)}
                      class="p-1 text-amber-600 hover:text-amber-700 hover:bg-amber-100 rounded-sm transition-colors"
                      title="Remove bookmark"
                    >
                      <i class="fas fa-bookmark text-xs"></i>
                    </button>
                  {/if}

                  <!-- Custom actions -->
                  {#each customActions as action}
                    <button
                      on:click|stopPropagation={() => action.handler(relic)}
                      class="p-1 text-{action.color}-500 hover:text-{action.color}-700 hover:bg-{action.color}-100 rounded-sm transition-colors"
                      title={action.title}
                    >
                      <i class="fas {action.icon} text-xs"></i>
                    </button>
                  {/each}

                  <!-- Standard actions -->
                  <button
                    on:click|stopPropagation={() => shareRelic(relic.id)}
                    class="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-100 rounded-sm transition-colors"
                    title="Share"
                  >
                    <i class="fas fa-share text-xs"></i>
                  </button>
                  <button
                    on:click|stopPropagation={() => copyRelicContent(relic.id)}
                    class="p-1 text-gray-500 hover:text-green-600 hover:bg-green-100 rounded-sm transition-colors"
                    title="Copy content"
                  >
                    <i class="fas fa-copy text-xs"></i>
                  </button>
                  {#if showForkButton}
                    <button
                      on:click|stopPropagation={() => fastForkRelic(relic)}
                      class="p-1 text-gray-500 hover:text-teal-600 hover:bg-teal-100 rounded-sm transition-colors"
                      title="Fork"
                    >
                      <i class="fas fa-code-branch text-xs"></i>
                    </button>
                  {/if}
                  <button
                    on:click|stopPropagation={() => downloadRelic(relic.id, relic.name, relic.content_type)}
                    class="p-1 text-gray-500 hover:text-orange-600 hover:bg-orange-100 rounded-sm transition-colors"
                    title="Download"
                  >
                    <i class="fas fa-download text-xs"></i>
                  </button>

                  <!-- Edit button -->
                  {#if onEdit}
                    <button
                      on:click|stopPropagation={() => onEdit(relic)}
                      class="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-100 rounded-sm transition-colors"
                      title="Edit"
                    >
                      <i class="fas fa-edit text-xs"></i>
                    </button>
                  {/if}

                  <!-- Delete button - always last as it's destructive -->
                  {#if onDelete}
                    <button
                      on:click|stopPropagation={() => onDelete(relic)}
                      class="p-1 text-red-500 hover:text-red-700 hover:bg-red-100 rounded-sm transition-colors"
                      title="Delete"
                    >
                      <i class="fas fa-trash text-xs"></i>
                    </button>
                  {/if}
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <div class="px-4 py-2 border-t border-[#ccc] bg-gray-50 text-xs text-gray-600 flex justify-between items-center gap-6">
      <div class="flex items-center gap-4">
        {#if showItemsCount}
          <span>{data.length} {data.length === 1 ? 'item' : 'items'}</span>
        {/if}
        {#if data.length > 0}
          <div class="flex items-center gap-2">
            <label for="items-per-page-{tableId}" class="text-gray-600">Per page:</label>
            <select
              id="items-per-page-{tableId}"
              bind:value={itemsPerPage}
              on:change={() => { currentPage = 1 }}
              class="pl-1 pr-6 py-0.5 border border-gray-300 rounded-sm text-gray-700 bg-white hover:border-gray-400 cursor-pointer w-14 focus:outline-none focus:border-blue-500"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
        {/if}
      </div>

      {#if totalPages > 1}
        <div class="flex items-center gap-1 whitespace-nowrap">
          <span class="text-gray-600 mr-2">
            Page {currentPage} of {totalPages}
          </span>
          <button
            on:click={() => goToPage(currentPage - 1)}
            disabled={currentPage === 1}
            class="px-2 py-0.5 border border-gray-300 rounded-sm bg-white text-gray-700 hover:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:hover:bg-white transition-colors"
            title="Previous"
          >
            <i class="fas fa-chevron-left text-[10px]"></i>
          </button>
          <button
            on:click={() => goToPage(currentPage + 1)}
            disabled={currentPage === totalPages}
            class="px-2 py-0.5 border border-gray-300 rounded-sm bg-white text-gray-700 hover:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:hover:bg-white transition-colors"
            title="Next"
          >
            <i class="fas fa-chevron-right text-[10px]"></i>
          </button>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .animate-fade-in {
    animation: fadeIn 0.2s ease-out;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateX(-4px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  .sort-arrow {
    font-size: 9px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    opacity: 0;
    color: #9ca3af;
    display: inline-block;
  }

  .group:hover .sort-arrow {
    opacity: 0.5;
  }

  .sort-arrow.active {
    opacity: 1 !important;
    color: #2563eb !important;
  }

  .sort-arrow.desc {
    transform: rotate(180deg);
  }
</style>
