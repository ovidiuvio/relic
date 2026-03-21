<script>
  import { getContext } from 'svelte'
  import { showToast } from '../../stores/toastStore'
  import { triggerDownload } from '../../services/utils/download'

  export let key = undefined
  export let value
  export let depth = 0

  const expandSignal = getContext('expandSignal')
  const darkModeStore = getContext('darkMode')
  const pageSizeStore = getContext('pageSize')
  const filterStore = getContext('filter')
  const onFork = getContext('onFork')
  const visibilityStore = getContext('visibility')
  $: darkMode = $darkModeStore
  $: pageSize = $pageSizeStore
  $: filter = $filterStore ?? ''

  let expanded = depth < 2
  let visibleCount = pageSize
  let copied = false

  $: if ($expandSignal === 'all') expanded = true
  $: if ($expandSignal === 'none') expanded = false

  $: isObject = value !== null && typeof value === 'object' && !Array.isArray(value)
  $: isArray = Array.isArray(value)
  $: isLeaf = !isObject && !isArray

  $: entries = isObject ? Object.entries(value) : isArray ? value.map((v, i) => [i, v]) : []
  // Reset pagination whenever entries or pageSize changes
  $: entries, pageSize, (visibleCount = pageSize)

  // While filtering: show all entries (no pagination) so no matches are hidden behind "Show more"
  $: activeEntries = filter ? entries : entries.slice(0, visibleCount)
  $: hiddenCount = filter ? 0 : entries.length - visibleCount

  $: count = isObject
    ? `{${entries.length} ${entries.length === 1 ? 'prop' : 'props'}}`
    : `[${entries.length} ${entries.length === 1 ? 'item' : 'items'}]`

  $: visible = (() => {
    if (depth === 0) return true
    const f = filter
    if (!f) return true
    const map = $visibilityStore
    // Containers: use pre-computed map (O(1) lookup)
    if (map && !isLeaf) return map.get(value) ?? false
    // Leaves: O(1) inline check (no recursion needed)
    const keyMatch = key !== undefined && String(key).toLowerCase().includes(f)
    if (keyMatch) return true
    if (value === null) return 'null'.includes(f)
    return String(value).toLowerCase().includes(f)
  })()
  // Auto-expand containers that have matching descendants when filter is active
  $: effectiveExpanded = filter ? (visible && !isLeaf) : expanded

  function toggle() {
    expanded = !expanded
  }

  function showMore() {
    visibleCount += pageSize
  }

  function copyValue() {
    const text = isLeaf
      ? (value === null ? 'null' : String(value))
      : JSON.stringify(value, null, 2)
    navigator.clipboard.writeText(text).then(() => {
      copied = true
      showToast('Copied to clipboard', 'success')
      setTimeout(() => (copied = false), 1500)
    }).catch(() => showToast('Failed to copy', 'error'))
  }

  function forkNode() {
    onFork?.(key, value)
  }

  function downloadNode() {
    const json = isLeaf
      ? (value === null ? 'null' : String(value))
      : JSON.stringify(value, null, 2)
    const name = (key !== undefined ? String(key) : 'node') + (isLeaf ? '.txt' : '.json')
    triggerDownload(json, name, isLeaf ? 'text/plain' : 'application/json')
  }

  // --- Highlight helpers ---

  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }

  function highlightMatch(text, f) {
    if (!f) return escapeHtml(text)
    const lower = text.toLowerCase()
    const i = lower.indexOf(f)
    if (i === -1) return escapeHtml(text)
    return (
      escapeHtml(text.slice(0, i)) +
      `<mark class="bg-yellow-200 text-yellow-900 rounded-sm">${escapeHtml(text.slice(i, i + f.length))}</mark>` +
      escapeHtml(text.slice(i + f.length))
    )
  }

  function valueClass(v) {
    if (v === null) return darkMode ? 'text-gray-500' : 'text-gray-400'
    if (typeof v === 'boolean') return darkMode ? 'text-purple-400' : 'text-purple-600'
    if (typeof v === 'number') return darkMode ? 'text-blue-400' : 'text-blue-600'
    if (typeof v === 'string') return darkMode ? 'text-green-400' : 'text-green-700'
    return darkMode ? 'text-gray-300' : 'text-gray-700'
  }

  function valueDisplay(v) {
    if (v === null) return 'null'
    if (typeof v === 'string') return v
    return String(v)
  }
</script>

