<script>
  import { createEventDispatcher } from 'svelte'

  export let currentUser = null
  const dispatch = createEventDispatcher()
  let activeSection = 'new'

  function navigate(section) {
    activeSection = section
    dispatch('navigate', { section })
  }
</script>

<nav class="bg-white shadow-sm border-b border-gray-200">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between h-16">
      <div class="flex items-center">
        <div class="flex-shrink-0 flex items-center">
          <i class="fas fa-cloud text-blue-600 text-2xl mr-2"></i>
          <span class="text-xl font-bold text-gray-900">Relic</span>
          <span class="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">Pro</span>
        </div>
        <div class="hidden sm:ml-6 sm:flex sm:space-x-8">
          <button
            on:click={() => navigate('new')}
            class="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm transition-colors"
            class:border-blue-500={activeSection === 'new'}
            class:text-gray-900={activeSection === 'new'}
          >
            <i class="fas fa-plus mr-1"></i>New Paste
          </button>
          <button
            on:click={() => navigate('recent')}
            class="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm transition-colors"
            class:border-blue-500={activeSection === 'recent'}
            class:text-gray-900={activeSection === 'recent'}
          >
            <i class="fas fa-clock mr-1"></i>Recent
          </button>
          <button
            on:click={() => navigate('my-pastes')}
            class="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm transition-colors"
            class:border-blue-500={activeSection === 'my-pastes'}
            class:text-gray-900={activeSection === 'my-pastes'}
          >
            <i class="fas fa-user mr-1"></i>My Pastes
          </button>
          <button
            on:click={() => navigate('api')}
            class="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm transition-colors"
            class:border-blue-500={activeSection === 'api'}
            class:text-gray-900={activeSection === 'api'}
          >
            <i class="fas fa-code mr-1"></i>API
          </button>
        </div>
      </div>
      <div class="flex items-center space-x-4">
        {#if currentUser}
          <div class="flex items-center space-x-2">
            <span class="text-sm text-gray-500">User:</span>
            <div class="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
              {currentUser.username.charAt(0).toUpperCase()}
            </div>
            <span class="text-sm font-medium text-gray-700">{currentUser.username}</span>
          </div>
        {/if}
      </div>
    </div>
  </div>
</nav>

<style>
</style>
