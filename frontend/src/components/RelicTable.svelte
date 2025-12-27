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

<div class="bg-white shadow-sm rounded-lg border border-gray-200">
  <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <h2 class="text-lg font-semibold text-gray-900 flex items-center">
        <i class="fas {titleIcon} {titleIconColor} mr-2"></i>
        {title}
      </h2>

      {#if tagFilter}
        <div class="flex items-center animate-fade-in">
          <div class="h-4 w-[1px] bg-gray-300 mx-2"></div>
          <div class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-[#fdf2f8] text-[#772953] border border-[#fbcfe8] shadow-sm">
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
      <i class="fa-solid fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
      <input
        type="text"
        bind:value={searchTerm}
        placeholder="Filter by name, type, or id..."
        class="w-full pl-9 pr-3 py-1.5 text-sm maas-input"
      />
    </div>
  </div>

  {#if loading}
    <div class="p-8 text-center">
      <div class="inline-block">
        <i class="fas fa-spinner fa-spin text-[#772953] text-2xl"></i>
      </div>
      <p class="text-sm text-gray-500 mt-2">Loading...</p>
    </div>
  {:else if data.length === 0}
    <div class="p-8 text-center text-gray-500">
      <i class="fas {emptyIcon} text-4xl mb-2"></i>
      <p>
        {searchTerm ? `${emptyMessageWithSearch} matching "${searchTerm}"` : emptyMessage}
      </p>
      {#if !searchTerm && emptyAction}
        <p class="text-sm mt-2">{emptyAction}</p>
      {/if}
    </div>
  {:else}
    <div class="overflow-x-auto">
      <table class="w-full maas-table text-sm">
        <thead>
          <tr class="text-gray-500 uppercase text-xs tracking-wider bg-gray-50 border-b border-gray-200">
            <th class="cursor-pointer hover:bg-gray-100 transition-colors group px-4 py-3 text-left select-none" on:click={() => handleSort('title')}>
              <div class="flex items-center gap-1.5">
                <span>{columnHeaders.title}</span>
                <i class="fas fa-arrow-up sort-arrow {sortBy === 'title' ? 'active' : ''} {sortBy === 'title' && sortOrder === 'desc' ? 'desc' : ''}"></i>
              </div>
            </th>
            <th class="cursor-pointer hover:bg-gray-100 transition-colors group px-4 py-3 text-left select-none" on:click={() => handleSort('date')}>
              <div class="flex items-center gap-1.5">
                <span>{getDateColumnHeader()}</span>
                <i class="fas fa-arrow-up sort-arrow {sortBy === 'date' ? 'active' : ''} {sortBy === 'date' && sortOrder === 'desc' ? 'desc' : ''}"></i>
              </div>
            </th>
            <th class="cursor-pointer hover:bg-gray-100 transition-colors group px-4 py-3 text-left select-none" on:click={() => handleSort('size')}>
              <div class="flex items-center gap-1.5">
                <span>{columnHeaders.size}</span>
                <i class="fas fa-arrow-up sort-arrow {sortBy === 'size' ? 'active' : ''} {sortBy === 'size' && sortOrder === 'desc' ? 'desc' : ''}"></i>
              </div>
            </th>
            <th class="px-4 py-3 text-left w-40">{columnHeaders.actions}</th>
          </tr>
        </thead>
        <tbody>
          {#each paginatedData as relic (relic.id)}
            <tr class="hover:bg-gray-50 cursor-pointer">
              <td>
                <div class="flex items-center gap-1.5">
                  <!-- Status indicators -->
                  {#if tableId !== 'recent-relics'}
                    <div class="flex items-center gap-0.5 flex-shrink-0">
                      {#if relic.access_level === 'private'}
                        <i class="fas fa-lock text-xs" style="color: #76306c;" title="Private - accessible only via URL"></i>
                      {:else if relic.access_level === 'public'}
                        <i class="fas fa-globe text-xs" style="color: #217db1;" title="Public - discoverable"></i>
                      {/if}
                    </div>
                  {/if}
                  <i class="fas {getTypeIcon(relic.content_type)} {getTypeIconColor(relic.content_type)} text-sm flex-shrink-0" title={getTypeLabel(relic.content_type)}></i>
                  <a href="/{relic.id}" class="font-medium text-[#0066cc] hover:underline truncate">
                    {relic.name || 'Untitled'}
                  </a>

                  <!-- Views & Bookmarks as small inline badges (Top Row) -->
                  <div class="flex items-center gap-3 ml-3 text-[10px] text-gray-400/80 whitespace-nowrap mt-[1px]">
                    <span class="flex items-center gap-1" title="Views">
                      <i class="fas fa-eye text-[9px] translate-y-[0.5px]"></i>
                      <span>{relic.access_count || 0}</span>
                    </span>
                    <span class="flex items-center gap-1" title="Bookmarks">
                      <i class="fas fa-bookmark text-[9px] translate-y-[0.5px]"></i>
                      <span>{relic.bookmark_count || 0}</span>
                    </span>
                  </div>
                </div>
                <div class="flex items-center flex-wrap gap-2 mt-1">
                  <!-- Copy ID -->
                  <div class="flex items-center group gap-1">
                    <span class="text-xs text-gray-400 font-mono">{relic.id}</span>
                    <button
                      on:click|stopPropagation={() => copyToClipboard(relic.id, 'Relic ID copied to clipboard!')}
                      class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-gray-600 transition-all duration-200 -mt-0.5"
                      title="Copy ID"
                    >
                      <i class="fas fa-copy text-xs"></i>
                    </button>
                  </div>
                  <!-- Tags (Bottom Row) -->
                  {#if relic.tags && relic.tags.length > 0}
                    <div class="flex items-center flex-wrap gap-1.5 ml-auto">
                      {#each relic.tags as tag}
                        <button
                          on:click|stopPropagation={() => dispatch('tag-click', typeof tag === 'string' ? tag : tag.name)}
                          class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-500 hover:bg-gray-200 transition-colors"
                        >
                          <i class="fas fa-tag mr-1 text-[8px] opacity-60"></i>
                          {typeof tag === 'string' ? tag : tag.name}
                        </button>
                      {/each}
                    </div>
                  {/if}
                </div>
              </td>
              <td class="text-gray-500 text-xs">
                {formatTimeAgo(getDateField(relic))}
              </td>
              <td class="font-mono text-xs">
                {formatBytes(relic.size_bytes || 0)}
              </td>
              <td>
                <div class="flex items-center gap-1">
                  {#if onRemoveBookmark}
                    <button
                      on:click|stopPropagation={() => onRemoveBookmark(relic)}
                      class="p-1.5 text-amber-600 hover:text-amber-700 hover:bg-amber-50 rounded transition-colors"
                      title="Remove from bookmarks"
                    >
                      <i class="fas fa-bookmark text-xs"></i>
                    </button>
                  {/if}

                  <!-- Custom actions -->
                  {#each customActions as action}
                    <button
                      on:click|stopPropagation={() => action.handler(relic)}
                      class="p-1.5 text-{action.color}-400 hover:text-{action.color}-600 hover:bg-{action.color}-50 rounded transition-colors"
                      title={action.title}
                    >
                      <i class="fas {action.icon} text-xs"></i>
                    </button>
                  {/each}

                  <!-- Standard actions -->
                  <button
                    on:click|stopPropagation={() => shareRelic(relic.id)}
                    class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                    title="Share relic"
                  >
                    <i class="fas fa-share text-xs"></i>
                  </button>
                  <button
                    on:click|stopPropagation={() => copyRelicContent(relic.id)}
                    class="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                    title="Copy content to clipboard"
                  >
                    <i class="fas fa-copy text-xs"></i>
                  </button>
                  <button
                    on:click|stopPropagation={() => viewRaw(relic.id)}
                    class="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors"
                    title="View raw content"
                  >
                    <i class="fas fa-code text-xs"></i>
                  </button>
                  {#if showForkButton}
                    <button
                      on:click|stopPropagation={() => fastForkRelic(relic)}
                      class="p-1.5 text-gray-400 hover:text-teal-600 hover:bg-teal-50 rounded transition-colors"
                      title="Fast fork - create instant copy"
                    >
                      <i class="fas fa-code-branch text-xs"></i>
                    </button>
                  {/if}
                  <button
                    on:click|stopPropagation={() => downloadRelic(relic.id, relic.name, relic.content_type)}
                    class="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
                    title="Download relic"
                  >
                    <i class="fas fa-download text-xs"></i>
                  </button>

                  <!-- Edit button -->
                  {#if onEdit}
                    <button
                      on:click|stopPropagation={() => onEdit(relic)}
                      class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                      title="Edit relic"
                    >
                      <i class="fas fa-edit text-xs"></i>
                    </button>
                  {/if}

                  <!-- Delete button - always last as it's destructive -->
                  {#if onDelete}
                    <button
                      on:click|stopPropagation={() => onDelete(relic)}
                      class="p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                      title="Delete relic"
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

    <div class="px-6 py-3 border-t border-gray-200 bg-gray-50 text-xs text-gray-500 flex justify-between items-center gap-6">
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
              class="pl-3 pr-8 py-1 border border-gray-300 rounded text-gray-700 bg-white hover:border-gray-400 cursor-pointer w-16"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
        {/if}
      </div>

      {#if totalPages > 1}
        <div class="flex items-center gap-2 whitespace-nowrap">
          <span class="text-gray-600">
            Page {currentPage} of {totalPages}
          </span>
          <button
            on:click={() => goToPage(currentPage - 1)}
            disabled={currentPage === 1}
            class="px-3 py-1 border border-gray-300 rounded text-gray-700 hover:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:hover:bg-gray-50 transition-colors"
            title="Previous page"
          >
            <i class="fas fa-chevron-left text-xs"></i>
          </button>
          <button
            on:click={() => goToPage(currentPage + 1)}
            disabled={currentPage === totalPages}
            class="px-3 py-1 border border-gray-300 rounded text-gray-700 hover:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed disabled:hover:bg-gray-50 transition-colors"
            title="Next page"
          >
            <i class="fas fa-chevron-right text-xs"></i>
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