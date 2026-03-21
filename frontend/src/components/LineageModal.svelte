<script>
  import { onMount } from 'svelte';
  import { getRelicLineage } from '../services/api/relics';
  import { showToast } from '../stores/toastStore';
  import LineageNode from './LineageNode.svelte';

  export let open = false;
  export let relicId = "";

  let lineageData = null;
  let isLoading = false;
  let loadingAll = false;
  let error = null;
  let truncated = false;
  let totalNodes = 0;

  async function fetchLineage(maxNodes = 200) {
    if (!relicId) return;

    const loadingAll_ = maxNodes === 0;
    if (loadingAll_) loadingAll = true; else isLoading = true;
    error = null;
    try {
      const params = maxNodes > 0 ? { max_nodes: maxNodes } : {};
      const response = await getRelicLineage(relicId, params);
      lineageData = response.data;
      truncated = response.data.truncated || false;
      totalNodes = response.data.total_nodes || 0;
    } catch (err) {
      error = "Failed to load fork lineage.";
      showToast(error, "error");
    } finally {
      isLoading = false;
      loadingAll = false;
    }
  }

  $: if (open && relicId) {
    fetchLineage();
  }

  function closeModal() {
    open = false;
  }

  function handleBackdropClick(e) {
    if (e.target === e.currentTarget) {
      closeModal();
    }
  }

  // Handle escape key
  function handleKeydown(e) {
    if (e.key.toLowerCase() === 'escape' && open) {
      closeModal();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 transition-opacity"
    on:click={handleBackdropClick}
    role="dialog"
    aria-modal="true"
    aria-labelledby="lineage-modal-title"
  >
    <div
      class="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col transform transition-all"
      on:click|stopPropagation
    >
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white rounded-t-xl z-10">
        <h2 id="lineage-modal-title" class="text-xl font-bold text-gray-900 flex items-center gap-3">
          <div class="p-2 bg-teal-50 text-teal-600 rounded-lg">
            <i class="fas fa-network-wired"></i>
          </div>
          Fork Lineage
        </h2>
        <button
          on:click={closeModal}
          class="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-2 rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
          title="Close (Esc)"
          aria-label="Close modal"
        >
          <i class="fas fa-times text-lg" aria-hidden="true"></i>
        </button>
      </div>

      <!-- Content -->
      <div class="p-6 overflow-y-auto flex-1 custom-scrollbar">
        {#if isLoading}
          <div class="flex flex-col items-center justify-center py-12 text-gray-500" role="status" aria-live="polite">
            <i class="fas fa-spinner fa-spin text-3xl mb-4 text-teal-600"></i>
            <p>Tracing lineage...</p>
          </div>
        {:else if error}
          <div class="text-center py-12">
            <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 text-red-500 mb-4">
              <i class="fas fa-exclamation-triangle text-2xl"></i>
            </div>
            <h3 class="text-lg font-medium text-gray-900 mb-2">Error Loading Lineage</h3>
            <p class="text-gray-500">{error}</p>
            <button
              class="mt-4 px-4 py-2 border border-gray-300 rounded-md text-sm font-medium hover:bg-gray-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
              on:click={fetchLineage}
            >
              Retry
            </button>
          </div>
        {:else if lineageData && lineageData.root}
          {#if truncated}
            <div class="mb-4 flex items-center justify-between gap-3 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700">
              <div class="flex items-center gap-2">
                <i class="fas fa-exclamation-triangle text-amber-500 flex-shrink-0"></i>
                Showing first {totalNodes} nodes. This fork tree is very large.
              </div>
              <button
                on:click={() => fetchLineage(0)}
                disabled={loadingAll}
                class="whitespace-nowrap px-3 py-1 rounded-md bg-amber-100 hover:bg-amber-200 border border-amber-300 text-amber-800 text-xs font-semibold transition-colors disabled:opacity-50 flex items-center gap-1.5"
              >
                {#if loadingAll}
                  <i class="fas fa-spinner fa-spin text-[10px]"></i> Loading...
                {:else}
                  <i class="fas fa-expand-alt text-[10px]"></i> Load all
                {/if}
              </button>
            </div>
          {/if}
          <div class="bg-gray-50 rounded-lg p-6 border border-gray-200 shadow-inner">
            <LineageNode
              node={lineageData.root}
              currentRelicId={lineageData.current_relic_id}
              level={0}
            />
          </div>
        {:else}
          <div class="text-center py-12 text-gray-500">
            <p>No lineage information available.</p>
          </div>
        {/if}
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 border-t border-gray-100 bg-gray-50 rounded-b-xl flex justify-end">
        <button
          type="button"
          on:click={closeModal}
          class="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
        >
          Close
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  /* Custom scrollbar for lineage container */
  .custom-scrollbar::-webkit-scrollbar {
    width: 8px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #a8a8a8;
  }
</style>
