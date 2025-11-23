<script>
  import { createEventDispatcher } from 'svelte'

  export let currentSection = 'new'
  export let currentUser = null
  export let pasteCount = 0
  const dispatch = createEventDispatcher()

  function navigate(section) {
    dispatch('navigate', { section })
  }

  function isActive(section) {
    return currentSection === section
  }
</script>

<aside class="w-64 bg-[#F2F2F2] border-r border-[#dfdcd9] flex flex-col shadow-[inset_-1px_0_0_rgba(0,0,0,0.05)] overflow-y-auto shrink-0">
  <div class="p-4 text-xs font-bold text-[#AEA79F] uppercase tracking-wider mb-1">Pastebin Controller</div>

  <nav class="flex flex-col">
    <button
      on:click={() => navigate('new')}
      class="maas-nav-item {isActive('new') ? 'active' : ''} px-6 py-3 text-sm flex items-center gap-3 text-left w-full"
    >
      <i class="fa-solid fa-plus w-4 text-center text-gray-500"></i>
      New Paste
    </button>
    <button
      on:click={() => navigate('recent')}
      class="maas-nav-item {isActive('recent') ? 'active' : ''} px-6 py-3 text-sm flex items-center gap-3 text-left w-full"
    >
      <i class="fa-solid fa-clock w-4 text-center text-gray-500"></i>
      Recent Pastes
      <span class="ml-auto bg-[#dfdcd9] text-gray-600 text-xs px-1.5 rounded-full">{pasteCount}</span>
    </button>
    <button
      on:click={() => navigate('my-pastes')}
      class="maas-nav-item {isActive('my-pastes') ? 'active' : ''} px-6 py-3 text-sm flex items-center gap-3 text-left w-full"
    >
      <i class="fa-solid fa-user w-4 text-center text-gray-500"></i>
      My Pastes
    </button>

    <div class="mt-6 mb-2 px-6 text-xs font-bold text-[#AEA79F] uppercase tracking-wider">Configuration</div>

    <button
      on:click={() => navigate('api')}
      class="maas-nav-item {isActive('api') ? 'active' : ''} px-6 py-3 text-sm flex items-center gap-3 text-left w-full"
    >
      <i class="fa-solid fa-code w-4 text-center text-gray-500"></i>
      API Documentation
    </button>
  </nav>

  <div class="mt-auto p-4 border-t border-[#dfdcd9]">
    <div class="text-xs text-gray-500">
      <div class="flex justify-between mb-1">
        <span>Storage</span>
        <span>24%</span>
      </div>
      <div class="w-full bg-gray-300 h-1.5 rounded-full overflow-hidden">
        <div class="bg-[#772953] h-full w-[24%]"></div>
      </div>
    </div>
  </div>
</aside>

<style>
  .maas-nav-item {
    color: #333;
    border-left: 4px solid transparent;
    transition: all 0.2s;
    background-color: transparent;
    cursor: pointer;
  }

  .maas-nav-item:hover {
    background-color: rgba(0,0,0,0.03);
    text-decoration: none;
  }

  .maas-nav-item.active {
    border-left-color: #E95420;
    font-weight: 500;
    background-color: #fff;
  }

  .maas-nav-item:focus {
    outline: none;
  }
</style>