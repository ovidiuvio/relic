<script>
  import {
    getTypeLabel,
    getTypeIcon,
    getTypeIconColor,
    formatBytes,
  } from "../services/typeUtils";
  import {
    shareRelic,
    copyRelicContent,
    downloadRelic,
    viewRaw,
    downloadArchiveFile,
    copyArchiveFileContent,
    viewArchiveFileRaw,
    copyToClipboard,
  } from "../services/relicActions";
  import ReportModal from "./ReportModal.svelte";
  import EditRelicModal from "./EditRelicModal.svelte";
  import { createEventDispatcher } from "svelte";

  export let relic;
  export let relicId;
  export let isBookmarked;
  export let bookmarkLoading;
  export let checkingBookmark;
  export let forkLoading;
  export let isAdmin = false;
  export let deleteLoading = false;
  // Archive file props
  export let isArchiveFile = false;

  const dispatch = createEventDispatcher();

  let showReportModal = false;
  let showEditModal = false;

  function handleUpdate(event) {
    const updatedRelic = event.detail;
    // Notify parent to update relic data
    dispatch('update', updatedRelic);
  }

  function copyRelicId() {
    copyToClipboard(relicId, 'Relic ID copied to clipboard!');
  }

  function handleShare() {
    shareRelic(relicId);
  }

  function handleCopyContent() {
    if (isArchiveFile && relic._extractedContent) {
      copyArchiveFileContent(relic._extractedContent);
    } else {
      copyRelicContent(relicId);
    }
  }

  function handleDownload() {
    if (isArchiveFile && relic._extractedContent) {
      downloadArchiveFile(
        relic._extractedContent,
        relic.name,
        relic.content_type,
      );
    } else {
      downloadRelic(relicId, relic.name, relic.content_type);
    }
  }

  function handleViewRaw() {
    if (isArchiveFile && relic._extractedContent) {
      viewArchiveFileRaw(
        relic._extractedContent,
        relic.name,
        relic.content_type,
      );
    } else {
      viewRaw(relicId);
    }
  }
</script>

<div
  class="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-start"
>
  <div class="flex-1 min-w-0">
    <!-- Title Row -->
    <div class="flex items-center gap-3 mb-1.5">
      <i
        class="fas {getTypeIcon(relic.content_type)} {getTypeIconColor(
          relic.content_type,
        )} text-lg flex-shrink-0"
      ></i>
      <h2 class="text-lg font-bold text-gray-800 truncate">
        {relic.name || "Untitled"}
      </h2>
      <span
        class="px-2 py-1 bg-gray-200 text-gray-700 rounded text-xs font-bold uppercase flex-shrink-0"
        >{getTypeLabel(relic.content_type)}</span
      >
    </div>

    <!-- ID and Date Row -->
    <div class="text-xs text-gray-500 flex items-center gap-3 font-mono">
      <button
        on:click={copyRelicId}
        class="hover:text-gray-700 transition-colors flex items-center gap-1.5"
        title="Copy ID"
      >
        <span>{relicId}</span>
        <i class="fas fa-copy text-[10px]"></i>
      </button>
      <span>&bull;</span>
      <span>{new Date(relic.created_at).toLocaleDateString()}</span>
      <span>&bull;</span>
      <span class="flex items-center gap-1">
        <i class="fas fa-weight text-gray-400"></i>
        {formatBytes(relic.size_bytes)}
      </span>
      <span>&bull;</span>
      <span class="flex items-center gap-1">
        <i class="fas fa-eye text-gray-400"></i>
        {relic.access_count}
      </span>
    </div>
  </div>

  <!-- Action Toolbar -->
  <div class="flex items-center gap-2 flex-shrink-0 ml-4">
    {#if !isArchiveFile}
      <button
        on:click={() => dispatch("toggle-bookmark")}
        disabled={checkingBookmark || bookmarkLoading}
        class="p-2 rounded transition-colors {isBookmarked
          ? 'text-amber-600 hover:text-amber-700 hover:bg-amber-50'
          : 'text-gray-400 hover:text-amber-600 hover:bg-amber-50'}"
        title={isBookmarked ? "Remove bookmark" : "Bookmark this relic"}
      >
        {#if bookmarkLoading}
          <i class="fas fa-spinner fa-spin text-sm"></i>
        {:else if isBookmarked}
          <i class="fas fa-bookmark text-sm"></i>
        {:else}
          <i class="far fa-bookmark text-sm"></i>
        {/if}
      </button>
    {/if}
    <button
      on:click={() => (showReportModal = true)}
      class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
      title="Report relic"
    >
      <i class="fas fa-flag text-sm"></i>
    </button>
    <button
      on:click={handleShare}
      class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
      title="Share relic"
    >
      <i class="fas fa-share text-sm"></i>
    </button>
    <button
      on:click={handleCopyContent}
      class="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
      title="Copy content to clipboard"
    >
      <i class="fas fa-copy text-sm"></i>
    </button>
    <button
      on:click={handleViewRaw}
      class="p-2 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors"
      title="View raw content"
    >
      <i class="fas fa-code text-sm"></i>
    </button>
    <button
      on:click={() => dispatch("fork")}
      disabled={forkLoading}
      class="p-2 text-gray-400 hover:text-teal-600 hover:bg-teal-50 rounded transition-colors"
      title="Create fork"
    >
      {#if forkLoading}
        <i class="fas fa-spinner fa-spin text-sm"></i>
      {:else}
        <i class="fas fa-code-branch text-sm"></i>
      {/if}
    </button>
    <button
      on:click={handleDownload}
      class="p-2 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
      title="Download relic"
    >
      <i class="fas fa-download text-sm"></i>
    </button>
    {#if relic.can_edit && !isArchiveFile}
      <button
        on:click={() => (showEditModal = true)}
        class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
        title="Edit relic"
      >
        <i class="fas fa-edit text-sm"></i>
      </button>
    {/if}
    {#if isAdmin && !isArchiveFile}
      <div class="w-px h-6 bg-gray-300 mx-1"></div>
      <button
        on:click={() => dispatch("delete")}
        disabled={deleteLoading}
        class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
        title="Delete relic (Admin)"
      >
        {#if deleteLoading}
          <i class="fas fa-spinner fa-spin text-sm"></i>
        {:else}
          <i class="fas fa-trash text-sm"></i>
        {/if}
      </button>
    {/if}
  </div>
</div>

<ReportModal bind:open={showReportModal} {relicId} relicName={relic.name} />
<EditRelicModal
  bind:show={showEditModal}
  {relic}
  on:close={() => (showEditModal = false)}
  on:update={handleUpdate}
/>
