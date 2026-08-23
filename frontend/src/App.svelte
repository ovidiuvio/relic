<script>
  import { onMount } from "svelte";
  import Toast from "./components/Toast.svelte";
  import KeyRevealModal from "./components/KeyRevealModal.svelte";
  import { toastStore } from "./stores/toastStore";
  import { matchRoute, sectionToPath } from "./routes";
  import { initUserKey, swSetKey, checkAdminStatus, updateUserName, registerUser, getVersion } from "./services/api";
  import { onMaintenance } from "./services/api/core";
  import { usingSw, getUserKey } from "./services/api/auth";
  import { showToast } from "./stores/toastStore";
  import { userPublicId as userPublicIdStore } from "./stores/userStore";
  import { publicSettings, loadPublicSettings } from "./stores/settingsStore";

  let currentSection = null;
  let routeLoader = null;
  let routeProps = {};

  let appLoading = true;
  let showKeyDropdown = false;
  let relicViewerFullWidth = false;
  let relicFormFullWidth = false;
  let isAdmin = false;
  let userName = "";
  let userPublicId = "";
  let isNameSaving = false;
  let appVersion = "loading...";
  let userKeyOnce = null;
  let showKeyReveal = false;

  function updateRouting() {
    const path = window.location.pathname;
    const urlParams = new URLSearchParams(window.location.search);

    console.log("[App] Route update - path:", path, "search:", urlParams.toString());

    const matched = matchRoute(path, urlParams);
    routeLoader = matched.loader;
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
    userKeyOnce = await initUserKey();
    if (userKeyOnce) showKeyReveal = true;

    try {
      // Load runtime policy the UI needs (render toggles, size limits)
      const settings = await loadPublicSettings();

      // If maintenance mode is active, show the maintenance page immediately
      // before any other API calls happen and without waiting for the Axios
      // interceptor to fire (which requires a separate blocked request).
      if (settings?.maintenance_mode) {
        maintenanceMessage = settings.maintenance_message || 'Relic is temporarily unavailable for maintenance.';
        // Still need to check admin status to potentially bypass maintenance
        try {
          const adminResponse = await checkAdminStatus();
          isAdmin = adminResponse.data.is_admin;
          // If admin, load remaining app data normally
          if (isAdmin) {
            const [versionResponse, userInfo] = await Promise.all([
              getVersion().catch(() => ({ data: { version: "unknown" } })),
              registerUser().catch(() => null),
            ]);
            appVersion = versionResponse.data.version;
            if (userInfo) {
              if (userInfo.name) userName = userInfo.name;
              if (userInfo.public_id) {
                userPublicId = userInfo.public_id;
                userPublicIdStore.set(userInfo.public_id);
              }
            }
          }
        } catch {
          isAdmin = false;
        }
        return; // appLoading cleared in finally
      }

      // Normal (non-maintenance) startup: load everything in parallel
      const [versionResponse, userInfo, adminResponse] = await Promise.all([
        getVersion().catch(() => ({ data: { version: "unknown" } })),
        registerUser().catch(() => null),
        checkAdminStatus().catch(() => ({ data: { is_admin: false } }))
      ]);

      appVersion = versionResponse.data.version;

      if (userInfo) {
        if (userInfo.name) userName = userInfo.name;
        if (userInfo.public_id) {
          userPublicId = userInfo.public_id;
          userPublicIdStore.set(userInfo.public_id);
        }
      }

      isAdmin = adminResponse.data.is_admin;
    } catch (error) {
      console.error("[App] Initial loading failed:", error);
    } finally {
      appLoading = false;
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
      if (showKeyDropdown && !e.target.closest(".user-key-dropdown")) {
        showKeyDropdown = false;
      }
    }

    document.addEventListener("click", handleDocumentClick);

    // Warm the monaco chunk once the app is idle. Nearly every route ends up
    // rendering an editor (the "/" form included), so this trades a little
    // background bandwidth for a ready editor. Deliberately NOT a static import or
    // modulepreload — those compete with first paint, which is what we just fixed.
    const conn = navigator.connection;
    if (!conn?.saveData && !/2g/.test(conn?.effectiveType || "")) {
      // Warm monaco itself, not just the wrapper component — the ~3.2 MB lives
      // behind MonacoEditor.svelte's own dynamic import of "monaco-editor".
      const warm = () =>
        Promise.all([
          import("./components/MonacoEditor.svelte"),
          import("monaco-editor"),
        ]).catch(() => {});
      if ("requestIdleCallback" in window) {
        requestIdleCallback(warm, { timeout: 3000 });
      } else {
        setTimeout(warm, 1500);
      }
    }

    // Listen for popstate to handle browser back/forward
    window.addEventListener("popstate", updateRouting);

    const unsubscribeMaintenance = onMaintenance((msg) => {
      maintenanceMessage = msg;
      appLoading = false;
    });

    return () => {
      window.removeEventListener("popstate", updateRouting);
      document.removeEventListener("click", handleDocumentClick);
      unsubscribeMaintenance();
    };
  });

  async function saveUserName() {
    if (!userName.trim()) return;
    isNameSaving = true;
    try {
        await updateUserName(userName);
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

  function uploadUserKey(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
      const userKey = e.target.result.trim();

      // Validate user key format (32 hex characters)
      if (!/^[a-f0-9]{32}$/i.test(userKey)) {
        showToast(
          "Invalid user key format. Please use a valid 32-character hexadecimal key.",
          "error",
        );
        return;
      }

      try {
        // Store key in SW vault (or localStorage in fallback mode)
        await swSetKey(userKey);
        const headers = { "Content-Type": "application/json" };
        if (!usingSw) headers["X-User-Key"] = userKey;
        const response = await fetch("/api/v1/user/register", {
          method: "POST",
          headers,
        });
        const data = await response.json();
        if (data.message?.includes("successfully") || data.message?.includes("already registered")) {
          showToast("User key imported successfully! Reloading...", "success");
          setTimeout(() => window.location.reload(), 1500);
        } else {
          showToast("Failed to import user key", "error");
        }
      } catch {
        showToast("Failed to import user key", "error");
      }
    };
    reader.readAsText(file);

    // Reset file input
    event.target.value = "";
    showKeyDropdown = false;
  }

  let maintenanceMessage = null;
  let showAdminKeyInput = false;
  let adminKeyInput = "";

  async function submitAdminKey() {
    const key = adminKeyInput.trim();
    if (!/^[a-f0-9]{32}$/i.test(key)) {
      showToast("Invalid key format. Expected 32 hex characters.", "error");
      return;
    }

    try {
      await swSetKey(key);
      showToast("Key saved! Attempting to reload...", "success");
      setTimeout(() => window.location.reload(), 1000);
    } catch (e) {
      showToast("Failed to save key", "error");
    }
  }

  function importAdminKeyFile(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
      const userKey = e.target.result.trim();
      if (!/^[a-f0-9]{32}$/i.test(userKey)) {
        showToast("Invalid key format. Expected 32 hex characters.", "error");
        return;
      }
      try {
        await swSetKey(userKey);
        showToast("Admin key imported! Reloading...", "success");
        setTimeout(() => window.location.reload(), 1000);
      } catch {
        showToast("Failed to import key", "error");
      }
    };
    reader.readAsText(file);
  }

  function handleFullWidthToggle(event) {
    if (currentSection === 'relic') {
        relicViewerFullWidth = event.detail.isFullWidth;
    } else if (currentSection === 'new') {
        relicFormFullWidth = event.detail.isFullWidth;
    }
  }