{#if visible}
<div class="tree-node" style="padding-left: {depth > 0 ? '1.25rem' : '0'}">
  {#if isObject || isArray}
    <div class="group flex items-center gap-1 cursor-pointer rounded px-1 py-0.5 select-none" role="button" tabindex="0" on:click={toggle} on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && toggle()}>
      <span class="{darkMode ? 'text-gray-500' : 'text-gray-400'} w-3 text-center text-[10px]">{effectiveExpanded ? '▼' : '▶'}</span>
      {#if key !== undefined}
        <span class="{darkMode ? 'text-gray-200' : 'text-gray-800'} font-medium">{@html highlightMatch(String(key), filter)}</span>
        <span class="{darkMode ? 'text-gray-500' : 'text-gray-400'}">:</span>
      {/if}
      {#if !effectiveExpanded}
        <span class="{darkMode ? 'text-gray-500' : 'text-gray-400'} text-[0.8em] font-mono">{count}</span>
      {:else}
        <span class="{darkMode ? 'text-gray-500' : 'text-gray-400'} text-[0.8em]">{isArray ? '[' : '{'}</span>
      {/if}
      <span class="inline-flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          on:click|stopPropagation={copyValue}
          class="px-0.5 py-0 leading-none rounded {darkMode ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'} transition-colors"
          title="Copy as JSON"
        >
          <i class="fas {copied ? 'fa-check text-green-500' : 'fa-copy'} text-[10px]"></i>
        </button>
        <button
          on:click|stopPropagation={forkNode}
          class="px-0.5 py-0 leading-none rounded {darkMode ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'} transition-colors"
          title="Fork node as new relic"
        >
          <i class="fas fa-code-branch text-[10px]"></i>
        </button>
        <button
          on:click|stopPropagation={downloadNode}
          class="px-0.5 py-0 leading-none rounded {darkMode ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'} transition-colors"
          title="Download node"
        >
          <i class="fas fa-download text-[10px]"></i>
        </button>
      </span>
    </div>
    {#if effectiveExpanded}
      <div>
        {#each activeEntries as [k, v]}
          <svelte:self key={k} value={v} depth={depth + 1} />
        {/each}
        {#if hiddenCount > 0}
          <div class="flex items-center gap-2 px-1 py-1" style="padding-left: 1.25rem">
            <button
              on:click|stopPropagation={showMore}
              class="text-xs px-2 py-0.5 rounded {darkMode ? 'text-blue-400 hover:bg-white/10' : 'text-blue-600 hover:bg-blue-50'} transition-colors"
            >
              Show {Math.min(pageSize, hiddenCount)} more
            </button>
            <span class="text-xs {darkMode ? 'text-gray-600' : 'text-gray-400'}">
              ({hiddenCount} remaining)
            </span>
          </div>
        {/if}
      </div>
      <div class="px-1 {darkMode ? 'text-gray-500' : 'text-gray-400'} text-[0.8em] font-mono">{isArray ? ']' : '}'}</div>
    {/if}
  {:else}
    <div class="group flex items-center gap-1 rounded px-1 py-0.5">
      <span class="w-3"></span>
      {#if key !== undefined}
        <span class="{darkMode ? 'text-gray-200' : 'text-gray-800'} font-medium">{@html highlightMatch(String(key), filter)}</span>
        <span class="{darkMode ? 'text-gray-500' : 'text-gray-400'}">:</span>
      {/if}
      <span class="font-mono {valueClass(value)}">
        {#if typeof value === 'string'}
          <span class="{darkMode ? 'text-gray-500' : 'text-gray-400'}">"</span>{@html highlightMatch(value, filter)}<span class="{darkMode ? 'text-gray-500' : 'text-gray-400'}">"</span>
        {:else}
          {@html highlightMatch(valueDisplay(value), filter)}
        {/if}
      </span>
      <span class="inline-flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          on:click|stopPropagation={copyValue}
          class="px-0.5 py-0 leading-none rounded {darkMode ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'} transition-colors"
          title="Copy value"
        >
          <i class="fas {copied ? 'fa-check text-green-500' : 'fa-copy'} text-[10px]"></i>
        </button>
        <button
          on:click|stopPropagation={forkNode}
          class="px-0.5 py-0 leading-none rounded {darkMode ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'} transition-colors"
          title="Fork node as new relic"
        >
          <i class="fas fa-code-branch text-[10px]"></i>
        </button>
        <button
          on:click|stopPropagation={downloadNode}
          class="px-0.5 py-0 leading-none rounded {darkMode ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'} transition-colors"
          title="Download node"
        >
          <i class="fas fa-download text-[10px]"></i>
        </button>
      </span>
    </div>
  {/if}
</div>
{/if}
