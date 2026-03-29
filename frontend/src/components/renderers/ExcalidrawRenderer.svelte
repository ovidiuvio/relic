<script>
  import { onMount, onDestroy } from 'svelte'

  export let processed

  // Container ref for React rendering
  let viewContainer
  let viewContainerHeight = 0

  // Dynamically load Excalidraw and React
  let ExcalidrawLib = null
  let React = null
  let createRoot = null
  let viewRoot = null
  let excalidrawLoading = true
  let excalidrawError = null

  onMount(async () => {
    try {
      // Dynamically import React, ReactDOM, and Excalidraw
      const [reactModule, reactDOMClientModule, excalidrawModule] = await Promise.all([
        import('react'),
        import('react-dom/client'),
        import('@excalidraw/excalidraw')
      ])

      React = reactModule.default
      createRoot = reactDOMClientModule.createRoot
      ExcalidrawLib = excalidrawModule.Excalidraw

      excalidrawLoading = false
    } catch (error) {
      console.error('[ExcalidrawRenderer] Failed to load Excalidraw:', error)
      excalidrawError = error.message
      excalidrawLoading = false
    }
  })

  onDestroy(() => {
    // Cleanup React component
    if (viewRoot) {
      viewRoot.unmount()
      viewRoot = null
    }
  })

  // Render Excalidraw using React 18 createRoot API
  function renderExcalidraw() {
    if (!React || !createRoot || !ExcalidrawLib || processed.error) return
    if (!viewContainer) return

    const props = {
      initialData: {
        elements: processed.data?.elements || [],
        appState: processed.data?.appState || {},
        scrollToContent: true
      },
      viewModeEnabled: true,
      zenModeEnabled: false,
      gridModeEnabled: false
    }

    // Create root if it doesn't exist, otherwise just update
    if (!viewRoot) {
      viewRoot = createRoot(viewContainer)
    }
    viewRoot.render(React.createElement(ExcalidrawLib, props))
  }

  // Re-render when container is ready
  $: if (!excalidrawLoading && !excalidrawError && viewContainer) {
    renderExcalidraw()
  }
</script>

<div class="border-t border-gray-200 flex flex-col flex-1 min-h-0">
  {#if excalidrawLoading}
    <div class="flex items-center justify-center p-12">
      <div class="text-center">
        <i class="fas fa-spinner fa-spin text-blue-600 text-4xl mb-4"></i>
        <p class="text-gray-600">Loading Excalidraw...</p>
      </div>
    </div>
  {:else if excalidrawError}
    <div class="flex items-center justify-center p-12">
      <div class="text-center">
        <i class="fas fa-exclamation-triangle text-red-600 text-4xl mb-4"></i>
        <p class="text-gray-600 mb-2">Failed to load Excalidraw editor</p>
        <p class="text-sm text-gray-500">{excalidrawError}</p>
      </div>
    </div>
  {:else if processed.error}
    <div class="flex items-center justify-center p-12">
      <div class="text-center">
        <i class="fas fa-exclamation-circle text-yellow-600 text-4xl mb-4"></i>
        <p class="text-gray-600 mb-2">Invalid Excalidraw file</p>
        <p class="text-sm text-gray-500">{processed.error}</p>
      </div>
    </div>
  {:else}
    <!-- Excalidraw Viewer (read-only) -->
    <div class="flex-1 min-h-0" bind:clientHeight={viewContainerHeight}>
      {#if viewContainerHeight > 0}
        <div bind:this={viewContainer} style="height: {viewContainerHeight}px; width: 100%;"></div>
      {/if}
    </div>
  {/if}
</div>
