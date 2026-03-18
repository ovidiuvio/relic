<script>
  export let node;
  export let currentRelicId;
  export let level = 0;

  // Format date nicely
  $: formattedDate = node.created_at ? new Date(node.created_at).toLocaleDateString() : '';
</script>

<div class="lineage-node">
  <div
    class="flex items-center py-2 px-3 rounded-md mb-1 border-l-4 transition-colors {node.id === currentRelicId ? 'bg-teal-50 border-teal-500 shadow-sm' : 'border-transparent hover:bg-gray-50'}"
    style="margin-left: {level * 1.5}rem;"
  >
    <!-- Connecting line indicator -->
    {#if level > 0}
      <div class="absolute w-4 border-t-2 border-gray-300" style="left: -1rem; top: 50%;"></div>
    {/if}

    <div class="flex-shrink-0 text-gray-400 mr-2">
      {#if level === 0}
        <i class="fas fa-code-branch rotate-90" title="Root Relic"></i>
      {:else}
        <i class="fas fa-code-branch" title="Fork"></i>
      {/if}
    </div>

    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2">
        <a
          href="/{node.id}"
          class="text-sm font-medium truncate {node.id === currentRelicId ? 'text-teal-700 pointer-events-none' : 'text-gray-900 hover:text-teal-600 hover:underline'}"
        >
          {node.name || 'Untitled'}
        </a>
        {#if node.id === currentRelicId}
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-teal-100 text-teal-800">
            Current
          </span>
        {/if}
      </div>
      <div class="flex items-center text-xs text-gray-500 mt-0.5 gap-2">
        <span class="font-mono">{node.id.substring(0, 8)}</span>
        <span>&bull;</span>
        <span>{formattedDate}</span>
      </div>
    </div>
  </div>

  {#if node.children && node.children.length > 0}
    <div class="children-container relative border-l border-gray-200 ml-4 mt-1">
      {#each node.children as child}
        <svelte:self node={child} currentRelicId={currentRelicId} level={level + 1} />
      {/each}
    </div>
  {/if}
</div>

<style>
  .children-container::before {
    content: '';
    position: absolute;
    top: 0;
    bottom: 0;
    left: -1px;
    width: 2px;
    background: linear-gradient(to bottom, transparent, transparent);
  }
</style>
