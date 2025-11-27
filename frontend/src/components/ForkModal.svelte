<script>
  import { forkRelic, getRelicRaw } from '../services/api'
  import { showToast } from '../stores/toastStore'
  import { getContentType, getFileExtension, detectLanguageHint } from '../services/typeUtils'
  import MonacoEditor from './MonacoEditor.svelte'

  export let open = false
  export let relicId = ''
  export let relic = null

  let forkName = ''
  let forkContent = ''
  let forkLanguage = 'auto'
  let forkAccessLevel = 'public'
  let forkExpiration = 'never'
  let isLoading = false
  let editorContent = ''

  async function loadOriginalContent() {
    if (!relicId) return

    try {
      console.log('[ForkModal] Loading original content for relic:', relicId)
      const response = await getRelicRaw(relicId)
      const content = await response.data.arrayBuffer()
      const text = new TextDecoder().decode(content)

      forkContent = text
      editorContent = text

      // Auto-detect language from original relic
      if (relic.language_hint) {
        forkLanguage = relic.language_hint
      } else {
        forkLanguage = detectLanguageHint(relic.content_type)
      }

      console.log('[ForkModal] Loaded original content, length:', text.length)
      console.log('[ForkModal] Initial forkContent:', forkContent.substring(0, 50))
      console.log('[ForkModal] Initial editorContent:', editorContent.substring(0, 50))
    } catch (error) {
      console.error('[ForkModal] Failed to load original content:', error)
      showToast('Failed to load original relic content', 'error')
      forkContent = ''
      editorContent = ''
    }
  }

  async function handleForkSubmit(e) {
    e.preventDefault()

    // Use editorContent as the most up-to-date content
    const finalContent = editorContent || forkContent || ''

    console.log('[ForkModal] Submitting fork with content length:', finalContent.length)
    console.log('[ForkModal] Content preview:', finalContent.substring(0, 100))
    console.log('[ForkModal] Fork name being submitted:', forkName)

    if (!finalContent.trim()) {
      showToast('Please enter some content', 'warning')
      return
    }

    isLoading = true

    try {
      // Determine content type based on type selection
      const contentType = forkLanguage !== 'auto' ? getContentType(forkLanguage) : 'text/plain'
      const fileExtension = forkLanguage !== 'auto' ? getFileExtension(forkLanguage) : 'txt'

      // Create a File object from the content with proper MIME type
      const blob = new Blob([finalContent], { type: contentType })
      const fileName = forkName || `fork-of-${relicId}.${fileExtension}`
      const file = new File([blob], fileName, { type: contentType })

      // Use our fork API function
      const response = await forkRelic(relicId, file, forkName, forkAccessLevel, forkExpiration)

      const data = response.data
      const forkedRelicUrl = `/${data.id}`
      showToast('Relic forked successfully!', 'success')

      // Navigate to the new forked relic
      window.location.href = forkedRelicUrl

      // Reset form and close modal
      resetForm()
      open = false
    } catch (error) {
      showToast(error.message || 'Failed to fork relic', 'error')
      console.error('[ForkModal] Error forking relic:', error)
    } finally {
      isLoading = false
    }
  }

  function resetForm() {
    forkName = ''
    forkContent = ''
    forkLanguage = 'auto'
    forkAccessLevel = 'public'
    forkExpiration = 'never'
    editorContent = ''
  }

  function handleContentChange(newContent) {
    forkContent = newContent
    editorContent = newContent
    console.log('[ForkModal] Content updated, new length:', newContent.length)
  }

  // Load original content when modal opens
  $: if (open && relicId && relic) {
    console.log('[ForkModal] Setting fork details - relic:', relic)
    // Don't auto-populate fork name - let user enter their own
    // forkName will remain as default (empty) allowing user to type
    console.log('[ForkModal] Fork name ready for user input')
    loadOriginalContent()
  }

  // Log fork name changes
  $: if (forkName) {
    console.log('[ForkModal] Fork name changed to:', forkName)
  }

  // Reset when modal closes
  $: if (!open) {
    resetForm()
  }

  function closeModal() {
    open = false
  }

  function handleBackdropClick(e) {
    if (e.target === e.currentTarget) {
      closeModal()
    }
  }
</script>

