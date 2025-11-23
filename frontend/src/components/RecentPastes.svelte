<script>
  import { onMount } from 'svelte'
  import { listPastes } from '../services/api'
  import PasteItem from './PasteItem.svelte'
  import { showToast } from '../stores/toastStore'

  let pastes = []
  let loading = true

  onMount(async () => {
    try {
      const response = await listPastes()
      pastes = response.data.pastes
    } catch (error) {
      showToast('Failed to load recent pastes', 'error')
      console.error('Error loading pastes:', error)
    } finally {
      loading = false
    }
  })

  function formatTimeAgo(dateString) {
    const now = new Date()
    const date = new Date(dateString)
    const diffInSeconds = Math.floor((now - date) / 1000)

    if (diffInSeconds < 60) return 'just now'
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
    return `${Math.floor(diffInSeconds / 86400)}d ago`
  }
</script>

<div class="px-4 sm:px-0">
  <div class="bg-white shadow-sm rounded-lg border border-gray-200">
    <div class="px-6 py-4 border-b border-gray-200">
      <h2 class="text-lg font-semibold text-gray-900 flex items-center">
        <i class="fas fa-clock text-blue-600 mr-2"></i>
        Recent Pastes
      </h2>
    </div>
    {#if loading}
      <div class="p-6 text-center">
        <div class="inline-block">
          <i class="fas fa-spinner fa-spin text-blue-600 text-2xl"></i>
        </div>
      </div>
    {:else if pastes.length === 0}
      <div class="p-6 text-center text-gray-500">
        <i class="fas fa-inbox text-4xl mb-2"></i>
        <p>No pastes yet</p>
      </div>
    {:else}
      <div class="divide-y divide-gray-200">
        {#each pastes as paste (paste.id)}
          <PasteItem {paste} isMine={false} {formatTimeAgo} />
        {/each}
      </div>
    {/if}
  </div>
</div>
