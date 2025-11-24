<script>
  import { onMount } from 'svelte'
  import Navigation from './components/Navigation.svelte'
  import RelicForm from './components/RelicForm.svelte'
  import RelicViewer from './components/RelicViewer.svelte'
  import RecentRelics from './components/RecentRelics.svelte'
  import MyRelics from './components/MyRelics.svelte'
  import ApiDocs from './components/ApiDocs.svelte'
  import Toast from './components/Toast.svelte'
  import { toastStore } from './stores/toastStore'

  let currentUser = null
  let currentSection = 'new'
  let currentRelicId = null

  function updateRouting() {
    const path = window.location.pathname
    const parts = path.split('/').filter(p => p)

    console.log('[App] Route update - path:', path, 'parts:', parts)

    if (parts.length === 1 && parts[0] && parts[0] !== 'api' && parts[0] !== 'recent' && parts[0] !== 'my-relics' && parts[0] !== 'new') {
      // This looks like a relic ID
      console.log('[App] Detected relic ID:', parts[0])
      currentRelicId = parts[0]
      currentSection = 'relic'
    } else if (parts.length === 0) {
      console.log('[App] Navigating to home')
      currentSection = 'new'
      currentRelicId = null
    } else {
      console.log('[App] Navigating to section:', parts[0])
      currentSection = parts[0]
      currentRelicId = null
    }

    console.log('[App] Routing result - section:', currentSection, 'relicId:', currentRelicId)
  }

  onMount(() => {
    // Initial routing on page load
    updateRouting()

    // Listen for popstate to handle browser back/forward
    window.addEventListener('popstate', updateRouting)
    return () => window.removeEventListener('popstate', updateRouting)
  })

  function handleNavigation(section) {
    currentSection = section
    currentRelicId = null

    if (section === 'new') {
      window.history.pushState({}, '', '/')
    } else {
      window.history.pushState({}, '', `/${section}`)
    }
  }
</script>

<svelte:head>
  <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@300;400;500;700&family=Ubuntu+Mono:wght@400;700&display=swap" rel="stylesheet">
</svelte:head>

<div class="min-h-screen flex flex-col font-ubuntu bg-[#F7F7F7] text-[#333333]">
  <!-- Header with Navigation -->
  <header class="bg-[#772953] text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-4">
      <div class="flex items-center justify-between h-16">
        <!-- Logo and Brand -->
        <div class="flex items-center gap-3">
          <div class="font-bold text-xl tracking-tight">RELIC <span class="font-light opacity-80">Bin</span></div>
          <span class="text-xs bg-black/20 px-2 py-0.5 rounded text-white/70">v1.0.0</span>
        </div>

        <!-- Top Navigation -->
        <nav class="hidden md:flex items-center space-x-1">
          <button
            on:click={() => handleNavigation('new')}
            class="maas-nav-top {currentSection === 'new' ? 'active' : ''} px-4 py-2 text-sm font-medium rounded-lg transition-colors"
          >
            <i class="fas fa-plus mr-2"></i>New Relic
          </button>
          <button
            on:click={() => handleNavigation('recent')}
            class="maas-nav-top {currentSection === 'recent' ? 'active' : ''} px-4 py-2 text-sm font-medium rounded-lg transition-colors"
          >
            <i class="fas fa-clock mr-2"></i>Recent
          </button>
          <button
            on:click={() => handleNavigation('my-relics')}
            class="maas-nav-top {currentSection === 'my-relics' ? 'active' : ''} px-4 py-2 text-sm font-medium rounded-lg transition-colors"
          >
            <i class="fas fa-user mr-2"></i>My Relics
          </button>
          <button
            on:click={() => handleNavigation('api')}
            class="maas-nav-top {currentSection === 'api' ? 'active' : ''} px-4 py-2 text-sm font-medium rounded-lg transition-colors"
          >
            <i class="fas fa-code mr-2"></i>API
          </button>
        </nav>

        <!-- User Menu -->
        <div class="flex items-center gap-4">
        </div>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="flex-1 overflow-auto">
    <div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
      {#if currentSection === 'relic' && currentRelicId}
        <RelicViewer relicId={currentRelicId} />
      {:else if currentSection === 'new' || currentSection === 'default' || currentSection === ''}
        <RelicForm />
      {:else if currentSection === 'recent'}
        <RecentRelics />
      {:else if currentSection === 'my-relics'}
        <MyRelics {currentUser} />
      {:else if currentSection === 'api'}
        <ApiDocs />
      {/if}
    </div>
  </main>

  <Toast />
</div>

<style global>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: 'Ubuntu', sans-serif;
    background-color: #F7F7F7;
    color: #333333;
  }

  :global(*) {
    box-sizing: border-box;
  }

  /* Ubuntu Mono for code */
  :global(.font-mono), :global(code), :global(pre) {
    font-family: 'Ubuntu Mono', monospace;
  }

  /* MAAS-style button primary */
  :global(.maas-btn-primary) {
    background-color: #0E8420;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    font-size: 0.875rem;
    font-weight: 500;
    transition: background-color 0.2s;
  }

  :global(.maas-btn-primary:hover) {
    background-color: #0a6b19;
  }

  /* MAAS-style button secondary */
  :global(.maas-btn-secondary) {
    background-color: white;
    border: 1px solid #cdcdcd;
    color: #333;
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    font-size: 0.875rem;
    font-weight: 500;
    transition: all 0.2s;
  }

  :global(.maas-btn-secondary:hover) {
    background-color: #f9f9f9;
    border-color: #999;
  }

  /* MAAS-style inputs */
  :global(.maas-input) {
    border: 1px solid #AEA79F;
    border-radius: 2px;
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  :global(.maas-input:focus) {
    border-color: #E95420;
    outline: none;
    box-shadow: 0 0 0 1px #E95420;
  }

  
  /* Card styling */
  :global(.maas-card) {
    background-color: white;
    border: 1px solid #dfdcd9;
    border-radius: 2px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }

  /* Table styling */
  :global(.maas-table th) {
    font-weight: 400;
    color: #111;
    border-bottom: 1px solid #AEA79F;
    text-align: left;
    padding: 0.75rem 1rem;
    font-size: 0.875rem;
  }

  :global(.maas-table td) {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #dfdcd9;
    vertical-align: middle;
  }

  :global(.maas-table tr:hover td) {
    background-color: #fcfcfc;
  }

  /* Top Navigation Styles */
  :global(.maas-nav-top) {
    color: rgba(255, 255, 255, 0.7);
    transition: all 0.2s;
    position: relative;
  }

  :global(.maas-nav-top:hover) {
    color: white;
    background-color: rgba(255, 255, 255, 0.1);
  }

  :global(.maas-nav-top.active) {
    color: white;
    background-color: rgba(255, 255, 255, 0.15);
    font-weight: 500;
  }

  :global(.maas-nav-top.active::after) {
    content: '';
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 20px;
    height: 2px;
    background-color: #E95420;
    border-radius: 1px;
  }

  :global(.maas-nav-top:focus) {
    outline: none;
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.3);
  }
</style>
