<script>
  import { onDestroy } from 'svelte';
  import { forkRelic, getRelicRaw } from "../services/api";
  import { showToast } from "../stores/toastStore";
  import {
    getContentType,
    getFileExtension,
    detectLanguageHint,
    getAvailableSyntaxOptions,
  } from "../services/typeUtils";
  import MonacoEditor from "./MonacoEditor.svelte";
  import MarkdownIt from "markdown-it";

  const md = new MarkdownIt({
    html: true,
    linkify: true,
    breaks: true,
    typographer: true,
  });

  const syntaxOptions = getAvailableSyntaxOptions();

  export let open = false;
  export let relicId = "";
  export let relic = null;

  let forkName = "";
  let forkContent = "";
  let forkLanguage = "auto";
  let forkAccessLevel = "public";
  let forkExpiration = "never";
  let isLoading = false;
  let editorContent = "";
  let isExpanded = false;
  let showPreview = false;
  let isBinary = false;
  let binaryBlob = null;
  let previewUrl = null;

  // Check if content type is binary/non-editable
  function isBinaryContentType(contentType) {
    const binaryTypes = [
      'application/pdf',
      'image/',
      'video/',
      'audio/',
      'application/zip',
      'application/x-zip-compressed',
      'application/gzip',
      'application/x-tar',
      'application/octet-stream'
    ];
    return binaryTypes.some(type => contentType?.startsWith(type));
  }

  async function loadOriginalContent() {
    if (!relicId) return;

    try {
      const response = await getRelicRaw(relicId);
      const content = await response.data.arrayBuffer();

      // Check if this is a binary file
      isBinary = isBinaryContentType(relic.content_type);

      if (isBinary) {
        // Store the binary blob directly
        binaryBlob = new Blob([content], { type: relic.content_type });

        // Create preview URL for images and PDFs
        if (relic.content_type?.startsWith('image/')) {
          previewUrl = URL.createObjectURL(binaryBlob);
        } else if (relic.content_type === 'application/pdf') {
          previewUrl = URL.createObjectURL(binaryBlob);
        }
      } else {
        // Text content - decode as before
        const text = new TextDecoder().decode(content);
        forkContent = text;
        editorContent = text;

        // Auto-detect language from original relic
        if (relic.language_hint) {
          forkLanguage = relic.language_hint;
        } else {
          forkLanguage = detectLanguageHint(relic.content_type);
        }
      }
    } catch (error) {
      showToast("Failed to load original relic content", "error");
      forkContent = "";
      editorContent = "";
      binaryBlob = null;
    }
  }

  async function handleForkSubmit(e) {
    e.preventDefault();

    isLoading = true;

    try {
      let file;

      if (isBinary) {
        // For binary files, use the original blob
        if (!binaryBlob) {
          showToast("No content to fork", "error");
          return;
        }

        const fileName = forkName || relic.name || `fork-of-${relicId}`;
        file = new File([binaryBlob], fileName, { type: relic.content_type });
      } else {
        // For text files, use editorContent as before
        const finalContent = editorContent || forkContent || "";

        if (!finalContent.trim()) {
          showToast("Please enter some content", "warning");
          return;
        }

        // Determine content type based on type selection
        const contentType =
          forkLanguage !== "auto" ? getContentType(forkLanguage) : "text/plain";
        const fileExtension =
          forkLanguage !== "auto" ? getFileExtension(forkLanguage) : "txt";

        // Create a File object from the content with proper MIME type
        const blob = new Blob([finalContent], { type: contentType });
        const fileName = forkName || `fork-of-${relicId}.${fileExtension}`;
        file = new File([blob], fileName, { type: contentType });
      }

      // Use our fork API function
      const response = await forkRelic(
        relicId,
        file,
        forkName,
        forkAccessLevel,
        forkExpiration,
      );

      const data = response.data;
      const forkedRelicUrl = `/${data.id}`;
      showToast("Relic forked successfully!", "success");

      // Navigate to the new forked relic
      window.location.href = forkedRelicUrl;

      // Reset form and close modal
      resetForm();
      open = false;
    } catch (error) {
      showToast(error.message || "Failed to fork relic", "error");
    } finally {
      isLoading = false;
    }
  }

  function resetForm() {
    forkName = "";
    forkContent = "";
    forkLanguage = "auto";
    forkAccessLevel = "public";
    forkExpiration = "never";
    editorContent = "";
    isExpanded = false;
    showPreview = false;
    isBinary = false;
    binaryBlob = null;
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      previewUrl = null;
    }
  }

  function handleContentChange(newContent) {
    forkContent = newContent;
    editorContent = newContent;
  }

  // Load original content when modal opens
  $: if (open && relicId && relic) {
    loadOriginalContent();
  }

  // Reset when modal closes
  $: if (!open) {
    resetForm();
  }

  function closeModal() {
    open = false;
  }

  function handleBackdropClick(e) {
    if (e.target === e.currentTarget) {
      closeModal();
    }
  }

  // Helper function to render markdown to HTML using markdown-it
  function renderMarkdown(text) {
    try {
      return md.render(text || "");
    } catch (error) {
      console.error("Markdown rendering error:", error);
      return '<p class="text-red-600">Error rendering markdown</p>';
    }
  }

  // Check if current language supports preview
  $: supportsPreview = forkLanguage === "markdown" || forkLanguage === "html";

  // Reset preview when language changes to non-previewable type
  $: if (!supportsPreview) {
    showPreview = false;
  }

  // Cleanup on component destroy
  onDestroy(() => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
  });
