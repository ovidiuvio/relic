<script>
  import { onMount } from "svelte";
  import Toast from "./components/Toast.svelte";
  import KeyRevealModal from "./components/KeyRevealModal.svelte";
  import { toastStore } from "./stores/toastStore";
  import { matchRoute, sectionToPath } from "./routes";
  import { initClientKey, swSetKey, checkAdminStatus, updateClientName, registerClient, getVersion } from "./services/api";
  import { usingSw, getClientKey } from "./services/api/auth";
  import { showToast } from "./stores/toastStore";
  import { clientPublicId as clientPublicIdStore } from "./stores/clientStore";

  let currentSection = null;
  let routeComponent = null;
  let routeProps = {};

  let showKeyDropdown = false;
  let relicViewerFullWidth = false;
  let relicFormFullWidth = false;
  let isAdmin = false;
  let clientName = "";
  let clientPublicId = "";
  let isNameSaving = false;
  let appVersion = "loading...";
  let clientKeyOnce = null;
  let showKeyReveal = false;

  function updateRouting() {
    const path = window.location.pathname;
    const urlParams = new URLSearchParams(window.location.search);

    console.log("[App] Route update - path:", path, "search:", urlParams.toString());

    const matched = matchRoute(path, urlParams);
    routeComponent = matched.component;
    routeProps = matched.props;
    currentSection = matched.section;

    console.log(
      "[App] Routing result - section:",
      currentSection,
      "props:",
      routeProps
    );
  }

  // Initial routing on page load - call it before onMount to prevent flicker
  updateRouting();

  onMount(async () => {
    // Initialise SW vault and migrate key from localStorage if needed.
    // Returns the key only on first creation or migration — null for returning users.
    clientKeyOnce = await initClientKey();
    if (clientKeyOnce) showKeyReveal = true;

    // Fetch app version
    try {
      const response = await getVersion();
      appVersion = response.data.version;
    } catch (error) {
      console.error("[App] Failed to fetch version:", error);
      appVersion = "unknown";
    }

    // Register/Fetch client info (SW injects X-Client-Key automatically)
    try {
        const clientInfo = await registerClient();
        if (clientInfo && clientInfo.name) clientName = clientInfo.name;
        if (clientInfo && clientInfo.public_id) {
          clientPublicId = clientInfo.public_id;
          clientPublicIdStore.set(clientInfo.public_id);
        }
    } catch (e) {
        console.error("Failed to fetch client info", e);
    }

    // Check admin status
    try {
      const response = await checkAdminStatus();
      isAdmin = response.data.is_admin;
    } catch (error) {
      console.error("[App] Failed to check admin status:", error);
      isAdmin = false;
    }

    // Load full-width preference from localStorage
    const savedViewer = localStorage.getItem("relic_viewer_fullwidth");
    if (savedViewer !== null) {
      relicViewerFullWidth = savedViewer === "true";
    }
    const savedForm = localStorage.getItem("relic_form_fullwidth");
    if (savedForm !== null) {
      relicFormFullWidth = savedForm === "true";
    }

    // Initial routing already handled at top level

    // Close credentials dropdown when clicking outside
    function handleDocumentClick(e) {
      if (showKeyDropdown && !e.target.closest(".client-key-dropdown")) {
        showKeyDropdown = false;
      }
    }

    document.addEventListener("click", handleDocumentClick);

    // Listen for popstate to handle browser back/forward
    window.addEventListener("popstate", updateRouting);
    return () => {
      window.removeEventListener("popstate", updateRouting);
      document.removeEventListener("click", handleDocumentClick);
    };
  });

  async function saveClientName() {
    if (!clientName.trim()) return;
    isNameSaving = true;
    try {
        await updateClientName(clientName);
        showToast("Name updated successfully", "success");
    } catch (error) {
        console.error("Failed to update name:", error);
        showToast("Failed to update name", "error");
    } finally {
        isNameSaving = false;
    }
  }

  function handleNavigation(section) {
    window.history.pushState({}, "", sectionToPath(section));
    updateRouting();
  }

  function handleTagClick(event) {
    const tagName = event.detail;
    
    // If we're already in a list section that supports tag filtering, stay there
    if (currentSection !== "recent" && currentSection !== "my-relics" && currentSection !== "my-bookmarks" && currentSection !== "space-view") {
      // Default to recent (public) view for discovering tags
      window.history.pushState({}, "", `/recent?tag=${encodeURIComponent(tagName)}`);
    } else if (currentSection === "space-view") {
      window.history.pushState({}, "", `/spaces/${routeProps.spaceId}?tag=${encodeURIComponent(tagName)}`);
    } else {
      window.history.pushState({}, "", `/${currentSection}?tag=${encodeURIComponent(tagName)}`);
    }
    updateRouting();
  }

  function uploadClientKey(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
      const clientKey = e.target.result.trim();

      // Validate client key format (32 hex characters)
      if (!/^[a-f0-9]{32}$/i.test(clientKey)) {
        showToast(
          "Invalid client key format. Please use a valid 32-character hexadecimal key.",
          "error",
        );
        return;
      }

      try {
        // Store key in SW vault (or localStorage in fallback mode)
        await swSetKey(clientKey);
        const headers = { "Content-Type": "application/json" };
        if (!usingSw) headers["X-Client-Key"] = clientKey;
        const response = await fetch("/api/v1/client/register", {
          method: "POST",
          headers,
        });
        const data = await response.json();
        if (data.message?.includes("successfully") || data.message?.includes("already registered")) {
          showToast("Client key imported successfully! Reloading...", "success");
          setTimeout(() => window.location.reload(), 1500);
        } else {
          showToast("Failed to import client key", "error");
        }
      } catch {
        showToast("Failed to import client key", "error");
      }
    };
    reader.readAsText(file);

    // Reset file input
    event.target.value = "";
    showKeyDropdown = false;
  }

  function handleFullWidthToggle(event) {
    if (currentSection === 'relic') {
        relicViewerFullWidth = event.detail.isFullWidth;
    } else if (currentSection === 'new') {
        relicFormFullWidth = event.detail.isFullWidth;
    }
  }
