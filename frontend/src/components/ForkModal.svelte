<script>
  import { onDestroy } from 'svelte';
  import { forkRelic, getRelicRaw } from "../services/api";
  import { showToast } from "../stores/toastStore";
  import {
    getContentType,
    getFileExtension,
    detectLanguageHint,
    isBinaryType
  } from "../services/typeUtils";
  import ForkSettings from './ForkSettings.svelte';
  import ForkEditor from './ForkEditor.svelte';

  export let open = false;
  export let relicId = "";
  export let relic = null;

  let forkName = "";
  let forkContent = "";
  let forkLanguage = "auto";
  let forkAccessLevel = "public";
  let forkExpiration = "never";
  let forkTags = "";
  let isLoading = false;
  let editorContent = "";
  let isExpanded = false;
  let isBinary = false;
  let binaryBlob = null;
  let previewUrl = null;

  async function loadOriginalContent() {
    if (!relicId) return;

    try {
      const response = await getRelicRaw(relicId);
      const content = await response.data.arrayBuffer();

      // Check if this is a binary file
      isBinary = isBinaryType(relic.content_type);

      if (isBinary) {
        // Store the binary blob directly
        binaryBlob = new Blob([content], { type: relic.content_type });

        // Create preview URL for images and PDFs
        if (relic.content_type?.startsWith('image/') || relic.content_type === 'application/pdf') {
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

      // Initialize tags from original relic
      if (relic.tags && Array.isArray(relic.tags)) {
        forkTags = relic.tags.map(t => typeof t === 'string' ? t : t.name).join(', ');
      } else {
        forkTags = "";
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
        forkTags
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
    forkTags = "";
    editorContent = "";
    isExpanded = false;
    isBinary = false;
    binaryBlob = null;
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      previewUrl = null;
    }
  }

  function handleContentChange(event) {
    const newContent = event.detail;
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
        <ForkSettings
          bind:forkName
          bind:forkLanguage
          bind:forkAccessLevel
          bind:forkExpiration
          bind:forkTags
          {isBinary}
          {relic}
        />

        <ForkEditor
          {isBinary}
          {binaryBlob}
          {previewUrl}
          {relic}
          {editorContent}
          {forkLanguage}
          on:change={handleContentChange}
          on:expand={(e) => isExpanded = e.detail}
        />

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
