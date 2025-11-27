<script>
  import { onMount, createEventDispatcher } from 'svelte'
  import * as monaco from 'monaco-editor'
  import {
    parseLineNumberFragment,
    getCurrentLineNumberFragment,
    getHighlightDecorations,
    getLineNumberFromClick,
    updateUrlWithLineNumbers,
    createLineTooltip
  } from '../utils/lineNumbers'

  export let value = ''
  export let language = 'plaintext'
  export let readOnly = true
  export let height = '600px'
  export let relicId = ''

  let container
  let editor
  let highlightedLines = []
  let currentFragment = null
  let lastClickedLine = null
  let selectedLines = new Set()

  const dispatch = createEventDispatcher()

  onMount(async () => {
    if (!container) return

    // Use Monaco's built-in tokenization which doesn't require workers
    self.MonacoEnvironment = {
      getWorker: () => {
        return {
          postMessage: () => {},
          terminate: () => {}
        }
      }
    }

    try {
      editor = monaco.editor.create(container, {
        value: value || '',
        language: language || 'plaintext',
        readOnly,
        theme: 'vs',
        automaticLayout: true,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        lineNumbers: 'on',
        fontSize: 13,
        fontFamily: '"Courier New", monospace',
        padding: { top: 16, bottom: 16 },
        glyphMargin: true,
        lineDecorationsWidth: 8,
        lineNumbersMinChars: 4,
        // Enable semantic highlighting with built-in tokenization
        'editor.semanticHighlighting.enabled': 'configuredByTheme',
        // Keep syntax highlighting without language services
        'editor.defaultColorDecorators': false,
        'editor.colorDecorators': false,
        'editor.formatOnPaste': false,
        'editor.formatOnType': false
      })

      // Set up line number click handlers
      setupLineClickHandlers()

      // Listen for content changes
      editor.onDidChangeModelContent(() => {
        dispatch('change', editor.getValue())
      })

      // Check for line number fragment on mount
      if (relicId) {
        checkLineNumberFragment()
      }
    } catch (e) {
      console.error('Failed to create Monaco Editor:', e)
    }

    return () => {
      editor?.dispose()
    }
  })

  
  function setupLineClickHandlers() {
    // Handle clicks on line numbers
    editor.onMouseDown((e) => {
      if (e.target.type === monaco.editor.MouseTargetType.GUTTER_LINE_NUMBERS) {
        const lineNumber = e.target.position.lineNumber
        if (e.event.leftButton) {
          if (e.event.shiftKey && lastClickedLine) {
            handleLineRangeClick(lastClickedLine, lineNumber)
          } else if ((e.event.ctrlKey || e.event.metaKey)) {
            handleMultiLineToggle(lineNumber)
          } else {
            handleLineClick(lineNumber)
          }
        }
      }
    })

    
    // Handle hover effects
    editor.onMouseMove((e) => {
      if (e.target.type === monaco.editor.MouseTargetType.GUTTER_LINE_NUMBERS) {
        container.style.cursor = 'pointer'
      } else {
        container.style.cursor = 'default'
      }
    })
  }

  function handleLineClick(lineNumber) {
    if (!relicId) return

    lastClickedLine = lineNumber
    selectedLines = new Set([lineNumber])

    // Update URL with line number fragment
    updateUrlWithLineNumbers(relicId, `L${lineNumber}`)

    // Apply highlighting immediately
    applyManualLineHighlighting()

    dispatch('line-clicked', { lineNumber })
  }

  function handleLineRangeClick(startLine, endLine) {
    if (!relicId) return

    lastClickedLine = endLine

    // Create range from start to end
    const rangeStart = Math.min(startLine, endLine)
    const rangeEnd = Math.max(startLine, endLine)

    // Update selectedLines to include all lines in range
    selectedLines = new Set()
    for (let i = rangeStart; i <= rangeEnd; i++) {
      selectedLines.add(i)
    }

    // Update URL with range fragment
    updateUrlWithLineNumbers(relicId, `L${rangeStart}-${rangeEnd}`)

    // Apply highlighting immediately
    applyManualLineHighlighting()

    dispatch('line-range-selected', {
      startLine: rangeStart,
      endLine: rangeEnd,
      lines: Array.from(selectedLines)
    })
  }

  function handleMultiLineToggle(lineNumber) {
    if (!relicId) return

    lastClickedLine = lineNumber

    // Toggle line selection
    if (selectedLines.has(lineNumber)) {
      selectedLines.delete(lineNumber)
    } else {
      selectedLines.add(lineNumber)
    }

    // Convert to sorted array for URL fragment
    const lines = Array.from(selectedLines).sort((a, b) => a - b)

    // Update URL with multi-line fragment
    updateUrlWithLineNumbers(relicId, lines)

    // Apply highlighting immediately for manual selections
    applyManualLineHighlighting()

    dispatch('multi-line-selected', {
      selectedLines: Array.from(selectedLines),
      lines: lines
    })
  }

  
  function checkLineNumberFragment() {
    const fragment = getCurrentLineNumberFragment()
    if (fragment && fragment !== currentFragment) {
      currentFragment = fragment
      applyLineHighlighting(fragment)
    } else if (!fragment && selectedLines.size > 0) {
      // Apply highlighting for manually selected lines
      applyManualLineHighlighting()
    }
  }

  function applyLineHighlighting(fragment) {
    if (!editor || !fragment) return

    const parsedLines = parseLineNumberFragment(fragment)

    if (!parsedLines.hasLines) {
      clearHighlighting()
      return
    }

    const totalLines = editor.getModel().getLineCount()
    const decorations = getHighlightDecorations(parsedLines, totalLines)

    if (decorations.length > 0) {
      highlightedLines = editor.deltaDecorations(highlightedLines, decorations)

      // Always auto-scroll for URL fragment based highlighting
      const firstLine = Math.min(...parsedLines.lines)

      // Use a small delay to ensure highlighting is applied before scrolling
      setTimeout(() => {
        editor.revealLineInCenter(firstLine)
      }, 100)
    }
  }

  function applyManualLineHighlighting() {
    if (!editor || selectedLines.size === 0) {
      clearHighlighting()
      return
    }

    const lines = Array.from(selectedLines).sort((a, b) => a - b)
    const decorations = lines.map(lineNumber => ({
      range: {
        startLineNumber: lineNumber,
        startColumn: 1,
        endLineNumber: lineNumber,
        endColumn: 1
      },
      options: {
        isWholeLine: true,
        className: 'line-number-highlight',
        glyphMarginClassName: 'line-number-glyph'
      }
    }))

    highlightedLines = editor.deltaDecorations(highlightedLines, decorations)

    // Don't auto-scroll - let user control viewport
  }

  function clearHighlighting() {
    if (highlightedLines.length > 0) {
      editor.deltaDecorations(highlightedLines, [])
      highlightedLines = []
    }
  }

  // Handle URL fragment changes
  function handleHashChange() {
    if (relicId) {
      checkLineNumberFragment()
    }
  }

  // Listen for hash changes
  onMount(() => {
    window.addEventListener('hashchange', handleHashChange)
    return () => {
      window.removeEventListener('hashchange', handleHashChange)
    }
  })

  $: if (editor && value) {
    const currentValue = editor.getValue()
    if (currentValue !== value) {
      editor.setValue(value)
      // Reapply line highlighting after content update
      if (currentFragment) {
        setTimeout(() => applyLineHighlighting(currentFragment), 100)
      }
    }
  }

  $: if (editor && language) {
    try {
      monaco.editor.setModelLanguage(editor.getModel(), language)
    } catch (e) {
      console.error('Failed to set language:', e)
    }
  }

  $: if (editor && relicId) {
    checkLineNumberFragment()
  }

  // Public method to highlight specific lines
  export function highlightLines(lines) {
    if (!editor || !lines) return

    const fragment = Array.isArray(lines)
      ? lines.join(',')
      : typeof lines === 'string'
        ? lines
        : `L${lines}`

    applyLineHighlighting(fragment)
  }
</script>

<div class="bg-white shadow-sm rounded-lg border border-gray-200 mb-6 overflow-hidden">
  <div bind:this={container} style="height: {height};" class="w-full monaco-editor-clickable-lines" />
</div>

<style>
  /* Styles for highlighted lines */
  :global(.line-number-highlight) {
    background-color: #fef3e2 !important;
    border-left: 3px solid #e95420 !important;
  }

  :global(.monaco-editor .line-number-highlight .line-number) {
    color: #c2410c !important;
    font-weight: 600 !important;
  }

  /* Hover effect for line numbers */
  :global(.monaco-editor .margin-view-overlays .line-numbers:hover) {
    background-color: #f3f4f6 !important;
    cursor: pointer !important;
  }

  /* Clickable line numbers styling */
  :global(.monaco-editor-clickable-lines .monaco-editor .line-numbers) {
    cursor: pointer !important;
    transition: background-color 0.2s ease !important;
  }

  :global(.monaco-editor-clickable-lines .monaco-editor .line-numbers:hover) {
    background-color: #e5e7eb !important;
  }

  /* Glyph margin for line highlights */
  :global(.line-number-glyph) {
    background-color: #e95420 !important;
    width: 3px !important;
  }

  </style>