</script>

{#if open}
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
    on:click={handleBackdropClick}
  >
    <div
      class="bg-white rounded-lg shadow-xl w-full h-[90vh] overflow-hidden flex flex-col transition-all duration-300"
      style="max-width: {isExpanded ? '98vw' : 'min(1200px, 95vw)'};"
      on:click|stopPropagation
    >
      <!-- Header -->
      <div
        class="px-6 py-3 border-b border-gray-200 flex items-center justify-between flex-shrink-0"
      >
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
      <form
        on:submit={handleForkSubmit}
        class="flex-1 flex flex-col overflow-hidden"
      >
        <!-- Compact Settings Bar -->
        <div
          class="px-6 py-3 border-b border-gray-200 bg-gray-50 flex-shrink-0"
        >
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:{isBinary ? 'grid-cols-3' : 'grid-cols-4'} gap-4">
            <div>
              <label
                for="forkName"
                class="block text-xs font-medium text-gray-600 mb-1"
                >Fork Name</label
              >
              <input
                type="text"
                id="forkName"
                bind:value={forkName}
                placeholder="My Fork"
                class="w-full px-2 py-1.5 text-sm maas-input border border-gray-300 rounded"
              />
            </div>

            {#if !isBinary}
              <div>
                <label
                  for="forkLanguage"
                  class="block text-xs font-medium text-gray-600 mb-1">Type</label
                >
                <select
                  id="forkLanguage"
                  bind:value={forkLanguage}
                  class="w-full px-2 py-1.5 text-sm maas-input bg-white"
                >
                  {#each syntaxOptions as option}
                    <option value={option.value}>{option.label}</option>
                  {/each}
                </select>
              </div>
            {/if}

            <div>
              <label
                for="forkAccessLevel"
                class="block text-xs font-medium text-gray-600 mb-1"
                >Visibility</label
              >
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
              <label
                for="forkExpiration"
                class="block text-xs font-medium text-gray-600 mb-1"
                >Expires</label
              >
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
                  <strong class="mr-1">Original:</strong>
                  {relic.name}
                </span>
                {#if relic?.content_type}
                  <span class="mx-2">•</span>
                {/if}
              {/if}
              {#if relic?.content_type}
                <span class="inline-flex items-center">
                  <strong class="mr-1">Type:</strong>
                  {relic.content_type}
                </span>
              {/if}
            </div>
          {/if}
        </div>

        <!-- Content Editor - Takes up most of the space -->
        <div class="flex-1 overflow-hidden flex flex-col">
          {#if isBinary}
            <!-- Binary/Non-editable Content Preview -->
            <div
              class="px-6 pt-6 pb-2 flex items-center justify-between flex-shrink-0"
            >
              <label class="text-sm font-medium text-gray-700">Preview</label>
              <div class="flex items-center gap-2">
                <!-- File size -->
                <div class="text-sm text-gray-500">
                  {binaryBlob ? (binaryBlob.size / 1024).toFixed(2) : 0} KB
                </div>
              </div>
            </div>

            <div class="flex-1 border-t border-gray-200 overflow-hidden bg-gray-50 flex items-center justify-center">
              {#if previewUrl && relic.content_type?.startsWith('image/')}
                <!-- Image Preview -->
                <div class="h-full w-full overflow-auto p-6 flex items-center justify-center">
                  <img src={previewUrl} alt={relic.name} class="max-w-full max-h-full object-contain" />
                </div>
              {:else if previewUrl && relic.content_type === 'application/pdf'}
                <!-- PDF Preview -->
                <div class="h-full w-full overflow-hidden">
                  <embed src={previewUrl} type="application/pdf" class="w-full h-full" />
                </div>
              {:else}
                <!-- Generic binary file -->
                <div class="text-center p-6">
                  <i class="fas fa-file text-gray-400 text-6xl mb-4"></i>
                  <p class="text-gray-600 text-sm mb-2">Binary file cannot be edited</p>
                  <p class="text-xs text-gray-500">{relic.content_type}</p>
                </div>
              {/if}
            </div>

            <div
              class="px-6 pb-6 pt-2 text-xs text-gray-500 text-center flex-shrink-0 bg-amber-50 border-t border-amber-200"
            >
              <i class="fas fa-info-circle text-amber-600 mr-1"></i>
              Binary files cannot be edited. The fork will contain the same content with your custom metadata.
            </div>
          {:else}
            <!-- Text Content Editor -->
            <div
              class="px-6 pt-6 pb-2 flex items-center justify-between flex-shrink-0"
            >
              <label for="forkContent" class="text-sm font-medium text-gray-700"
                >Content Editor</label
              >
              <div class="flex items-center gap-2">
                <!-- Character count -->
                <div class="text-sm text-gray-500">
                  {editorContent.length} characters
                </div>

                <!-- Expand Toggle -->
                <button
                  type="button"
                  on:click={() => (isExpanded = !isExpanded)}
                  class="px-2 py-1 rounded text-xs font-medium transition-colors {isExpanded
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
                  title={isExpanded ? "Normal width" : "Expand modal"}
                >
                  <i class="fas {isExpanded ? 'fa-compress' : 'fa-expand'}"></i>
                </button>

                <!-- Preview/Source Toggle (for Markdown and HTML) -->
                {#if supportsPreview}
                  <div class="flex items-center gap-1">
                    <button
                      type="button"
                      on:click={() => (showPreview = false)}
                      class="px-2 py-1 rounded text-xs font-medium transition-colors {!showPreview
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
                      title="Edit mode"
                    >
                      <i class="fas fa-edit"></i>
                    </button>
                    <button
                      type="button"
                      on:click={() => (showPreview = true)}
                      class="px-2 py-1 rounded text-xs font-medium transition-colors {showPreview
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
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
                <!-- Markdown Preview -->
                <div
                  class="h-full overflow-y-auto p-6 prose prose-sm max-w-none"
                  on:wheel|stopPropagation
                >
                  {@html renderMarkdown(editorContent)}
                </div>
              {:else if showPreview && forkLanguage === "html"}
                <!-- HTML Preview -->
                <div class="h-full overflow-hidden" on:wheel|stopPropagation>
                  <iframe
                    srcdoc={editorContent}
                    class="w-full h-full border-0"
                    sandbox="allow-same-origin allow-scripts allow-forms"
                    title="HTML Preview"
                  ></iframe>
                </div>
              {:else}
                <!-- Editor Mode -->
                <MonacoEditor
                  value={editorContent}
                  language={forkLanguage === "auto" ? "plaintext" : forkLanguage}
                  readOnly={false}
                  height="calc(90vh - 280px)"
                  noWrapper={true}
                  on:change={(event) => handleContentChange(event.detail)}
                />
              {/if}
            </div>
            <div
              class="px-6 pb-6 pt-2 text-xs text-gray-500 text-center flex-shrink-0"
            >
              <i class="fas fa-info-circle text-teal-600 mr-1"></i>
              Edit the content above to customize your fork
            </div>
          {/if}
        </div>

        <!-- Actions -->
        <div
          class="px-6 py-3 border-t border-gray-200 bg-gray-50 flex-shrink-0"
        >
          <div class="flex justify-between items-center">
            <div class="text-xs text-gray-500">
              {#if forkAccessLevel === "public"}
                <i class="fas fa-globe mr-1" style="color: #217db1;"></i>
                Public fork - anyone can view
              {:else}
                <i class="fas fa-lock mr-1" style="color: #76306c;"></i>
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
