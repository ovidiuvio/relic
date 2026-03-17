<script>
  import MonacoEditor from '../MonacoEditor.svelte'
  import { createEventDispatcher } from 'svelte'
  import { createEventForwarder } from '../../services/utils/eventUtils'
  import { tryParseJson } from '../../services/utils/jsonRepair.js'

  export let processed
  export let relicId
  export let showSyntaxHighlighting
  export let showLineNumbers
  export let showComments = true
  export let fontSize = 13
  export let comments = []
  export let isAdmin = false
  export let darkMode = true
  export let beautify = false
  export let isFormattable = false
  export let showLineFilter = false

  const dispatch = createEventDispatcher()
  const forwardEvent = createEventForwarder(dispatch)

  $: language = (processed.type === 'code' || processed.type === 'diff') ? (processed.metadata?.language || 'plaintext') : 'plaintext'

  let beautifyRepaired = false

  function tryBeautify(content, lang) {
    beautifyRepaired = false
    try {
      if (lang === 'json') {
        const { value, repaired } = tryParseJson(content)
        beautifyRepaired = repaired
        return JSON.stringify(value, null, 2)
      }
      return content
    } catch {
      return content
    }
  }

  $: displayValue = (beautify && isFormattable)
    ? tryBeautify(processed.preview || processed.text || '', language)
    : (processed.preview || processed.text || '')

  // Line filter
  let filterValue = ''
  let debouncedFilter = ''
  let filterCase = localStorage.getItem('filterCase') === 'true'
  let regexError = false
  let showCheatsheet = false
  let filterDebounce

  $: localStorage.setItem('filterCase', String(filterCase))

  // Reset filter when content changes (keep mode toggles)
  $: processed, clearFilter()

  function clearFilter() {
    filterValue = ''
    debouncedFilter = ''
    clearTimeout(filterDebounce)
  }

  function onFilterInput() {
    clearTimeout(filterDebounce)
    filterDebounce = setTimeout(() => {
      debouncedFilter = filterValue
    }, 150)
  }

  // Build a compiled matcher function from current filter state
  $: matchLine = (() => {
    const raw = debouncedFilter.trim()
    if (!raw) return null

    regexError = false

    try {
      const re = new RegExp(raw, filterCase ? '' : 'i')
      return (line) => re.test(line)
    } catch {
      regexError = true
      return () => false
    }
  })()

  // Single reactive pass: filter lines + remap ANSI decorations together
  $: filterResult = (() => {
    const rawDecos = showSyntaxHighlighting && processed.hasAnsiCodes
      ? (processed.ansiDecorations || [])
      : []

    if (!matchLine) return { value: displayValue, decos: rawDecos, matchCount: null }

    const lines = displayValue.split('\n')
    const n = lines.length

    // Find matched lines (with optional invert)
    const matchedIndices = []
    for (let i = 0; i < n; i++) {
      if (matchLine(lines[i])) matchedIndices.push(i)
    }

    const filteredText = matchedIndices.map(i => lines[i]).join('\n')

    if (rawDecos.length === 0) {
      return { value: filteredText, decos: [], matchCount: matchedIndices.length }
    }

    // Build per-line char-offset tables
    const origStarts = new Int32Array(n)
    let off = 0
    for (let i = 0; i < n; i++) { origStarts[i] = off; off += lines[i].length + 1 }

    const m = matchedIndices.length
    const newStarts = new Int32Array(m)
    off = 0
    for (let i = 0; i < m; i++) { newStarts[i] = off; off += lines[matchedIndices[i]].length + 1 }

    // Index decorations by line: for each decoration find which original lines it
    // touches using a forward scan with early exit (origStarts is sorted).
    const lineDecos = new Map()
    for (let di = 0; di < rawDecos.length; di++) {
      const { start, end } = rawDecos[di].range
      // Binary search for first line whose end > start
      let lo = 0, hi = n - 1
      while (lo < hi) {
        const mid = (lo + hi) >> 1
        if (origStarts[mid] + lines[mid].length <= start) lo = mid + 1
        else hi = mid
      }
      for (let li = lo; li < n; li++) {
        const ls = origStarts[li]
        if (ls >= end) break
        if (start < ls + lines[li].length) {
          if (!lineDecos.has(li)) lineDecos.set(li, [])
          lineDecos.get(li).push(di)
        }
      }
    }

    // Emit remapped decorations only for matched lines
    const result = []
    for (let i = 0; i < m; i++) {
      const lineIdx = matchedIndices[i]
      const dis = lineDecos.get(lineIdx)
      if (!dis) continue
      const ls = origStarts[lineIdx]
      const le = ls + lines[lineIdx].length
      for (const di of dis) {
        const { start, end } = rawDecos[di].range
        result.push({
          range: {
            start: Math.max(start, ls) - ls + newStarts[i],
            end:   Math.min(end,   le) - ls + newStarts[i],
          },
          options: rawDecos[di].options,
        })
      }
    }

    return { value: filteredText, decos: result, matchCount: matchedIndices.length }
  })()

  $: filteredValue = filterResult.value
  $: filteredDecorations = filterResult.decos
  $: filterMatchCount = filterResult.matchCount
  $: totalLineCount = displayValue ? displayValue.split('\n').length : 0
</script>

