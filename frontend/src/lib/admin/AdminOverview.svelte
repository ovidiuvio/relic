<script>
  // Admin · Overview: the instance at a glance, in the same frame as the other sections.
  // The list holds Health (scheduler, last backup, reports: a dot, the state in words, and a link
  // to the section that acts on it) and Instance (the totals with their breakdowns). The
  // inspector column holds recent activity: the latest job runs and reports.
  import Icon from "../ui/Icon.svelte";
  import PageBar from "../shell/PageBar.svelte";
  import Workbench from "../shell/Workbench.svelte";
  import InsSection from "../relics/inspector/InsSection.svelte";
  import { InspectorPanel } from "../shell/inspectorPanel.svelte.js";
  import { adminStats, lastBackup, refreshAdminStats, refreshLastBackup, backupTime } from "./adminState";
  import { runStatus } from "./jobs";
  import { getAdminJobs, getAdminReports } from "../../services/api";
  import { formatBytes } from "../../services/typeUtils";
  import { relativeTime } from "../relics/format";

  const panel = new InspectorPanel();
  let scheduler = $state(null); // { running, jobs, paused }
  let runs = $state.raw([]);
  let reports = $state.raw([]);
  let refreshing = $state(false);

  async function loadActivity() {
    const [jobsRes, reportsRes] = await Promise.allSettled([getAdminJobs(), getAdminReports(6, 0)]);
    if (jobsRes.status === "fulfilled") {
      const d = jobsRes.value.data;
      scheduler = { running: !!d.running, jobs: d.jobs?.length ?? 0, paused: d.jobs?.filter((j) => j.paused).length ?? 0 };
      runs = (d.history || []).slice(-8).reverse();
    }
    if (reportsRes.status === "fulfilled") reports = reportsRes.value.data.reports || [];
  }
  loadActivity();

  async function refresh() {
    refreshing = true;
    await Promise.all([refreshAdminStats(), refreshLastBackup(), loadActivity()]);
    refreshing = false;
  }

  const s = $derived($adminStats);
  const n = (v) => (v ?? 0).toLocaleString("en-US");
  const plural = (v, one, many = `${one}s`) => `${n(v)} ${v === 1 ? one : many}`;
  // A backup older than two days is worth a look.
  const backupStale = $derived(!!$lastBackup && Date.now() - new Date(backupTime($lastBackup)) > 2 * 86400000);

  const health = $derived([
    {
      label: "Scheduler",
      dot: !scheduler ? "r-dot-idle" : scheduler.running ? (scheduler.paused ? "r-dot-warning" : "") : "r-dot-danger",
      state: !scheduler ? "…" : scheduler.running ? `Running, ${plural(scheduler.jobs, "job")}` : "Stopped",
      detail: scheduler?.paused ? `${n(scheduler.paused)} paused` : "",
      link: { href: "/admin/jobs", label: "Jobs" },
    },
    {
      label: "Last backup",
      dot: $lastBackup === undefined ? "r-dot-idle" : !$lastBackup || backupStale ? "r-dot-warning" : "",
      state: $lastBackup === undefined ? "…" : $lastBackup ? relativeTime(backupTime($lastBackup)) : "None yet",
      detail: $lastBackup ? `${$lastBackup.filename} · ${formatBytes($lastBackup.size_bytes)}` : "",
      link: { href: "/admin/backups", label: "Backups" },
    },
    {
      label: "Reports",
      dot: !s ? "r-dot-idle" : s.total_reports ? "r-dot-danger" : "",
      state: !s ? "…" : s.total_reports ? `${n(s.total_reports)} waiting` : "None waiting",
      detail: "",
      link: { href: "/admin/reports", label: s?.total_reports ? "Review" : "Reports" },
    },
  ]);

  const totals = $derived(
    s
      ? [
          { label: "Relics", value: n(s.total_relics), detail: `${n(s.public_relics)} public · ${n(s.private_relics)} private · ${n(s.restricted_relics)} restricted`, href: "/admin/relics" },
          { label: "Users", value: n(s.total_users), detail: `${plural(s.admin_count, "admin")} · ${n(Math.max(0, s.total_users - s.admin_count))} standard`, href: "/admin/users" },
          { label: "Storage", value: formatBytes(s.total_size_bytes), detail: `${formatBytes(s.total_relics ? s.total_size_bytes / s.total_relics : 0)} per relic on average` },
          { label: "Spaces", value: n(s.total_spaces), detail: "shared collections", href: "/spaces" },
          { label: "Comments", value: n(s.total_comments), detail: "" },
          { label: "Bookmarks", value: n(s.total_bookmarks), detail: "" },
        ]
      : []
  );
</script>

