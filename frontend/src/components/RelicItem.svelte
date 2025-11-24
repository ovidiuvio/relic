<script>
  import { showToast } from '../stores/toastStore'
  import { deleteRelic, getRelicRaw } from '../services/api'

  export let relic = {}
  export let isMine = false
  export let formatTimeAgo = (date) => date

  async function handleDelete() {
    if (!confirm('Are you sure you want to delete this relic?')) return

    try {
      await deleteRelic(relic.id)
      showToast('Relic deleted successfully', 'success')
      // TODO: Refresh list
    } catch (error) {
      showToast('Failed to delete relic', 'error')
    }
  }

  function copyToClipboard() {
    const url = `${window.location.origin}/${relic.id}`
    navigator.clipboard.writeText(url).then(() => {
      showToast('URL copied to clipboard!', 'success')
    })
  }

  async function copyContent() {
    try {
      const response = await getRelicRaw(relic.id)
      const text = await response.data.text()
      navigator.clipboard.writeText(text).then(() => {
        showToast('Content copied to clipboard!', 'success')
      })
    } catch (error) {
      showToast('Failed to copy content', 'error')
    }
  }

  function viewRaw() {
    window.open(`/${relic.id}/raw`, '_blank')
  }

  function handleNavigateToRelic(e) {
    e.preventDefault()
    window.history.pushState({}, '', `/${relic.id}`)
    // Trigger a popstate event to notify App component
    window.dispatchEvent(new PopStateEvent('popstate', {}))
  }
</script>

<div class="p-6 hover:bg-gray-50 transition-colors">
  <div class="flex items-start justify-between">
    <div class="flex-1 min-w-0">
      <div class="flex items-center space-x-2 mb-2">
        <h3 class="text-sm font-medium text-gray-900 truncate">
          <a href="/{relic.id}" on:click={handleNavigateToRelic} class="hover:text-blue-600 transition-colors">
            {relic.name || 'Untitled'}
          </a>
        </h3>
        {#if relic.language_hint}
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
            {relic.language_hint}
          </span>
        {/if}
        {#if isMine}
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
            Mine
          </span>
        {/if}
      </div>
      <p class="text-sm text-gray-500 mb-2 font-mono truncate">
        {relic.description || 'No description'}
      </p>
      <div class="flex items-center space-x-4 text-xs text-gray-500">
        <span class="flex items-center">
          <i class="fas fa-eye mr-1"></i>
          {relic.access_count} views
        </span>
        <span class="flex items-center">
          <i class="fas fa-clock mr-1"></i>
          {formatTimeAgo(relic.created_at)}
        </span>
        <span class="flex items-center">
          <i class="fas fa-code-branch mr-1"></i>
          v{relic.version_number}
        </span>
      </div>
    </div>
    <div class="ml-4 flex-shrink-0 flex space-x-2">
      <button
        on:click={copyToClipboard}
        class="text-gray-400 hover:text-gray-600 transition-colors"
        title="Copy URL"
      >
        <i class="fas fa-share"></i>
      </button>
      <button
        on:click={copyContent}
        class="text-gray-400 hover:text-gray-600 transition-colors"
        title="Copy content"
      >
        <i class="fas fa-copy"></i>
      </button>
      <button
        on:click={viewRaw}
        class="text-gray-400 hover:text-gray-600 transition-colors"
        title="View raw"
      >
        <i class="fas fa-file-code"></i>
      </button>
      {#if isMine}
        <button
          on:click={handleDelete}
          class="text-red-400 hover:text-red-600 transition-colors"
          title="Delete"
        >
          <i class="fas fa-trash"></i>
        </button>
      {/if}
    </div>
  </div>
</div>