<div class="border-t border-gray-200">
  {#if beautify && beautifyRepaired}
    <div class="flex items-center gap-1.5 px-4 py-1.5 bg-amber-50 border-b border-amber-200 text-[11px] text-amber-700 font-medium">
      <i class="fas fa-wrench text-[10px]"></i>
      auto-repaired — displaying best-effort formatted output; stored relic is unchanged
    </div>
  {/if}
  <!-- Line filter bar -->
  {#if showLineFilter}
    <div class="border-b {darkMode ? 'border-gray-700' : 'border-gray-200'} px-3 py-1.5">
      <div class="relative">
        <i class="fas fa-search absolute left-2 top-1/2 -translate-y-1/2 text-[10px] {regexError ? 'text-red-400' : (darkMode ? 'text-gray-500' : 'text-gray-400')}"></i>
        <input
          type="text"
          placeholder="Filter lines… (regex)"
          bind:value={filterValue}
          on:input={onFilterInput}
          class="w-full text-xs pl-6 {filterValue ? 'pr-20' : 'pr-12'} py-1 rounded border {darkMode ? 'bg-gray-800 border-gray-600 text-gray-200 placeholder-gray-600' : 'bg-white border-gray-300 text-gray-700 placeholder-gray-400'} focus:outline-none focus:ring-1 focus:ring-blue-400"
        />
        <!-- Right-side controls -->
        <div class="absolute right-1.5 top-1/2 -translate-y-1/2 flex items-center gap-0.5">
          <!-- Case-sensitive toggle -->
          <button
            on:click={() => filterCase = !filterCase}
            title="Case sensitive"
            class="px-1 py-0.5 rounded text-[10px] font-mono leading-none transition-colors {filterCase ? 'text-blue-400' : (darkMode ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600')}"
          >Aa</button>
          <!-- Regex cheatsheet -->
          <button
            on:click={() => showCheatsheet = true}
            title="Regex cheatsheet"
            class="px-1 py-0.5 rounded text-[10px] font-mono leading-none transition-colors {darkMode ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'}"
          >?</button>
          <!-- Match count -->
          {#if matchLine !== null}
            <span class="text-[11px] {darkMode ? 'text-gray-400' : 'text-gray-500'} whitespace-nowrap pointer-events-none ml-0.5">
              {filterMatchCount}/{totalLineCount}
            </span>
          {/if}
          <!-- Clear button -->
          {#if filterValue}
            <button
              on:click={clearFilter}
              class="{darkMode ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'} ml-0.5"
            >
              <i class="fas fa-times text-[10px]"></i>
            </button>
          {/if}
        </div>
      </div>
    </div>
  {/if}
  <MonacoEditor
    value={filteredValue}
    {language}
    readOnly={true}
    height="calc(100vh - 300px)"
    relicId={relicId}
    noWrapper={true}
    {showSyntaxHighlighting}
    {showLineNumbers}
    {showComments}
    {fontSize}
    {comments}
    {isAdmin}
    {darkMode}
    ansiDecorations={filteredDecorations}
    on:line-clicked={forwardEvent}
    on:line-range-selected={forwardEvent}
    on:multi-line-selected={forwardEvent}
    on:line-copied={forwardEvent}
    on:createComment={forwardEvent}
    on:updateComment={forwardEvent}
    on:deleteComment={forwardEvent}
    on:toggle-comments={forwardEvent}
  />
</div>
{#if processed.truncated}
  <div class="bg-blue-50 border-t border-gray-200 px-6 py-4 text-center text-sm text-blue-700 rounded-b-lg">
    Content truncated. <a href="/{relicId}/raw" class="font-semibold hover:underline">Download full file</a>
  </div>
{/if}

<!-- Regex cheatsheet modal -->
{#if showCheatsheet}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
    on:click={() => showCheatsheet = false}
  >
    <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
    <div
      class="w-96 rounded-xl shadow-2xl border overflow-hidden {darkMode ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'}"
      on:click|stopPropagation
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b {darkMode ? 'border-gray-700' : 'border-gray-100'}">
        <span class="text-sm font-semibold {darkMode ? 'text-gray-100' : 'text-gray-800'}">Regex cheatsheet</span>
        <button
          on:click={() => showCheatsheet = false}
          class="{darkMode ? 'text-gray-500 hover:text-gray-300' : 'text-gray-400 hover:text-gray-600'}"
        ><i class="fas fa-times text-xs"></i></button>
      </div>
      <!-- Rows -->
      <div class="px-4 py-3 space-y-2.5 text-[12px]">
        {#each [
          ['error|warn',           'match either term'],
          ['error.*warn',          'error followed by warn'],
          ['^import',              'line starts with'],
          ['\\bfoo\\b',           'exact word boundary'],
          ['};?$',                 'line ends with'],
          ['\\d+',                'one or more digits'],
          ['[A-Z]{2,}',           'two or more uppercase letters'],
          ['(TODO|FIXME)',         'either annotation'],
        ] as [pattern, desc]}
          <div class="flex items-center gap-3">
            <code class="font-mono text-[11px] w-36 shrink-0 {darkMode ? 'text-blue-300' : 'text-blue-600'}">{pattern}</code>
            <span class="{darkMode ? 'text-gray-400' : 'text-gray-500'}">{desc}</span>
          </div>
        {/each}
      </div>
      <!-- Footer hint -->
      <div class="px-4 py-2.5 border-t text-[11px] {darkMode ? 'border-gray-700 text-gray-500' : 'border-gray-100 text-gray-400'}">
        Toggle <span class="font-mono font-medium">Aa</span> for case-sensitive matching
      </div>
    </div>
  </div>
{/if}
