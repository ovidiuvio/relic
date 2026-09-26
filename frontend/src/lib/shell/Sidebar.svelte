<script>
  // Wide-screen navigation (≥1600px): Relics and Spaces groups, each heading carrying its
  // create action, your spaces, the searches you pinned, and Admin at the foot. Below 1600px the
  // navbar tabs do this job (and pinned searches are in the search bar's panel).
  import Icon from "../ui/Icon.svelte";
  import { navigate } from "../../utils/navigation";
  import { session } from "../../stores/session";
  import { sidebarData, refreshSidebar } from "./sidebarData";
  import { compactNumber } from "../relics/format";
  import { searchHistory } from "../search/history.svelte.js";

  let { section, routeProps = {} } = $props();

  // Refresh counts when the page changes: a new relic, bookmark or space shows up on return.
  $effect(() => {
    section;
    refreshSidebar();
  });

  const counts = $derived($sidebarData.counts);

  searchHistory.load();
  const here = $derived.by(() => {
    routeProps;
    return location.pathname + location.search;
  });

  const relicLinks = $derived([
    { section: "recent", path: "/recent", icon: "clock", label: "Recent", count: counts.recent },
    { section: "my-relics", path: "/my-relics", icon: "user", label: "My relics", count: counts.mine },
    { section: "my-bookmarks", path: "/my-bookmarks", icon: "bookmark", label: "Bookmarks", count: counts.bookmarks },
  ]);

  // A stable colour per space, from the type palette, so a space is recognisable at a glance.
  const DOTS = ["code", "doc", "data", "archive", "image", "web", "text"];
  function dotFor(id) {
    let h = 0;
    for (const c of id) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    return `var(--type-${DOTS[h % DOTS.length]})`;
  }

  const current = (s) => (section === s ? "page" : undefined);
</script>

<aside class="sidebar" aria-label="Sections">
  <nav class="sb-group" aria-labelledby="sb-relics">
    <div class="sb-head">
      <span id="sb-relics">Relics</span>
      <button class="sb-add" onclick={() => navigate("/")} title="New relic" aria-label="New relic">
        <Icon name="plus" />
      </button>
    </div>
    {#each relicLinks as link (link.section)}
      <a href={link.path} aria-current={current(link.section)}>
        <Icon name={link.icon} />{link.label}<em>{compactNumber(link.count)}</em>
      </a>
    {/each}
  </nav>

  <nav class="sb-group" aria-labelledby="sb-spaces">
    <div class="sb-head">
      <span id="sb-spaces">Spaces</span>
      <button class="sb-add" onclick={() => navigate("/spaces?create=1")} title="New space" aria-label="New space">
        <Icon name="plus" />
      </button>
    </div>
    <a href="/spaces" aria-current={current("spaces")}>
      <Icon name="layers" />All spaces<em>{compactNumber(counts.spaces)}</em>
    </a>
    {#each $sidebarData.spaces as space (space.id)}
      <a
        class="sb-sub"
        href="/spaces/{space.id}"
        aria-current={section === "space-view" && routeProps.spaceId === space.id ? "page" : undefined}
        title={space.name}
      >
        <span class="sb-dot" style:background={dotFor(space.id)}></span>
        <span class="sb-name">{space.name}</span>
        {#if space.visibility === "private"}<Icon name="lock" size={12} />{/if}
        <em>{compactNumber(space.relic_count)}</em>
      </a>
    {/each}
  </nav>

  {#if searchHistory.pinned?.length}
    <nav class="sb-group" aria-labelledby="sb-searches">
      <div class="sb-head"><span id="sb-searches">Searches</span></div>
      {#each searchHistory.pinned as saved (saved.id)}
        <a class="sb-sub" href={saved.path} aria-current={here === saved.path ? "page" : undefined} title={saved.name ? `${saved.name}: ${saved.query}` : saved.query}>
          <Icon name="pin" size={12} />
          <span class="sb-name">{saved.name || saved.query}</span>
        </a>
      {/each}
    </nav>
  {/if}

  {#if $session.isAdmin}
    <div class="sb-foot">
      <a href="/admin" aria-current={current("admin")}><Icon name="shield" />Admin</a>
    </div>
  {/if}
</aside>

<style>
  .sidebar {
    flex: none;
    display: flex;
    flex-direction: column;
    width: var(--rail-w);
    min-height: 0;
    overflow-y: auto;
    padding: var(--space-2\.5) 0 0;
    border-right: 1px solid var(--line);
    background: var(--subtle);
  }
  .sb-group {
    display: grid;
    gap: 1px;
    padding: var(--space-1) var(--space-2) var(--space-3);
  }
  .sb-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 26px;
    padding: 0 var(--space-2);
    color: var(--ink-3);
    font: 700 11px var(--font-mono);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .sb-add {
    display: grid;
    place-items: center;
    width: 22px;
    height: 22px;
    margin-right: -4px;
    border: 0;
    border-radius: var(--radius-xs);
    background: none;
    color: var(--ink-2);
    cursor: pointer;
  }
  .sb-add :global(.r-icon) {
    width: 15px;
    height: 15px;
  }
  .sb-add:hover {
    background: var(--hover);
    color: var(--accent);
  }
  .sidebar a {
    display: flex;
    align-items: center;
    gap: 9px;
    height: 30px;
    padding: 0 var(--space-2);
    border-radius: var(--radius-sm);
    color: var(--ink-2);
    font-weight: 500;
    text-decoration: none;
  }
  .sidebar a :global(.r-icon) {
    width: 15px;
    height: 15px;
    color: var(--ink-3);
  }
  .sidebar a:hover {
    background: var(--hover);
  }
  .sidebar a[aria-current="page"] {
    background: var(--accent-soft);
    color: var(--accent);
  }
  .sidebar a[aria-current="page"] :global(.r-icon) {
    color: var(--accent);
  }
  .sidebar em {
    margin-left: auto;
    color: var(--ink-3);
    font: 12px var(--font-mono);
    font-style: normal;
  }
  .sidebar .sb-sub {
    height: 26px;
    font-weight: 400;
  }
  .sb-sub :global(.r-icon) {
    width: 12px;
    height: 12px;
  }
  .sb-dot {
    flex: none;
    width: 8px;
    height: 8px;
    margin: 0 3px;
    border-radius: 2px;
  }
  .sb-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sb-foot {
    margin-top: auto;
    padding: var(--space-2);
    border-top: 1px solid var(--line);
  }
</style>
