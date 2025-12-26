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

  let currentSection = "new";
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

      console.log("[App] Detected relic ID:", parts[0]);
    } else if (parts.length === 0) {
      console.log("[App] Navigating to home");
      currentSection = "new";
      currentRelicId = null;
      currentFilePath = null;
    } else {
      console.log("[App] Navigating to section:", parts[0]);
      currentSection = parts[0];
      currentRelicId = null;
      currentFilePath = null;
    }

    console.log(
      "[App] Routing result - section:",
      currentSection,
      "relicId:",
      currentRelicId,
      "filePath:",
      currentFilePath,
      "tagFilter:",
      activeTagFilter,
    );
  }

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

    // Initial routing on page load
    updateRouting();

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
    
    // If we're already in a list section that supports tag filtering, stay there
    if (currentSection !== "recent" && currentSection !== "my-relics" && currentSection !== "my-bookmarks") {
      currentSection = "recent"; // Default to recent (public) view for discovering tags
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
    navigator.clipboard
      .writeText(clientKey)
      .then(() => {
        showToast("Client key copied to clipboard", "success");
      })
      .catch(() => {
        showToast("Failed to copy client key", "error");
      });
    showKeyDropdown = false;
  }

  function uploadClientKey(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const clientKey = e.target.result.trim();

      // Validate client key format (32 hex characters)
      if (!/^[a-f0-9]{32}$/i.test(clientKey)) {
        showToast(
          "Invalid client key format. Please use a valid 32-character hexadecimal key.",
          "error",
        );
        return;
      }

      // Store the new client key
      localStorage.setItem("relic_client_key", clientKey);

      // Re-register with server
      fetch("/api/v1/client/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Client-Key": clientKey,
        },
      })
        .then((response) => response.json())
        .then((data) => {
          if (
            data.message.includes("successfully") ||
            data.message.includes("already registered")
          ) {
            showToast(
              "Client key imported successfully! Reloading...",
              "success",
            );
            setTimeout(() => {
              window.location.reload();
            }, 1500);
          } else {
            showToast("Failed to import client key", "error");
          }
        })
        .catch(() => {
          showToast("Failed to import client key", "error");
        });
    };
    reader.readAsText(file);

    // Reset file input
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

<div class="min-h-screen flex flex-col font-ubuntu text-[#333333]">
  <!-- Header with Navigation -->
  <header class="bg-[#772953] text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-6">
      <div class="flex items-center justify-between h-16">
        <!-- Logo and Brand -->
        <button
          on:click={() => handleNavigation("recent")}
          class="logo-button flex items-center gap-3 hover:opacity-80 transition-opacity"
          title="Go to Recent Relics"
        >
          <div class="font-bold text-xl tracking-tight">
            RELIC <span class="font-light opacity-80">Bin</span>
          </div>
          <span class="text-xs bg-black/20 px-2 py-0.5 rounded text-white/70"
            >{appVersion}</span
          >
        </button>

        <!-- Top Navigation -->
        <nav class="hidden md:flex items-center space-x-1 ml-auto">
          <button
            on:click={() => handleNavigation("new")}
            class="maas-nav-top {currentSection === 'new'
              ? 'active'
              : ''} px-4 py-2 text-sm font-medium rounded-lg transition-colors"
          >
            <i class="fas fa-plus mr-2"></i>New Relic
          </button>
          <button
            on:click={() => handleNavigation("recent")}
            class="maas-nav-top {currentSection === 'recent'
              ? 'active'
              : ''} px-4 py-2 text-sm font-medium rounded-lg transition-colors"
          >
            <i class="fas fa-clock mr-2"></i>Recent
          </button>
          <button
            on:click={() => handleNavigation("my-relics")}
            class="maas-nav-top {currentSection === 'my-relics'
              ? 'active'
              : ''} px-4 py-2 text-sm font-medium rounded-lg transition-colors"
          >
            <i class="fas fa-user mr-2"></i>My Relics
          </button>
          <button
            on:click={() => handleNavigation("my-bookmarks")}
            class="maas-nav-top {currentSection === 'my-bookmarks'
              ? 'active'
              : ''} px-4 py-2 text-sm font-medium rounded-lg transition-colors"
          >
            <i class="fas fa-bookmark mr-2"></i>Bookmarks
          </button>
          {#if isAdmin}
            <button
              on:click={() => handleNavigation("admin")}
              class="maas-nav-top {currentSection === 'admin'
                ? 'active'
                : ''} px-4 py-2 text-sm font-medium rounded-lg transition-colors"
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
              title="Relic Key"
            >
              <i class="fas fa-key"></i>
            </button>

            {#if showKeyDropdown}
              <div
                class="absolute right-0 mt-2 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50"
                on:click={e => e.stopPropagation()}
              >
                <div class="p-3 border-b border-gray-200">
                  <p class="text-sm font-medium text-gray-900">
                    Manage Your Relic Key
                  </p>
                  <p class="text-xs text-gray-500 mt-1">
                    Backup your key to access your relics from any device
                  </p>
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

                <div class="py-2">
                  <button
                    on:click={downloadClientKey}
                    class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors flex items-center"
                  >
                    <i class="fas fa-download w-5 text-blue-600"></i>
                    <span>Download Key</span>
                  </button>

                  <button
                    on:click={copyClientKey}
                    class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors flex items-center"
                  >
                    <i class="fas fa-copy w-5 text-green-600"></i>
                    <span>Copy to Clipboard</span>
                  </button>

                  <label
                    class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors cursor-pointer flex items-center"
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
                    Your relic key identifies you as the owner of your relics
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
  <main class="flex-1 overflow-auto">
    <div
      class="{relicViewerFullWidth && currentSection === 'relic'
        ? 'w-full'
        : 'max-w-7xl mx-auto'} py-6 px-4 sm:px-6 lg:px-8 transition-all duration-300"
    >
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
  </main>

  <Toast />
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
