<script>
  import { onMount } from 'svelte'
  import { showToast } from '../stores/toastStore'
  import { getClientRelics, deleteRelic } from '../services/api'
  import { shareRelic, copyRelicContent, downloadRelic, viewRaw } from '../services/relicActions'

  let relics = []
  let loading = true
  let searchTerm = ''

  function formatTimeAgo(dateString) {
    const now = new Date()
    const date = new Date(dateString)
    const diffInSeconds = Math.floor((now - date) / 1000)

    if (diffInSeconds < 60) return 'just now'
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
    return `${Math.floor(diffInSeconds / 86400)}d ago`
  }

  async function loadMyRelics() {
    try {
      loading = true
      const response = await getClientRelics()
      relics = response.data.relics || []
    } catch (error) {
      console.error('Failed to load client relics:', error)
      showToast('Failed to load your relics', 'error')
      relics = []
    } finally {
      loading = false
    }
  }

  async function handleDeleteRelic(relicId, relicName) {
    if (!confirm(`Are you sure you want to delete "${relicName || 'Untitled'}"? This action cannot be undone.`)) {
      return
    }

    try {
      await deleteRelic(relicId)
      showToast('Relic deleted successfully', 'success')
      // Reload the relics list
      await loadMyRelics()
    } catch (error) {
      console.error('Failed to delete relic:', error)
      showToast('Failed to delete relic', 'error')
    }
  }

  
  onMount(() => {
    loadMyRelics()
  })
</script>

<div class="px-4 sm:px-0">
  <div class="bg-white shadow-sm rounded-lg border border-gray-200">
    <div class="px-6 py-4 border-b border-gray-200">
      <h2 class="text-lg font-semibold text-gray-900 flex items-center justify-between">
        <span class="flex items-center">
          <i class="fas fa-user text-blue-600 mr-2"></i>
          My Relics
        </span>
        <div class="flex items-center space-x-2">
          <span class="text-sm text-gray-500">Total: </span>
          <span class="text-sm font-medium text-gray-900">{relics.length}</span>
        </div>
      </h2>
    </div>

    <!-- Search Bar -->
    <div class="px-6 py-4 border-b border-gray-200">
      <div class="relative">
        <i class="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 text-sm"></i>
        <input
          type="text"
          bind:value={searchTerm}
          placeholder="Filter by name, type, or id..."
          class="w-full pl-9 pr-3 py-1.5 text-sm maas-input"
        />
      </div>
    </div>

    {#if loading}
      <div class="p-8 text-center">
        <div class="inline-block">
          <i class="fas fa-spinner fa-spin text-[#772953] text-2xl"></i>
        </div>
        <p class="text-sm text-gray-500 mt-2">Loading your relics...</p>
      </div>
    {:else if relics.length === 0}
      <div class="p-8 text-center text-gray-500">
        <i class="fas fa-inbox text-4xl mb-2"></i>
        <p>No relics yet</p>
        <p class="text-sm mt-2">Create your first relic to get started!</p>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full maas-table text-sm">
          <thead>
            <tr class="text-gray-500 uppercase text-xs tracking-wider bg-gray-50">
              <th class="w-8"><input type="checkbox" class="rounded border-gray-300"></th>
              <th>Title / ID</th>
              <th>Type</th>
              <th>Created</th>
              <th>Size</th>
              <th class="w-40">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each relics as relic (relic.id)}
              <tr class="hover:bg-gray-50 cursor-pointer">
                <td class="text-center">
                  <input type="checkbox" class="rounded border-gray-300" />
                </td>
                <td>
                  <a href="/{relic.id}" class="font-medium text-[#0066cc] hover:underline block">
                    {relic.name || 'Untitled'}
                  </a>
                  <span class="text-xs text-gray-400 font-mono">{relic.id}</span>
                </td>
                <td>
                  <span class="text-sm">{relic.content_type || 'Text'}</span>
                </td>
                <td class="text-gray-500 text-xs">
                  {formatTimeAgo(relic.created_at)}
                </td>
                <td class="font-mono text-xs">
                  {relic.size_bytes ? Math.round(relic.size_bytes / 1024) + ' KB' : '0 KB'}
                </td>
                <td>
                  <div class="flex items-center gap-1">
                    <button
                      on:click|stopPropagation={() => shareRelic(relic.id)}
                      class="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                      title="Share relic"
                    >
                      <i class="fas fa-share text-xs"></i>
                    </button>
                    <button
                      on:click|stopPropagation={() => copyRelicContent(relic.id)}
                      class="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors"
                      title="Copy content to clipboard"
                    >
                      <i class="fas fa-copy text-xs"></i>
                    </button>
                    <button
                      on:click|stopPropagation={() => viewRaw(relic.id)}
                      class="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
                      title="View raw content"
                    >
                      <i class="fas fa-code text-xs"></i>
                    </button>
                    <button
                      on:click|stopPropagation={() => downloadRelic(relic.id, relic.name, relic.content_type)}
                      class="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                      title="Download relic"
                    >
                      <i class="fas fa-download text-xs"></i>
                    </button>
                    <button
                      on:click|stopPropagation={() => handleDeleteRelic(relic.id, relic.name)}
                      class="p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                      title="Delete relic"
                    >
                      <i class="fas fa-trash text-xs"></i>
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>