</script>

{#if appLoading}
  <div class="h-screen w-screen bg-[#fcfbfc] flex items-center justify-center">
    <svg class="animate-spin h-8 w-8 text-[#772953]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  </div>
{:else if maintenanceMessage && !isAdmin}
  <div class="min-h-screen bg-[#fcfbfc] flex flex-col justify-between py-12 px-4 sm:px-6 lg:px-8 font-ubuntu text-[#333333]">
    <div class="my-auto max-w-3xl w-full mx-auto bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      
      <!-- Status Page Header -->
      <div class="bg-[#772953] text-white px-8 py-4 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="font-bold text-lg tracking-tight">RELIC <span class="font-light opacity-80">Bin</span></span>
          <span class="text-xs bg-white/20 px-2 py-0.5 rounded text-white/90 font-mono font-semibold uppercase tracking-wider">Status</span>
        </div>
        <div class="text-xs text-white/70 font-mono">
          503 SERVICE UNAVAILABLE
        </div>
      </div>

      <div class="p-8 space-y-8">
        <!-- Main Alert -->
        <div class="bg-amber-50 border-l-4 border-[#E95420] p-6 rounded-r-lg text-left">
          <h3 class="text-lg font-bold text-gray-900 leading-tight">Instance Undergoing Maintenance</h3>
          <p class="text-sm text-gray-600 mt-1">
            This Relic Bin instance is temporarily offline for non-administrator traffic.
          </p>
        </div>

        <!-- Administrator Notice (Real Configured Message) -->
        <div class="space-y-3 text-left">
          <h4 class="text-xs font-semibold text-[#772953] uppercase tracking-wider">Message from Administrator</h4>
          <div class="bg-gray-50 border border-gray-200 rounded-lg p-5 font-mono text-sm text-gray-800 leading-relaxed italic">
            "{maintenanceMessage}"
          </div>
        </div>

        <!-- Diagnostics (Factual Metadata) -->
        <div class="space-y-3 text-left">
          <h4 class="text-xs font-semibold text-[#772953] uppercase tracking-wider">Diagnostics</h4>
          <div class="bg-gray-50 border border-gray-200 rounded-lg p-5 font-mono text-xs space-y-2 text-gray-700">
            <div class="flex justify-between border-b border-gray-200 pb-1.5">
              <span>Timestamp:</span>
              <span class="text-gray-900 font-semibold">{new Date().toISOString()}</span>
            </div>
            <div class="flex justify-between border-b border-gray-200 pb-1.5">
              <span>Service URL:</span>
              <span class="text-gray-900 font-semibold">{window.location.origin}</span>
            </div>
            <div class="flex justify-between border-b border-gray-200 pb-1.5">
              <span>Client Vault:</span>
              <span class="text-gray-900 font-semibold">{usingSw ? 'Active (Service Worker)' : 'Fallback (LocalStorage)'}</span>
            </div>
            <div class="flex justify-between">
              <span>App Version:</span>
              <span class="text-gray-900 font-semibold">{appVersion}</span>
            </div>
          </div>
        </div>

        <!-- Admin Login Section -->
        <div class="border-t border-gray-150 pt-8 mt-8">
          {#if showAdminKeyInput}
            <div class="max-w-md mx-auto space-y-4 text-left">
              <span class="text-xs font-semibold uppercase tracking-wider text-gray-500 block mb-1">
                Admin Authentication
              </span>
              <div class="flex gap-2">
                <input
                  id="admin-key"
                  type="password"
                  placeholder="Enter 32-character hex key"
                  bind:value={adminKeyInput}
                  class="flex-1 text-sm font-mono border border-gray-300 rounded px-3 py-2 focus:outline-none focus:border-[#E95420] focus:ring-1 focus:ring-[#E95420]"
                />
                <button
                  on:click={submitAdminKey}
                  class="maas-btn-primary whitespace-nowrap"
                >
                  Submit
                </button>
              </div>
              <div class="flex justify-between items-center text-xs text-gray-500 mt-1">
                <span>Or import key file (.txt):</span>
                <label class="text-[#772953] hover:underline cursor-pointer font-semibold">
                  Choose File
                  <input
                    type="file"
                    accept=".txt"
                    on:change={importAdminKeyFile}
                    class="hidden"
                  />
                </label>
              </div>
              <button
                on:click={() => showAdminKeyInput = false}
                class="text-xs text-gray-500 hover:text-gray-700 block text-center w-full mt-4 hover:underline"
              >
                Cancel
              </button>
            </div>
          {:else}
            <button
              on:click={() => showAdminKeyInput = true}
              class="text-xs font-medium text-[#772953] hover:text-[#5e1f42] hover:underline transition-colors block mx-auto"
            >
              Are you an administrator? Authenticate
            </button>
          {/if}
        </div>
      </div>
    </div>
    
    <div class="text-center text-xs text-gray-400 mt-8 font-mono">
      RELIC_BIN_VERSION: {appVersion}
    </div>
  </div>
  <Toast />
{:else}
  <div class="h-screen overflow-hidden flex flex-col font-ubuntu text-[#333333]">
    <!-- Admin Maintenance Warning Banner -->
    {#if $publicSettings.maintenance_mode}
      <div class="bg-amber-600 text-white px-6 py-2 text-center text-xs font-semibold flex items-center justify-center gap-2 relative z-50 shadow-md">
        <i class="fas fa-exclamation-triangle animate-pulse"></i>
        <span>Maintenance Mode is active. Normal traffic is blocked. You are bypassing this as an administrator.</span>
        <button
          on:click={() => handleNavigation("admin")}
          class="ml-3 underline hover:text-white/80 transition-colors font-bold uppercase tracking-wider text-[10px]"
        >
          Manage Limits
        </button>
      </div>
    {/if}

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

          <!-- User Key Menu -->
          <div class="flex items-center gap-4">
            <div class="user-key-dropdown relative">
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
                              bind:value={userName}
                              placeholder="Anonymous"
                              class="flex-1 text-sm text-gray-900 border border-gray-300 rounded px-2 py-1 focus:outline-none focus:border-blue-500"
                          />
                          <button
                              on:click={saveUserName}
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
                              {userPublicId || '...'}
                          </span>
                          <button
                              on:click={() => navigator.clipboard.writeText(userPublicId).then(() => { showToast('Public ID copied', 'success'); showKeyDropdown = false; })}
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
                        on:change={uploadUserKey}
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
        {#if routeLoader}
          {#await routeLoader()}
            <div class="flex items-center justify-center py-12 text-gray-500">
              <svg class="animate-spin h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
          {:then { default: Component }}
            <svelte:component
              this={Component}
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
          {:catch error}
            <!-- Usually a stale chunk hash after a deploy; a reload fetches the new manifest. -->
            <div class="text-center py-12">
              <p class="text-gray-700 font-medium">Failed to load this page.</p>
              <p class="text-sm text-gray-500 mt-1">{error.message}</p>
              <button
                on:click={() => window.location.reload()}
                class="mt-4 px-4 py-2 bg-[#772953] text-white rounded hover:bg-[#5e1f42] transition-colors"
              >
                Reload
              </button>
            </div>
          {/await}
        {/if}
      </div>
    </main>

    <Toast />
    <KeyRevealModal
      show={showKeyReveal}
      userKey={userKeyOnce || ''}
      on:confirm={() => { showKeyReveal = false; userKeyOnce = null; }}
    />
  </div>
{/if}


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
