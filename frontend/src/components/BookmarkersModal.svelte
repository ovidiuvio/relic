<script>
  import { getRelicBookmarkers } from '../services/api/bookmarks';
  import { showToast } from '../stores/toastStore';
  import { formatTimeAgo } from '../services/typeUtils';
  import { copyToClipboard } from '../services/relicActions';

  export let open = false;
  export let relicId = "";
  export let relicName = "";

  let bookmarkers = [];
  let total = 0;
  let currentPage = 1;
  const limit = 25;
  let isLoading = false;
  let error = null;

  $: totalPages = Math.max(1, Math.ceil(total / limit));

  async function fetchBookmarkers(page = 1) {
    if (!relicId) return;

    isLoading = true;
    error = null;
    try {
      const data = await getRelicBookmarkers(relicId, { limit, offset: (page - 1) * limit });
      bookmarkers = data.bookmarkers;
      total = data.total;
      currentPage = page;
    } catch (err) {
      error = "Failed to load bookmarkers.";
      showToast(error, "error");
    } finally {
      isLoading = false;
    }
  }

  $: if (open && relicId) {
    fetchBookmarkers(1);
  }

  function closeModal() {
    open = false;
  }

  function handleBackdropClick(e) {
    if (e.target === e.currentTarget) {
      closeModal();
    }
  }

  function handleKeydown(e) {
    if (e.key.toLowerCase() === 'escape' && open) {
      closeModal();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
  <div
    class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4 transition-opacity backdrop-blur-sm"
    on:click={handleBackdropClick}
    role="dialog"
    aria-modal="true"
    aria-labelledby="bookmarkers-modal-title"
  >
    <div
      class="bg-white rounded-2xl shadow-3xl w-full max-w-xl max-h-[80vh] flex flex-col transform transition-all border border-gray-100 overflow-hidden"
      on:click|stopPropagation
    >
      <!-- Header -->
      <div class="px-8 py-5 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white/95 z-20 backdrop-blur-md">
        <div class="flex items-center gap-4">
            <div class="w-12 h-12 bg-amber-50 text-amber-600 rounded-2xl flex items-center justify-center border border-amber-100 shadow-sm">
                <i class="fas fa-bookmark text-lg"></i>
            </div>
            <div class="flex flex-col">
                <h2 id="bookmarkers-modal-title" class="text-lg font-black text-gray-900 tracking-tight leading-tight">Insight Bookmarkers</h2>
                <div class="flex items-center gap-2 mt-0.5">
                    <span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Relic</span>
                    <a href="/{relicId}" target="_blank" class="text-xs font-bold text-blue-600 hover:text-blue-700 hover:underline flex items-center gap-1.5 transition-colors">
                        {relicName || relicId}
                        <i class="fas fa-external-link-alt text-[9px] opacity-40"></i>
                    </a>
                </div>
            </div>
        </div>
        <div class="flex items-center gap-4">
            {#if total > 0}
                <div class="px-3 py-1 bg-amber-50/50 text-amber-600 rounded-full text-[9px] font-black border border-amber-100 uppercase tracking-widest shadow-inner leading-none">
                    {total} saved
                </div>
            {/if}
            <button
              on:click={closeModal}
              class="text-gray-300 hover:text-gray-900 hover:bg-gray-100 p-2.5 rounded-full transition-all focus:outline-none"
              title="Close"
            >
              <i class="fas fa-times text-md"></i>
            </button>
        </div>
      </div>

      <!-- Content Area -->
      <div class="overflow-y-auto flex-1 custom-scrollbar bg-white">
        {#if isLoading}
          <div class="flex flex-col items-center justify-center py-32">
            <div class="w-16 h-16 relative">
                <i class="fas fa-circle-notch fa-spin text-4xl text-amber-500 absolute inset-0"></i>
                <div class="absolute inset-0 flex items-center justify-center">
                    <i class="fas fa-compass text-xs text-amber-300 animate-pulse"></i>
                </div>
            </div>
            <p class="text-xs font-bold text-gray-400 mt-6 uppercase tracking-[0.2em]">Retracing saved views...</p>
          </div>
        {:else if error}
          <div class="p-16 text-center">
            <div class="w-20 h-20 bg-red-50 text-red-500 rounded-3xl flex items-center justify-center mx-auto mb-6 rotate-3 border border-red-100">
                <i class="fas fa-plug-circle-exclamation text-3xl"></i>
            </div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">Sync Interrupted</h3>
            <p class="text-sm text-gray-500 mb-8 max-w-[280px] mx-auto leading-relaxed font-medium">{error}</p>
            <button
                class="px-10 py-3 bg-white text-gray-900 border border-gray-200 rounded-xl font-bold hover:bg-gray-50 transition-all shadow-sm active:scale-95"
                on:click={() => fetchBookmarkers(1)}
            >
                Refresh Data
            </button>
          </div>
        {:else if bookmarkers.length > 0}
          <div class="min-w-full inline-block align-middle">
            <table class="min-w-full maas-table text-sm border-spacing-0">
                <thead class="bg-gray-50/40 border-b border-gray-100 sticky top-0 z-10 backdrop-blur-sm px-8">
                    <tr class="text-gray-400 uppercase text-[9px] font-black tracking-[0.2em] text-left">
                        <th class="px-8 py-4 font-black">User Identity</th>
                        <th class="px-8 py-4 font-black text-right">Temporal Mark</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-50 bg-white">
                    {#each bookmarkers as user}
                        <tr class="hover:bg-gray-50/50 transition-all duration-300 group">
                            <td class="px-8 py-5">
                                <div class="flex items-center gap-4">
                                    <div class="w-10 h-10 rounded-2xl bg-gradient-to-br from-amber-50 to-white text-amber-600 flex items-center justify-center font-black text-sm border border-amber-100 group-hover:border-amber-400 transition-all shadow-sm group-hover:shadow-md">
                                        {user.name ? user.name.substring(0, 1) : '?'}
                                    </div>
                                    <div class="flex flex-col">
                                        <span class="font-black text-gray-900 text-sm group-hover:text-amber-700 transition-colors uppercase tracking-tight leading-snug">{user.name || 'Anonymous'}</span>
                                        <div class="flex items-center gap-2 mt-0.5">
                                            <span class="text-[11px] font-mono text-gray-400 group-hover:text-gray-500 transition-colors">{user.public_id}</span>
                                            <button 
                                                on:click={() => copyToClipboard(user.public_id, 'User ID copied!')}
                                                class="opacity-0 group-hover:opacity-100 text-[10px] text-gray-300 hover:text-blue-500 transition-all active:scale-90"
                                                title="Copy ID"
                                            >
                                                <i class="fas fa-copy"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </td>
                            <td class="px-8 py-5 text-right font-medium text-gray-500 whitespace-nowrap">
                                <span class="px-2.5 py-1 bg-gray-50 rounded-lg border border-gray-100 text-[11px] font-bold text-gray-400 group-hover:text-gray-600 group-hover:bg-white group-hover:border-amber-100 transition-all duration-300">
                                    {formatTimeAgo(user.bookmarked_at)}
                                </span>
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
          </div>
        {:else}
          <div class="text-center py-32 px-8">
            <div class="relative w-24 h-24 mx-auto mb-8">
                <div class="absolute inset-0 bg-gray-100 rounded-full animate-ping opacity-10"></div>
                <div class="relative w-24 h-24 bg-gray-50 rounded-full flex items-center justify-center border border-gray-100 transform -rotate-12">
                    <i class="fas fa-fingerprint text-4xl text-gray-200"></i>
                </div>
            </div>
            <h3 class="text-lg font-black text-gray-900 mb-2 tracking-tight">Isolated Record</h3>
            <p class="text-xs text-gray-400 max-w-[240px] mx-auto leading-relaxed font-bold uppercase tracking-wider">
                This relic has not been flagged by the collective yet.
            </p>
          </div>
        {/if}
      </div>

      <!-- Footer Area -->
      <div class="px-8 py-5 border-t border-gray-100 bg-gray-50/50 flex justify-between items-center z-20 backdrop-blur-sm">
        <div class="flex items-center gap-3">
          {#if totalPages > 1}
            <button
              on:click={() => fetchBookmarkers(currentPage - 1)}
              disabled={currentPage <= 1 || isLoading}
              class="w-7 h-7 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-700 hover:bg-white border border-transparent hover:border-gray-200 transition-all disabled:opacity-30"
            >
              <i class="fas fa-chevron-left text-xs"></i>
            </button>
            <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest leading-none">
              {currentPage} / {totalPages}
            </span>
            <button
              on:click={() => fetchBookmarkers(currentPage + 1)}
              disabled={currentPage >= totalPages || isLoading}
              class="w-7 h-7 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-700 hover:bg-white border border-transparent hover:border-gray-200 transition-all disabled:opacity-30"
            >
              <i class="fas fa-chevron-right text-xs"></i>
            </button>
          {:else}
            <div class="flex -space-x-2">
                {#each bookmarkers.slice(0, 3) as user}
                    <div class="w-6 h-6 rounded-full border-2 border-white bg-amber-50 text-amber-600 flex items-center justify-center font-black text-[8px] shadow-sm">
                        {user.name ? user.name.substring(0, 1) : '?'}
                    </div>
                {/each}
            </div>
            <span class="text-[9px] font-black text-gray-400 uppercase tracking-widest leading-none">Collective Activity</span>
          {/if}
        </div>
        <button
          type="button"
          on:click={closeModal}
          class="px-6 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 transition-colors focus:outline-none"
        >
          Dismiss
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .custom-scrollbar::-webkit-scrollbar {
    width: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: #f1f5f9;
    border-radius: 10px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #e2e8f0;
  }

  .shadow-3xl {
      box-shadow: 0 50px 100px -20px rgba(0, 0, 0, 0.15), 0 30px 60px -30px rgba(0, 0, 0, 0.2);
  }

  :global(.maas-table.border-spacing-0) {
      border-collapse: collapse !important;
  }
</style>
