<script>
  // A content report in the admin inspector: the reported relic and its owner, the reason in
  // full, and the two outcomes, Dismiss the report or Delete the relic, each confirmed inline.
  import Icon from "../ui/Icon.svelte";
  import AdminInspector from "./AdminInspector.svelte";
  import InsSection from "../relics/inspector/InsSection.svelte";
  import { deleteReport, deleteRelic } from "../../services/api";
  import { showToast } from "../../stores/toastStore";
  import { fullDate, relativeTime } from "../relics/format";

  let {
    report = null,
    confirm = null, // { what: "dismiss" | "delete", n } from a row action
    onowner, // (report) show the owner's relics
    ondismissed, // (report)
    onrelicdeleted, // (report)
    onclose = null,
  } = $props();

  let confirming = $state(null);
  let busy = $state(false);

  $effect(() => {
    report?.id;
    confirming = null;
  });
  $effect(() => {
    if (!confirm || !report) return;
    confirm.n;
    confirming = confirm.what;
  });

  const relicGone = $derived(!!report && !report.relic_owner_id && report.relic_name?.startsWith("Unknown"));

  async function dismiss() {
    busy = true;
    try {
      await deleteReport(report.id);
      showToast("Report dismissed", "success");
      ondismissed?.(report);
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t dismiss the report", "error");
    } finally {
      busy = false;
      confirming = null;
    }
  }

  async function removeRelic() {
    busy = true;
    try {
      await deleteRelic(report.relic_id);
      showToast("Relic deleted", "success");
      onrelicdeleted?.(report);
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t delete the relic", "error");
    } finally {
      busy = false;
      confirming = null;
    }
  }
</script>

<AdminInspector
  label="Report details"
  icon="flag"
  badgeClass="r-t-web"
  title={report ? report.relic_name || "Untitled" : null}
  copyId={report ? { text: report.relic_id, shown: report.relic_id.match(/.{1,8}/g).join(" "), label: "relic ID" } : null}
  emptyText="Select a report to review it."
  {onclose}
>
  {#snippet actions()}
    <a class="r-btn r-btn-primary r-btn-md" href="/{report.relic_id}"><Icon name="eye" />Open relic</a>
    <button class="r-btn r-btn-secondary r-btn-md" onclick={() => (confirming = "dismiss")} disabled={!!confirming}><Icon name="check" />Dismiss</button>
    <button class="r-btn r-btn-danger-text r-btn-md" onclick={() => (confirming = "delete")} disabled={!!confirming}><Icon name="trash" />Delete relic</button>
  {/snippet}
  {#snippet meta()}
    <span class="r-pill r-pill-warning"><Icon name="flag" />Reported {relativeTime(report.created_at)}</span>
  {/snippet}

  {#if confirming === "dismiss"}
    <div class="ins-confirm r-confirm is-mild">
      <b>Dismiss this report?</b>
      <span>The relic stays as it is and the report leaves this list.</span>
      <div class="r-confirm-actions">
        <button class="r-btn r-btn-secondary r-btn-sm" onclick={() => (confirming = null)} disabled={busy}>Cancel</button>
        <button class="r-btn r-btn-primary r-btn-sm" onclick={dismiss} disabled={busy}>{busy ? "Dismissing…" : "Dismiss report"}</button>
      </div>
    </div>
  {:else if confirming === "delete"}
    <div class="ins-confirm r-confirm">
      <b>Delete “{report.relic_name || "Untitled"}”?</b>
      <span>It goes for everyone, with its comments and bookmarks. Forks made from it stay. This can’t be undone.</span>
      <div class="r-confirm-actions">
        <button class="r-btn r-btn-secondary r-btn-sm" onclick={() => (confirming = null)} disabled={busy}>Cancel</button>
        <button class="r-btn r-btn-danger r-btn-sm" onclick={removeRelic} disabled={busy}>{busy ? "Deleting…" : "Delete relic"}</button>
      </div>
    </div>
  {/if}

  <InsSection id="admin-report-reason" title="Reason" defaultOpen>
    <p class="reason">{report.reason}</p>
  </InsSection>

  <InsSection id="admin-report-details" title="Details" defaultOpen>
    <dl class="r-kv">
      <dt>Relic</dt><dd><a class="r-link" href="/{report.relic_id}">{report.relic_name || "Untitled"}</a></dd>
      <dt>Owner</dt>
      <dd>
        {#if report.relic_owner_id}
          <button class="r-link" onclick={() => onowner?.(report)} title="Show their relics">{report.relic_owner_name || "—"}</button>
        {:else}Anonymous{/if}
      </dd>
      {#if report.relic_owner_public_id}<dt>Owner ID</dt><dd class="r-mono">{report.relic_owner_public_id}</dd>{/if}
      <dt>Reported</dt><dd>{fullDate(report.created_at)}</dd>
    </dl>
    {#if relicGone}<p class="ins-note">The relic has been deleted; dismiss the report to clear it.</p>{/if}
  </InsSection>
</AdminInspector>

<style>
  .ins-confirm {
    margin: var(--space-3) var(--space-4) 0;
  }
  .r-confirm.is-mild {
    border-color: var(--line-2);
    background: var(--subtle);
    color: var(--ink-2);
  }
  .reason {
    margin: 0;
    color: var(--ink);
    font-size: 13px;
    line-height: 1.5;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .r-kv button.r-link {
    padding: 0;
    border: 0;
    background: none;
    font: inherit;
    cursor: pointer;
  }
</style>
