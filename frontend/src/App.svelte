<script>
  import Navigation from './components/Navigation.svelte'
  import HeroSection from './components/HeroSection.svelte'
  import PasteForm from './components/PasteForm.svelte'
  import RecentPastes from './components/RecentPastes.svelte'
  import MyPastes from './components/MyPastes.svelte'
  import ApiDocs from './components/ApiDocs.svelte'
  import Toast from './components/Toast.svelte'
  import { toastStore } from './stores/toastStore'

  let currentUser = null
  let currentSection = 'new'

  function handleNavigation(section) {
    currentSection = section
  }
</script>

<div class="min-h-screen bg-gray-50">
  <Navigation {currentUser} on:navigate={(e) => handleNavigation(e.detail.section)} />

  <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    {#if currentSection === 'new' || currentSection === 'default'}
      <HeroSection />
      <PasteForm />
    {/if}

    {#if currentSection === 'recent'}
      <RecentPastes />
    {/if}

    {#if currentSection === 'my-pastes'}
      <MyPastes {currentUser} />
    {/if}

    {#if currentSection === 'api'}
      <ApiDocs />
    {/if}
  </main>

  <Toast />
</div>

<style global>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  }
</style>
