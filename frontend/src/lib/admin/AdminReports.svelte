<script>
  // Admin · Reports: content people flagged. Each report is dismissed or its relic deleted,
  // from the row or the inspector, with the confirmation inline.
  import { untrack } from "svelte";
  import Icon from "../ui/Icon.svelte";
  import DataList from "../ui/DataList.svelte";
  import PageBar from "../shell/PageBar.svelte";
  import Workbench from "../shell/Workbench.svelte";
  import ReportInspector from "./ReportInspector.svelte";
  import { PagedFeed } from "../data/PagedFeed.svelte.js";
  import { InspectorPanel } from "../shell/inspectorPanel.svelte.js";
  import { layout } from "../shell/layout";
  import { relicOwner, refreshAdminStats } from "./adminState";
  import { getAdminReports } from "../../services/api";
  import { navigate } from "../../utils/navigation";
  import { shortDate, clockTime } from "../relics/format";

  const COLUMNS = [
    { key: "relic", label: "Relic", width: "minmax(0, 1fr)" },
    { key: "owner", label: "Owner", width: "minmax(0, 140px)", hide: "narrow" },
    { key: "reason", label: "Reason", width: "minmax(0, 1.4fr)", sort: "asc", hide: "phone" },
    { key: "created_at", label: "Reported", width: "110px", sort: "desc", num: true },
  ];

  const feed = new PagedFeed((p) => getAdminReports(p.limit, p.offset, p.sort_by, p.sort_order).then((r) => r.data), { rows: "reports" });
  const panel = new InspectorPanel();
  let sort = $state({ key: "created_at", dir: "desc" });
  let selectedId = $state(null);
  let confirm = $state(null);

  $effect(() => {
    const params = { sort_by: sort.key, sort_order: sort.dir };
    untrack(() => feed.reset(params));
  });

  const selected = $derived(feed.items.find((r) => r.id === selectedId) ?? null);
  $effect(() => {
    if ($layout.dock && feed.items.length && !selected) selectedId = feed.items[0].id;
  });

  function onSort(key) {
    const first = COLUMNS.find((c) => c.key === key).sort;
    sort = sort.key === key ? { key, dir: sort.dir === "asc" ? "desc" : "asc" } : { key, dir: first };
  }

  function select(report) {
    selectedId = report.id;
    confirm = null;
    if (!$layout.dock) panel.show(false);
  }

  function ask(what) {
    return (report) => {
      selectedId = report.id;
      panel.show($layout.dock);
      confirm = { what, n: (confirm?.n ?? 0) + 1 };
    };
  }

  function showOwner(report) {
    relicOwner.set({ id: report.relic_owner_id, publicId: report.relic_owner_public_id, label: report.relic_owner_name || "—" });
    navigate("/admin/relics");
  }

  function onDismissed(report) {
    const i = feed.items.findIndex((r) => r.id === report.id);
    feed.remove(report.id);
    selectedId = feed.items[Math.min(i, feed.items.length - 1)]?.id ?? null;
    refreshAdminStats();
  }

  // Deleting the relic removes its reports too; reload to show what's left.
  async function onRelicDeleted() {
    await feed.reload();
    refreshAdminStats();
  }

  const actions = [
    { icon: "eye", title: "Open relic", run: (r) => navigate(`/${r.relic_id}`) },
    { icon: "check", title: "Dismiss report", run: ask("dismiss") },
    { icon: "trash", title: "Delete relic", run: ask("delete") },
  ];
</script>

<Workbench {panel} hasSelection={!!selected} label="Reports" phoneDrawer>
  {#snippet pagebar({ inspectorOpen, toggleInspector })}
    <PageBar title="Reports" count={feed.total} {inspectorOpen} ontoggleinspector={toggleInspector}>
      {#snippet actions()}
        <button class="r-btn r-btn-ghost r-btn-icon" onclick={() => feed.reload()} title="Refresh" aria-label="Refresh"><Icon name="history" /></button>
      {/snippet}
    </PageBar>
  {/snippet}

  <DataList
    label="Reports"
    rows={feed.items}
    columns={COLUMNS}
    loading={feed.loading}
    hasMore={feed.hasMore}
    {selectedId}
    {sort}
    {actions}
    emptyText="No reports waiting. Nothing to review."
    onsort={onSort}
    onselect={select}
    onopen={(r) => navigate(`/${r.relic_id}`)}
    onloadmore={() => feed.more()}
  >
    {#snippet cell(report, c)}
      {#if c.key === "relic"}
        <Icon name="flag" size={13} class="report-flag" />
        <a class="report-relic" href="/{report.relic_id}" tabindex="-1" title={report.relic_name}>{report.relic_name || "Untitled"}</a>
      {:else if c.key === "owner"}
        {#if report.relic_owner_id}
          <button class="report-owner" tabindex="-1" onclick={() => showOwner(report)} title="Show their relics">{report.relic_owner_name || "—"}</button>
        {:else}<span class="report-anon">anonymous</span>{/if}
      {:else if c.key === "reason"}
        <span class="report-reason" title={report.reason}>{report.reason}</span>
      {:else if c.key === "created_at"}
        <span title={new Date(report.created_at).toLocaleString()}>{shortDate(report.created_at)} {clockTime(report.created_at)}</span>
      {/if}
    {/snippet}
  </DataList>

  {#snippet inspector({ close })}
    <ReportInspector report={selected} {confirm} onowner={showOwner} ondismissed={onDismissed} onrelicdeleted={onRelicDeleted} onclose={close} />
  {/snippet}

  {#snippet status()}
    <span><Icon name="flag" />{feed.total == null ? "…" : `${feed.total.toLocaleString("en-US")} ${feed.total === 1 ? "report" : "reports"}`}</span>
    {#if feed.error}<span class="status-error">Couldn’t load. <button class="r-link" onclick={() => feed.reload()}>Retry</button></span>{/if}
    <span class="r-gap"></span>
    <span class="r-hints"><span><kbd class="r-kbd">↵</kbd>open relic</span><span><kbd class="r-kbd">]</kbd>inspector</span></span>
  {/snippet}
</Workbench>

<style>
  :global(.report-flag) {
    flex: none;
    color: var(--warning);
  }
  .report-relic {
    min-width: 0;
    overflow: hidden;
    color: var(--ink);
    text-overflow: ellipsis;
    text-decoration: none;
  }
  .report-relic:hover {
    color: var(--accent);
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  .report-owner {
    min-width: 0;
    overflow: hidden;
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink-3);
    font: 12.5px var(--font-mono);
    text-overflow: ellipsis;
    cursor: pointer;
  }
  .report-owner:hover {
    color: var(--accent);
    text-decoration: underline;
  }
  .report-anon {
    color: var(--line-2);
    font: 12.5px var(--font-mono);
  }
  .report-reason {
    overflow: hidden;
    color: var(--ink-2);
    text-overflow: ellipsis;
  }
</style>
