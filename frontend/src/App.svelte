<script>
  import { onMount } from "svelte";
  import RelicForm from "./components/RelicForm.svelte";
  import RelicViewer from "./components/RelicViewer.svelte";
  import RecentRelics from "./components/RecentRelics.svelte";
  import MyRelics from "./components/MyRelics.svelte";
  import MyBookmarks from "./components/MyBookmarks.svelte";
  import AdminPanel from "./components/AdminPanel.svelte";
  import Toast from "./components/Toast.svelte";
  import { toastStore } from "./stores/toastStore";
  import { getOrCreateClientKey, checkAdminStatus, updateClientName, registerClient, getVersion } from "./services/api";
  import { showToast } from "./stores/toastStore";

  let currentSection = null;
  let currentRelicId = null;
  let currentFilePath = null; // For archive file paths
  let showKeyDropdown = false;
  let relicViewerFullWidth = false;
  let isAdmin = false;
  let clientName = "";
  let isNameSaving = false;
  let appVersion = "loading...";
  let activeTagFilter = null;

  function updateRouting() {
    const path = window.location.pathname;
    const parts = path.split("/").filter((p) => p);
    const urlParams = new URLSearchParams(window.location.search);
    const tagParam = urlParams.get('tag');

    console.log("[App] Route update - path:", path, "parts:", parts, "tag:", tagParam);

    // Update tag filter from URL
    activeTagFilter = tagParam;

    if (
      parts.length >= 1 &&
      parts[0] &&
      parts[0] !== "api" &&
      parts[0] !== "recent" &&
      parts[0] !== "my-relics" &&
      parts[0] !== "my-bookmarks" &&
      parts[0] !== "new" &&
      parts[0] !== "admin"
    ) {
      // This looks like a relic ID (possibly with file path)
      currentRelicId = parts[0];
      currentSection = "relic";

      // Check if there's a file path (parts after the relic ID)
      if (parts.length > 1) {
        currentFilePath = parts.slice(1).join("/");
        console.log("[App] Detected archive file path:", currentFilePath);
      } else {
        currentFilePath = null;
      }
    } else if (parts.length === 0) {
      currentSection = "new";
      currentRelicId = null;
      currentFilePath = null;
    } else {
      currentSection = parts[0];
      currentRelicId = null;
      currentFilePath = null;
    }
  }

  // Initial routing on page load
  updateRouting();

  onMount(async () => {
    // Initialize client key on app start
    const key = getOrCreateClientKey();

    // Fetch app version
    try {
      const response = await getVersion();
      appVersion = response.data.version;
    } catch (error) {
      console.error("[App] Failed to fetch version:", error);
      appVersion = "unknown";
    }

    // Register/Fetch client info
    try {
        const clientInfo = await registerClient(key);
        if (clientInfo && clientInfo.name) {
            clientName = clientInfo.name;
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
    const saved = localStorage.getItem("relic_viewer_fullwidth");
    if (saved !== null) {
      relicViewerFullWidth = saved === "true";
    }

    function handleDocumentClick(e) {
      if (showKeyDropdown && !e.target.closest(".client-key-dropdown")) {
        showKeyDropdown = false;
      }
    }

    document.addEventListener("click", handleDocumentClick);
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
    currentSection = section;
    currentRelicId = null;
    activeTagFilter = null;

    if (section === "new") {
      window.history.pushState({}, "", "/");
    } else {
      window.history.pushState({}, "", `/${section}`);
    }
  }

  function handleTagClick(event) {
    const tagName = event.detail;
    activeTagFilter = tagName;
    
    if (currentSection !== "recent" && currentSection !== "my-relics" && currentSection !== "my-bookmarks") {
      currentSection = "recent";
    }
    
    currentRelicId = null;
    window.history.pushState({}, "", `/${currentSection}?tag=${encodeURIComponent(tagName)}`);
  }

  function downloadClientKey() {
    const clientKey = getOrCreateClientKey();
    const blob = new Blob([clientKey], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `relic-client-key-${clientKey.substring(0, 8)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast("Client key downloaded successfully", "success");
    showKeyDropdown = false;
  }

  function copyClientKey() {
    const clientKey = getOrCreateClientKey();
    navigator.clipboard.writeText(clientKey)
      .then(() => showToast("Client key copied to clipboard", "success"))
      .catch(() => showToast("Failed to copy client key", "error"));
    showKeyDropdown = false;
  }

  function uploadClientKey(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const clientKey = e.target.result.trim();
      if (!/^[a-f0-9]{32}$/i.test(clientKey)) {
        showToast("Invalid client key format.", "error");
        return;
      }
      localStorage.setItem("relic_client_key", clientKey);
      fetch("/api/v1/client/register", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Client-Key": clientKey },
      })
      .then((response) => response.json())
      .then((data) => {
        showToast("Client key imported successfully! Reloading...", "success");
        setTimeout(() => window.location.reload(), 1500);
      })
      .catch(() => showToast("Failed to import client key", "error"));
    };
    reader.readAsText(file);
    event.target.value = "";
    showKeyDropdown = false;
  }

  function handleFullWidthToggle(event) {
    relicViewerFullWidth = event.detail.isFullWidth;
  }
</script>

<svelte:head>
  <link
    href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@300;400;500;700&family=Ubuntu+Mono:wght@400;700&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="h-screen flex flex-col overflow-hidden">
  <!-- Fixed Header -->
  <header class="bg-[#383d41] text-white flex items-center justify-between px-4 h-[50px] shrink-0 z-50 shadow-md">
    <!-- Brand -->
    <button
      on:click={() => handleNavigation("recent")}
      class="flex items-center gap-2 hover:opacity-80 transition-opacity"
      title="Relic Dashboard"
    >
        <div class="bg-[#E85E00] w-8 h-8 flex items-center justify-center rounded-sm font-bold text-white">R</div>
        <div class="font-bold text-lg tracking-tight text-white/90">
            RELIC <span class="font-light opacity-70">VE</span>
        </div>
    </button>

    <!-- Search / User Menu -->
    <div class="flex items-center gap-4">
        <span class="text-xs text-white/50 hidden md:block">Version: {appVersion}</span>

        <div class="client-key-dropdown relative">
            <button
              on:click={() => (showKeyDropdown = !showKeyDropdown)}
              class="flex items-center gap-2 px-3 py-1 bg-[#4d5357] hover:bg-[#5e656a] rounded-sm transition-colors text-sm border border-[#222]"
              title="User Settings"
            >
              <i class="fas fa-user-circle"></i>
              <span class="hidden sm:inline">{clientName || "Anonymous"}</span>
              <i class="fas fa-caret-down text-xs ml-1"></i>
            </button>

            {#if showKeyDropdown}
              <div
                class="absolute right-0 mt-2 w-72 bg-white border border-gray-400 rounded-sm shadow-xl z-50 text-gray-800"
                on:click={e => e.stopPropagation()}
              >
                <div class="p-3 border-b border-gray-200 bg-[#f5f5f5]">
                    <p class="text-sm font-bold text-gray-800">
                        Authentication
                    </p>
                </div>

                <div class="p-3 border-b border-gray-200">
                    <label class="block text-xs font-medium text-gray-700 mb-1">Display Name</label>
                    <div class="flex gap-2">
                        <input 
                            type="text" 
                            bind:value={clientName} 
                            placeholder="Anonymous"
                            class="flex-1 text-sm maas-input"
                        />
                        <button 
                            on:click={saveClientName}
                            disabled={isNameSaving}
                            class="maas-btn-primary w-8 px-0"
                            title="Save Name"
                        >
                            {#if isNameSaving}
                                <i class="fas fa-spinner fa-spin text-xs"></i>
                            {:else}
                                <i class="fas fa-check text-xs"></i>
                            {/if}
                        </button>
                    </div>
                </div>

                <div class="py-2">
                  <button
                    on:click={downloadClientKey}
                    class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-[#e3f2fd] hover:text-[#2196f3] transition-colors flex items-center"
                  >
                    <i class="fas fa-download w-4 mr-2"></i>
                    <span>Download Key</span>
                  </button>

                  <button
                    on:click={copyClientKey}
                    class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-[#e3f2fd] hover:text-[#2196f3] transition-colors flex items-center"
                  >
                    <i class="fas fa-copy w-4 mr-2"></i>
                    <span>Copy to Clipboard</span>
                  </button>

                  <label
                    class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-[#e3f2fd] hover:text-[#2196f3] transition-colors cursor-pointer flex items-center"
                  >
                    <i class="fas fa-upload w-4 mr-2"></i>
                    <span>Import Key</span>
                    <input
                      type="file"
                      accept=".txt"
                      on:change={uploadClientKey}
                      class="hidden"
                    />
                  </label>
                </div>
              </div>
            {/if}
        </div>
    </div>
  </header>

  <div class="flex flex-1 overflow-hidden">
    <!-- Sidebar -->
    <aside class="w-64 bg-[#f5f5f5] border-r border-[#ccc] flex flex-col font-sans text-sm select-none shrink-0">
        <!-- Root Node -->
        <div class="px-2 py-2 font-bold text-gray-700 bg-[#e0e0e0] border-b border-[#ccc] flex items-center">
            <i class="fas fa-server mr-2 text-gray-500"></i> Datacenter
        </div>

        <!-- Tree -->
        <div class="flex-1 overflow-y-auto py-2">
            <!-- Relic Bin Node -->
            <div class="pl-2 py-1 flex items-center text-gray-700">
                <i class="fas fa-caret-down mr-1 w-4 text-center text-gray-500"></i>
                <i class="fas fa-database mr-2 text-gray-600"></i>
                <span class="font-medium">Relic Bin</span>
            </div>

            <!-- Children -->
            <div class="pl-4 relative">
                <!-- Vertical Line Guide (Visual) -->
                <div class="absolute left-[13px] top-0 bottom-0 w-px bg-gray-300"></div>

                <!-- Create -->
                <button
                    class="w-full text-left py-1.5 pl-8 pr-2 cursor-pointer flex items-center transition-colors relative {currentSection === 'new' ? 'bg-[#2196f3] text-white font-bold' : 'hover:bg-[#e6e6e6] text-gray-800'}"
                    on:click={() => handleNavigation('new')}
                >
                    <i class="fas fa-plus-circle mr-2 w-4 text-center {currentSection === 'new' ? 'text-white' : 'text-green-600'}"></i>
                    Create Relic
                </button>

                <!-- Recent -->
                <button
                    class="w-full text-left py-1.5 pl-8 pr-2 cursor-pointer flex items-center transition-colors relative {currentSection === 'recent' ? 'bg-[#2196f3] text-white font-bold' : 'hover:bg-[#e6e6e6] text-gray-800'}"
                    on:click={() => handleNavigation('recent')}
                >
                    <i class="fas fa-clock mr-2 w-4 text-center {currentSection === 'recent' ? 'text-white' : 'text-blue-600'}"></i>
                    Recent
                </button>

                <!-- My Relics -->
                <button
                    class="w-full text-left py-1.5 pl-8 pr-2 cursor-pointer flex items-center transition-colors relative {currentSection === 'my-relics' ? 'bg-[#2196f3] text-white font-bold' : 'hover:bg-[#e6e6e6] text-gray-800'}"
                    on:click={() => handleNavigation('my-relics')}
                >
                    <i class="fas fa-user mr-2 w-4 text-center {currentSection === 'my-relics' ? 'text-white' : 'text-purple-600'}"></i>
                    My Relics
                </button>

                <!-- Bookmarks -->
                <button
                    class="w-full text-left py-1.5 pl-8 pr-2 cursor-pointer flex items-center transition-colors relative {currentSection === 'my-bookmarks' ? 'bg-[#2196f3] text-white font-bold' : 'hover:bg-[#e6e6e6] text-gray-800'}"
                    on:click={() => handleNavigation('my-bookmarks')}
                >
                    <i class="fas fa-bookmark mr-2 w-4 text-center {currentSection === 'my-bookmarks' ? 'text-white' : 'text-amber-600'}"></i>
                    Bookmarks
                </button>

                {#if isAdmin}
                    <!-- Admin -->
                    <button
                        class="w-full text-left py-1.5 pl-8 pr-2 cursor-pointer flex items-center transition-colors relative {currentSection === 'admin' ? 'bg-[#2196f3] text-white font-bold' : 'hover:bg-[#e6e6e6] text-gray-800'}"
                        on:click={() => handleNavigation('admin')}
                    >
                        <i class="fas fa-shield-alt mr-2 w-4 text-center {currentSection === 'admin' ? 'text-white' : 'text-red-600'}"></i>
                        Admin
                    </button>
                {/if}
            </div>

            {#if currentSection === 'relic' && currentRelicId}
                <!-- Dynamic Node for active relic -->
                <div class="mt-2 pl-2 py-1 flex items-center text-gray-700">
                    <i class="fas fa-caret-down mr-1 w-4 text-center text-gray-500"></i>
                    <i class="fas fa-file-code mr-2 text-gray-600"></i>
                    <span class="font-medium truncate pr-2">Active Relic</span>
                </div>
                <div class="pl-4 relative">
                    <div class="absolute left-[13px] top-0 bottom-0 w-px bg-gray-300"></div>
                    <div
                        class="w-full text-left py-1.5 pl-8 pr-2 cursor-pointer flex items-center transition-colors relative bg-[#2196f3] text-white font-bold"
                    >
                        <i class="fas fa-eye mr-2 w-4 text-center"></i>
                        <span class="truncate">{currentRelicId}</span>
                    </div>
                </div>
            {/if}
        </div>

        <!-- Footer -->
        <div class="p-2 border-t border-[#ccc] text-xs text-center text-gray-500">
            Relic Bin &copy; 2024
        </div>
    </aside>

    <!-- Main Content Area -->
    <main class="flex-1 overflow-hidden flex flex-col bg-[#e0e0e0]">
        <!-- Top Toolbar / Breadcrumb (Optional placeholder) -->
        <div class="h-[35px] bg-white border-b border-[#ccc] flex items-center px-4 shrink-0 shadow-sm">
            <div class="text-sm font-bold text-gray-700 flex items-center">
                <i class="fas fa-home mr-2 text-gray-400"></i>
                <span class="text-gray-400">Datacenter</span>
                <span class="mx-2 text-gray-400">/</span>
                <span>
                    {#if currentSection === 'new'}Create Relic
                    {:else if currentSection === 'recent'}Recent Relics
                    {:else if currentSection === 'my-relics'}My Relics
                    {:else if currentSection === 'my-bookmarks'}Bookmarks
                    {:else if currentSection === 'admin'}Administration
                    {:else if currentSection === 'relic'}Relic Viewer
                    {:else}Dashboard{/if}
                </span>
                {#if currentRelicId}
                    <span class="mx-2 text-gray-400">/</span>
                    <span class="font-mono text-gray-600">{currentRelicId}</span>
                {/if}
            </div>
        </div>

        <!-- Content Scroller -->
        <div class="flex-1 overflow-auto p-4">
            <div class="{relicViewerFullWidth && currentSection === 'relic' ? 'w-full' : 'max-w-7xl mx-auto'} transition-all duration-300">
                {#if currentSection === "relic" && currentRelicId}
                    <RelicViewer
                        relicId={currentRelicId}
                        filePath={currentFilePath}
                        on:fullwidth-toggle={handleFullWidthToggle}
                        on:tag-click={handleTagClick}
                    />
                {:else if currentSection === "new" || currentSection === "default" || currentSection === ""}
                    <RelicForm />
                {:else if currentSection === "recent"}
                    <RecentRelics tagFilter={activeTagFilter} on:tag-click={handleTagClick} />
                {:else if currentSection === "my-relics"}
                    <MyRelics tagFilter={activeTagFilter} on:tag-click={handleTagClick} />
                {:else if currentSection === "my-bookmarks"}
                    <MyBookmarks tagFilter={activeTagFilter} on:tag-click={handleTagClick} />
                {:else if currentSection === "admin"}
                    <AdminPanel />
                {/if}
            </div>
        </div>
    </main>
  </div>

  <Toast />
</div>

<style>
  /* Local component styles if needed, otherwise using global utilities */
</style>
