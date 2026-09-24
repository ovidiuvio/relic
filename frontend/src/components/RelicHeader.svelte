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
  import AddToSpaceModal from "./AddToSpaceModal.svelte";
  import IconButton from "./IconButton.svelte";
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
  let showAddToSpaceModal = false;

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

  // Counter coloring logic (shared with RelicTable)
  function counterLevel(value, isViews = false) {
    if (!value || value <= 0) return null
    if (isViews) {
      if (value >= 100) return 'high'
      if (value >= 50)  return 'medium'
      if (value >= 10)  return 'low'
      return null
    }
    if (value >= 10) return 'high'
    if (value >= 5)  return 'medium'
    if (value >= 2)  return 'low'
    return null
  }

  const LEVEL_CLASS = { high: 'text-red-500/70', medium: 'text-orange-400/80', low: 'text-blue-500/70' }

  function counterClass(value, isViews = false) {
    const level = counterLevel(value, isViews)
    return level ? LEVEL_CLASS[level] : 'text-gray-400/70'
  }
</script>

<div
  class="px-5 py-3 border-b border-gray-200 bg-gray-50 flex flex-col gap-1.5"
>
  <div class="flex justify-between items-start gap-6">
    <div class="flex-1 min-w-0 flex flex-col gap-1.5">
      <!-- Title Area: Focus on Name + Type -->
      <div class="flex items-center gap-2">
        <i
          class="fas {getTypeIcon(relic.content_type)} {getTypeIconColor(
            relic.content_type,
          )} text-[15px] flex-shrink-0"
        ></i>
        <h1 class="text-[15px] font-bold text-gray-800 truncate max-w-[500px] leading-tight" title={relic.name || "Untitled"}>
          {relic.name || "Untitled"}
        </h1>
        <span class="ml-1.5 px-1.5 py-0.5 bg-gray-200/60 text-gray-500 rounded text-2xs font-bold uppercase tracking-wider leading-none">
          {getTypeLabel(relic.content_type)}
        </span>
      </div>

      <!-- Second Line: ID (Now only ID) -->
      <div class="flex items-center">
        <div class="text-[11px] text-gray-400 font-mono flex items-center gap-1.5 group cursor-default">
          <button on:click={copyRelicId} class="hover:text-link transition-colors" aria-label="Copy relic ID {relicId}">
            {relicId}
          </button>
          <i class="fas fa-copy text-[10px] opacity-0 group-hover:opacity-70 group-focus-within:opacity-70 transition-opacity" aria-hidden="true"></i>
        </div>
      </div>
    </div>

    <!-- Action Toolbar -->
    <div class="flex items-center gap-0.5 flex-shrink-0 -mt-1" role="group" aria-label="Relic actions">
      {#if !isArchiveFile}
        <IconButton
          label={isBookmarked ? "Remove bookmark" : "Bookmark"}
          icon="{isBookmarked ? 'fas' : 'far'} fa-bookmark"
          pressed={isBookmarked}
          loading={bookmarkLoading}
          disabled={checkingBookmark}
          align="end"
          on:click={() => dispatch("toggle-bookmark")}
        />
      {/if}
      <IconButton label="Report" icon="fas fa-flag" align="end" on:click={() => (showReportModal = true)} />
      <IconButton label="Share link" icon="fas fa-share" align="end" on:click={handleShare} />
      {#if !isArchiveFile}
        <IconButton label="Add to space" icon="fas fa-layer-group" align="end" on:click={() => (showAddToSpaceModal = true)} />
      {/if}
      <div class="w-px h-4 bg-gray-300 mx-1" aria-hidden="true"></div>
      <IconButton label="Copy content" icon="fas fa-copy" align="end" on:click={handleCopyContent} />
      <IconButton label="View raw" icon="fas fa-code" align="end" on:click={handleViewRaw} />
      <IconButton label="Fork" icon="fas fa-code-branch" loading={forkLoading} align="end" on:click={() => dispatch("fork")} />
      <IconButton label="Download" icon="fas fa-download" align="end" on:click={handleDownload} />
      {#if relic.can_edit && !isArchiveFile}
        <IconButton label="Edit details" icon="fas fa-edit" align="end" on:click={() => (showEditModal = true)} />
      {/if}
      {#if isAdmin && !isArchiveFile}
        <div class="w-px h-4 bg-gray-300 mx-1" aria-hidden="true"></div>
        <IconButton label="Delete relic (admin)" icon="fas fa-trash" tone="danger" loading={deleteLoading} align="end" on:click={() => dispatch("delete")} />
      {/if}
    </div>
  </div>

  <!-- Third Line: Metadata & Tags -->
  <div class="flex items-center justify-between flex-wrap gap-x-4 gap-y-1.5 text-[11px] text-gray-400">
      <div class="flex items-center gap-3">
        <span class="flex items-center gap-1.5 opacity-60">
          <i class="far fa-calendar text-[10px]"></i>
          {new Date(relic.created_at).toLocaleDateString()}
        </span>
        <span class="flex items-center gap-1.5 opacity-60">
          <i class="fas fa-database text-[10px]"></i>
          {formatBytes(relic.size_bytes)}
        </span>
        {#if relic.access_count > 0}
          <span class="flex items-center gap-1.5 {counterClass(relic.access_count, true)}" title="Views">
            <i class="far fa-eye text-[10px]"></i>
            {relic.access_count}
          </span>
        {/if}
        {#if relic.bookmark_count > 0}
          <span class="flex items-center gap-1.5 {counterClass(relic.bookmark_count)}" title="Bookmarks">
            <i class="far fa-bookmark text-[10px]"></i>
            {relic.bookmark_count}
          </span>
        {/if}
        {#if relic.comments_count > 0}
          <span class="flex items-center gap-1.5 {counterClass(relic.comments_count)}" title="Comments">
            <i class="far fa-comment-alt text-[10px]"></i>
            {relic.comments_count}
          </span>
        {/if}
        {#if relic.forks_count > 0}
          <span class="flex items-center gap-1.5 {counterClass(relic.forks_count)}" title="Forks">
            <i class="fas fa-code-branch text-[10px]"></i>
            {relic.forks_count}
          </span>
        {/if}
      </div>

      <!-- Tags Mini-list (Now after counters) -->
      {#if relic.tags && relic.tags.length > 0}
        <div class="flex items-center gap-2 ml-auto">
          {#each relic.tags as tag}
              <div class="flex items-center group/tag">
                <button
                  on:click={() => dispatch('tag-click', tag.name || tag)}
                  class="hover:text-blue-600 transition-colors flex items-center gap-1"
                >
                  <span class="opacity-50">#</span>{tag.name || tag}
                </button>
                {#if relic.can_edit}
                  <button
                    on:click|stopPropagation={() => dispatch('remove-tag', tag.name || tag)}
                    class="ml-1 opacity-0 group-hover/tag:opacity-100 focus-visible:opacity-100 hover:text-red-500 transition-all text-[9px]"
                    title="Remove tag"
                    aria-label="Remove tag {tag.name || tag}"
                  >
                    <i class="fas fa-times" aria-hidden="true"></i>
                  </button>
                {/if}
              </div>
            {/each}
        </div>
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
<AddToSpaceModal
  bind:open={showAddToSpaceModal}
  {relicId}
  relicName={relic.name}
/>
