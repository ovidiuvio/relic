<script>
  // The aubergine bar on every page. Its groups sit over the columns they control:
  //   below 1600px: wordmark, tabs and search over the list; Admin, New relic, profile on the right.
  //   from 1600px:  wordmark over the sidebar, search over the list, profile on the right
  //                 (tabs, New relic and Admin live in the sidebar).
  import Icon from "../ui/Icon.svelte";
  import RelicMark from "../ui/RelicMark.svelte";
  import NavSearch from "./NavSearch.svelte";
  import ProfileMenu from "./ProfileMenu.svelte";
  import { NAV_ITEMS, ADMIN_ITEM, isActive } from "./navItems";
  import { layout } from "./layout";
  import { session, initials } from "../../stores/session";
  import { appVersion, loadVersion, REPO_URL } from "./appVersion";

  let { section, routeProps = {} } = $props();

  loadVersion();
  // "1.4.0" reads as v1.4.0; a build label such as "dev" or a commit hash stays as it is.
  const versionLabel = $derived(/^\d+\.\d+/.test($appVersion ?? "") ? `v${$appVersion}` : $appVersion);

  // Where this version lives on GitHub: its release, or its commit when the server reports a hash.
  const versionUrl = $derived.by(() => {
    const v = $appVersion ?? "";
    if (/^\d+\.\d+/.test(v)) return `${REPO_URL}/releases/tag/v${v}`;
    if (/^[0-9a-f]{7,40}$/.test(v)) return `${REPO_URL}/commit/${v}`;
    return null;
  });

  let profileOpen = $state(false);
  let profileEl = $state();

  // A new page closes the profile.
  $effect(() => {
    section;
    profileOpen = false;
  });

  function onWindowClick(event) {
    if (profileOpen && !profileEl?.contains(event.target)) profileOpen = false;
  }

  function onWindowKeydown(event) {
    if (event.key === "Escape" && profileOpen) profileOpen = false;
  }
</script>

<svelte:window onclick={onWindowClick} onkeydown={onWindowKeydown} />