<Workbench {panel} label="Overview">
  {#snippet pagebar({ inspectorOpen, toggleInspector })}
    <PageBar title="Overview" {inspectorOpen} ontoggleinspector={toggleInspector}>
      {#snippet actions()}
        <button class="r-btn r-btn-ghost r-btn-icon" onclick={refresh} disabled={refreshing} title="Refresh" aria-label="Refresh"><Icon name="history" /></button>
      {/snippet}
    </PageBar>
  {/snippet}

  <div class="ov">
    <div class="r-day" role="presentation"><span>Health</span><span class="r-day-rule"></span></div>
    {#each health as h (h.label)}
      <a class="ov-row" href={h.link.href}>
        <span class="ov-label">{h.label}</span>
        <span class="ov-state"><i class="r-dot {h.dot}"></i>{h.state}</span>
        <span class="ov-detail">{h.detail}</span>
        <span class="ov-go">{h.link.label}<Icon name="chevr" /></span>
      </a>
    {/each}

    <div class="r-day" role="presentation"><span>Instance</span><span class="r-day-rule"></span></div>
    {#if s}
      {#each totals as t (t.label)}
        {#if t.href}
          <a class="ov-row" href={t.href}>
            <span class="ov-label">{t.label}</span>
            <span class="ov-value">{t.value}</span>
            <span class="ov-detail">{t.detail}</span>
            <span class="ov-go">Open<Icon name="chevr" /></span>
          </a>
        {:else}
          <div class="ov-row">
            <span class="ov-label">{t.label}</span>
            <span class="ov-value">{t.value}</span>
            <span class="ov-detail">{t.detail}</span>
            <span></span>
          </div>
        {/if}
      {/each}
    {:else}
      <p class="ov-empty">Loading…</p>
    {/if}
  </div>

  {#snippet inspector({ close })}
    <aside class="r-inspector" aria-label="Recent activity">
      <div class="r-ins-mode">
        <div>
          <h2>Recent activity</h2>
          <p>Since the server started</p>
        </div>
        {#if close}<button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={close} aria-label="Hide inspector"><Icon name="x" /></button>{/if}
      </div>
      <div class="r-ins-body">
        <InsSection id="admin-ov-runs" title="Job runs" aside={runs.length ? String(runs.length) : "none"} defaultOpen>
          {#if runs.length}
            <div class="r-feed">
              {#each runs as run (run.run_id)}
                {@const st = runStatus(run)}
                <div>
                  <i class="r-dot {st.dot}"></i>
                  <a href="/admin/jobs">{run.job_name || run.job_id}<span class="feed-muted">&nbsp;· {st.label.toLowerCase()}{run.trigger_type === "manual" ? ", by hand" : ""}</span></a>
                  <em>{relativeTime(run.start_time)}</em>
                </div>
              {/each}
            </div>
          {:else}
            <p class="ins-note">No runs since the server started.</p>
          {/if}
        </InsSection>
        <InsSection id="admin-ov-reports" title="Reports" aside={reports.length ? String(s?.total_reports ?? reports.length) : "none"} defaultOpen>
          {#if reports.length}
            <div class="r-feed">
              {#each reports as report (report.id)}
                <div>
                  <Icon name="flag" />
                  <a href="/admin/reports" title={report.reason}>{report.relic_name || "Untitled"}<span class="feed-muted">&nbsp;· {report.reason}</span></a>
                  <em>{relativeTime(report.created_at)}</em>
                </div>
              {/each}
            </div>
          {:else}
            <p class="ins-note">No reports waiting.</p>
          {/if}
        </InsSection>
      </div>
    </aside>
  {/snippet}
</Workbench>

<style>
  .ov {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-bottom: var(--space-4);
  }
  .ov-row {
    display: grid;
    grid-template-columns: 140px 220px minmax(0, 1fr) auto;
    align-items: center;
    gap: var(--space-3);
    height: 34px;
    padding: 0 var(--space-4);
    color: var(--ink);
    font-size: 13px;
    text-decoration: none;
    white-space: nowrap;
  }
  a.ov-row:hover {
    background: var(--hover);
  }
  a.ov-row:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }
  .ov-label {
    color: var(--ink-2);
  }
  .ov-state {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-weight: 500;
  }
  .ov-value {
    font-weight: 500;
    font-variant-numeric: tabular-nums;
  }
  .ov-detail {
    min-width: 0;
    overflow: hidden;
    color: var(--ink-3);
    font: 12.5px var(--font-mono);
    text-overflow: ellipsis;
  }
  .ov-go {
    display: flex;
    align-items: center;
    gap: 2px;
    color: var(--ink-3);
    font-size: 12.5px;
    visibility: hidden;
  }
  .ov-go :global(.r-icon) {
    width: 13px;
    height: 13px;
  }
  a.ov-row:hover .ov-go,
  a.ov-row:focus-visible .ov-go {
    visibility: visible;
    color: var(--accent);
  }
  .ov-empty {
    margin: 0;
    padding: var(--space-3) var(--space-4);
    color: var(--ink-3);
  }
  .r-inspector {
    height: 100%;
  }
  .r-feed a {
    min-width: 0;
    overflow: hidden;
    color: var(--ink);
    text-decoration: none;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .r-feed a:hover {
    color: var(--accent);
  }
  .r-feed .r-dot {
    justify-self: center;
  }
  .feed-muted {
    color: var(--ink-3);
  }
  .ins-note {
    margin: 0;
    color: var(--ink-3);
    font-size: 12px;
  }
  @media (max-width: 1180px) {
    .ov-row {
      grid-template-columns: 110px 170px minmax(0, 1fr) auto;
    }
  }
  @media (max-width: 767px) {
    .ov-row {
      grid-template-columns: 96px minmax(0, 1fr);
      height: 40px;
    }
    .ov-row > :nth-child(n + 3) {
      display: none;
    }
  }
</style>
