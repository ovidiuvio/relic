<script>
  // Admin · Jobs: the background scheduler. Scheduled shows each periodic job (run it now, pause,
  // resume); History shows recent runs, filtered by job and status, with logs and stack traces
  // in the inspector. Refreshes itself every 30 seconds, and every second or so while a run
  // you started is going.
  import { onDestroy } from "svelte";
  import Icon from "../ui/Icon.svelte";
  import DataList from "../ui/DataList.svelte";
  import PageBar from "../shell/PageBar.svelte";
  import Workbench from "../shell/Workbench.svelte";
  import JobInspector from "./JobInspector.svelte";
  import { InspectorPanel } from "../shell/inspectorPanel.svelte.js";
  import { layout } from "../shell/layout";
  import { describeTrigger, runStatus } from "./jobs";
  import { refreshLastBackup, refreshAdminStats } from "./adminState";
  import { getAdminJobs, runAdminJob, pauseAdminJob, resumeAdminJob } from "../../services/api";
  import { showToast } from "../../stores/toastStore";
  import { fullDate, relativeTime } from "../relics/format";

  const JOB_COLUMNS = [
    { key: "name", label: "Job", width: "minmax(0, 1fr)" },
    { key: "func", label: "Function", width: "minmax(0, 1fr)", mono: true, hide: "narrow" },
    { key: "schedule", label: "Schedule", width: "minmax(0, 170px)", hide: "phone" },
    { key: "next", label: "Next run", width: "120px", num: true },
  ];
  const RUN_COLUMNS = [
    { key: "status", label: "Status", width: "96px" },
    { key: "job", label: "Job", width: "minmax(0, 1fr)" },
    { key: "job_id", label: "ID", width: "minmax(0, 160px)", mono: true, hide: "phone" },
    { key: "trigger", label: "Trigger", width: "84px", hide: "narrow" },
    { key: "start", label: "Started", width: "130px", num: true, hide: "phone" },
    { key: "duration", label: "Duration", width: "80px", num: true },
  ];
  const STATUSES = [
    { key: "", label: "All" },
    { key: "success", label: "Succeeded" },
    { key: "failed", label: "Failed" },
    { key: "running", label: "Running" },
  ];

  const panel = new InspectorPanel();
  let jobs = $state.raw([]);
  let history = $state.raw([]); // newest first
  let schedulerRunning = $state(null);
  let loading = $state(false);
  let loadError = $state(false);
  let view = $state("scheduled");
  let jobFilter = $state("");
  let statusFilter = $state("");
  let selectedJobId = $state(null);
  let selectedRunId = $state(null);
  let busy = $state({}); // jobId → "run" | "pause" | "resume"
  let confirm = $state(null);

  async function load() {
    loading = true;
    try {
      const { data } = await getAdminJobs();
      jobs = data.jobs || [];
      history = (data.history || []).slice().reverse();
      schedulerRunning = !!data.running;
      loadError = false;
    } catch (error) {
      console.error("[admin] Failed to load jobs", error);
      loadError = true;
    } finally {
      loading = false;
    }
  }
  load();

  const timers = new Set();
  const refresh = setInterval(() => !loading && load(), 30_000);
  onDestroy(() => {
    clearInterval(refresh);
    timers.forEach(clearTimeout);
  });

  const runs = $derived(history.filter((r) => (!jobFilter || r.job_id === jobFilter) && (!statusFilter || r.status === statusFilter)));
  const selectedJob = $derived(jobs.find((j) => j.id === selectedJobId) ?? null);
  const selectedRun = $derived(history.find((r) => r.run_id === selectedRunId) ?? null);

  $effect(() => {
    if (!$layout.dock) return;
    if (view === "scheduled" && jobs.length && !selectedJob) selectedJobId = jobs[0].id;
    if (view === "history" && runs.length && !runs.some((r) => r.run_id === selectedRunId)) selectedRunId = runs[0].run_id;
  });

  function selectJob(job) {
    selectedJobId = job.id;
    confirm = null;
    if (!$layout.dock) panel.show(false);
  }

  function selectRun(run) {
    selectedRunId = run.run_id;
    if (!$layout.dock) panel.show(false);
  }

  function showHistory(jobId = "") {
    jobFilter = jobId;
    statusFilter = "";
    view = "history";
    selectedRunId = null;
  }

  function openRun(run) {
    jobFilter = run.job_id;
    statusFilter = "";
    view = "history";
    selectedRunId = run.run_id;
  }

  function askRun(job) {
    selectJob(job);
    panel.show($layout.dock);
    confirm = { n: (confirm?.n ?? 0) + 1 };
  }

  async function runJob(job) {
    busy = { ...busy, [job.id]: "run" };
    try {
      const { data } = await runAdminJob(job.id);
      if (data.success) {
        showToast(data.message || `Started “${job.name || job.id}”`, "success");
        await load();
        watchRun(job, data.run_id);
      } else {
        showToast(data.message || `Couldn’t start “${job.name || job.id}”`, "error");
      }
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (error.response?.status === 409) showToast(detail || `“${job.name || job.id}” is already running`, "warning");
      else showToast(detail || `Couldn’t start “${job.name || job.id}”`, "error");
    } finally {
      busy = { ...busy, [job.id]: null };
    }
  }

  // Refresh until the run finishes (at most 30 s), then say if it failed.
  function watchRun(job, runId) {
    const deadline = Date.now() + 30_000;
    const tick = async () => {
      await load();
      const run = history.find((r) => r.run_id === runId);
      const done = run && (run.status === "success" || run.status === "failed");
      if (done) {
        if (run.status === "failed") showToast(`“${run.job_name || job.id}” failed`, "error");
        if (job.id.startsWith("backup")) refreshLastBackup();
        refreshAdminStats();
        return;
      }
      if (Date.now() < deadline) schedule();
    };
    const schedule = () => {
      const t = setTimeout(() => (timers.delete(t), tick()), 1500);
      timers.add(t);
    };
    schedule();
  }

  async function togglePause(job) {
    const action = job.paused ? "resume" : "pause";
    busy = { ...busy, [job.id]: action };
    try {
      const { data } = job.paused ? await resumeAdminJob(job.id) : await pauseAdminJob(job.id);
      if (data.success) {
        showToast(data.message || (job.paused ? "Job resumed" : "Job paused"), "success");
        await load();
      } else {
        showToast(data.message || `Couldn’t ${action} the job`, "error");
      }
    } catch (error) {
      showToast(error.response?.data?.detail || `Couldn’t ${action} the job`, "error");
    } finally {
      busy = { ...busy, [job.id]: null };
    }
  }

  const jobActions = [
    { icon: "history", title: "History", run: (j) => showHistory(j.id) },
    { icon: "play", title: "Run now", run: askRun, disabled: (j) => j.paused || !!busy[j.id] },
  ];

  const jobName = (id) => jobs.find((j) => j.id === id)?.name || id;
