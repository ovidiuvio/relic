<script>
  import MonacoEditor from "./MonacoEditor.svelte";
  import MarkdownIt from "markdown-it";
  import { createEventDispatcher, onMount, onDestroy } from "svelte";

  const dispatch = createEventDispatcher();
  const md = new MarkdownIt({
    html: true,
    linkify: true,
    breaks: true,
    typographer: true,
  });

  export let isBinary = false;
  export let binaryBlob = null;
  export let previewUrl = null;
  export let relic = null;
  export let editorContent = "";
  export let forkLanguage = "auto";
  export let darkMode = true;

  let isExpanded = false;
  let showPreview = false;

  // Excalidraw-specific state
  let isExcalidraw = false;
  let excalidrawData = null;
  let excalidrawContainer = null;
  let excalidrawAPI = null;
  let ExcalidrawLib = null;
  let React = null;
  let createRoot = null;
  let excalidrawRoot = null;
  let excalidrawLoading = false;
  let excalidrawError = null;

  // Editor preferences (initialize from localStorage like RelicViewer)
  let showSyntaxHighlighting = (() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('relic_editor_syntax_highlighting')
      return saved === 'false' ? false : true
    }
    return true
  })()

  let showLineNumbers = (() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('relic_editor_line_numbers')
      return saved === 'false' ? false : true
    }
    return true
  })()

  let fontSize = (() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('relic_editor_font_size')
      return saved ? parseInt(saved, 10) : 13
    }
    return 13
  })()

  // Save editor preferences
  $: if (typeof window !== 'undefined') {
    localStorage.setItem('relic_editor_syntax_highlighting', showSyntaxHighlighting.toString())
  }

  $: if (typeof window !== 'undefined') {
    localStorage.setItem('relic_editor_line_numbers', showLineNumbers.toString())
  }

  $: if (typeof window !== 'undefined') {
    localStorage.setItem('relic_editor_font_size', fontSize.toString())
  }

  $: supportsPreview = forkLanguage === "markdown" || forkLanguage === "html";
  $: if (!supportsPreview) showPreview = false;

  // Check if this is an Excalidraw file
  $: {
    isExcalidraw = relic?.content_type === 'application/vnd.excalidraw+json' ||
                   relic?.language_hint === 'excalidraw';

    if (isExcalidraw && editorContent) {
      try {
        excalidrawData = JSON.parse(editorContent);
        if (!excalidrawLoading && !ExcalidrawLib) {
          loadExcalidraw();
        }
      } catch (error) {
        console.error('[ForkEditor] Failed to parse Excalidraw data:', error);
        excalidrawData = null;
      }
    }
  }

  async function loadExcalidraw() {
    if (excalidrawLoading || ExcalidrawLib) return;

    try {
      excalidrawLoading = true;

      const [reactModule, reactDOMClientModule, excalidrawModule] = await Promise.all([
        import('react'),
        import('react-dom/client'),
        import('@excalidraw/excalidraw')
      ]);

      React = reactModule.default;
      createRoot = reactDOMClientModule.createRoot;
      ExcalidrawLib = excalidrawModule.Excalidraw;

      excalidrawLoading = false;

      // Trigger render
      renderExcalidraw();
    } catch (error) {
      console.error('[ForkEditor] Failed to load Excalidraw:', error);
      excalidrawError = error.message;
      excalidrawLoading = false;
    }
  }

  function renderExcalidraw() {
    if (!React || !createRoot || !ExcalidrawLib || !excalidrawContainer || !excalidrawData) return;

    const props = {
      initialData: {
        elements: excalidrawData.elements || [],
        appState: excalidrawData.appState || {}
      },
      onChange: (elements, appState) => {
        // Update the editor content with the new drawing data
        const updatedData = {
          type: 'excalidraw',
          version: 2,
          source: 'relic',
          elements: elements,
          appState: {
            viewBackgroundColor: appState.viewBackgroundColor,
            currentItemStrokeColor: appState.currentItemStrokeColor,
            currentItemBackgroundColor: appState.currentItemBackgroundColor,
            currentItemFillStyle: appState.currentItemFillStyle,
            currentItemStrokeWidth: appState.currentItemStrokeWidth,
            currentItemRoughness: appState.currentItemRoughness,
            currentItemOpacity: appState.currentItemOpacity,
            gridSize: appState.gridSize,
            colorPalette: appState.colorPalette
          }
        };

        const jsonContent = JSON.stringify(updatedData, null, 2);
        dispatch('change', jsonContent);
      },
      excalidrawAPI: (api) => {
        excalidrawAPI = api;
      }
    };

    if (!excalidrawRoot) {
      excalidrawRoot = createRoot(excalidrawContainer);
    }
    excalidrawRoot.render(React.createElement(ExcalidrawLib, props));
  }

  // Re-render when container or data is ready
  $: if (!excalidrawLoading && !excalidrawError && excalidrawContainer && excalidrawData && ExcalidrawLib) {
    renderExcalidraw();
  }

  onMount(() => {
    if (isExcalidraw && editorContent) {
      loadExcalidraw();
    }
  });

  onDestroy(() => {
    if (excalidrawRoot) {
      excalidrawRoot.unmount();
      excalidrawRoot = null;
    }
    excalidrawAPI = null;
  });

  function renderMarkdown(text) {
    try {
      return md.render(text || "");
    } catch (error) {
      console.error("Markdown rendering error:", error);
      return '<p class="text-red-600">Error rendering markdown</p>';
    }
  }

  function handleContentChange(event) {
    dispatch('change', event.detail);
  }

  function toggleExpanded() {
    isExpanded = !isExpanded;
    dispatch('expand', isExpanded);
  }
