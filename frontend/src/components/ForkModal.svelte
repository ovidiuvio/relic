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
    } catch (error) {
      showToast('Failed to load original relic content', 'error')
      forkContent = ''
      editorContent = ''
    }
  }

  async function handleForkSubmit(e) {
    e.preventDefault()

    // Use editorContent as the most up-to-date content
    const finalContent = editorContent || forkContent || ''

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
  }

  // Load original content when modal opens
  $: if (open && relicId && relic) {
    loadOriginalContent()
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
    <div class="bg-white rounded-lg shadow-xl w-full h-[90vh] overflow-hidden flex flex-col" style="max-width: min(1200px, 95vw);" on:click|stopPropagation>
      <!-- Header -->
      <div class="px-6 py-3 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
        <div class="flex items-center gap-4">
          <h2 class="text-lg font-semibold text-gray-900 flex items-center">
            <i class="fas fa-code-branch text-teal-600 mr-2"></i>
            Fork Relic
          </h2>
          <div class="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
            From: {relicId}
          </div>
        </div>
        <button
          on:click={closeModal}
          class="text-gray-400 hover:text-gray-600 transition-colors p-1"
          title="Close"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>

      <!-- Form -->
      <form on:submit={handleForkSubmit} class="flex-1 flex flex-col overflow-hidden">
        <!-- Compact Settings Bar -->
        <div class="px-6 py-3 border-b border-gray-200 bg-gray-50 flex-shrink-0">
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label for="forkName" class="block text-xs font-medium text-gray-600 mb-1">Fork Name</label>
              <input
                type="text"
                id="forkName"
                bind:value={forkName}
                placeholder="My Fork"
                class="w-full px-2 py-1.5 text-sm maas-input border border-gray-300 rounded"
              />
            </div>

            <div>
              <label for="forkLanguage" class="block text-xs font-medium text-gray-600 mb-1">Type</label>
              <select
                id="forkLanguage"
                bind:value={forkLanguage}
                class="w-full px-2 py-1.5 text-sm maas-input bg-white"
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

            <div>
              <label for="forkAccessLevel" class="block text-xs font-medium text-gray-600 mb-1">Visibility</label>
              <select
                id="forkAccessLevel"
                bind:value={forkAccessLevel}
                class="w-full px-2 py-1.5 text-sm maas-input bg-white"
              >
                <option value="public">Public</option>
                <option value="private">Private</option>
              </select>
            </div>

            <div>
              <label for="forkExpiration" class="block text-xs font-medium text-gray-600 mb-1">Expires</label>
              <select
                id="forkExpiration"
                bind:value={forkExpiration}
                class="w-full px-2 py-1.5 text-sm maas-input bg-white"
              >
                <option value="never">Never</option>
                <option value="1h">1 Hour</option>
                <option value="24h">24 Hours</option>
                <option value="7d">7 Days</option>
                <option value="30d">30 Days</option>
              </select>
            </div>
          </div>

          {#if relic?.name || relic?.content_type}
            <div class="mt-2 text-xs text-gray-500">
              {#if relic?.name}
                <span class="inline-flex items-center">
                  <strong class="mr-1">Original:</strong> {relic.name}
                </span>
                {#if relic?.content_type}
                  <span class="mx-2">•</span>
                {/if}
              {/if}
              {#if relic?.content_type}
                <span class="inline-flex items-center">
                  <strong class="mr-1">Type:</strong> {relic.content_type}
                </span>
              {/if}
            </div>
          {/if}
        </div>

        <!-- Content Editor - Takes up most of the space -->
        <div class="flex-1 p-6 overflow-hidden flex flex-col">
          <div class="flex items-center justify-between mb-2 flex-shrink-0">
            <label for="forkContent" class="text-sm font-medium text-gray-700">Content Editor</label>
            <div class="text-sm text-gray-500">
              {editorContent.length} characters
            </div>
          </div>
          <div class="flex-1 border border-gray-200 rounded-lg overflow-hidden relative">
            <MonacoEditor
              value={editorContent}
              language={forkLanguage === 'auto' ? 'plaintext' : forkLanguage}
              readOnly={false}
              height="calc(90vh - 280px)"
              on:change={(event) => handleContentChange(event.detail)}
            />
          </div>
          <div class="mt-2 text-xs text-gray-500 text-center flex-shrink-0">
            <i class="fas fa-info-circle text-teal-600 mr-1"></i>
            Edit the content above to customize your fork
          </div>
        </div>

        <!-- Actions -->
        <div class="px-6 py-3 border-t border-gray-200 bg-gray-50 flex-shrink-0">
          <div class="flex justify-between items-center">
            <div class="text-xs text-gray-500">
              {#if forkAccessLevel === 'public'}
                <i class="fas fa-globe text-blue-500 mr-1"></i>
                Public fork - anyone can view
              {:else}
                <i class="fas fa-lock text-gray-500 mr-1"></i>
                Private fork - URL-only access
              {/if}
            </div>
            <div class="flex gap-3">
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
        </div>
      </form>
    </div>
  </div>
{/if}