</script>

<svelte:head>
  <link
    href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@300;400;500;700&family=Ubuntu+Mono:wght@400;700&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="h-screen overflow-hidden flex flex-col font-ubuntu text-[#333333]">
  <!-- Header with Navigation -->
  <header class="bg-[#772953] text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-6">
      <div class="flex items-center justify-between h-14">
        <!-- Logo and Brand -->
        <div class="flex items-center gap-3">
          <button
            on:click={() => handleNavigation("recent")}
            class="logo-button flex items-center hover:opacity-80 transition-opacity"
            title="Go to Recent Relics"
          >
            <div class="font-bold text-xl tracking-tight">
              RELIC <span class="font-light opacity-80">Bin</span>
            </div>
          </button>
          
          <a
            href="https://github.com/ovidiuvio/relic"
            target="_blank"
            rel="noopener noreferrer"
            class="text-xs bg-black/20 px-2 py-0.5 rounded text-white/70 hover:bg-black/30 hover:text-white transition-all"
            title="View Source on GitHub"
          >
            {appVersion}
          </a>
        </div>

        <!-- Top Navigation -->
        <nav class="hidden md:flex items-center space-x-1 ml-auto">
          <button
            on:click={() => handleNavigation("new")}
            class="maas-nav-top {currentSection === 'new' ? 'active' : ''}"
          >
            <i class="fas fa-plus mr-2"></i>New Relic
          </button>
          <button
            on:click={() => handleNavigation("recent")}
            class="maas-nav-top {currentSection === 'recent' ? 'active' : ''}"
          >
            <i class="fas fa-clock mr-2"></i>Recent
          </button>
          <button
            on:click={() => handleNavigation("spaces")}
            class="maas-nav-top {currentSection === 'spaces' || currentSection === 'space-view' ? 'active' : ''}"
          >
            <i class="fas fa-layer-group mr-2"></i>Spaces
          </button>
          <button
            on:click={() => handleNavigation("my-relics")}
            class="maas-nav-top {currentSection === 'my-relics' ? 'active' : ''}"
          >
            <i class="fas fa-user mr-2"></i>My Relics
          </button>
          <button
            on:click={() => handleNavigation("my-bookmarks")}
            class="maas-nav-top {currentSection === 'my-bookmarks' ? 'active' : ''}"
          >
            <i class="fas fa-bookmark mr-2"></i>Bookmarks
          </button>
          {#if isAdmin}
            <button
              on:click={() => handleNavigation("admin")}
              class="maas-nav-top {currentSection === 'admin' ? 'active' : ''}"
            >
              <i class="fas fa-shield-alt mr-2"></i>Admin
            </button>
          {/if}
        </nav>

        <!-- Client Key Menu -->
        <div class="flex items-center gap-4">
          <div class="client-key-dropdown relative">
            <button
              on:click={() => (showKeyDropdown = !showKeyDropdown)}
              class="p-2 text-white/80 hover:text-white transition-colors"
              title="Profile"
            >
              <i class="fas fa-user-circle"></i>
            </button>

            {#if showKeyDropdown}
              <div
                class="absolute right-0 mt-2 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50"
                on:click={e => e.stopPropagation()}
              >
                <div class="p-3 border-b border-gray-200">
                  <p class="text-sm font-medium text-gray-900">Profile</p>
                </div>

                <div class="p-3 border-b border-gray-200">
                    <label class="block text-xs font-medium text-gray-700 mb-1">Display Name</label>
                    <div class="flex gap-2">
                        <input
                            type="text"
                            bind:value={clientName}
                            placeholder="Anonymous"
                            class="flex-1 text-sm text-gray-900 border border-gray-300 rounded px-2 py-1 focus:outline-none focus:border-blue-500"
                        />
                        <button
                            on:click={saveClientName}
                            disabled={isNameSaving}
                            class="w-8 h-[30px] flex items-center justify-center bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex-shrink-0"
                            title="Save Name"
                        >
                            {#if isNameSaving}
                                <i class="fas fa-spinner fa-spin text-xs"></i>
                            {:else}
                                <i class="fas fa-check text-xs"></i>
                            {/if}
                        </button>
                    </div>
                    <p class="text-[10px] text-gray-500 mt-1">Required for commenting</p>
                </div>

                <div class="p-3 border-b border-gray-200">
                    <label class="block text-xs font-medium text-gray-700 mb-1">Your Public ID</label>
                    <div class="flex gap-2 items-center">
                        <span class="flex-1 text-sm font-mono text-gray-900 select-all">
                            {clientPublicId || '...'}
                        </span>
                        <button
                            on:click={() => navigator.clipboard.writeText(clientPublicId).then(() => { showToast('Public ID copied', 'success'); showKeyDropdown = false; })}
                            class="w-8 h-[30px] flex items-center justify-center border border-gray-300 rounded hover:bg-gray-100 transition-colors flex-shrink-0"
                            title="Copy Public ID"
                        >
                            <i class="fas fa-copy text-xs text-gray-600"></i>
                        </button>
                    </div>
                    <p class="text-[10px] text-gray-500 mt-1">Share this ID so others can add you to spaces</p>
                </div>

                <div class="py-2">
                  <label
                    class="maas-dropdown-item block w-full text-left px-4 py-2 text-gray-700 hover:bg-gray-50 transition-colors cursor-pointer flex items-center"
                  >
                    <i class="fas fa-upload w-5 text-purple-600"></i>
                    <span>Import Key</span>
                    <input
                      type="file"
                      accept=".txt"
                      on:change={uploadClientKey}
                      class="hidden"
                    />
                  </label>
                </div>

                <div class="px-4 py-3 bg-gray-50 rounded-b-lg">
                  <p class="text-xs text-gray-500">
                    <i class="fas fa-info-circle mr-1"></i>
                    {#if usingSw}
                      Your key is stored securely and cannot be displayed again.
                      Use Import to restore from a backup.
                    {:else}
                      Your key is stored in browser local storage.
                      Use Import to restore from a backup on another device.
                    {/if}
                  </p>
                </div>
              </div>
            {/if}
          </div>
        </div>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="flex-1 overflow-auto flex flex-col">
    <div
      class="w-full {((currentSection === 'relic' && relicViewerFullWidth) || (currentSection === 'new' && relicFormFullWidth))
        ? ''
        : 'max-w-7xl mx-auto'} py-6 px-4 sm:px-6 lg:px-8 transition-all duration-300{(currentSection === 'relic' || currentSection === 'new') ? ' flex-1 flex flex-col min-h-0' : ''}"
    >
      {#if routeComponent}
        <svelte:component
          this={routeComponent}
          {...routeProps}
          on:fullwidth-toggle={handleFullWidthToggle}
          on:tag-click={handleTagClick}
          on:navigate={(e) => handleNavigation(e.detail.path)}
          on:clear-tag-filter={() => {
            if (currentSection === 'space-view') {
              window.history.pushState({}, "", `/spaces/${routeProps.spaceId}`);
              updateRouting();
            }
          }}
        />
      {/if}
    </div>
  </main>

  <Toast />
  <KeyRevealModal
    show={showKeyReveal}
    clientKey={clientKeyOnce || ''}
    on:confirm={() => { showKeyReveal = false; clientKeyOnce = null; }}
  />
</div>


<style global>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: "Ubuntu", sans-serif;
    color: #333333;
  }

  :global(*) {
    box-sizing: border-box;
  }

  /* Ubuntu Mono for code */
  :global(.font-mono),
  :global(code),
  :global(pre) {
    font-family: "Ubuntu Mono", monospace;
  }

  /* MAAS-style button primary */
  :global(.maas-btn-primary) {
    background-color: #0e8420;
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
    border: 1px solid #aea79f;
    border-radius: 2px;
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  :global(.maas-input:focus) {
    border-color: #e95420;
    outline: none;
    box-shadow: 0 0 0 1px #e95420;
  }

  /* Card styling */
  :global(.maas-card) {
    background-color: white;
    border: 1px solid #dfdcd9;
    border-radius: 2px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }

  /* Table styling */
  :global(.maas-table th) {
    font-weight: 400;
    color: #111;
    border-bottom: 1px solid #aea79f;
    text-align: left;
    padding: 0.6rem 1rem;
    font-size: 13px;
  }

  :global(.maas-table td) {
    padding: 0.625rem 1rem;
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
    font-size: 13.5px;
    font-weight: 500;
    padding: 0.5rem 1rem;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
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
    content: "";
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 20px;
    height: 2px;
    background-color: #e95420;
    border-radius: 1px;
  }

  :global(.maas-nav-top:focus) {
    outline: none;
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.3);
  }

  /* Logo button styling */
  :global(.logo-button) {
    background: none;
    border: none;
    padding: 0;
    font-family: inherit;
    cursor: pointer;
  }
</style>
