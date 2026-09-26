<script>
  // The admin inspector for background jobs: a scheduled job (schedule, next run, Run now,
  // Pause or Resume, its recent runs) or one run from the history (status, timing, logs and
  // the stack trace when it failed).
  import Icon from "../ui/Icon.svelte";
  import AdminInspector from "./AdminInspector.svelte";
  import InsSection from "../relics/inspector/InsSection.svelte";
  import { copyToClipboard } from "../../services/relicActions";
  import { fullDate, relativeTime } from "../relics/format";
  import { describeTrigger, runStatus } from "./jobs";

  let {
    job = null, // a scheduled job
    run = null, // or a run from the history
    runs = [], // the job's runs, newest first
    busy = null, // "run" | "pause" | "resume" while an action is in flight
    confirm = null, // { n } from the row's Run now
    onrun, // (job)
    ontogglepause, // (job)
    onselectrun, // (run)
    onhistory, // (jobId) show its runs in History
    onclose = null,
  } = $props();

  let confirming = $state(false);
  $effect(() => {
    job?.id;
    confirming = false;
  });
  $effect(() => {
    if (!confirm || !job) return;
    confirm.n;
    confirming = !job.paused;
  });

  function start() {
    confirming = false;
    onrun?.(job);
  }

  const status = $derived(run ? runStatus(run) : null);
</script>

