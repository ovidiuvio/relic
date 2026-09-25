<script>
  import { onMount, tick } from "svelte";
  import Toasts from "./lib/ui/Toasts.svelte";
  import KeyRevealModal from "./components/KeyRevealModal.svelte";
  import { toastStore } from "./stores/toastStore";
  import { matchRoute, sectionToPath } from "./routes";
  import { initUserKey } from "./services/api";
  import { pageTitle } from "./stores/pageTitle";
  import { loadSession } from "./stores/session";
  import NavBar from "./lib/shell/NavBar.svelte";
  import BottomTabs from "./lib/shell/BottomTabs.svelte";
  import Sidebar from "./lib/shell/Sidebar.svelte";
  import { layout } from "./lib/shell/layout";
  import { navigate, internalLinkTarget } from "./utils/navigation";

  // Default titles; the relic viewer and space page replace them with real names.
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

  let currentSection = null;
  let routeLoader = null;
  let routeProps = {};
  // Rebuilt pages draw their own frame (page bar, list, inspector) edge to edge;
  // legacy pages still sit in the centred content column until they are rebuilt.
  let fullBleed = false;

  let relicViewerFullWidth = false;
  let relicFormFullWidth = false;
  let userKeyOnce = null;
  let showKeyReveal = false;
  let mainEl;
  let lastPathname = null;

  $: wideLegacy = (currentSection === "relic" && relicViewerFullWidth) || (currentSection === "new" && relicFormFullWidth);
  $: fillsHeight = currentSection === "relic" || currentSection === "new";
  $: contentClass = fullBleed
    ? "flex-1 min-h-0 flex flex-col"
    : `w-full ${wideLegacy ? "" : "max-w-7xl mx-auto"} py-6 px-4 sm:px-6 lg:px-8 transition-all duration-300${fillsHeight ? " flex-1 flex flex-col min-h-0" : ""}`;

  $: document.title = $pageTitle ? `${$pageTitle} · Relic` : "Relic";

  function updateRouting() {
    const path = window.location.pathname;
    const urlParams = new URLSearchParams(window.location.search);

    console.log("[App] Route update - path:", path, "search:", urlParams.toString());

    const matched = matchRoute(path, urlParams);
    routeLoader = matched.loader;
    routeProps = matched.props;
    fullBleed = !!matched.fullBleed;
    currentSection = matched.section;
    pageTitle.set(SECTION_TITLES[currentSection] || "");

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

  // Initial routing on page load - call it before onMount to prevent flicker
  updateRouting();

  onMount(async () => {
    // Initialise SW vault and migrate key from localStorage if needed.
    // Returns the key only on first creation or migration — null for returning users.
    userKeyOnce = await initUserKey();
    if (userKeyOnce) showKeyReveal = true;

    // Who is using Relic: name, public ID, admin status, version. Needs the key above;
    // not awaited, so link handling and back/forward don't wait on three API calls.
    loadSession();

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
      document.removeEventListener("click", handleLinkClick);
    };
  });

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

  function handleFullWidthToggle(event) {
    if (currentSection === 'relic') {
        relicViewerFullWidth = event.detail.isFullWidth;
    } else if (currentSection === 'new') {
        relicFormFullWidth = event.detail.isFullWidth;
    }
  }
</script>

<div class="h-screen overflow-hidden flex flex-col text-gray-900">
  <a
    href="#main-content"
    on:click|preventDefault={() => mainEl?.focus()}
    class="sr-only-focusable fixed left-2 top-2 z-[300] rounded bg-white px-3 py-2 text-sm font-medium text-brand-700 shadow"
  >
    Skip to content
  </a>

  <NavBar section={currentSection} {routeProps} />

  <div class="flex-1 min-h-0 flex">
  {#if $layout.rail}
    <Sidebar section={currentSection} {routeProps} />
  {/if}

  <!-- Main Content -->
  <main id="main-content" bind:this={mainEl} tabindex="-1" class="flex-1 min-w-0 flex flex-col focus:outline-none {fullBleed ? 'overflow-hidden' : 'overflow-auto'}">
    <div class={contentClass}>
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
  </div>

  <BottomTabs section={currentSection} />

  <Toasts />
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

</style>
