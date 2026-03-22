/**
 * Creates a debounced reloader for server-side paginated lists.
 *
 * Usage in Svelte components:
 *   const reloader = createReloader()
 *   $: if (searchTerm !== undefined) reloader.debounce(() => load(1))
 *   $: if (reloader.tagChanged(tagFilter)) load(1)
 *   onMount(async () => { await load(1); reloader.setReady() })
 */
export function createReloader(delay = 300) {
  let _timer
  let _ready = false
  let _prevTag
  let _gen = 0

  return {
    setReady() { _ready = true },
    reset() { _ready = false; clearTimeout(_timer); _gen++ },
    clear() { clearTimeout(_timer) },
    debounce(fn) {
      if (!_ready) return
      clearTimeout(_timer)
      _gen++
      _timer = setTimeout(fn, delay)
    },
    tagChanged(tag) {
      if (tag === _prevTag) return false
      _prevTag = tag
      return _ready
    },
    /** Call at the start of a load function to capture the current generation. */
    gen() { return _gen },
    /** Returns true if a newer request has been issued since `g` was captured. */
    stale(g) { return g !== _gen }
  }
}

// Simple filter function for relics
export function filterRelics(relics, searchTerm, getTypeLabel, tagFilter = null) {
  return relics.filter(relic => {
    // If a tagFilter is configured, reject any relic that doesn't include it.
    if (tagFilter) {
      if (!relic.tags) return false;
      const hasTag = relic.tags.some(tag => (typeof tag === 'string' ? tag : tag.name).toLowerCase() === tagFilter.toLowerCase());
      if (!hasTag) return false;
    }

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
