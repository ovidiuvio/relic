<script>
  import { onMount, onDestroy } from 'svelte'
  import { renderPDFPage,processPDF } from '../services/processors/pdfProcessor.js'
  import { getRelicRaw } from '../services/api'
  import { showToast } from '../stores/toastStore'

  export let pdfDocument = null
  export let metadata = {}
  export let passwordRequired = false
  export let relicId = ''

  let currentPage = 1
  let loading = false
  let scale = 1.5
  let showPasswordModal = passwordRequired
  let passwordInput = ''
  let passwordError = ''
  let processingPassword = false
  let canvasElements = [] // Array of canvas elements for all pages
  let scrollContainer
  let renderingPages = new Set() // Track which pages are currently rendering

  $: numPages = metadata?.numPages || 0
  $: canGoPrev = currentPage > 1
  $: canGoNext = currentPage < numPages

  // Export control methods for parent component
  export function getState() {
    return { currentPage, numPages, scale, loading }
  }

  export function zoomInMethod() {
    zoomIn()
  }

  export function zoomOutMethod() {
    zoomOut()
  }

  export function resetZoomMethod() {
    resetZoom()
  }

  // Render all pages when PDF document is loaded
  $: if (pdfDocument && canvasElements.length > 0) {
    renderAllPages()
  }

  // Show password modal if required
  $: if (passwordRequired && !pdfDocument) {
    showPasswordModal = true
  }

  async function renderAllPages() {
    if (!pdfDocument || canvasElements.length === 0) return

    loading = true
    try {
      // Render all pages
      for (let i = 1; i <= numPages; i++) {
        const canvas = canvasElements[i - 1]
        if (canvas && !renderingPages.has(i)) {
          renderingPages.add(i)
          try {
            await renderPDFPage(pdfDocument, i, canvas, scale)
          } catch (error) {
            console.error(`Failed to render page ${i}:`, error)
          } finally {
            renderingPages.delete(i)
          }
        }
      }
    } catch (error) {
      console.error('Failed to render pages:', error)
      showToast('Failed to render PDF pages', 'error')
    } finally {
      loading = false
      renderingPages.clear()
    }
  }

  function handleScroll() {
    if (!scrollContainer) return

    // Find which page is currently in view
    const containerTop = scrollContainer.scrollTop
    const containerHeight = scrollContainer.clientHeight
    const containerMiddle = containerTop + containerHeight / 2

    // Find the page that's most visible in the middle of the viewport
    for (let i = 0; i < canvasElements.length; i++) {
      const canvas = canvasElements[i]
      if (canvas) {
        const canvasTop = canvas.offsetTop
        const canvasBottom = canvasTop + canvas.height

        if (containerMiddle >= canvasTop && containerMiddle <= canvasBottom) {
          currentPage = i + 1
          break
        }
      }
    }
  }

  function scrollToPage(pageNum) {
    if (!scrollContainer || !canvasElements[pageNum - 1]) return

    const canvas = canvasElements[pageNum - 1]
    scrollContainer.scrollTo({
      top: canvas.offsetTop - 20,
      behavior: 'smooth'
    })
  }

  function zoomIn() {
    scale = Math.min(scale + 0.25, 3.0)
    renderAllPages()
  }

  function zoomOut() {
    scale = Math.max(scale - 0.25, 0.5)
    renderAllPages()
  }

  function resetZoom() {
    scale = 1.5
    renderAllPages()
  }

  async function submitPassword() {
    if (!passwordInput.trim()) {
      passwordError = 'Please enter a password'
      return
    }

    processingPassword = true
    passwordError = ''

    try {
      // Fetch raw content again
      const rawResponse = await getRelicRaw(relicId)
      const content = await rawResponse.data.arrayBuffer()

      // Try to process with password
      const result = await processPDF(new Uint8Array(content), passwordInput)

      if (result.passwordRequired) {
        passwordError = result.passwordError || 'Incorrect password'
      } else {
        // Success! Update the document
        pdfDocument = result.pdfDocument
        metadata = result.metadata
        showPasswordModal = false
        passwordInput = ''
        showToast('PDF unlocked successfully', 'success')
      }
    } catch (error) {
      console.error('Password authentication error:', error)
      passwordError = 'Failed to unlock PDF'
    } finally {
      processingPassword = false
    }
  }

  function cancelPassword() {
    showPasswordModal = false
    showToast('PDF preview cancelled. You can download the file instead.', 'info')
  }

  // Keyboard navigation
  function handleKeydown(event) {
    // Don't intercept if password modal is open
    if (showPasswordModal) return

    if (event.key === 'ArrowLeft' || event.key === 'PageUp') {
      event.preventDefault()
      if (canGoPrev) {
        currentPage--
        scrollToPage(currentPage)
      }
    } else if (event.key === 'ArrowRight' || event.key === 'PageDown') {
      event.preventDefault()
      if (canGoNext) {
        currentPage++
        scrollToPage(currentPage)
      }
    } else if (event.key === 'Home') {
      event.preventDefault()
      currentPage = 1
      scrollToPage(1)
    } else if (event.key === 'End') {
      event.preventDefault()
      currentPage = numPages
      scrollToPage(numPages)
    } else if (event.key === '+' || event.key === '=') {
      event.preventDefault()
      zoomIn()
    } else if (event.key === '-') {
      event.preventDefault()
      zoomOut()
    } else if (event.key === '0') {
      event.preventDefault()
      resetZoom()
    }
  }

  function handlePasswordKeydown(event) {
    if (event.key === 'Enter') {
      submitPassword()
    } else if (event.key === 'Escape') {
      cancelPassword()
    }
  }

  onMount(() => {
    window.addEventListener('keydown', handleKeydown)
  })

  onDestroy(() => {
    window.removeEventListener('keydown', handleKeydown)
    // Clean up PDF document
    if (pdfDocument) {
      pdfDocument.destroy()
    }
  })
