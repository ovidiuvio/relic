<script>
  import { onMount, onDestroy } from "svelte";
  import {
    getRelic,
    getRelicRaw,
    addBookmark,
    removeBookmark,
    checkBookmark,
    deleteRelic,
    checkAdminStatus,
    getComments,
    createComment,
    updateComment,
    deleteComment
  } from "../services/api";
  import { processContent } from '../services/processors';
  import { processArchive } from '../services/processors/archiveProcessor';
  import { showToast } from '../stores/toastStore';
  import { downloadRelic, fastForkArchiveFile } from '../services/relicActions';
  import ForkModal from './ForkModal.svelte';
  import PDFViewer from './PDFViewer.svelte';
  import { createEventDispatcher } from 'svelte';
  import { getCurrentLineNumberFragment } from '../utils/lineNumbers';
  import { getFileTypeDefinition } from '../services/typeUtils';

  // Sub-components
  import RelicHeader from './RelicHeader.svelte';
  import RelicStatusBar from './RelicStatusBar.svelte';
  import MarkdownRenderer from './renderers/MarkdownRenderer.svelte';
  import HtmlRenderer from './renderers/HtmlRenderer.svelte';
  import CodeRenderer from './renderers/CodeRenderer.svelte';
  import ImageRenderer from './renderers/ImageRenderer.svelte';
  import CsvRenderer from './renderers/CsvRenderer.svelte';
  import ArchiveRenderer from './renderers/ArchiveRenderer.svelte';
  import ExcalidrawRenderer from './renderers/ExcalidrawRenderer.svelte';
  import RelicIndexRenderer from './renderers/RelicIndexRenderer.svelte';

  const dispatch = createEventDispatcher();

  export let relicId = "";
  export let filePath = null; // Optional: path to file within archive

  let relic = null;
  let processed = null;
  let loading = true;
  let isArchiveFile = false; // True if viewing a file from within an archive
  let archiveContext = null; // Metadata about the archive (for breadcrumbs)
  let showSource = false; // Unified source view toggle
  let isBookmarked = false;
  let checkingBookmark = false;
  let bookmarkLoading = false;
  let showForkModal = false;
  let forkLoading = false;
  let pdfViewerRef = null;
  let pdfState = { currentPage: 1, numPages: 0, scale: 1.5, loading: false };
  let isAdmin = false;
  let deleteLoading = false;
  let comments = [];

  // Update PDF state periodically
  let pdfStateInterval;
  $: if (processed?.type === "pdf" && pdfViewerRef) {
    if (pdfStateInterval) clearInterval(pdfStateInterval);
    pdfStateInterval = setInterval(() => {
      if (pdfViewerRef && pdfViewerRef.getState) {
        pdfState = pdfViewerRef.getState();
      }
    }, 100);
  } else {
    if (pdfStateInterval) {
      clearInterval(pdfStateInterval);
      pdfStateInterval = null;
    }
  }

  // Initialize from localStorage immediately
  let isFullWidth = (() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("relic_viewer_fullwidth");
      return saved === "true";
    }
    return false;
  })();

  let showSyntaxHighlighting = (() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("relic_editor_syntax_highlighting");
      return saved === "false" ? false : true;
    }
    return true;
  })();

  let showLineNumbers = (() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("relic_editor_line_numbers");
      return saved === "false" ? false : true;
    }
    return true;
  })();

  let showComments = (() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("relic_editor_show_comments");
      return saved === "false" ? false : true;
    }
    return true;
  })();

  let fontSize = (() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("relic_editor_font_size");
      return saved ? parseInt(saved, 10) : 13;
    }
    return 13;
  })();

  // Dispatch initial state to parent on mount
  onMount(async () => {
    dispatch("fullwidth-toggle", { isFullWidth });

    // Check admin status
    try {
      const response = await checkAdminStatus();
      isAdmin = response.data.is_admin;
    } catch (error) {
      console.error("[RelicViewer] Failed to check admin status:", error);
      isAdmin = false;
    }
  });

  // Save full-width preference and dispatch to parent
  $: {
    if (typeof window !== "undefined") {
      localStorage.setItem("relic_viewer_fullwidth", isFullWidth.toString());
    }
    dispatch("fullwidth-toggle", { isFullWidth });
  }

  // Save editor preferences
  $: if (typeof window !== "undefined") {
    localStorage.setItem(
      "relic_editor_syntax_highlighting",
      showSyntaxHighlighting.toString(),
    );
  }

  $: if (typeof window !== "undefined") {
    localStorage.setItem(
      "relic_editor_line_numbers",
      showLineNumbers.toString(),
    );
  }

  $: if (typeof window !== "undefined") {
    localStorage.setItem(
      "relic_editor_show_comments",
      showComments.toString(),
    );
  }

  $: if (typeof window !== "undefined") {
    localStorage.setItem("relic_editor_font_size", fontSize.toString());
  }

  async function loadComments(id) {
    try {
      comments = await getComments(id);
    } catch (error) {
      console.error("Failed to load comments:", error);
    }
  }

  async function handleCreateComment(event) {
    const { lineNumber, content, parentId } = event.detail;
    try {
      const newComment = await createComment(relicId, lineNumber, content, parentId);
      comments = [...comments, newComment];
      showToast("Comment added", "success");
    } catch (error) {
      console.error("Error creating comment:", error);
      if (error.response && error.response.data && error.response.data.detail) {
        showToast(error.response.data.detail, "error");
      } else {
        showToast("Failed to add comment", "error");
      }
    }
  }

  async function handleUpdateComment(event) {
    const { commentId, content } = event.detail;
    try {
      const updatedComment = await updateComment(relicId, commentId, content);
      comments = comments.map(c => c.id === commentId ? updatedComment : c);
      showToast("Comment updated", "success");
    } catch (error) {
      console.error("Error updating comment:", error);
      showToast("Failed to update comment", "error");
    }
  }

  async function handleDeleteComment(event) {
    const commentId = event.detail;
    try {
      await deleteComment(relicId, commentId);
      comments = comments.filter(c => c.id !== commentId);
      showToast("Comment deleted", "success");
    } catch (error) {
      showToast("Failed to delete comment", "error");
    }
  }

  async function loadRelic(id) {
    if (!id) return;
    loading = true;
    relic = null;
    processed = null;
    showSource = false;

    console.log("[RelicViewer] Loading relic:", id);
    try {
      console.log("[RelicViewer] Fetching relic metadata...");
      const relicResponse = await getRelic(id);
      console.log("[RelicViewer] Relic metadata received:", relicResponse.data);
      relic = relicResponse.data;

      // Fetch and process raw content
      console.log("[RelicViewer] Fetching raw content...");
      const rawResponse = await getRelicRaw(id);
      const content = await rawResponse.data.arrayBuffer();
      console.log("[RelicViewer] Raw content received, processing...");

      processed = await processContent(
        new Uint8Array(content),
        relic.content_type,
        relic.language_hint,
      );
      console.log("[RelicViewer] Content processed:", processed);

      // Check bookmark status
      await checkBookmarkStatus(id);

      // Load comments
      await loadComments(id);

      console.log("[RelicViewer] Relic loaded successfully");
    } catch (error) {
      console.error("[RelicViewer] Error loading relic:", error);
      showToast("Failed to load relic: " + error.message, "error");
    } finally {
      loading = false;
    }
  }

  async function loadArchiveFile(archiveId, filepath) {
    if (!archiveId || !filepath) return;
    loading = true;
    relic = null;
    processed = null;
    isArchiveFile = false;
    archiveContext = null;

    console.log(
      "[RelicViewer] Loading file from archive:",
      archiveId,
      filepath,
    );
    try {
      // Load the archive relic metadata
      console.log("[RelicViewer] Fetching archive metadata...");
      const archiveResponse = await getRelic(archiveId);
      const archiveRelic = archiveResponse.data;

      // Fetch and process the archive
      console.log("[RelicViewer] Fetching archive content...");
      const rawResponse = await getRelicRaw(archiveId);
      const content = await rawResponse.data.arrayBuffer();

      console.log("[RelicViewer] Processing archive...");
      const archive = await processArchive(
        new Uint8Array(content),
        archiveRelic.content_type,
      );

      console.log(
        "[RelicViewer] Archive processed, extracting file:",
        filepath,
      );

      // Extract the specific file
      const fileContent = await archive.extractFile(filepath);

      // Find the file metadata
      const fileMetadata = archive.files.find((f) => f.path === filepath);
      if (!fileMetadata) {
        throw new Error("File not found in archive");
      }

      console.log("[RelicViewer] File extracted, processing content...");

      // Process the extracted file content
      processed = await processContent(
        fileContent,
        fileMetadata.contentType,
        fileMetadata.languageHint,
      );

      // Create a virtual relic object for the extracted file
      relic = {
        id: archiveId,
        name: fileMetadata.name,
        content_type: fileMetadata.contentType,
        language_hint: fileMetadata.languageHint,
        size_bytes: fileMetadata.size,
        created_at: archiveRelic.created_at,
        access_count: archiveRelic.access_count,
        access_level: archiveRelic.access_level,
        // Mark as archive file
        _isFromArchive: true,
        _extractedContent: fileContent,
      };

      // Store archive context for breadcrumbs
      isArchiveFile = true;
      archiveContext = {
        archiveId: archiveId,
        archiveName: archiveRelic.name,
        filePath: filepath,
        fileName: fileMetadata.name,
      };

      console.log("[RelicViewer] Archive file loaded successfully");
    } catch (error) {
      console.error("[RelicViewer] Error loading archive file:", error);
      showToast("Failed to load file from archive: " + error.message, "error");
    } finally {
      loading = false;
    }
  }

  async function checkBookmarkStatus(id) {
    try {
      checkingBookmark = true;
      const response = await checkBookmark(id);
      isBookmarked = response.data.is_bookmarked;
    } catch (error) {
      console.error("[RelicViewer] Error checking bookmark status:", error);
      isBookmarked = false;
    } finally {
      checkingBookmark = false;
    }
  }

  async function toggleBookmark() {
    if (bookmarkLoading) return;

    try {
      bookmarkLoading = true;
      if (isBookmarked) {
        await removeBookmark(relicId);
        showToast("Bookmark removed", "success");
        isBookmarked = false;
      } else {
        await addBookmark(relicId);
        showToast("Bookmarked!", "success");
        isBookmarked = true;
      }
    } catch (error) {
      console.error("[RelicViewer] Error toggling bookmark:", error);
      if (error.response?.status === 409) {
        showToast("Already bookmarked", "info");
        isBookmarked = true;
      } else if (error.response?.status === 401) {
        showToast("Client key required to bookmark", "error");
      } else {
        showToast("Failed to update bookmark", "error");
      }
    } finally {
      bookmarkLoading = false;
    }
  }

  async function handleFork() {
    if (isArchiveFile && relic._extractedContent) {
      // For archive files, create a new relic directly
      forkLoading = true;
      try {
        await fastForkArchiveFile(
          relic._extractedContent,
          relic.name,
          relic.content_type,
        );
      } catch (error) {
        console.error("[RelicViewer] Error forking archive file:", error);
      } finally {
        forkLoading = false;
      }
    } else {
      // For normal relics, show the fork modal
      showForkModal = true;
    }
  }

  async function handleDelete() {
    if (
      !confirm(
        `Delete relic "${relic.name || relicId}"?\n\nThis action cannot be undone.`,
      )
    ) {
      return;
    }

    deleteLoading = true;
    try {
      await deleteRelic(relicId);
      showToast("Relic deleted successfully", "success");
      // Navigate back to home
      window.history.pushState({}, "", "/");
      window.dispatchEvent(new PopStateEvent("popstate"));
    } catch (error) {
      console.error("[RelicViewer] Error deleting relic:", error);
      const message = error.response?.data?.detail || "Failed to delete relic";
      showToast(message, "error");
    } finally {
      deleteLoading = false;
    }
  }

  function handleRelicUpdate(event) {
    const updatedRelic = event.detail;
    if (updatedRelic) {
      const oldContentType = relic.content_type;
      const oldLanguageHint = relic.language_hint;

      relic = { ...relic, ...updatedRelic };

      // If content_type or language_hint changed, re-process to update syntax highlighting
      const contentTypeChanged = updatedRelic.content_type && updatedRelic.content_type !== oldContentType;
      const languageHintChanged = updatedRelic.language_hint !== oldLanguageHint;

      if (processed && (contentTypeChanged || languageHintChanged)) {
          // Trigger reload to re-process content with new type hint
          loadRelic(relicId);
      }
    }
  }

  $: if (relicId) {
    if (filePath) {
      loadArchiveFile(relicId, filePath);
    } else {
      loadRelic(relicId);
    }
  }

  // Auto-show source view if URL has line numbers and content is text/code
  $: if (relic && processed) {
    const lineFragment = getCurrentLineNumberFragment();
    if (lineFragment) {
      const typeDef = getFileTypeDefinition(relic.content_type);
      if (
        typeDef.category === "text" ||
        typeDef.category === "code" ||
        typeDef.category === "markdown" ||
        typeDef.category === "html"
      ) {
        showSource = true;
      }
    }
  }

  function handleLineClicked(event) {
    // No toast needed for line clicks - the URL update is sufficient
  }

  function handleLineCopied(event) {
    const { lineNumber } = event.detail;
    showToast(`Line ${lineNumber} URL copied to clipboard!`, "success");
  }

  function handleLineRangeSelected(event) {
    // No toast needed for range selection - the URL update is sufficient
  }

  function handleMultiLineSelected(event) {
    // No toast needed for multi-line selection - the URL update is sufficient
  }

  onDestroy(() => {
    if (pdfStateInterval) {
      clearInterval(pdfStateInterval);
    }
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-12">
    <i class="fas fa-spinner fa-spin text-blue-600 text-4xl"></i>
  </div>
{:else if relic}
  <div
    class="{isFullWidth
      ? 'w-full px-0'
      : 'max-w-7xl mx-auto px-4'} py-6 transition-all duration-300"
  >
    <!-- Unified Container -->
    <div
      class="bg-white shadow-sm border border-gray-200 overflow-hidden {isFullWidth
        ? 'rounded-none'
        : 'rounded-lg'}"
    >
      <RelicHeader
        {relic}
        {relicId}
        {isBookmarked}
        {bookmarkLoading}
        {checkingBookmark}
        {forkLoading}
        {isArchiveFile}
        {isAdmin}
        {deleteLoading}
        on:toggle-bookmark={toggleBookmark}
        on:fork={handleFork}
        on:delete={handleDelete}
        on:update={handleRelicUpdate}
      />

      <RelicStatusBar
        {relic}
        {processed}
        {isFullWidth}
        {showSyntaxHighlighting}
        {showLineNumbers}
        {showComments}
        {showSource}
        {pdfState}
        {fontSize}
        on:toggle-fullwidth={() => (isFullWidth = !isFullWidth)}
        on:toggle-syntax={() =>
          (showSyntaxHighlighting = !showSyntaxHighlighting)}
        on:toggle-linenumbers={() => (showLineNumbers = !showLineNumbers)}
        on:toggle-comments={() => (showComments = !showComments)}
        on:toggle-source={(e) => (showSource = e.detail)}
        on:update-font-size={(e) => (fontSize = e.detail)}
        on:pdf-zoom-in={() => pdfViewerRef?.zoomInMethod()}
        on:pdf-zoom-out={() => pdfViewerRef?.zoomOutMethod()}
        on:pdf-reset-zoom={() => pdfViewerRef?.resetZoomMethod()}
      />

      <!-- Optional Description -->
      {#if relic.description}
        <div class="px-6 py-3 bg-blue-50 border-b border-gray-200">
          <p class="text-sm text-gray-700 leading-relaxed">
            {relic.description}
          </p>
        </div>
      {/if}

      <!-- Archive Context Breadcrumb -->
      {#if isArchiveFile && archiveContext}
        <div class="px-6 py-3 bg-purple-50 border-b border-purple-200">
          <div class="flex items-center gap-2 text-sm">
            <i class="fas fa-file-archive text-purple-600"></i>
            <span class="text-gray-600">From archive:</span>
            <a
              href="/{archiveContext.archiveId}"
              class="text-purple-700 hover:text-purple-900 font-medium hover:underline"
            >
              {archiveContext.archiveName || archiveContext.archiveId}
            </a>
            <i class="fas fa-chevron-right text-gray-400 text-xs"></i>
            <span class="text-gray-700 font-mono text-xs"
              >{archiveContext.filePath}</span
            >
          </div>
          <p class="text-xs text-gray-600 mt-1">
            <i class="fas fa-info-circle mr-1"></i>
            This file was extracted from an archive. Actions (fork, download) will
            work on just this file.
          </p>
        </div>
      {/if}

      <!-- Content -->
      {#if processed}
        {#if processed.type === "markdown"}
          <MarkdownRenderer
            {processed}
            {relicId}
            {showSource}
            {showSyntaxHighlighting}
            {showLineNumbers}
            {showComments}
            {fontSize}
            {comments}
            {isAdmin}
            on:line-clicked={handleLineClicked}
            on:line-range-selected={handleLineRangeSelected}
            on:multi-line-selected={handleMultiLineSelected}
            on:line-copied={handleLineCopied}
            on:createComment={handleCreateComment}
            on:deleteComment={handleDeleteComment}
            on:toggle-comments={() => (showComments = !showComments)}
          />
        {:else if processed.type === "html"}
          <HtmlRenderer
            {processed}
            {relicId}
            {showSource}
            {showSyntaxHighlighting}
            {showLineNumbers}
            {showComments}
            {fontSize}
            {comments}
            {isAdmin}
            on:line-clicked={handleLineClicked}
            on:line-range-selected={handleLineRangeSelected}
            on:multi-line-selected={handleMultiLineSelected}
            on:line-copied={handleLineCopied}
            on:createComment={handleCreateComment}
            on:updateComment={handleUpdateComment}
            on:deleteComment={handleDeleteComment}
            on:toggle-comments={() => (showComments = !showComments)}
          />
        {:else if processed.type === "code" || processed.type === "text"}
          <CodeRenderer
            {processed}
            {relicId}
            {showSyntaxHighlighting}
            {showLineNumbers}
            {showComments}
            {fontSize}
            {comments}
            {isAdmin}
            on:line-clicked={handleLineClicked}
            on:line-range-selected={handleLineRangeSelected}
            on:multi-line-selected={handleMultiLineSelected}
            on:line-copied={handleLineCopied}
            on:createComment={handleCreateComment}
            on:updateComment={handleUpdateComment}
            on:deleteComment={handleDeleteComment}
            on:toggle-comments={() => (showComments = !showComments)}
          />
        {:else if processed.type === "image"}
          <ImageRenderer {processed} relicName={relic.name} />
        {:else if processed.type === "pdf"}
          <div class="border-t border-gray-200">
            <PDFViewer
              bind:this={pdfViewerRef}
              pdfDocument={processed.pdfDocument}
              metadata={processed.metadata}
              passwordRequired={processed.passwordRequired}
              {relicId}
            />
          </div>
        {:else if processed.type === "csv"}
          <CsvRenderer {processed} />
        {:else if processed.type === "archive"}
          <ArchiveRenderer
            {processed}
            {relicId}
            {showSyntaxHighlighting}
            {showLineNumbers}
            {fontSize}
          />
        {:else if processed.type === "relicindex"}
          <RelicIndexRenderer {processed} {relicId} />
        {:else if processed.type === "excalidraw"}
          <ExcalidrawRenderer {processed} {relicId} {relic} />
        {:else}
          <div class="border-t border-gray-200 p-6 text-center">
            <i class="fas fa-file text-gray-400 text-6xl mb-4"></i>
            <p class="text-gray-600 mb-4">
              Preview not available for this file type
            </p>
            <button
              on:click={() =>
                downloadRelic(relicId, relic.name, relic.content_type)}
              class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              <i class="fas fa-download mr-2"></i>
              Download File
            </button>
          </div>
        {/if}
      {:else}
        <div class="border-t border-gray-200 p-6 text-center">
          <i class="fas fa-file text-gray-400 text-6xl mb-4"></i>
          <p class="text-gray-600">Loading preview...</p>
        </div>
      {/if}
    </div>
  </div>
{:else}
  <div class="flex items-center justify-center py-12">
    <div class="text-center">
      <i class="fas fa-search text-gray-400 text-6xl mb-4"></i>
      <p class="text-gray-600">Relic not found</p>
    </div>
  </div>
{/if}

<!-- Fork Modal -->
{#if relic}
  <ForkModal bind:open={showForkModal} {relicId} {relic} />
{/if}

<style>
  /* Removed Monaco overrides to allow component styling to take precedence */
</style>
