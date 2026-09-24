<script>
  import { onMount, tick } from "svelte";
  import Toast from "./components/Toast.svelte";
  import KeyRevealModal from "./components/KeyRevealModal.svelte";
  import { toastStore } from "./stores/toastStore";
  import { matchRoute, sectionToPath } from "./routes";
  import { initUserKey, swSetKey, checkAdminStatus, updateUserName, registerUser, getVersion } from "./services/api";
  import { usingSw, getUserKey } from "./services/api/auth";
  import { showToast } from "./stores/toastStore";
  import { userPublicId as userPublicIdStore } from "./stores/userStore";
  import { pageTitle } from "./stores/pageTitle";
  import { navigate, internalLinkTarget } from "./utils/navigation";

  // Default titles; RelicViewer / SpaceViewer replace them with real names.
  const SECTION_TITLES = {
    new: "New relic",
    recent: "Recent relics",
    spaces: "Spaces",
    "space-view": "Space",
    "my-relics": "My relics",
    "my-bookmarks": "Bookmarks",
    admin: "Admin",
    relic: "Relic",
  };

  const NAV_ITEMS = [
    { section: "recent", label: "Recent", icon: "fa-clock", path: "/recent" },
    { section: "spaces", label: "Spaces", icon: "fa-layer-group", path: "/spaces", alsoActive: ["space-view"] },
    { section: "my-relics", label: "My Relics", icon: "fa-user", path: "/my-relics" },
    { section: "my-bookmarks", label: "Bookmarks", icon: "fa-bookmark", path: "/my-bookmarks" },
  ];

  let currentSection = null;
  let routeLoader = null;
  let routeProps = {};

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
  let mobileNavOpen = false;
  let mainEl;
  let lastPathname = null;

  $: navItems = isAdmin
    ? [...NAV_ITEMS, { section: "admin", label: "Admin", icon: "fa-shield-alt", path: "/admin" }]
    : NAV_ITEMS;
  $: isActive = (item) => currentSection === item.section || item.alsoActive?.includes(currentSection);
  $: document.title = $pageTitle ? `${$pageTitle} · Relic` : "Relic";

  function updateRouting() {
    const path = window.location.pathname;
    const urlParams = new URLSearchParams(window.location.search);

    console.log("[App] Route update - path:", path, "search:", urlParams.toString());

    const matched = matchRoute(path, urlParams);
    routeLoader = matched.loader;
    routeProps = matched.props;
    currentSection = matched.section;
    pageTitle.set(SECTION_TITLES[currentSection] || "");
    mobileNavOpen = false;
    showKeyDropdown = false;

    console.log(
      "[App] Routing result - section:",
      currentSection,
      "props:",
      routeProps
    );

    // On a real page change (not a query-only update such as a tag filter),
    // reset scroll and move focus to the content so screen readers follow.
    const pageChanged = lastPathname !== null && lastPathname !== path;
    lastPathname = path;
    if (pageChanged) {
      tick().then(() => {
        mainEl?.scrollTo(0, 0);
        mainEl?.focus({ preventScroll: true });
      });
    }
  }

  // Route same-origin links through the SPA instead of reloading the page.
  function handleLinkClick(event) {
    const path = internalLinkTarget(event);
    if (path === null) return;
    event.preventDefault();
    navigate(path);
  }

  function handleGlobalKeydown(event) {
    if (event.key !== "Escape") return;
    if (showKeyDropdown) showKeyDropdown = false;
    if (mobileNavOpen) mobileNavOpen = false;
  }

  // Initial routing on page load - call it before onMount to prevent flicker
  updateRouting();

  onMount(async () => {
    // Initialise SW vault and migrate key from localStorage if needed.
    // Returns the key only on first creation or migration — null for returning users.
    userKeyOnce = await initUserKey();
    if (userKeyOnce) showKeyReveal = true;

    // Fetch app version
    try {
      const response = await getVersion();
      appVersion = response.data.version;
    } catch (error) {
      console.error("[App] Failed to fetch version:", error);
      appVersion = "unknown";
    }

    // Register/Fetch user info (SW injects X-User-Key automatically)
    try {
        const userInfo = await registerUser();
        if (userInfo && userInfo.name) userName = userInfo.name;
        if (userInfo && userInfo.public_id) {
          userPublicId = userInfo.public_id;
          userPublicIdStore.set(userInfo.public_id);
        }
    } catch (e) {
        console.error("Failed to fetch user info", e);
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
      if (showKeyDropdown && !e.target.closest(".user-key-dropdown")) {
        showKeyDropdown = false;
      }
    }

    document.addEventListener("click", handleDocumentClick);
    document.addEventListener("click", handleLinkClick);

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

    return () => {
      window.removeEventListener("popstate", updateRouting);
      document.removeEventListener("click", handleDocumentClick);
      document.removeEventListener("click", handleLinkClick);
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
    navigate(sectionToPath(section));
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

  function handleFullWidthToggle(event) {
    if (currentSection === 'relic') {
        relicViewerFullWidth = event.detail.isFullWidth;
    } else if (currentSection === 'new') {
        relicFormFullWidth = event.detail.isFullWidth;
    }
  }
</script>

<svelte:window on:keydown={handleGlobalKeydown} />

<div class="h-screen overflow-hidden flex flex-col text-gray-900">
  <a
    href="#main-content"
    on:click|preventDefault={() => mainEl?.focus()}
    class="sr-only-focusable fixed left-2 top-2 z-[300] rounded bg-white px-3 py-2 text-sm font-medium text-brand-700 shadow"
  >
    Skip to content
  </a>

  <header class="relative z-40 bg-brand-600 text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-4 sm:px-6">
      <div class="flex items-center justify-between h-14">
        <!-- Logo and Brand -->
        <div class="flex items-center gap-3 flex-shrink-0">
          <a href="/recent" class="flex items-center hover:opacity-80 transition-opacity rounded" aria-label="Relic home">
            <span class="font-bold text-xl tracking-tight">
              RELIC <span class="font-light opacity-80">Bin</span>
            </span>
          </a>
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
        <nav aria-label="Main" class="hidden md:flex items-stretch self-stretch ml-auto">
          <a href="/" aria-current={currentSection === "new" ? "page" : undefined} class="nav-link {currentSection === 'new' ? 'active' : ''}">
            <i class="fas fa-plus mr-2" aria-hidden="true"></i>New Relic
          </a>
          {#each navItems as item (item.section)}
            <a
              href={item.path}
              aria-current={isActive(item) ? "page" : undefined}
              class="nav-link {isActive(item) ? 'active' : ''}"
            >
              <i class="fas {item.icon} mr-2" aria-hidden="true"></i>{item.label}
            </a>
          {/each}
        </nav>

        <div class="flex items-center gap-2 md:ml-2">

          <!-- Profile menu -->
          <div class="user-key-dropdown relative">
            <button
              on:click={() => (showKeyDropdown = !showKeyDropdown)}
              class="w-9 h-9 flex items-center justify-center rounded-full text-white/80 hover:text-white transition-colors"
              aria-label="Profile"
              aria-haspopup="true"
              aria-expanded={showKeyDropdown}
              aria-controls="profile-menu"
            >
              <i class="fas fa-user-circle text-lg" aria-hidden="true"></i>
            </button>

            {#if showKeyDropdown}
              <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
              <div
                id="profile-menu"
                class="absolute right-0 mt-2 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50"
                on:click={e => e.stopPropagation()}
              >
                <div class="p-3 border-b border-gray-200">
                  <p class="text-sm font-medium text-gray-900">Profile</p>
                </div>

                <div class="p-3 border-b border-gray-200">
                    <label for="profile-display-name" class="block text-xs font-medium text-gray-700 mb-1">Display name</label>
                    <div class="flex gap-2">
                        <input
                            id="profile-display-name"
                            type="text"
                            bind:value={userName}
                            placeholder="Anonymous"
                            on:keydown={(e) => e.key === "Enter" && saveUserName()}
                            class="flex-1 text-sm text-gray-900 border border-gray-300 rounded px-2 py-1 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                        />
                        <button
                            on:click={saveUserName}
                            disabled={isNameSaving}
                            class="btn-primary w-8 h-[30px] !p-0 flex-shrink-0"
                            aria-label="Save name"
                            title="Save name"
                        >
                            {#if isNameSaving}
                                <i class="fas fa-spinner fa-spin text-xs" aria-hidden="true"></i>
                            {:else}
                                <i class="fas fa-check text-xs" aria-hidden="true"></i>
                            {/if}
                        </button>
                    </div>
                    <p class="text-2xs text-gray-500 mt-1">Required for commenting</p>
                </div>

                <div class="p-3 border-b border-gray-200">
                    <div class="block text-xs font-medium text-gray-700 mb-1">Your public ID</div>
                    <div class="flex gap-2 items-center">
                        <span class="flex-1 text-sm font-mono text-gray-900 select-all break-all">
                            {userPublicId || '...'}
                        </span>
                        <button
                            on:click={() => navigator.clipboard.writeText(userPublicId).then(() => { showToast('Public ID copied', 'success'); showKeyDropdown = false; })}
                            class="btn-secondary w-8 h-[30px] !p-0 flex-shrink-0"
                            aria-label="Copy public ID"
                            title="Copy public ID"
                        >
                            <i class="fas fa-copy text-xs text-gray-600" aria-hidden="true"></i>
                        </button>
                    </div>
                    <p class="text-2xs text-gray-500 mt-1">Share this ID so others can add you to spaces</p>
                </div>

                <div class="py-2">
                  <label
                    class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 focus-within:bg-gray-50 focus-within:ring-2 focus-within:ring-inset focus-within:ring-brand-500 transition-colors cursor-pointer flex items-center"
                  >
                    <i class="fas fa-upload w-5 text-gray-500" aria-hidden="true"></i>
                    <span>Import key</span>
                    <input
                      type="file"
                      accept=".txt"
                      on:change={uploadUserKey}
                      class="sr-only"
                    />
                  </label>
                </div>

                <div class="px-4 py-3 bg-gray-50 rounded-b-lg">
                  <p class="text-xs text-gray-500">
                    <i class="fas fa-info-circle mr-1" aria-hidden="true"></i>
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

          <!-- Mobile menu toggle -->
          <button
            class="md:hidden w-9 h-9 flex items-center justify-center rounded text-white/80 hover:text-white hover:bg-white/10"
            on:click={() => (mobileNavOpen = !mobileNavOpen)}
            aria-label={mobileNavOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileNavOpen}
            aria-controls="mobile-nav"
          >
            <i class="fas {mobileNavOpen ? 'fa-times' : 'fa-bars'}" aria-hidden="true"></i>
          </button>
        </div>
      </div>
    </div>

    {#if mobileNavOpen}
      <nav id="mobile-nav" aria-label="Main" class="md:hidden absolute inset-x-0 top-full bg-white border-b border-gray-200 shadow-lg">
        <ul class="px-2 py-2">
          <li>
            <a href="/" class="mobile-nav-link {currentSection === 'new' ? 'active' : ''}" aria-current={currentSection === "new" ? "page" : undefined}>
              <i class="fas fa-plus w-5 text-center" aria-hidden="true"></i>New Relic
            </a>
          </li>
          {#each navItems as item (item.section)}
            <li>
              <a href={item.path} class="mobile-nav-link {isActive(item) ? 'active' : ''}" aria-current={isActive(item) ? "page" : undefined}>
                <i class="fas {item.icon} w-5 text-center" aria-hidden="true"></i>{item.label}
              </a>
            </li>
          {/each}
        </ul>
      </nav>
    {/if}
  </header>

  <!-- Main Content -->
  <main id="main-content" bind:this={mainEl} tabindex="-1" class="flex-1 overflow-auto flex flex-col focus:outline-none">
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
              class="btn-primary mt-4"
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


<style global>
  :global(body) {
    margin: 0;
    padding: 0;
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

  /* MAAS-style inputs */
  :global(.maas-input) {
    border: 1px solid #aea79f;
    border-radius: 2px;
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  :global(.maas-input:focus) {
    border-color: theme('colors.brand.500');
    outline: none;
    box-shadow: 0 0 0 1px theme('colors.brand.500');
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

  /* Header navigation: underline tab for the active page (no pill overlay). */
  .nav-link {
    position: relative;
    display: flex;
    align-items: center;
    padding: 0 1rem;
    font-size: 13.5px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.7);
    transition: color 0.15s;
  }

  .nav-link::after {
    content: "";
    position: absolute;
    left: 0.75rem;
    right: 0.75rem;
    bottom: 0;
    height: 3px;
    border-radius: 3px 3px 0 0;
    background-color: transparent;
    transition: background-color 0.15s;
  }

  .nav-link:hover {
    color: white;
  }

  .nav-link:hover::after {
    background-color: rgba(255, 255, 255, 0.3);
  }

  .nav-link.active {
    color: white;
  }

  .nav-link.active::after {
    background-color: white;
  }

  .mobile-nav-link {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.625rem 0.75rem;
    border-radius: 0.375rem;
    font-size: 15px;
    font-weight: 500;
    color: theme('colors.gray.700');
  }

  .mobile-nav-link:hover {
    background-color: theme('colors.gray.50');
  }

  .mobile-nav-link.active {
    color: theme('colors.brand.700');
    background-color: theme('colors.brand.50');
  }
</style>