</script>

<div class="flex-1 overflow-hidden flex flex-col">
  {#if isExcalidraw}
    <!-- Excalidraw Editor -->
    <div class="px-6 pt-6 pb-2 flex items-center justify-between flex-shrink-0">
      <label class="text-sm font-medium text-gray-700">Excalidraw Editor</label>
      <div class="flex items-center gap-2">
        <div class="text-sm text-gray-500">
          {excalidrawData?.elements?.length || 0} elements
        </div>

        <!-- Full-width Toggle -->
        <button
          type="button"
          on:click={toggleExpanded}
          class="px-2 py-1 rounded text-xs font-medium transition-colors {isExpanded ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
          title={isExpanded ? "Normal width" : "Full width"}
        >
          <i class="fas {isExpanded ? 'fa-compress' : 'fa-expand'}"></i>
        </button>
      </div>
    </div>

    <div class="flex-1 border-t border-gray-200 overflow-hidden bg-gray-50">
      {#if excalidrawLoading}
        <div class="h-full flex items-center justify-center">
          <div class="text-center">
            <i class="fas fa-spinner fa-spin text-blue-600 text-4xl mb-4"></i>
            <p class="text-gray-600">Loading Excalidraw editor...</p>
          </div>
        </div>
      {:else if excalidrawError}
        <div class="h-full flex items-center justify-center">
          <div class="text-center">
            <i class="fas fa-exclamation-triangle text-red-600 text-4xl mb-4"></i>
            <p class="text-gray-600 mb-2">Failed to load Excalidraw editor</p>
            <p class="text-sm text-gray-500">{excalidrawError}</p>
          </div>
        </div>
      {:else}
        <div class="h-full" bind:this={excalidrawContainer}></div>
      {/if}
    </div>

    <div class="px-6 pb-6 pt-2 text-xs text-gray-500 text-center flex-shrink-0">
      <i class="fas fa-info-circle text-teal-600 mr-1"></i>
      Edit the drawing above to customize your fork
    </div>
  {:else if isBinary}
    <!-- Binary/Non-editable Content Preview -->
    <div class="px-6 pt-6 pb-2 flex items-center justify-between flex-shrink-0">
      <label class="text-sm font-medium text-gray-700">Preview</label>
      <div class="flex items-center gap-2">
        <div class="text-sm text-gray-500">
          {binaryBlob ? (binaryBlob.size / 1024).toFixed(2) : 0} KB
        </div>
      </div>
    </div>

    <div class="flex-1 border-t border-gray-200 overflow-hidden bg-gray-50 flex items-center justify-center">
      {#if previewUrl && relic.content_type?.startsWith('image/')}
        <div class="h-full w-full overflow-auto p-6 flex items-center justify-center">
          <img src={previewUrl} alt={relic.name} class="max-w-full max-h-full object-contain" />
        </div>
      {:else if previewUrl && relic.content_type === 'application/pdf'}
        <div class="h-full w-full overflow-hidden">
          <embed src={previewUrl} type="application/pdf" class="w-full h-full" />
        </div>
      {:else}
        <div class="text-center p-6">
          <i class="fas fa-file text-gray-400 text-6xl mb-4"></i>
          <p class="text-gray-600 text-sm mb-2">Binary file cannot be edited</p>
          <p class="text-xs text-gray-500">{relic.content_type}</p>
        </div>
      {/if}
    </div>

    <div class="px-6 pb-6 pt-2 text-xs text-gray-500 text-center flex-shrink-0 bg-amber-50 border-t border-amber-200">
      <i class="fas fa-info-circle text-amber-600 mr-1"></i>
      Binary files cannot be edited. The fork will contain the same content with your custom metadata.
    </div>
  {:else}
    <!-- Text Content Editor -->
    <div class="px-6 pt-6 pb-2 flex items-center justify-between flex-shrink-0">
      <label for="forkContent" class="text-sm font-medium text-gray-700">Content Editor</label>
      <div class="flex items-center gap-2">
        <div class="text-sm text-gray-500">{editorContent.length} characters</div>

        <!-- Full-width Toggle -->
        <button
          type="button"
          on:click={toggleExpanded}
          class="px-2 py-1 rounded text-xs font-medium transition-colors {isExpanded ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
          title={isExpanded ? "Normal width" : "Full width"}
        >
          <i class="fas {isExpanded ? 'fa-compress' : 'fa-expand'}"></i>
        </button>

        <!-- Editor Controls -->
        <div class="flex items-center gap-1 border-l border-gray-300 pl-2 ml-2">
          <button
            type="button"
            on:click={() => showSyntaxHighlighting = !showSyntaxHighlighting}
            class="px-2 py-1 rounded text-xs font-medium transition-colors {showSyntaxHighlighting ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
            title="Toggle syntax highlighting"
          >
            <i class="fas fa-palette text-xs"></i>
          </button>
          <button
            type="button"
            on:click={() => showLineNumbers = !showLineNumbers}
            class="px-2 py-1 rounded text-xs font-medium transition-colors {showLineNumbers ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
            title="Toggle line numbers"
          >
            <i class="fas fa-list-ol text-xs"></i>
          </button>

          <!-- Font Size Combo Box -->
          <div class="flex items-center gap-2 border-l border-gray-300 pl-2 ml-2">
            <i class="fas fa-text-height text-xs text-gray-600"></i>
            <select
              value={fontSize.toString()}
              on:change={(e) => {
                const val = e.target.value
                if (val === 'custom') {
                  const custom = prompt('Enter font size (8-72):', fontSize.toString())
                  if (custom && !isNaN(parseInt(custom, 10))) {
                    const num = parseInt(custom, 10)
                    if (num >= 8 && num <= 72) {
                      fontSize = num
                    }
                  }
                } else {
                  fontSize = parseInt(val, 10)
                }
              }}
              class="pl-1.5 pr-0.5 py-1 rounded text-xs bg-white border border-gray-300 text-gray-700 cursor-pointer hover:border-gray-400"
              style="min-width: fit-content; width: auto;"
              title="Font size"
            >
              <option value="12">12</option>
              <option value="13">13</option>
              <option value="14">14</option>
              <option value="15">15</option>
              <option value="16">16</option>
              <option value="18">18</option>
              <option value="20">20</option>
              <option value="custom">Custom...</option>
            </select>
          </div>
        </div>

        <!-- Preview/Edit Mode Tabs -->
        {#if supportsPreview}
          <div class="flex items-center gap-1">
            <button
              type="button"
              on:click={() => (showPreview = false)}
              class="px-2 py-1 rounded text-xs font-medium transition-colors {!showPreview ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
              title="Edit mode"
            >
              <i class="fas fa-edit"></i>
            </button>
            <button
              type="button"
              on:click={() => (showPreview = true)}
              class="px-2 py-1 rounded text-xs font-medium transition-colors {showPreview ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
              title="Preview mode"
            >
              <i class="fas fa-eye"></i>
            </button>
          </div>
        {/if}
      </div>
    </div>

    <div class="flex-1 border-t border-gray-200 overflow-hidden">
      {#if showPreview && forkLanguage === "markdown"}
        <div class="h-full overflow-y-auto p-6 prose prose-sm max-w-none" on:wheel|stopPropagation>
          {@html renderMarkdown(editorContent)}
        </div>
      {:else if showPreview && forkLanguage === "html"}
        <div class="h-full overflow-hidden" on:wheel|stopPropagation>
          <iframe
            srcdoc={editorContent}
            class="w-full h-full border-0"
            sandbox="allow-same-origin allow-scripts allow-forms"
            title="HTML Preview"
          ></iframe>
        </div>
      {:else}
        <MonacoEditor
          value={editorContent}
          language={forkLanguage === "auto" ? "plaintext" : forkLanguage}
          readOnly={false}
          height="calc(90vh - 280px)"
          noWrapper={true}
          showSyntaxHighlighting={showSyntaxHighlighting}
          showLineNumbers={showLineNumbers}
          fontSize={fontSize}
          {darkMode}
          on:change={handleContentChange}
        />
      {/if}
    </div>
    <div class="px-6 pb-6 pt-2 text-xs text-gray-500 text-center flex-shrink-0">
      <i class="fas fa-info-circle text-teal-600 mr-1"></i>
      Edit the content above to customize your fork
    </div>
  {/if}
</div>
