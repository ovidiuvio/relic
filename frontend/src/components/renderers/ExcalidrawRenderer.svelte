<script>
  import { onMount, onDestroy } from 'svelte'
  import Icon from '../../lib/ui/Icon.svelte'

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

<div class="exc">
  {#if excalidrawLoading}
    <div class="exc-state" role="status"><p>Loading the drawing…</p></div>
  {:else if excalidrawError}
    <div class="exc-state" role="alert">
      <Icon name="info" size={22} />
      <p>The drawing viewer didn’t load.</p>
      <small>{excalidrawError}</small>
    </div>
  {:else if processed.error}
    <div class="exc-state" role="alert">
      <Icon name="info" size={22} />
      <p>This isn’t a drawing Excalidraw can open.</p>
      <small>{processed.error}</small>
    </div>
  {:else}
    <!-- Excalidraw Viewer (read-only) -->
    <div class="exc-view" bind:clientHeight={viewContainerHeight}>
      {#if viewContainerHeight > 0}
        <div bind:this={viewContainer} style="height: {viewContainerHeight}px; width: 100%;"></div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .exc {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .exc-view {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }
  .exc-state {
    flex: 1;
    display: grid;
    place-content: center;
    justify-items: center;
    gap: var(--space-2);
    padding: var(--space-5);
    color: var(--ink-3);
    font: 13px/1.5 var(--font-sans);
    text-align: center;
    overflow-wrap: anywhere;
  }
  .exc-state p {
    margin: 0;
    color: var(--ink-2);
  }
</style>
