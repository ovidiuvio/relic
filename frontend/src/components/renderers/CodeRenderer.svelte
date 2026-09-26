<script>
  import FilterStrip from '../../lib/viewer/FilterStrip.svelte'
  import Icon from '../../lib/ui/Icon.svelte'
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

  let monacoHeight = 0

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
  let filterDebounce

  const REGEX_PATTERNS = [
    ['error|warn', 'either term'],
    ['error.*warn', 'error, then warn'],
    ['^import', 'lines starting with'],
    ['\\bfoo\\b', 'the whole word'],
    ['};?$', 'lines ending with'],
    ['\\d+', 'one or more digits'],
    ['[A-Z]{2,}', 'two or more capitals'],
    ['(TODO|FIXME)', 'either annotation'],
  ]

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

<div class="code-view">
  {#if beautify && beautifyRepaired}
    <div class="r-banner r-banner-warning code-notice" role="status">
      <Icon name="info" />Repaired to show it: this is a best-effort format, the stored relic is unchanged.
    </div>
  {/if}
  {#if showLineFilter}
    <FilterStrip
      bind:value={filterValue}
      bind:caseSensitive={filterCase}
      placeholder="Filter lines (regular expression)"
      label="Filter lines"
      dark={darkMode}
      error={regexError}
      count={matchLine !== null ? { matched: filterMatchCount, total: totalLineCount } : null}
      patterns={REGEX_PATTERNS}
      oninput={onFilterInput}
    />
  {/if}
  <!-- overflow-hidden: clientHeight is rounded, so the editor can end up a
       fraction of a pixel taller than this box; unclipped, that gives the
       viewer's scroll container a near-full-height native scrollbar in Chrome. -->
  <div class="flex-1 min-h-0 overflow-hidden" bind:clientHeight={monacoHeight}>
  {#if monacoHeight > 0}
  <MonacoEditor
    value={filteredValue}
    {language}
    readOnly={true}
    height="{monacoHeight}px"
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
  {/if}
  </div>
</div>
{#if processed.truncated}
  <div class="r-banner r-banner-info code-notice" role="status">
    <Icon name="info" />Only the start of this file is shown.
    <a class="r-link" href="/{relicId}/raw">Open the full file</a>
  </div>
{/if}

<style>
  .code-view {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .code-notice {
    flex: none;
  }
  .code-notice :global(.r-icon) {
    flex: none;
    width: 14px;
    height: 14px;
  }
</style>
