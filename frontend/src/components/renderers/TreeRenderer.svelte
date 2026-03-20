<script>
  import { createEventDispatcher, setContext } from 'svelte'
  import { writable } from 'svelte/store'
  import TreeNode from './TreeNode.svelte'
  import { tryParseJson } from '../../services/utils/jsonRepair.js'
  import { createRelic } from '../../services/api'
  import { showToast } from '../../stores/toastStore'

  export let processed
  export let darkMode = true
  export let fontSize = 13
  export let lang = null
  export let pageSize = 100

  const dispatch = createEventDispatcher()

  const expandSignal = writable(null)
  setContext('expandSignal', expandSignal)

  const darkModeStore = writable(darkMode)
  setContext('darkMode', darkModeStore)
  $: darkModeStore.set(darkMode)

  const pageSizeStore = writable(pageSize)
  setContext('pageSize', pageSizeStore)
  $: pageSizeStore.set(pageSize)

  const filterStore = writable('')
  setContext('filter', filterStore)

  // Pre-computed visibility map: container object reference → boolean.
  // A single O(N) pass so TreeNode lookups are O(1) instead of each node
  // doing its own recursive descent on every filter change.
  const visibilityStore = writable(null) // null = no filter active, show everything
  setContext('visibility', visibilityStore)

  function computeVisibility(root, f) {
    if (!f) return null
    const map = new Map()
    function visit(v, k) {
      const keyMatch = k !== undefined && String(k).toLowerCase().includes(f)
      if (v === null || typeof v !== 'object') {
        const valMatch = v === null ? 'null'.includes(f) : String(v).toLowerCase().includes(f)
        return keyMatch || valMatch
      }
      const ents = Array.isArray(v) ? v.map((x, i) => [i, x]) : Object.entries(v)
      let childVisible = false
      for (const [ck, cv] of ents) {
        if (visit(cv, ck)) childVisible = true
      }
      const visible = keyMatch || childVisible
      map.set(v, visible)
      return visible
    }
    visit(root, undefined)
    return map
  }

  $: {
    const f = $filterStore
    visibilityStore.set(parsedValue != null ? computeVisibility(parsedValue, f) : null)
  }

  setContext('onFork', async (nodeKey, nodeValue) => {
    const json = JSON.stringify(nodeValue, null, 2)
    const name = (nodeKey !== undefined ? String(nodeKey) : 'node') + '.json'
    const file = new File([json], name, { type: 'application/json' })
    try {
      const response = await createRelic({ file, name, access_level: 'public', expires_in: 'never' })
      showToast('Node forked as new relic!', 'success')
      window.location.href = `/${response.data.id}`
    } catch (e) {
      showToast('Failed to fork node', 'error')
    }
  })

  let filterValue = ''
  let filterDebounce
  let parseError = null
  let parsedValue = null
  let repaired = false
  let generation = 0

  export function expandAll() { expandSignal.set('all') }
  export function collapseAll() { expandSignal.set('none') }

  function clearFilter() {
    filterValue = ''
    clearTimeout(filterDebounce)
    filterStore.set('')
  }

  function onFilterInput() {
    clearTimeout(filterDebounce)
    filterDebounce = setTimeout(() => {
      filterStore.set(filterValue.toLowerCase().trim())
    }, 150)
  }

  // Reset filter when content changes
  $: processed, clearFilter()

  $: {
    parseError = null
    parsedValue = null
    repaired = false
    const gen = ++generation
    const effectiveLang = lang ?? processed?.metadata?.language
    const content = processed?.preview || processed?.text || ''
    if (content) {
      try {
        if (effectiveLang === 'json') {
          const result = tryParseJson(content)
          parsedValue = result.value
          repaired = result.repaired
        } else if (effectiveLang === 'yaml' || effectiveLang === 'yml') {
          import('js-yaml').then(m => {
            if (gen !== generation) return
            try {
              parsedValue = m.default.load(content)
            } catch (e) {
              parseError = e.message
              dispatch('parse-error')
            }
          })
        } else if (effectiveLang === 'toml') {
          import('smol-toml').then(m => {
            if (gen !== generation) return
            try {
              parsedValue = m.parse(content)
            } catch (e) {
              parseError = e.message
              dispatch('parse-error')
            }
          })
        } else if (effectiveLang === 'xml') {
          import('fast-xml-parser').then(m => {
            if (gen !== generation) return
            try {
              const parser = new m.XMLParser({ ignoreAttributes: false })
              parsedValue = parser.parse(content)
            } catch (e) {
              parseError = e.message
              dispatch('parse-error')
            }
          })
        } else {
          parseError = 'Unsupported format for tree view'
          dispatch('parse-error')
        }
      } catch (e) {
        parseError = e.message
      }
    }
  }
</script>

<div class="border-t border-gray-200 {darkMode ? 'bg-[#1e1e1e]' : 'bg-white'}">
  {#if parseError}
    <div class="p-4">
      <div class="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700 mb-3">
        <i class="fas fa-exclamation-triangle"></i>
        <span>Parse error: {parseError}</span>
        <button
          on:click={() => dispatch('parse-error')}
          class="ml-auto text-xs underline hover:no-underline"
        >
          Switch to code view
        </button>
      </div>
      <pre class="text-xs font-mono {darkMode ? 'text-gray-300' : 'text-gray-700'} whitespace-pre-wrap overflow-auto" style="font-size: {fontSize}px">{processed?.preview || processed?.text || ''}</pre>
    </div>
  {:else if parsedValue !== null && parsedValue !== undefined}
    {#if repaired}
      <div class="flex items-center gap-1.5 px-4 py-1.5 border-b {darkMode ? 'border-amber-900/40 bg-amber-950/30 text-amber-400' : 'border-amber-200 bg-amber-50 text-amber-700'} text-xs font-medium">
        <i class="fas fa-wrench text-xs"></i>
        auto-repaired — displaying best-effort output; stored relic is unchanged
      </div>
    {/if}
    <!-- Filter input -->
    <div class="border-b {darkMode ? 'border-gray-700' : 'border-gray-200'} px-3 py-1.5">
      <div class="relative">
        <i class="fas fa-search absolute left-2 top-1/2 -translate-y-1/2 text-xs {darkMode ? 'text-gray-500' : 'text-gray-400'}"></i>
        <input
          type="text"
          placeholder="Filter keys and values…"
          bind:value={filterValue}
          on:input={onFilterInput}
          class="w-full text-xs pl-6 {filterValue ? 'pr-6' : 'pr-2'} py-1 rounded border {darkMode ? 'bg-gray-800 border-gray-600 text-gray-200 placeholder-gray-600' : 'bg-white border-gray-300 text-gray-700 placeholder-gray-400'} focus:outline-none focus:ring-1 focus:ring-blue-400"
        />
        {#if filterValue}
          <button
            on:click={clearFilter}
            class="absolute right-2 top-1/2 -translate-y-1/2 {darkMode ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'}"
          >
            <i class="fas fa-times text-xs"></i>
          </button>
        {/if}
      </div>
    </div>
    <div
      class="overflow-auto p-4 {darkMode ? 'text-gray-300' : 'text-gray-800'}"
      style="height: calc(100vh - 300px); font-size: {fontSize}px;"
    >
      <TreeNode value={parsedValue} depth={0} />
    </div>
  {:else}
    <div class="flex items-center justify-center p-12 text-gray-400">
      <i class="fas fa-spinner fa-spin mr-2"></i>
      Parsing...
    </div>
  {/if}
</div>
