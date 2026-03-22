<script>
  import { getRelicLineage } from '../services/api/relics';
  import { showToast } from '../stores/toastStore';

  export let open = false;
  export let relicId = "";

  let lineageData = null;
  let isLoading = false;
  let loadingAll = false;
  let error = null;
  let truncated = false;
  let totalNodes = 0;

  // Map of id → node for fast lookup
  let nodeMap = {};

  // Collapsed node ids
  let collapsedIds = new Set();

  // The node id used as the display root (may differ from the real root)
  let viewRootId = null;

  async function fetchLineage(maxNodes = 200) {
    if (!relicId) return;

    const loadingAll_ = maxNodes > 200;
    if (loadingAll_) loadingAll = true; else isLoading = true;
    error = null;
    try {
      const params = { max_nodes: maxNodes };
      const response = await getRelicLineage(relicId, params);
      lineageData = response.data;
      truncated = response.data.truncated || false;
      totalNodes = response.data.total_nodes || 0;
      collapsedIds = new Set();
      nodeMap = buildNodeMap(lineageData.root);
      viewRootId = lineageData.current_relic_id ?? lineageData.root?.id ?? null;
    } catch (err) {
      error = "Failed to load fork lineage.";
      showToast(error, "error");
    } finally {
      isLoading = false;
      loadingAll = false;
    }
  }

  function buildNodeMap(root) {
    const map = {};
    if (!root) return map;
    const stack = [root];
    while (stack.length) {
      const node = stack.pop();
      map[node.id] = node;
      for (const child of node.children ?? []) stack.push(child);
    }
    return map;
  }

  // DFS walk from a given root node, respecting collapsedIds.
  // Returns flat array of { node, depth }.
  function flattenTree(rootNode, collapsed) {
    if (!rootNode) return [];
    const result = [];
    const stack = [{ node: rootNode, depth: 0 }];
    while (stack.length) {
      const { node, depth } = stack.pop();
      result.push({ node, depth });
      if (!collapsed.has(node.id) && node.children?.length) {
        // Push in reverse so left-most child is processed first
        for (let i = node.children.length - 1; i >= 0; i--) {
          stack.push({ node: node.children[i], depth: depth + 1 });
        }
      }
    }
    return result;
  }

  $: viewRootNode = nodeMap[viewRootId] ?? lineageData?.root ?? null;
  $: flatNodes = flattenTree(viewRootNode, collapsedIds);
  $: realRootId = lineageData?.root?.id ?? null;
  $: isRebased = viewRootId && viewRootId !== realRootId;

  function toggleCollapse(id) {
    const next = new Set(collapsedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    collapsedIds = next;
  }

  function rebase(id) {
    viewRootId = id;
    collapsedIds = new Set();
  }

  function resetRebase() {
    viewRootId = realRootId;
    collapsedIds = new Set();
  }

  $: if (open && relicId) {
    fetchLineage();
  }

  function closeModal() {
    open = false;
  }

  function handleBackdropClick(e) {
    if (e.target === e.currentTarget) closeModal();
  }

  function handleKeydown(e) {
    if (e.key.toLowerCase() === 'escape' && open) closeModal();
  }

  function fmtDate(dt) {
    return dt ? new Date(dt).toLocaleDateString() : '';
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
            <div class="mb-3 flex items-center justify-between gap-3 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700">
              <div class="flex items-center gap-2">
                <i class="fas fa-exclamation-triangle text-amber-500 flex-shrink-0"></i>
                Showing first {totalNodes} nodes. This fork tree is very large.
              </div>
              <button
                on:click={() => fetchLineage(5000)}
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

          {#if isRebased}
            <div class="mb-3 flex items-center gap-2 px-3 py-2 bg-teal-50 border border-teal-200 rounded-lg text-sm text-teal-700">
              <i class="fas fa-crosshairs text-teal-500 flex-shrink-0"></i>
              <span class="flex-1">Viewing subtree rooted at <span class="font-mono font-semibold">{viewRootId.substring(0, 8)}</span></span>
              <button
                on:click={resetRebase}
                class="whitespace-nowrap px-2.5 py-1 rounded-md bg-teal-100 hover:bg-teal-200 border border-teal-300 text-teal-800 text-xs font-semibold transition-colors flex items-center gap-1.5"
              >
                <i class="fas fa-arrow-up text-[10px]"></i> Back to root
              </button>
            </div>
          {/if}

          <div class="bg-gray-50 rounded-lg border border-gray-200 shadow-inner overflow-hidden">
            {#each flatNodes as { node, depth }, i (node.id)}
              {@const isCurrent = node.id === lineageData.current_relic_id}
              {@const hasChildren = node.children?.length > 0}
              {@const isCollapsed = collapsedIds.has(node.id)}
              <div
                class="flex items-center gap-2 px-3 py-2 border-b border-gray-100 last:border-b-0 transition-colors {isCurrent ? 'bg-teal-50' : 'hover:bg-white'}"
                style="padding-left: calc(0.75rem + {depth * 1.25}rem)"
              >
                <!-- Collapse toggle -->
                <button
                  on:click={() => toggleCollapse(node.id)}
                  class="w-5 h-5 flex-shrink-0 flex items-center justify-center rounded text-gray-400 hover:text-gray-700 hover:bg-gray-200 transition-colors {hasChildren ? '' : 'invisible'}"
                  title={isCollapsed ? 'Expand' : 'Collapse'}
                >
                  <i class="fas fa-chevron-{isCollapsed ? 'right' : 'down'} text-[10px]"></i>
                </button>

                <!-- Branch icon -->
                <i class="fas fa-code-branch {isCurrent ? 'text-teal-500' : 'text-gray-300'} text-xs flex-shrink-0 {depth > 0 ? '' : 'rotate-90'}"></i>

                <!-- Name + meta -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <a
                      href="/{node.id}"
                      class="text-sm font-medium truncate {isCurrent ? 'text-teal-700 pointer-events-none' : 'text-gray-800 hover:text-teal-600 hover:underline'}"
                    >
                      {node.name || 'Untitled'}
                    </a>
                    {#if isCurrent}
                      <span class="flex-shrink-0 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-teal-100 text-teal-700">Current</span>
                    {/if}
                    {#if hasChildren && isCollapsed}
                      <span class="flex-shrink-0 text-[10px] text-gray-400">{node.children.length} fork{node.children.length !== 1 ? 's' : ''} hidden</span>
                    {/if}
                  </div>
                  <div class="flex items-center text-[11px] text-gray-400 gap-1.5 mt-0.5">
                    <span class="font-mono">{node.id.substring(0, 8)}</span>
                    <span>&bull;</span>
                    <span>{fmtDate(node.created_at)}</span>
                  </div>
                </div>

                <!-- Rebase button -->
                {#if !isCurrent || isRebased}
                  <button
                    on:click={() => rebase(node.id)}
                    class="flex-shrink-0 w-7 h-7 flex items-center justify-center rounded-md text-gray-300 hover:text-teal-600 hover:bg-teal-50 border border-transparent hover:border-teal-200 transition-colors {viewRootId === node.id ? 'text-teal-600 bg-teal-50 border-teal-200' : ''}"
                    title="View tree from this node"
                  >
                    <i class="fas fa-crosshairs text-xs"></i>
                  </button>
                {/if}
              </div>
            {/each}
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
