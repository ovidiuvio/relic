<script>
  import Icon from '../lib/ui/Icon.svelte'
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

  let cancelled = false
  function cancelPassword() {
    showPasswordModal = false
    cancelled = true
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

{#if showPasswordModal}
  <!-- Asked inline, where the PDF will show; no dialog. -->
  <div class="pdf-state">
    <form class="pdf-lock" on:submit|preventDefault={submitPassword}>
      <Icon name="lock" size={22} />
      <h3>This PDF has a password</h3>
      <p>Enter it to see the pages. It stays in this browser tab.</p>
      <span class="r-input" class:is-error={passwordError}>
        <!-- svelte-ignore a11y-autofocus -->
        <input
          type="password"
          bind:value={passwordInput}
          on:keydown={(e) => e.key === 'Escape' && cancelPassword()}
          placeholder="Password"
          aria-label="PDF password"
          disabled={processingPassword}
          autofocus
        />
      </span>
      {#if passwordError}<p class="pdf-error" role="alert">{passwordError}</p>{/if}
      <div class="pdf-actions">
        <button type="button" class="r-btn r-btn-secondary r-btn-md" on:click={cancelPassword} disabled={processingPassword}>Cancel</button>
        <button class="r-btn r-btn-primary r-btn-md" disabled={processingPassword || !passwordInput}>{processingPassword ? 'Unlocking…' : 'Unlock'}</button>
      </div>
    </form>
  </div>
{:else if pdfDocument}
  <div bind:this={scrollContainer} on:scroll={handleScroll} class="pdf-pages">
    {#if loading}<p class="pdf-loading" role="status">Rendering {numPages} {numPages === 1 ? 'page' : 'pages'}…</p>{/if}
    {#each Array(numPages) as _, i}
      <figure class="pdf-page">
        <figcaption>Page {i + 1}</figcaption>
        <canvas bind:this={canvasElements[i]}></canvas>
      </figure>
    {/each}
  </div>
{:else}
  <div class="pdf-state">
    <Icon name={cancelled ? 'lock' : 'file'} size={22} />
    <p>{cancelled ? 'No preview without the password.' : 'This PDF couldn’t be shown.'}</p>
    <div class="pdf-actions">
      {#if cancelled}<button class="r-btn r-btn-secondary r-btn-md" on:click={() => { cancelled = false; showPasswordModal = true }}>Enter the password</button>{/if}
      {#if relicId}<a class="r-btn r-btn-primary r-btn-md" href="/{relicId}/raw" data-reload><Icon name="download" />Open the raw file</a>{/if}
    </div>
  </div>
{/if}

<style>
  .pdf-pages {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-4);
    padding: var(--space-4);
    overflow: auto;
    background: var(--chip);
  }
  .pdf-page {
    display: grid;
    gap: 4px;
    margin: 0;
  }
  .pdf-page figcaption {
    color: var(--ink-3);
    font: 11.5px var(--font-mono);
  }
  canvas {
    max-width: 100%;
    height: auto;
    background: #fff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 4px 12px rgba(0, 0, 0, 0.06);
  }
  .pdf-loading {
    margin: 0;
    color: var(--ink-3);
    font-size: 12.5px;
  }
  .pdf-state {
    flex: 1;
    display: grid;
    place-content: center;
    justify-items: center;
    gap: var(--space-2);
    padding: var(--space-5);
    background: var(--surface);
    color: var(--ink-3);
    font: 13px/1.5 var(--font-sans);
    text-align: center;
  }
  .pdf-state p {
    margin: 0;
    color: var(--ink-2);
  }
  .pdf-lock {
    display: grid;
    justify-items: center;
    gap: var(--space-2);
    width: min(320px, 100%);
  }
  .pdf-lock h3 {
    margin: 0;
    color: var(--ink);
    font-size: 15px;
    font-weight: 600;
  }
  .pdf-lock .r-input {
    width: 100%;
    margin-top: var(--space-1);
  }
  .pdf-lock .r-input.is-error {
    border-color: var(--danger);
  }
  .pdf-error {
    color: var(--danger) !important;
    font-size: 12.5px;
  }
  .pdf-actions {
    display: flex;
    gap: var(--space-2);
    margin-top: var(--space-1);
  }
</style>
