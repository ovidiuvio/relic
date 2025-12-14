import { writable, derived } from 'svelte/store'

// Simple filter function for relics
export function filterRelics(relics, searchTerm, getTypeLabel) {
  return relics.filter(relic => {
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return (
      (relic.name && relic.name.toLowerCase().includes(term)) ||
      relic.id.toLowerCase().includes(term) ||
      (relic.content_type && getTypeLabel(relic.content_type).toLowerCase().includes(term))
    )
  })
}

// Create reactive pagination functionality
export function usePagination(filteredData, itemsPerPage, currentPage) {
  const totalPages = derived([filteredData, itemsPerPage], ([$filteredData, $itemsPerPage]) => {
    return Math.ceil($filteredData.length / $itemsPerPage)
  })

  const paginatedData = derived([filteredData, itemsPerPage, currentPage], ([$filteredData, $itemsPerPage, $currentPage]) => {
    const start = ($currentPage - 1) * $itemsPerPage
    const end = start + $itemsPerPage
    return $filteredData.slice(start, end)
  })

  const goToPage = (page, maxPage) => {
    currentPage.set(Math.max(1, Math.min(page, maxPage)))
  }

  return {
    totalPages,
    paginatedData,
    goToPage
  }
}

// Create a simple pagination store
export function createPaginationStore(initialPage = 1) {
  const { subscribe, set, update } = writable(initialPage)

  return {
    subscribe,
    set,
    reset: () => set(1),
    next: (maxPage) => update(n => Math.min(n + 1, maxPage)),
    prev: () => update(n => Math.max(1, n - 1)),
    goTo: (page, maxPage) => set(Math.max(1, Math.min(page, maxPage)))
  }
}