<header class="r-nav app-nav" class:has-rail={$layout.rail}>
  <div class="nav-brand">
    <a class="r-wordmark" href="/recent" aria-label="Relic, recent relics">
      <RelicMark /><span class="wordmark-text">Relic</span>
    </a>
  </div>

  <div class="nav-main">
    {#if !$layout.rail}
      <nav class="r-nav-links" aria-label="Main">
        {#each NAV_ITEMS as item (item.section)}
          <a href={item.path} aria-current={isActive(item, section) ? "page" : undefined}>
            <Icon name={item.icon} />{item.label}
          </a>
        {/each}
      </nav>
    {/if}
    <NavSearch {section} {routeProps} />
  </div>

  <div class="nav-end">
    <div class="nav-meta">
      {#if $appVersion}
        {#if versionUrl}
          <a class="nav-ver" href={versionUrl} target="_blank" rel="noopener" title="This version on GitHub">{versionLabel}</a>
        {:else}
          <span class="nav-ver" title="Relic version">{versionLabel}</span>
        {/if}
      {/if}
      <a href={REPO_URL} target="_blank" rel="noopener" title="Relic on GitHub" aria-label="Relic on GitHub"><Icon name="github" /></a>
      <a href="/about" aria-current={section === "about" ? "page" : undefined}>About</a>
    </div>
    {#if !$layout.rail}
      {#if $session.isAdmin}
        <nav class="r-nav-links" aria-label="Administration">
          <a href={ADMIN_ITEM.path} aria-current={isActive(ADMIN_ITEM, section) ? "page" : undefined} title={ADMIN_ITEM.label}>
            <Icon name={ADMIN_ITEM.icon} /><span class="wide-label">{ADMIN_ITEM.label}</span>
          </a>
        </nav>
      {/if}
      <a class="r-btn r-nav-new" href="/" aria-current={section === "new" ? "page" : undefined} title="New relic">
        <Icon name="plus" /><span class="wide-label">New relic</span>
      </a>
    {/if}

    <div class="profile-anchor" bind:this={profileEl}>
      <button
        class="r-nav-avatar"
        onclick={() => (profileOpen = !profileOpen)}
        aria-label="Profile"
        aria-expanded={profileOpen}
        aria-controls="profile-menu"
        title={$session.name || "Profile"}
      >
        {#if $session.name}{initials($session.name)}{:else}<Icon name="user" />{/if}
      </button>
      {#if profileOpen}
        <ProfileMenu onclose={() => (profileOpen = false)} />
      {/if}
    </div>
  </div>
</header>

<style>
  .app-nav {
    position: relative;
    z-index: 40;
    flex: none;
    gap: 0;
    padding: 0;
  }
  .nav-brand {
    flex: none;
    display: flex;
    align-items: center;
    align-self: stretch;
    padding: 0 var(--space-4) 0 var(--space-5);
  }
  .nav-main {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    align-self: stretch;
    gap: var(--space-4);
  }
  .nav-end {
    flex: none;
    display: flex;
    align-items: center;
    align-self: stretch;
    gap: var(--space-3);
    padding: 0 var(--space-3\.5) 0 var(--space-4);
  }
  .app-nav :global(.r-nav-search) {
    margin-left: 0;
  }
  .r-nav-links a :global(.r-icon) {
    width: 15px;
    height: 15px;
  }
  /* Quiet links for wide screens, where the bar has room to spare. */
  .nav-meta {
    display: none;
    align-items: center;
    gap: var(--space-3);
    margin-right: var(--space-2);
    color: var(--nav-ink-2);
    font-size: 12.5px;
  }
  .nav-meta a {
    display: flex;
    align-items: center;
    color: inherit;
    text-decoration: none;
  }
  .nav-meta a:hover,
  .nav-meta a[aria-current="page"] {
    color: var(--on-accent);
  }
  .nav-meta .r-icon {
    width: 16px;
    height: 16px;
  }
  .nav-ver {
    font-family: var(--font-mono);
  }
  span.nav-ver {
    cursor: default;
  }
  @media (min-width: 1440px) {
    .nav-meta {
      display: flex;
    }
  }
  .profile-anchor {
    position: relative;
    flex: none;
  }
  .r-nav-avatar {
    border: 0;
    cursor: pointer;
  }
  .r-nav-new {
    border: 0;
  }

  /* From 1600px the wordmark takes the sidebar's width, so search starts at the list's edge. */
  .has-rail .nav-brand {
    width: var(--rail-w);
  }
  .has-rail .nav-main {
    padding: 0 var(--space-4);
  }
  .has-rail .nav-main :global(.r-nav-search),
  .has-rail .nav-main :global(.r-nav-search:focus-within) {
    width: min(100%, 720px);
  }

  /* Narrower desktops: shorter search, then icon-only New relic and Admin. */
  @media (max-width: 1180px) {
    .app-nav :global(.r-nav-search) {
      width: 240px;
    }
    .app-nav :global(.r-nav-search:focus-within) {
      width: 340px;
    }
  }
  @media (max-width: 1000px) {
    .wide-label {
      display: none;
    }
    .r-nav-new {
      width: var(--field);
      padding: 0;
    }
  }

  /* Phones: sections move to the bottom tab bar; search takes the free width. */
  @media (max-width: 767px) {
    .nav-brand {
      padding: 0 var(--space-2\.5) 0 var(--space-3\.5);
    }
    .nav-end {
      gap: var(--space-2\.5);
      padding: 0 var(--space-2\.5);
    }
    .r-nav-links,
    .wordmark-text {
      display: none;
    }
    .app-nav :global(.r-nav-search),
    .app-nav :global(.r-nav-search:focus-within) {
      flex: 1;
      width: auto;
    }
    .app-nav :global(.r-nav-scope),
    .app-nav :global(.r-nav-search .r-kbd) {
      display: none;
    }
  }
</style>
