<script>
  // Admin · Users: everyone registered, searchable from the navbar (?search=) and sortable.
  // The inspector holds their key, admin rights and Delete.
  import { untrack } from "svelte";
  import Icon from "../ui/Icon.svelte";
  import DataList from "../ui/DataList.svelte";
  import PageBar from "../shell/PageBar.svelte";
  import Workbench from "../shell/Workbench.svelte";
  import UserInspector from "./UserInspector.svelte";
  import { PagedFeed } from "../data/PagedFeed.svelte.js";
  import { InspectorPanel } from "../shell/inspectorPanel.svelte.js";
  import { layout } from "../shell/layout";
  import { filterUrl } from "../relics/filters";
  import { relicOwner, refreshAdminStats } from "./adminState";
  import { getAdminUsers } from "../../services/api";
  import { copyToClipboard } from "../../services/relicActions";
  import { navigate } from "../../utils/navigation";
  import { shortDate, compactNumber } from "../relics/format";

  let { search = null } = $props();

  const PATH = "/admin/users";
  const COLUMNS = [
    { key: "name", label: "Name", width: "minmax(0, 1fr)", sort: "asc" },
    { key: "public_id", label: "Public ID", width: "minmax(0, 220px)", mono: true, hide: "phone" },
    { key: "role", label: "Role", width: "96px" },
    { key: "relic_count", label: "Relics", width: "64px", sort: "desc", num: true },
    { key: "created_at", label: "Joined", width: "90px", sort: "desc", num: true, hide: "narrow" },
  ];

  const feed = new PagedFeed((p) => getAdminUsers(p.limit, p.offset, p.sort_by, p.sort_order, p.search).then((r) => r.data), { rows: "users" });
  const panel = new InspectorPanel();
  let sort = $state({ key: "created_at", dir: "desc" });
  let selectedId = $state(null);
  let confirm = $state(null);

  $effect(() => {
    const params = { sort_by: sort.key, sort_order: sort.dir, search: search || null };
    untrack(() => feed.reset(params));
  });

  const selected = $derived(feed.items.find((u) => u.id === selectedId) ?? null);
  $effect(() => {
    if ($layout.dock && feed.items.length && !selected) selectedId = feed.items[0].id;
  });

  function onSort(key) {
    const first = COLUMNS.find((c) => c.key === key).sort;
    sort = sort.key === key ? { key, dir: sort.dir === "asc" ? "desc" : "asc" } : { key, dir: first };
  }

  function select(user) {
    selectedId = user.id;
    confirm = null;
    if (!$layout.dock) panel.show(false);
  }

  function showRelics(user) {
    relicOwner.set({ id: user.id, publicId: user.public_id, label: user.name || "—" });
    navigate("/admin/relics");
  }

  function askDelete(user) {
    selectedId = user.id;
    panel.show($layout.dock);
    confirm = { n: (confirm?.n ?? 0) + 1 };
  }

  function onDeleted(user) {
    const i = feed.items.findIndex((u) => u.id === user.id);
    feed.remove(user.id);
    selectedId = feed.items[Math.min(i, feed.items.length - 1)]?.id ?? null;
    refreshAdminStats();
  }

  const actions = [
    { icon: "file", title: "View relics", run: showRelics },
    { icon: "copy", title: "Copy public ID", run: (u) => copyToClipboard(u.public_id, "Public ID copied"), when: (u) => !!u.public_id },
    { icon: "trash", title: "Delete user", run: askDelete, when: (u) => !u.is_admin },
  ];
</script>

<Workbench {panel} hasSelection={!!selected} label="Users" phoneDrawer>
  {#snippet pagebar({ inspectorOpen, toggleInspector })}
    <PageBar title="Users" count={feed.total} {inspectorOpen} ontoggleinspector={toggleInspector}>
      {#snippet filters()}
        {#if search}
          <span class="r-chip-filter">{search}<button onclick={() => navigate(filterUrl(PATH, { search: null }))} aria-label="Clear search"><Icon name="x" /></button></span>
        {/if}
      {/snippet}
      {#snippet actions()}
        <button class="r-btn r-btn-ghost r-btn-icon" onclick={() => feed.reload()} title="Refresh" aria-label="Refresh"><Icon name="history" /></button>
      {/snippet}
    </PageBar>
  {/snippet}

  <DataList
    label="Users"
    rows={feed.items}
    columns={COLUMNS}
    loading={feed.loading}
    hasMore={feed.hasMore}
    {selectedId}
    {sort}
    {actions}
    emptyText={search ? "No users match your search." : "No users yet."}
    emptyAction={search ? { href: PATH, label: "Clear search" } : null}
    onsort={onSort}
    onselect={select}
    onopen={showRelics}
    onloadmore={() => feed.more()}
  >
    {#snippet cell(user, c)}
      {#if c.key === "name"}
        <span class="user-name" class:is-unnamed={!user.name}>{user.name || "—"}</span>
      {:else if c.key === "public_id"}
        {user.public_id || "—"}
      {:else if c.key === "role"}
        {#if user.is_super_admin}<span class="r-pill r-pill-accent role" title="Set with ADMIN_USER_IDS"><Icon name="shield" />super</span>
        {:else if user.is_admin}<span class="r-pill r-pill-accent role"><Icon name="shield" />admin</span>
        {:else}<span class="role-user">user</span>{/if}
      {:else if c.key === "relic_count"}
        {compactNumber(user.relic_count)}
      {:else if c.key === "created_at"}
        {shortDate(user.created_at)}
      {/if}
    {/snippet}
  </DataList>

  {#snippet inspector({ close })}
    <UserInspector
      user={selected}
      {confirm}
      onrelics={showRelics}
      onchanged={(u) => (feed.update(u), refreshAdminStats())}
      ondeleted={onDeleted}
      onclose={close}
    />
  {/snippet}

  {#snippet status()}
    <span><Icon name="users" />{feed.total == null ? "…" : `${feed.total.toLocaleString("en-US")} ${feed.total === 1 ? "user" : "users"}`}</span>
    <span>{feed.items.length.toLocaleString("en-US")} loaded</span>
    {#if feed.error}<span class="status-error">Couldn’t load more. <button class="r-link" onclick={() => feed.reload()}>Retry</button></span>{/if}
    <span class="r-gap"></span>
    <span class="r-hints"><span><kbd class="r-kbd">/</kbd>search</span><span><kbd class="r-kbd">↵</kbd>their relics</span><span><kbd class="r-kbd">]</kbd>inspector</span></span>
  {/snippet}
</Workbench>

<style>
  .user-name {
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .user-name.is-unnamed {
    color: var(--ink-3);
  }
  .role {
    height: 18px;
    font-size: 11.5px;
  }
  .role-user {
    color: var(--ink-3);
    font-size: 12px;
  }
</style>
