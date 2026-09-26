<script>
  import { navigate } from '../../utils/navigation';
  import { createEventDispatcher, setContext } from 'svelte'
  import { writable } from 'svelte/store'
  import TreeNode from './TreeNode.svelte'
  import FilterStrip from '../../lib/viewer/FilterStrip.svelte'
  import Icon from '../../lib/ui/Icon.svelte'
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
      navigate(`/${response.data.id}`)
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

<div class="tree-view" class:is-dark={darkMode}>
  {#if parseError}
    <div class="r-banner r-banner-danger tree-notice" role="alert">
      <Icon name="info" /><span class="tree-error">Couldn’t read it as a tree: {parseError}</span>
      <button class="r-btn r-btn-secondary" on:click={() => dispatch('parse-error')}>Show as code</button>
    </div>
    <pre class="tree-raw" style="font-size: {fontSize}px">{processed?.preview || processed?.text || ''}</pre>
  {:else if parsedValue !== null && parsedValue !== undefined}
    {#if repaired}
      <div class="r-banner r-banner-warning tree-notice" role="status">
        <Icon name="info" />Repaired to show it: this is a best-effort reading, the stored relic is unchanged.
      </div>
    {/if}
    <FilterStrip bind:value={filterValue} placeholder="Filter keys and values" dark={darkMode} oninput={onFilterInput} />
    <div class="tree-body" style="font-size: {fontSize}px;">
      <TreeNode value={parsedValue} depth={0} />
    </div>
  {:else}
    <p class="tree-loading" role="status">Reading…</p>
  {/if}
</div>

<style>
  .tree-view {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    background: var(--surface);
    color: var(--ink);
  }
  .tree-view.is-dark {
    background: #1e1e1e;
    color: #d4d4d4;
  }
  .tree-notice {
    flex: none;
  }
  .tree-notice :global(.r-icon) {
    flex: none;
    width: 14px;
    height: 14px;
  }
  .tree-error {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .tree-notice .r-btn {
    margin-left: auto;
  }
  .tree-raw {
    flex: 1;
    min-height: 0;
    margin: 0;
    padding: var(--space-4);
    overflow: auto;
    font-family: var(--font-mono);
    white-space: pre-wrap;
  }
  .tree-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: var(--space-3) var(--space-4);
  }
  .tree-loading {
    margin: auto;
    color: var(--ink-3);
  }
</style>
