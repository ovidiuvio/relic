<script>
  import { showToast } from '../stores/toastStore'
  import { deletePaste } from '../services/api'

  export let paste = {}
  export let isMine = false
  export let formatTimeAgo = (date) => date

  async function handleDelete() {
    if (!confirm('Are you sure you want to delete this paste?')) return

    try {
      await deletePaste(paste.id)
      showToast('Paste deleted successfully', 'success')
      // TODO: Refresh list
    } catch (error) {
      showToast('Failed to delete paste', 'error')
    }
  }

  function copyToClipboard() {
    const url = `${window.location.origin}/${paste.id}`
    navigator.clipboard.writeText(url).then(() => {
      showToast('URL copied to clipboard!', 'success')
    })
  }

  function handleEdit() {
    showToast('Edit functionality would be implemented here', 'info')
  }
</script>

<div class="p-6 hover:bg-gray-50 transition-colors">
  <div class="flex items-start justify-between">
    <div class="flex-1 min-w-0">
      <div class="flex items-center space-x-2 mb-2">
        <h3 class="text-sm font-medium text-gray-900 truncate">
          <a href="/{paste.id}" class="hover:text-blue-600 transition-colors">
            {paste.name || 'Untitled'}
          </a>
        </h3>
        {#if paste.language_hint}
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
            {paste.language_hint}
          </span>
        {/if}
        {#if isMine}
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
            Mine
          </span>
        {/if}
      </div>
      <p class="text-sm text-gray-500 mb-2 font-mono truncate">
        {paste.description || 'No description'}
      </p>
      <div class="flex items-center space-x-4 text-xs text-gray-500">
        <span class="flex items-center">
          <i class="fas fa-eye mr-1"></i>
          {paste.access_count} views
        </span>
        <span class="flex items-center">
          <i class="fas fa-clock mr-1"></i>
          {formatTimeAgo(paste.created_at)}
        </span>
        <span class="flex items-center">
          <i class="fas fa-code-branch mr-1"></i>
          v{paste.version_number}
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
      {#if isMine}
        <button
          on:click={handleEdit}
          class="text-gray-400 hover:text-gray-600 transition-colors"
          title="Edit"
        >
          <i class="fas fa-edit"></i>
        </button>
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