{#if run}
  <AdminInspector label="Job run" icon="play" badgeClass="r-t-code" title={run.job_name || run.job_id} copyId={{ text: run.run_id, label: "run ID" }} {onclose}>
    {#snippet actions()}
      {#if run.logs?.length}
        <button class="r-btn r-btn-secondary r-btn-md" onclick={() => copyToClipboard(run.logs.join("\n"), "Logs copied")}><Icon name="copy" />Copy logs</button>
      {/if}
      {#if run.traceback}
        <button class="r-btn r-btn-secondary r-btn-md" onclick={() => copyToClipboard(run.traceback, "Stack trace copied")}><Icon name="copy" />Copy stack trace</button>
      {/if}
    {/snippet}
    {#snippet meta()}
      <span class="r-pill" class:r-pill-warning={run.status === "running"} class:is-failed={run.status === "failed"}><i class="r-dot {status.dot}"></i>{status.label}</span>
      <span>{run.trigger_type === "manual" ? "Run by hand" : "Scheduled"}</span>
    {/snippet}

    <InsSection id="admin-run-details" title="Details" defaultOpen>
      <dl class="r-kv">
        <dt>Job</dt><dd><button class="r-link" onclick={() => onhistory?.(run.job_id)} title="Show this job’s runs">{run.job_id}</button></dd>
        <dt>Started</dt><dd>{fullDate(run.start_time)}</dd>
        <dt>Duration</dt><dd>{run.duration != null ? `${run.duration.toFixed(3)} s` : "—"}</dd>
        <dt>Status</dt><dd>{status.label}</dd>
      </dl>
      {#if run.status === "success"}<p class="ins-note">Completed successfully.</p>{/if}
      {#if run.status === "running"}<p class="ins-note">Still running. The list refreshes itself.</p>{/if}
    </InsSection>

    {#if run.error}
      <InsSection id="admin-run-error" title="Error" defaultOpen><pre class="ins-log is-error">{run.error}</pre></InsSection>
    {/if}
    {#if run.logs?.length}
      <InsSection id="admin-run-logs" title="Logs" aside="{run.logs.length} {run.logs.length === 1 ? 'line' : 'lines'}" defaultOpen><pre class="ins-log">{run.logs.join("\n")}</pre></InsSection>
    {/if}
    {#if run.traceback}
      <InsSection id="admin-run-trace" title="Stack trace"><pre class="ins-log is-error">{run.traceback}</pre></InsSection>
    {/if}
  </AdminInspector>
{:else}
  <AdminInspector label="Job details" icon="play" badgeClass="r-t-code" title={job ? job.name || job.id : null} copyId={job ? { text: job.id, label: "job ID" } : null} emptyText="Select a job to run, pause or see its history." {onclose}>
    {#snippet actions()}
      <button class="r-btn r-btn-primary r-btn-md" onclick={() => (confirming = true)} disabled={job.paused || !!busy || confirming} title={job.paused ? "Resume it first" : "Run now"}>
        <Icon name="play" />{busy === "run" ? "Starting…" : "Run now"}
      </button>
      <button class="r-btn r-btn-secondary r-btn-md" onclick={() => ontogglepause?.(job)} disabled={!!busy}>
        {job.paused ? (busy === "resume" ? "Resuming…" : "Resume") : busy === "pause" ? "Pausing…" : "Pause"}
      </button>
      <button class="r-btn r-btn-ghost r-btn-md" onclick={() => onhistory?.(job.id)}><Icon name="history" />History</button>
    {/snippet}
    {#snippet meta()}
      {#if job.paused}<span class="r-pill r-pill-warning">Paused</span>{:else}<span class="r-pill"><i class="r-dot"></i>Scheduled</span>{/if}
      <span>{describeTrigger(job)}</span>
    {/snippet}

    {#if confirming}
      <div class="r-confirm is-mild ins-confirm">
        <b>Run “{job.name || job.id}” now?</b>
        <span>It runs once straight away, outside its schedule. The schedule doesn’t change.</span>
        <div class="r-confirm-actions">
          <button class="r-btn r-btn-secondary r-btn-sm" onclick={() => (confirming = false)}>Cancel</button>
          <button class="r-btn r-btn-primary r-btn-sm" onclick={start}>Run now</button>
        </div>
      </div>
    {/if}

    <InsSection id="admin-job-details" title="Details" defaultOpen>
      <dl class="r-kv">
        <dt>Schedule</dt><dd>{describeTrigger(job)}</dd>
        <dt>Next run</dt><dd title={job.next_run_time ? fullDate(job.next_run_time) : ""}>{job.paused ? "Paused" : job.next_run_time ? `${fullDate(job.next_run_time)} (${relativeTime(job.next_run_time)})` : "Not scheduled"}</dd>
        <dt>Function</dt><dd class="r-mono" title={job.func}>{job.func}</dd>
      </dl>
      <p class="ins-note">Pausing lasts until the server restarts; the pause isn’t saved.</p>
    </InsSection>

    <InsSection id="admin-job-runs" title="Recent runs" aside={runs.length ? String(runs.length) : "none"} defaultOpen>
      {#if runs.length}
        <div class="job-runs">
          {#each runs.slice(0, 8) as r (r.run_id)}
            {@const s = runStatus(r)}
            <button class="job-run" onclick={() => onselectrun?.(r)}>
              <i class="r-dot {s.dot}"></i>
              <span>{fullDate(r.start_time)}</span>
              <em>{r.duration != null ? `${r.duration.toFixed(2)} s` : s.label}</em>
            </button>
          {/each}
        </div>
        {#if runs.length > 8}<button class="r-link more-runs" onclick={() => onhistory?.(job.id)}>All {runs.length} runs</button>{/if}
      {:else}
        <p class="ins-note">No runs since the server started.</p>
      {/if}
    </InsSection>
  </AdminInspector>
{/if}

<style>
  .ins-confirm {
    margin: var(--space-3) var(--space-4) 0;
  }
  .r-confirm.is-mild {
    border-color: var(--line-2);
    background: var(--subtle);
    color: var(--ink-2);
  }
  .r-pill .r-dot {
    width: 7px;
    height: 7px;
  }
  .r-pill.is-failed {
    background: var(--danger-soft);
    color: var(--danger-ink);
  }
  .r-kv button.r-link,
  .more-runs {
    padding: 0;
    border: 0;
    background: none;
    font: inherit;
    cursor: pointer;
  }
  .more-runs {
    margin-top: var(--space-2);
    font-size: 12.5px;
  }
  .job-runs {
    display: grid;
  }
  .job-run {
    display: grid;
    grid-template-columns: 10px 1fr auto;
    align-items: center;
    gap: var(--space-2);
    height: 28px;
    padding: 0 var(--space-1);
    border: 0;
    border-top: 1px solid var(--line);
    background: none;
    color: var(--ink);
    font: 12.5px var(--font-sans);
    text-align: left;
    cursor: pointer;
  }
  .job-run:first-child {
    border-top: 0;
  }
  .job-run:hover {
    background: var(--hover);
  }
  .job-run em {
    color: var(--ink-3);
    font: 12px var(--font-mono);
    font-style: normal;
  }
</style>
