import { writable, derived } from 'svelte/store'

// Simple filter function for relics
export function filterRelics(relics, searchTerm, getTypeLabel) {
  return relics.filter(relic => {
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return (
      (relic.name && relic.name.toLowerCase().includes(term)) ||
      relic.id.toLowerCase().includes(term) ||
      (relic.content_type && getTypeLabel(relic.content_type).toLowerCase().includes(term)) ||
      (relic.tags && relic.tags.some(tag => (typeof tag === 'string' ? tag : tag.name).toLowerCase().includes(term)))
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

// Simple pagination utilities for plain values (non-store)
export function calculateTotalPages(filteredData, itemsPerPage) {
  return Math.ceil(filteredData.length / itemsPerPage)
}

export function paginateData(filteredData, currentPage, itemsPerPage) {
  const start = (currentPage - 1) * itemsPerPage
  const end = start + itemsPerPage
  return filteredData.slice(start, end)
}

export function clampPage(page, totalPages) {
  return Math.max(1, Math.min(page, totalPages))
}

export function sortData(data, sortBy, sortOrder) {
  if (!sortBy) return data

  return [...data].sort((a, b) => {
    let aVal, bVal

    if (sortBy === 'date') {
      aVal = a.bookmarked_at || a.created_at
      bVal = b.bookmarked_at || b.created_at
    } else if (sortBy === 'title') {
      aVal = (a.name || a.id || '').toLowerCase()
      bVal = (b.name || b.id || '').toLowerCase()
    } else if (sortBy === 'size') {
      aVal = a.size_bytes || 0
      bVal = b.size_bytes || 0
    } else if (sortBy === 'type') {
      aVal = a.content_type || ''
      bVal = b.content_type || ''
    } else {
      aVal = a[sortBy]
      bVal = b[sortBy]
    }

    if (aVal === bVal) return 0
    if (aVal === null || aVal === undefined) return 1
    if (bVal === null || bVal === undefined) return -1

    if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1
    if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1
    return 0
  })
}