{#if open}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" on:click={handleBackdropClick}>
    <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col" on:click|stopPropagation>
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900 flex items-center">
          <i class="fas fa-code-branch text-teal-600 mr-2"></i>
          Fork Relic
        </h2>
        <button
          on:click={closeModal}
          class="text-gray-400 hover:text-gray-600 transition-colors"
          title="Close"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>

      <!-- Form -->
      <form on:submit={handleForkSubmit} class="flex-1 overflow-y-auto">
        <div class="p-6 space-y-6">
          <!-- Original Relic Info -->
          <div class="bg-gray-50 rounded-lg p-4">
            <h3 class="text-sm font-medium text-gray-700 mb-2">Original Relic</h3>
            <div class="text-xs text-gray-600">
              <div><strong>ID:</strong> {relicId}</div>
              {#if relic?.name}
                <div><strong>Name:</strong> {relic.name}</div>
              {/if}
              {#if relic?.content_type}
                <div><strong>Type:</strong> {relic.content_type}</div>
              {/if}
            </div>
          </div>

          <!-- Fork Details -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label for="forkName" class="block text-sm font-medium text-gray-700 mb-1">Fork Name</label>
              <input
                type="text"
                id="forkName"
                bind:value={forkName}
                placeholder="e.g. My Forked Configuration"
                class="w-full px-3 py-2 text-sm maas-input border border-gray-300 rounded"
              />
              <p class="text-xs text-gray-500 mt-1">A descriptive name for this fork (leave empty to auto-generate)</p>
            </div>

            <div>
              <label for="forkLanguage" class="block text-sm font-medium text-gray-700 mb-1">Content Type</label>
              <select
                id="forkLanguage"
                bind:value={forkLanguage}
                class="w-full px-3 py-2 text-sm maas-input bg-white"
              >
                <option value="auto">Auto-detect</option>
                <option value="text">Plain Text</option>
                <option value="markdown">Markdown</option>
                <option value="html">HTML</option>
                <option value="css">CSS</option>
                <option value="json">JSON</option>
                <option value="xml">XML</option>
                <option value="javascript">JavaScript</option>
                <option value="python">Python</option>
                <option value="bash">Bash</option>
                <option value="sql">SQL</option>
                <option value="java">Java</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label for="forkAccessLevel" class="block text-sm font-medium text-gray-700 mb-1">Visibility</label>
              <select
                id="forkAccessLevel"
                bind:value={forkAccessLevel}
                class="w-full px-3 py-2 text-sm maas-input bg-white"
              >
                <option value="public">Public</option>
                <option value="private">Private</option>
              </select>
              <p class="text-xs text-gray-500 mt-1">
                {#if forkAccessLevel === 'public'}Anyone can view this fork
                {:else}Private fork - only accessible via direct URL
                {/if}
              </p>
            </div>

            <div>
              <label for="forkExpiration" class="block text-sm font-medium text-gray-700 mb-1">Expiration</label>
              <select
                id="forkExpiration"
                bind:value={forkExpiration}
                class="w-full px-3 py-2 text-sm maas-input bg-white"
              >
                <option value="never">Never</option>
                <option value="1h">1 Hour</option>
                <option value="24h">24 Hours</option>
                <option value="7d">7 Days</option>
                <option value="30d">30 Days</option>
              </select>
            </div>
          </div>

          <!-- Content Editor -->
          <div>
            <label for="forkContent" class="block text-sm font-medium text-gray-700 mb-1">Content</label>
            <div class="border border-gray-200 rounded-lg overflow-hidden" style="height: 400px;">
              <MonacoEditor
                value={editorContent}
                language={forkLanguage === 'auto' ? 'plaintext' : forkLanguage}
                readOnly={false}
                height="400px"
                on:change={(event) => handleContentChange(event.detail)}
              />
            </div>
            <div class="flex items-center justify-between mt-2 text-sm text-gray-500">
              <div>{editorContent.length} characters</div>
              <div class="text-xs">
                <i class="fas fa-info-circle text-teal-600"></i>
                Edit the content above to customize your fork
              </div>
          </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="px-6 py-4 border-t border-gray-200 bg-gray-50">
          <div class="flex justify-end gap-3">
            <button
              type="button"
              on:click={closeModal}
              disabled={isLoading}
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              class="maas-btn-primary px-6 py-2 text-sm rounded font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {#if isLoading}
                <i class="fas fa-spinner fa-spin mr-1"></i>
                Creating Fork...
              {:else}
                <i class="fas fa-code-branch mr-1"></i>
                Create Fork
              {/if}
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
{/if}