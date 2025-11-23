<script>
  import { showToast } from '../stores/toastStore'

  export let currentUser = null

  let myPastes = []

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
      <h2 class="text-lg font-semibold text-gray-900 flex items-center justify-between">
        <span class="flex items-center">
          <i class="fas fa-user text-blue-600 mr-2"></i>
          My Pastes
        </span>
        <div class="flex items-center space-x-2">
          <span class="text-sm text-gray-500">Total: </span>
          <span class="text-sm font-medium text-gray-900">{myPastes.length}</span>
        </div>
      </h2>
    </div>
    {#if myPastes.length === 0}
      <div class="p-6 text-center text-gray-500">
        {#if !currentUser}
          <p>Sign in to see your pastes</p>
        {:else}
          <i class="fas fa-inbox text-4xl mb-2"></i>
          <p>No pastes yet</p>
        {/if}
      </div>
    {:else}
      <div class="divide-y divide-gray-200">
        <!-- TODO: Render my pastes -->
      </div>
    {/if}
  </div>
</div>
