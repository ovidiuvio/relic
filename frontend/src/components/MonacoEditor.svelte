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
  import CommentEditor from './CommentEditor.svelte'
  import { processMarkdown } from '../services/markdownProcessor'
  import { getClientKey } from '../services/api'

  export let value = ''
  export let language = 'plaintext'
  export let readOnly = true
  export let height = '600px'
  export let relicId = ''
  export let noWrapper = false
  export let showSyntaxHighlighting = true
  export let showLineNumbers = true
  export let showComments = true
  export let fontSize = 13
  export let comments = []

  let container
  let editor
  let highlightedLines = []
  let currentFragment = null
  let lastClickedLine = null
  let selectedLines = new Set()
  
  // Comment system state
  let commentDecorations = []
  let commentViewZones = new Map() // lineNumber -> zoneId
  let commentResizeObservers = new Map() // zoneId -> ResizeObserver
  let activeCommentInputs = new Set() // lineNumbers with active input
  let collapsedThreads = new Set() // lineNumbers with collapsed threads
  let collapsedComments = new Set() // commentIds with collapsed state
  let activeReplyInput = null // { commentId: string, type: 'reply' | 'quote', content?: string }
  let activeEditInput = null // { commentId: string }
  let commentWidgets = new Map() // zoneId -> widget DOM element
  let commentEditorComponents = [] // Track Svelte components for cleanup
  let hoveredGlyphLine = null
  let currentClientId = null

  const dispatch = createEventDispatcher()

  onMount(async () => {
    if (typeof window !== 'undefined') {
        currentClientId = getClientKey()
    }

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
      // Define relic theme
      monaco.editor.defineTheme('relic-theme', {
        base: 'vs',
        inherit: true,
        rules: [
          { token: '', foreground: '374151' } // gray-700 (matches oklch(0.278...) better than gray-800)
        ],
        colors: {
          'editor.lineHighlightBackground': '#f3f4f6', // gray-100
          'editorLineNumber.foreground': '#9ca3af', // gray-400 (lighter to match mock)
          'editorLineNumber.activeForeground': '#374151', // gray-700
          'scrollbarSlider.background': '#cccccc',
          'scrollbarSlider.hoverBackground': '#b3b3b3',
          'scrollbarSlider.activeBackground': '#999999',
          'editor.selectionBackground': '#e5e7eb' // Lighter selection
        }
      })

      editor = monaco.editor.create(container, {
        value: value || '',
        language: language || 'plaintext',
        readOnly,
        theme: 'relic-theme',
        automaticLayout: true,
        minimap: { enabled: false },
        folding: false,
        guides: { indentation: false },
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        lineNumbers: 'on',
        fontSize,
        lineHeight: 24,
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
        padding: { top: 16, bottom: 16 },
        glyphMargin: true,
        lineDecorationsWidth: 8,
        lineNumbersMinChars: 4,
        renderLineHighlight: 'none', // Cleaner look
        overviewRulerBorder: false,
        hideCursorInOverviewRuler: true,
        scrollbar: {
          vertical: 'visible',
          horizontal: 'visible',
          useShadows: false,
          verticalScrollbarSize: 8,
          horizontalScrollbarSize: 8
        },
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

  $: if (editor && comments) {
    updateCommentDecorations()
    updateCommentZones()
  }

  $: if (editor && (showComments !== undefined)) {
    updateCommentDecorations()
    updateCommentZones()
  }

  function updateCommentDecorations() {
    if (!editor) return

    const newDecorations = []
    const linesWithComments = new Set(comments.map(c => c.line_number))

    // Always add decoration for lines with comments
    linesWithComments.forEach(lineNumber => {
      newDecorations.push({
        range: new monaco.Range(lineNumber, 1, lineNumber, 1),
        options: {
          isWholeLine: false,
          glyphMarginClassName: 'comment-glyph',
          glyphMarginHoverMessage: { value: 'View comments' }
        }
      })
    })
    
    if (showComments) {
        // Also add decoration for lines with active input
        activeCommentInputs.forEach(lineNumber => {
        if (!linesWithComments.has(lineNumber)) {
            newDecorations.push({
            range: new monaco.Range(lineNumber, 1, lineNumber, 1),
            options: {
                isWholeLine: false,
                glyphMarginClassName: 'comment-glyph-add',
                glyphMarginHoverMessage: { value: 'Add comment' }
            }
            })
        }
        })

        // Add decoration for hovered line
        if (hoveredGlyphLine && !linesWithComments.has(hoveredGlyphLine) && !activeCommentInputs.has(hoveredGlyphLine)) {
            newDecorations.push({
            range: new monaco.Range(hoveredGlyphLine, 1, hoveredGlyphLine, 1),
            options: {
                isWholeLine: false,
                glyphMarginClassName: 'comment-glyph-add',
                glyphMarginHoverMessage: { value: 'Add comment' }
            }
            })
        }
    }

    commentDecorations = editor.deltaDecorations(commentDecorations, newDecorations)
  }

  function updateCommentZones() {
    if (!editor) return

    editor.changeViewZones(changeAccessor => {
      // Remove all existing zones
      commentViewZones.forEach(zoneId => {
        changeAccessor.removeZone(zoneId)
      })
      commentViewZones.clear()
      
      // Cleanup old widgets
      commentWidgets.forEach(widget => widget.remove())
      commentWidgets.clear()
      
      // Cleanup observers
      commentResizeObservers.forEach(observer => observer.disconnect())
      commentResizeObservers.clear()

      if (!showComments) return

      // Group comments by line
      const commentsByLine = {}
      comments.forEach(c => {
        if (!commentsByLine[c.line_number]) commentsByLine[c.line_number] = []
        commentsByLine[c.line_number].push(c)
      })

      // Add zones for lines with comments or active input
      const allLines = new Set([...Object.keys(commentsByLine).map(Number), ...activeCommentInputs])
      
      allLines.forEach(lineNumber => {
        const lineComments = commentsByLine[lineNumber] || []
        const showInput = activeCommentInputs.has(lineNumber)
        
        if (lineComments.length === 0 && !showInput) return

        const domNode = document.createElement('div')
        domNode.className = 'comment-widget-zone'
        
        // Wrapper for content to measure height
        const wrapper = document.createElement('div')
        wrapper.className = 'comment-widget-wrapper'
        wrapper.style.fontSize = `${fontSize}px`
        domNode.appendChild(wrapper)
        
        // Prevent editor from stealing focus
        domNode.addEventListener('mousedown', (e) => e.stopPropagation())
        domNode.addEventListener('mouseup', (e) => e.stopPropagation())
        domNode.addEventListener('click', (e) => e.stopPropagation())
        
        // Build Tree
        const commentMap = new Map(lineComments.map(c => [c.id, {...c, children: []}]))
        const rootComments = []
        
        commentMap.forEach(c => {
            if (c.parent_id && commentMap.has(c.parent_id)) {
                commentMap.get(c.parent_id).children.push(c)
            } else {
                rootComments.push(c)
            }
        })
        
        const sortComments = (list) => list.sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
        sortComments(rootComments)
        commentMap.forEach(c => sortComments(c.children))

        // Helper to create input box
        const createInputBox = (onSubmit, onCancel, initialValue = '', submitLabel = 'Comment') => {
            const container = document.createElement('div')
            container.className = 'comment-editor-wrapper'
            
            // Prevent editor from stealing focus
            const stopPropagation = (e) => e.stopPropagation();
            ['mousedown', 'mouseup', 'click', 'mousemove', 'keydown', 'keyup', 'input', 'paste', 'cut', 'copy'].forEach(evt => 
                container.addEventListener(evt, stopPropagation)
            );

            const component = new CommentEditor({
                target: container,
                props: {
                    initialValue,
                    submitLabel
                }
            })
            
            component.$on('submit', (e) => {
                onSubmit(e.detail)
            })
            
            component.$on('cancel', () => {
                onCancel()
            })
            
            commentEditorComponents.push(component)
            return container
        }

        // Render Tree Function
        const renderComment = (comment, container, depth = 0) => {
            const commentEl = document.createElement('div')
            commentEl.className = `comment-item depth-${depth}`
            
            const escapeHtml = (unsafe) => {
                return unsafe
                     .replace(/&/g, "&amp;")
                     .replace(/</g, "&lt;")
                     .replace(/>/g, "&gt;")
                     .replace(/"/g, "&quot;")
                     .replace(/'/g, "&#039;");
            }
            
            const authorName = comment.author_name ? escapeHtml(comment.author_name) : 'Anonymous';
            const content = escapeHtml(comment.content);
            const hasChildren = comment.children && comment.children.length > 0;
            const isCollapsed = collapsedComments.has(comment.id);
            
            if (activeEditInput && activeEditInput.commentId === comment.id) {
                commentEl.innerHTML = `
                    <div class="comment-main">
                        <div class="comment-header">
                            <span class="comment-author">${authorName}</span>
                            <span class="comment-time">${new Date(comment.created_at).toLocaleString()}</span>
                        </div>
                    </div>
                `
                const inputEl = createInputBox((text) => {
                    dispatch('updateComment', { commentId: comment.id, content: text })
                    activeEditInput = null
                    updateCommentZones()
                }, () => {
                    activeEditInput = null
                    updateCommentZones()
                }, comment.content, 'Save')
                
                commentEl.querySelector('.comment-main').appendChild(inputEl)
                setTimeout(() => {
                    const textarea = inputEl.querySelector('textarea')
                    if (textarea) textarea.focus()
                }, 0)
            } else {
                const collapseIcon = hasChildren 
                    ? `<span class="comment-collapse-toggle" style="cursor: pointer; margin-right: 4px; color: #9ca3af; width: 12px; display: inline-block; text-align: center;">
                         <i class="fas fa-chevron-${isCollapsed ? 'right' : 'down'}"></i>
                       </span>` 
                    : `<span style="width: 16px; display: inline-block;"></span>`;

                const isAuthor = currentClientId && comment.client_id === currentClientId;

                commentEl.innerHTML = `
                    <div class="comment-main">
                        <div class="comment-header">
                            <div class="comment-info" style="display: flex; align-items: center;">
                                ${collapseIcon}
                                <span class="comment-author">${authorName}</span>
                                <span class="comment-time">${new Date(comment.created_at).toLocaleString()}</span>
                            </div>
                            <div class="comment-tools">
                                <button class="comment-tool-btn reply-btn" title="Reply"><i class="fas fa-reply"></i></button>
                                <button class="comment-tool-btn quote-btn" title="Quote"><i class="fas fa-quote-right"></i></button>
                                ${isAuthor ? `
                                <button class="comment-tool-btn edit-btn" title="Edit"><i class="fas fa-pen"></i></button>
                                <button class="comment-delete" data-id="${comment.id}" title="Delete"><i class="fas fa-times"></i></button>
                                ` : ''}
                            </div>
                        </div>
                        ${!isCollapsed ? `<div class="comment-content markdown-body" style="padding-left: 16px;"></div>` : ''}
                    </div>
                `
                
                if (!isCollapsed) {
                    processMarkdown(comment.content).then(result => {
                        const contentDiv = commentEl.querySelector('.comment-content');
                        if (contentDiv) contentDiv.innerHTML = result.html;
                    });
                }
                
                const toggleBtn = commentEl.querySelector('.comment-collapse-toggle');
                if (toggleBtn) {
                    toggleBtn.onclick = (e) => {
                        e.stopPropagation();
                        if (collapsedComments.has(comment.id)) {
                            collapsedComments.delete(comment.id);
                        } else {
                            collapsedComments.add(comment.id);
                        }
                        collapsedComments = collapsedComments;
                        updateCommentZones();
                    };
                }
                
                if (isAuthor) {
                    commentEl.querySelector('.comment-delete').onclick = () => dispatch('deleteComment', comment.id)
                    commentEl.querySelector('.edit-btn').onclick = () => {
                        activeEditInput = { commentId: comment.id }
                        updateCommentZones()
                    }
                }
                
                commentEl.querySelector('.reply-btn').onclick = () => {
                    activeReplyInput = { commentId: comment.id, type: 'reply' }
                    updateCommentZones()
                }
                
                commentEl.querySelector('.quote-btn').onclick = () => {
                    activeReplyInput = { commentId: comment.id, type: 'quote', content: `> ${comment.content}\n\n` }
                    updateCommentZones()
                }
            }

            container.appendChild(commentEl)

            if (!isCollapsed) {
                if (activeReplyInput && activeReplyInput.commentId === comment.id) {
                    const replyContainer = document.createElement('div')
                    replyContainer.className = 'comment-children' // Indent the reply input
                    
                    const inputEl = createInputBox((text) => {
                        dispatch('createComment', { lineNumber, content: text, parentId: comment.id })
                        activeReplyInput = null
                        updateCommentZones()
                    }, () => {
                        activeReplyInput = null
                        updateCommentZones()
                    }, activeReplyInput.content || '')
                    
                    replyContainer.appendChild(inputEl)
                    container.appendChild(replyContainer)
                    setTimeout(() => inputEl.querySelector('textarea').focus(), 0)
                }

                if (hasChildren) {
                    const childrenContainer = document.createElement('div')
                    childrenContainer.className = 'comment-children'
                    comment.children.forEach(child => renderComment(child, childrenContainer, depth + 1))
                    container.appendChild(childrenContainer)
                }
            }
        }

        // Create Thread Container
        const threadContainer = document.createElement('div')
        threadContainer.className = 'thread-container'
        
        // Thread Header
        const threadHeader = document.createElement('div')
        threadHeader.className = 'thread-header'
        const isCollapsed = collapsedThreads.has(lineNumber)
        const commentCount = lineComments.length
        
        threadHeader.innerHTML = `
            <div class="thread-title">
                <i class="fas fa-chevron-${isCollapsed ? 'right' : 'down'}"></i>
                <span>${commentCount} Comment${commentCount !== 1 ? 's' : ''}</span>
            </div>
            <div class="thread-actions">
            </div>
        `
        
        threadHeader.onclick = (e) => {
            // Don't toggle if clicking actions
            if (e.target.closest('.thread-actions')) return
            
            if (collapsedThreads.has(lineNumber)) {
                collapsedThreads.delete(lineNumber)
            } else {
                collapsedThreads.add(lineNumber)
            }
            collapsedThreads = collapsedThreads // Trigger reactivity if needed, though we manually update
            updateCommentZones()
        }
        
        threadContainer.appendChild(threadHeader)
        
        // Thread Body
        if (!isCollapsed) {
            const threadBody = document.createElement('div')
            threadBody.className = 'thread-body'
            
            rootComments.forEach(c => renderComment(c, threadBody))
            
            if (showInput) {
                const inputEl = createInputBox((text) => {
                    dispatch('createComment', { lineNumber, content: text })
                    activeCommentInputs.delete(lineNumber)
                    activeCommentInputs = activeCommentInputs
                    updateCommentDecorations()
                }, () => {
                    activeCommentInputs.delete(lineNumber)
                    activeCommentInputs = activeCommentInputs
                    updateCommentDecorations()
                    updateCommentZones()
                })
                threadBody.appendChild(inputEl)
                setTimeout(() => inputEl.querySelector('textarea').focus(), 0)
            } else {
                const replyBtnContainer = document.createElement('div')
                replyBtnContainer.className = 'thread-reply-container'
                replyBtnContainer.innerHTML = `
                    <button class="thread-reply-btn" title="Add Comment">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="overflow: visible;"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path><line x1="12" y1="8" x2="12" y2="14"></line><line x1="9" y1="11" x2="15" y2="11"></line></svg>
                    </button>
                `
                replyBtnContainer.onclick = (e) => {
                    e.stopPropagation()
                    activeCommentInputs.add(lineNumber)
                    updateCommentZones()
                }
                threadBody.appendChild(replyBtnContainer)
            }
            
            threadContainer.appendChild(threadBody)
        }
        
        wrapper.appendChild(threadContainer)

        // Calculate height
        document.body.appendChild(domNode)
        const height = wrapper.offsetHeight
        document.body.removeChild(domNode)

        const zone = {
          afterLineNumber: lineNumber,
          heightInPx: height || 100,
          domNode: domNode
        }

        const zoneId = changeAccessor.addZone(zone)
        
        commentViewZones.set(lineNumber, zoneId)
        commentWidgets.set(zoneId, domNode)
        
        const observer = new ResizeObserver(() => {
            const newHeight = wrapper.offsetHeight
            if (Math.abs(newHeight - zone.heightInPx) > 2) {
                editor.changeViewZones(accessor => {
                    zone.heightInPx = newHeight
                    accessor.layoutZone(zoneId)
                })
            }
        })
        observer.observe(wrapper)
        commentResizeObservers.set(zoneId, observer)
      })
    })
  }

  
  function setupLineClickHandlers() {
    // Handle clicks on line numbers
    editor.onMouseDown((e) => {
      if (e.target.type === monaco.editor.MouseTargetType.GUTTER_GLYPH_MARGIN) {
        const lineNumber = e.target.position.lineNumber
        const hasComments = comments.some(c => c.line_number === lineNumber)

        if (!showComments) {
            if (hasComments) {
                dispatch('toggle-comments')
            }
            return
        }

        if (hasComments) {
            // If comments exist, toggle collapse state
            if (collapsedThreads.has(lineNumber)) {
                collapsedThreads.delete(lineNumber)
            } else {
                // If already expanded, toggle input
                if (activeCommentInputs.has(lineNumber)) {
                    activeCommentInputs.delete(lineNumber)
                } else {
                    activeCommentInputs.add(lineNumber)
                }
            }
        } else {
            // No comments, toggle input
            if (activeCommentInputs.has(lineNumber)) {
                activeCommentInputs.delete(lineNumber)
            } else {
                activeCommentInputs.add(lineNumber)
            }
        }
        
        collapsedThreads = collapsedThreads
        activeCommentInputs = activeCommentInputs
        updateCommentDecorations()
        updateCommentZones()
      } else if (e.target.type === monaco.editor.MouseTargetType.GUTTER_LINE_NUMBERS) {
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
      if (e.target.type === monaco.editor.MouseTargetType.GUTTER_GLYPH_MARGIN) {
        if (!showComments) {
            const lineNumber = e.target.position.lineNumber
            const hasComments = comments.some(c => c.line_number === lineNumber)
            if (hasComments) {
                container.style.cursor = 'pointer'
            } else {
                container.style.cursor = 'default'
            }
            return
        }

        const lineNumber = e.target.position.lineNumber
        if (hoveredGlyphLine !== lineNumber) {
            hoveredGlyphLine = lineNumber
            updateCommentDecorations()
        }
        container.style.cursor = 'pointer'
      } else {
        if (hoveredGlyphLine !== null) {
            hoveredGlyphLine = null
            updateCommentDecorations()
        }
        
        if (e.target.type === monaco.editor.MouseTargetType.GUTTER_LINE_NUMBERS) {
            container.style.cursor = 'pointer'
        } else {
            container.style.cursor = 'default'
        }
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

  // Handle syntax highlighting toggle
  $: if (editor) {
    const model = editor.getModel()
    if (model) {
      if (!showSyntaxHighlighting) {
        // Disable by changing language to plaintext (no syntax highlighting)
        monaco.editor.setModelLanguage(model, 'plaintext')
      } else {
        // Re-enable with original language
        monaco.editor.setModelLanguage(model, language)
      }
    }
  }

  // Handle line numbers toggle
  $: if (editor) {
    editor.updateOptions({
      lineNumbers: showLineNumbers ? 'on' : 'off'
    })
  }

  // Handle font size changes
  $: if (editor) {
    editor.updateOptions({
      fontSize
    })
    
    // Update existing comment widgets font size
    if (commentWidgets) {
        commentWidgets.forEach(widget => {
            const wrapper = widget.querySelector('.comment-widget-wrapper')
            if (wrapper) wrapper.style.fontSize = `${fontSize}px`
        })
    }
  }
</script>

{#if noWrapper}
  <div bind:this={container} style="height: {height};" class="w-full monaco-editor-clickable-lines" />
{:else}
  <div class="bg-white shadow-sm rounded-lg border border-gray-200 mb-6 overflow-hidden">
    <div bind:this={container} style="height: {height};" class="w-full monaco-editor-clickable-lines" />
  </div>
{/if}

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
  :global(.comment-glyph) {
    background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%236B7280"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>') no-repeat center center;
    background-size: 14px 14px;
    cursor: pointer;
  }
  
  :global(.comment-glyph-add) {
    background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%239CA3AF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path><line x1="12" y1="8" x2="12" y2="14"></line><line x1="9" y1="11" x2="15" y2="11"></line></svg>') no-repeat center center;
    background-size: 14px 14px;
    cursor: pointer;
    opacity: 0.5;
    z-index: 10;
  }
  
  :global(.comment-glyph-add:hover) {
    opacity: 1 !important;
    background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%234B5563" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path><line x1="12" y1="8" x2="12" y2="14"></line><line x1="9" y1="11" x2="15" y2="11"></line></svg>') no-repeat center center;
    background-size: 14px 14px;
  }

  :global(.comment-widget-zone) {
    padding: 4px 0 4px 0; /* Removed indentation to align with margin */
    width: 100% !important;
    pointer-events: auto !important;
    z-index: 10;
  }

  :global(.thread-container) {
    background: transparent;
    border: none;
    padding-left: 0;
    width: calc(100% - 40px);
    overflow: hidden;
    margin-bottom: 8px;
  }

  :global(.thread-header) {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 0;
    background: transparent;
    border-bottom: none;
    cursor: pointer;
    user-select: none;
    font-size: 12px;
    color: #9ca3af;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  }
  
  :global(.thread-header:hover) {
    background: transparent;
    color: #6b7280;
  }

  :global(.thread-title) {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
  }
  
  :global(.thread-actions) {
    display: flex;
    gap: 8px;
  }
  
  :global(.thread-body) {
    padding: 0;
  }

  :global(.comment-item) {
    display: flex;
    gap: 12px;
    padding: 4px 0;
    border-bottom: none;
    background: transparent;
    transition: background-color 0.2s;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  }

  :global(.comment-item:hover) {
    background-color: transparent;
  }
  
  :global(.comment-item:last-child) {
    border-bottom: none;
  }
  
  :global(.comment-children) {
    border-left: none;
    margin-left: 12px;
    padding-left: 0;
  }

  :global(.comment-main) {
    flex: 1;
    min-width: 0;
  }

  :global(.comment-header) {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    margin-bottom: 2px;
    padding-bottom: 0;
    gap: 8px;
  }

  :global(.comment-author) {
    font-weight: 600;
    color: #6b7280;
    font-size: inherit;
  }

  :global(.comment-time) {
    font-size: 11px;
    color: #9ca3af;
    margin-left: 8px;
  }

  :global(.comment-tools) {
    display: flex;
    gap: 4px;
    opacity: 0;
    transition: opacity 0.2s;
  }
  
  :global(.comment-item:hover .comment-tools) {
    opacity: 1;
  }

  :global(.comment-tool-btn) {
    background: transparent;
    border: 1px solid transparent;
    cursor: pointer;
    color: #9ca3af;
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  
  :global(.comment-tool-btn:hover) {
    background: #f3f4f6;
    color: #4b5563;
    border-color: #e5e7eb;
  }

  :global(.comment-delete) {
    color: #ef4444;
    cursor: pointer;
    background: none;
    border: none;
    font-size: 11px;
    line-height: 1;
    padding: 2px 6px;
    margin-left: 4px;
    opacity: 0.6;
  }

  :global(.comment-delete:hover) {
    opacity: 1;
    background: #fee2e2;
    border-radius: 4px;
  }

  :global(.comment-content) {
    font-size: inherit;
    color: #6b7280;
    line-height: 1.5;
  }

  :global(.comment-editor-wrapper) {
    padding: 8px 0;
    background: transparent;
    border-top: none;
  }

  :global(.comment-actions) {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  :global(.comment-cancel) {
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    color: #4b5563;
    background: white;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  :global(.comment-cancel:hover) {
    background-color: #f9fafb;
    border-color: #9ca3af;
  }

  :global(.comment-submit) {
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    color: white;
    background: #2563eb; /* Blue instead of orange for cleaner look */
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  
  :global(.comment-submit:hover) {
    background-color: #1d4ed8;
  }
  
  :global(.line-number-glyph) {
    box-shadow: inset 3px 0 0 0 #e95420 !important;
    background-color: transparent !important;
    width: 100% !important;
  }

  :global(.comment-editor-wrapper) {
    margin-bottom: 8px;
    width: calc(100% - 40px);
  }

  :global(.thread-reply-container) {
    padding: 4px 0;
    margin-top: 4px;
  }

  :global(.thread-reply-btn) {
    background: transparent;
    border: none;
    cursor: pointer;
    color: #9ca3af;
    font-size: 12px;
    padding: 6px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    transition: all 0.2s;
    line-height: 1;
  }

  :global(.thread-reply-btn:hover) {
    background: transparent;
    color: #6b7280;
  }

  </style>