</script>

<!-- Password Modal -->
{#if showPasswordModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
      <div class="flex items-center gap-3 mb-4">
        <i class="fas fa-lock text-red-600 text-2xl"></i>
        <h3 class="text-lg font-bold text-gray-900">Password Protected PDF</h3>
      </div>

      <p class="text-sm text-gray-600 mb-4">
        This PDF is password protected. Please enter the password to view it.
      </p>

      <div class="mb-4">
        <input
          type="password"
          bind:value={passwordInput}
          on:keydown={handlePasswordKeydown}
          placeholder="Enter password"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={processingPassword}
          autofocus
        />
        {#if passwordError}
          <p class="text-sm text-red-600 mt-2">
            <i class="fas fa-exclamation-circle mr-1"></i>
            {passwordError}
          </p>
        {/if}
      </div>

      <div class="flex gap-3">
        <button
          on:click={submitPassword}
          disabled={processingPassword}
          class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {#if processingPassword}
            <i class="fas fa-spinner fa-spin mr-2"></i>
            Unlocking...
          {:else}
            <i class="fas fa-unlock mr-2"></i>
            Unlock
          {/if}
        </button>
        <button
          on:click={cancelPassword}
          disabled={processingPassword}
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </div>
  </div>
{/if}

{#if pdfDocument}
  <!-- PDF Canvas Container - Continuous Scroll -->
  <div
    bind:this={scrollContainer}
    on:scroll={handleScroll}
    class="bg-gray-100 p-6 overflow-auto"
    style="height: calc(100vh - 400px); min-height: 500px;"
  >
    <div class="flex flex-col items-center gap-4">
      {#if loading}
        <div class="flex items-center gap-2 mb-4">
          <i class="fas fa-spinner fa-spin text-blue-600 text-xl"></i>
          <p class="text-sm text-gray-600">Rendering {numPages} pages...</p>
        </div>
      {/if}
      {#each Array(numPages) as _, i}
        <div class="relative">
          <div class="absolute -top-6 left-0 text-xs text-gray-500">
            Page {i + 1}
          </div>
          <canvas
            bind:this={canvasElements[i]}
            class="shadow-lg bg-white"
          ></canvas>
        </div>
      {/each}
    </div>
  </div>

{:else if !showPasswordModal}
  <div class="p-6 text-center text-gray-600">
    <i class="fas fa-exclamation-circle text-4xl mb-4"></i>
    <p>Failed to load PDF. Please try downloading the file instead.</p>
  </div>
{/if}

<style>
  /* Ensure canvas doesn't overflow container */
  canvas {
    max-width: 100%;
    height: auto;
  }
</style>