</script>

<Workbench {panel} hasSelection={view === "scheduled" ? !!selectedJob : !!selectedRun} label="Jobs" phoneDrawer>
  {#snippet pagebar({ inspectorOpen, toggleInspector })}
    <PageBar title="Jobs" {inspectorOpen} ontoggleinspector={toggleInspector}>
      {#snippet filters()}
        <nav class="r-facets" aria-label="View">
          <a href="/admin/jobs" aria-current={view === "scheduled" ? "true" : undefined} onclick={(e) => (e.preventDefault(), (view = "scheduled"))}>Scheduled <em>{jobs.length}</em></a>
          <a href="/admin/jobs" aria-current={view === "history" ? "true" : undefined} onclick={(e) => (e.preventDefault(), showHistory(jobFilter))}>History <em>{history.length}</em></a>
        </nav>
        {#if view === "history"}
          <span class="r-pagebar-sep"></span>
          <label class="r-pagebar-opt">Job
            <select bind:value={jobFilter}>
              <option value="">All jobs</option>
              {#each jobs as j (j.id)}<option value={j.id}>{j.name || j.id}</option>{/each}
            </select>
          </label>
          <nav class="r-facets" aria-label="Status">
            {#each STATUSES as s (s.key)}
              <a href="/admin/jobs" aria-current={statusFilter === s.key ? "true" : undefined} onclick={(e) => (e.preventDefault(), (statusFilter = s.key))}>{s.label}</a>
            {/each}
          </nav>
          {#if jobFilter || statusFilter}
            <button class="r-btn r-btn-ghost r-btn-sm" onclick={() => ((jobFilter = ""), (statusFilter = ""))} title="Show every run"><Icon name="x" />Clear</button>
          {/if}
        {/if}
      {/snippet}
      {#snippet actions()}
        <span class="scheduler" title={schedulerRunning ? "The scheduler is running" : "The scheduler is stopped"}>
          {#if schedulerRunning != null}<i class="r-dot {schedulerRunning ? '' : 'r-dot-danger'}"></i>{schedulerRunning ? "Scheduler running" : "Scheduler stopped"}{/if}
        </span>
        <button class="r-btn r-btn-ghost r-btn-icon" onclick={load} disabled={loading} title="Refresh" aria-label="Refresh"><Icon name="history" /></button>
      {/snippet}
    </PageBar>
  {/snippet}

  {#if view === "scheduled"}
    <DataList
      label="Scheduled jobs"
      rows={jobs}
      columns={JOB_COLUMNS}
      loading={loading && !jobs.length}
      selectedId={selectedJobId}
      actions={jobActions}
      emptyText={loadError ? "Couldn’t load the scheduler." : "No scheduled jobs."}
      emptyAction={loadError ? { label: "Retry", run: load } : null}
      onselect={selectJob}
    >
      {#snippet cell(job, c)}
        {#if c.key === "name"}
          <Icon name={job.id.startsWith("backup") ? "database" : "play"} size={13} />
          <span class="cell-text">{job.name || job.id}</span>
          {#if job.paused}<span class="r-pill r-pill-warning mini">paused</span>{/if}
          {#if busy[job.id] === "run"}<span class="r-pill mini">starting</span>{/if}
        {:else if c.key === "func"}
          {job.func}
        {:else if c.key === "schedule"}
          <span class="cell-text muted">{describeTrigger(job)}</span>
        {:else if c.key === "next"}
          <span title={job.next_run_time ? fullDate(job.next_run_time) : ""}>{job.paused ? "paused" : job.next_run_time ? relativeTime(job.next_run_time) : "—"}</span>
        {/if}
      {/snippet}
    </DataList>
  {:else}
    <DataList
      label="Job runs"
      rows={runs}
      rowId={(r) => r.run_id}
      columns={RUN_COLUMNS}
      loading={loading && !history.length}
      selectedId={selectedRunId}
      emptyText={jobFilter || statusFilter ? "No runs match these filters since the server started." : "No runs since the server started."}
      emptyAction={jobFilter || statusFilter ? { label: "Clear filters", run: () => ((jobFilter = ""), (statusFilter = "")) } : null}
      onselect={selectRun}
    >
      {#snippet cell(run, c)}
        {@const s = runStatus(run)}
        {#if c.key === "status"}
          <i class="r-dot {s.dot}"></i><span class="cell-text" class:is-failed={run.status === "failed"}>{s.label}</span>
        {:else if c.key === "job"}
          <span class="cell-text">{run.job_name || jobName(run.job_id)}</span>
        {:else if c.key === "job_id"}
          {run.job_id}
        {:else if c.key === "trigger"}
          <span class="muted">{run.trigger_type === "manual" ? "by hand" : "schedule"}</span>
        {:else if c.key === "start"}
          <span title={fullDate(run.start_time)}>{relativeTime(run.start_time)}</span>
        {:else if c.key === "duration"}
          {run.duration != null ? `${run.duration.toFixed(2)} s` : "—"}
        {/if}
      {/snippet}
    </DataList>
  {/if}

  {#snippet inspector({ close })}
    {#if view === "history"}
      <JobInspector run={selectedRun} onhistory={showHistory} onclose={close} />
    {:else}
      <JobInspector
        job={selectedJob}
        runs={selectedJob ? history.filter((r) => r.job_id === selectedJob.id) : []}
        busy={selectedJob ? busy[selectedJob.id] : null}
        {confirm}
        onrun={runJob}
        ontogglepause={togglePause}
        onselectrun={openRun}
        onhistory={showHistory}
        onclose={close}
      />
    {/if}
  {/snippet}

  {#snippet status()}
    <span><Icon name="play" />{jobs.length} {jobs.length === 1 ? "job" : "jobs"}</span>
    <span>{view === "history" && (jobFilter || statusFilter) ? `${runs.length} of ${history.length} runs` : `${history.length} ${history.length === 1 ? "run" : "runs"}`} kept in memory (up to 500)</span>
    {#if loadError}<span class="status-error">Couldn’t refresh. <button class="r-link" onclick={load}>Retry</button></span>{/if}
    <span class="r-gap"></span>
    <span class="r-hints"><span>refreshes every 30 s</span><span><kbd class="r-kbd">]</kbd>inspector</span></span>
  {/snippet}
</Workbench>

<style>
  .scheduler {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--ink-2);
    font-size: 12.5px;
    white-space: nowrap;
  }
  .cell-text {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .cell-text.is-failed {
    color: var(--danger);
    font-weight: 500;
  }
  .muted {
    color: var(--ink-3);
  }
  .mini {
    flex: none;
    height: 17px;
    padding: 0 6px;
    font-size: 11px;
  }
</style>
