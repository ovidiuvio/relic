<script module>
  // App remounts the page on every section change; the access check is remembered for the
  // session so switching sections doesn't flash "Checking…" again.
  let knownAdmin = false;
</script>

<script>
  // The admin area: its side navigation beside the current section (/admin/<section>). On phones
  // the sections are a row of links above it instead. People who aren't admins see why not.
  import Icon from "../lib/ui/Icon.svelte";
  import AdminNav from "../lib/admin/AdminNav.svelte";
  import AdminOverview from "../lib/admin/AdminOverview.svelte";
  import AdminRelics from "../lib/admin/AdminRelics.svelte";
  import AdminUsers from "../lib/admin/AdminUsers.svelte";
  import AdminReports from "../lib/admin/AdminReports.svelte";
  import AdminBackups from "../lib/admin/AdminBackups.svelte";
  import AdminJobs from "../lib/admin/AdminJobs.svelte";
  import AdminConfig from "../lib/admin/AdminConfig.svelte";
  import { ADMIN_SECTIONS, adminPath } from "../lib/admin/sections";
  import { refreshAdminStats, refreshLastBackup } from "../lib/admin/adminState";
  import { layout } from "../lib/shell/layout";
  import { pageTitle } from "../stores/pageTitle";
  import { checkAdminStatus } from "../services/api";

  let { tab = "overview", search = null, tag = null, visibility = null, type = null } = $props();

  let access = $state(knownAdmin ? "admin" : "checking"); // "checking" | "admin" | "denied"

  if (!knownAdmin) {
    checkAdminStatus()
      .then(({ data }) => {
        knownAdmin = !!data.is_admin;
        access = data.is_admin ? "admin" : "denied";
        if (data.is_admin) {
          refreshAdminStats();
          refreshLastBackup();
        }
      })
      .catch(() => (access = "denied"));
  } else {
    refreshAdminStats();
    refreshLastBackup();
  }

  const section = $derived(ADMIN_SECTIONS.find((s) => s.key === tab) ?? ADMIN_SECTIONS[0]);
  $effect(() => {
    pageTitle.set(section.key === "overview" ? "Admin" : `${section.label} · Admin`);
  });
</script>

{#if access === "checking"}
  <div class="admin-state" role="status">Checking your access…</div>
{:else if access === "denied"}
  <div class="admin-state">
    <Icon name="lock" size={24} />
    <h1>Admins only</h1>
    <p>You don’t have admin rights on this instance. Admins are set with the <code>ADMIN_USER_IDS</code> variable, or added by another admin.</p>
    <a class="r-btn r-btn-secondary r-btn-md" href="/recent">Back to Recent</a>
  </div>
{:else}
  <div class="admin">
    {#if !$layout.phone}<AdminNav tab={section.key} />{/if}
    <div class="admin-main">
      {#if $layout.phone}
        <nav class="r-facets admin-tabs" aria-label="Admin">
          {#each ADMIN_SECTIONS as s (s.key)}
            <a href={adminPath(s.key)} aria-current={s.key === section.key ? "true" : undefined}>{s.label}</a>
          {/each}
        </nav>
      {/if}
      {#key section.key}
        {#if section.key === "overview"}<AdminOverview />
        {:else if section.key === "relics"}<AdminRelics {search} {tag} {visibility} {type} />
        {:else if section.key === "users"}<AdminUsers {search} />
        {:else if section.key === "reports"}<AdminReports />
        {:else if section.key === "backups"}<AdminBackups />
        {:else if section.key === "jobs"}<AdminJobs />
        {:else if section.key === "config"}<AdminConfig />{/if}
      {/key}
    </div>
  </div>
{/if}

<style>
  .admin {
    flex: 1;
    min-height: 0;
    display: flex;
  }
  .admin-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .admin-tabs {
    flex: none;
    height: 40px;
    align-items: center;
    padding: 0 var(--space-4);
    overflow-x: auto;
    border-bottom: 1px solid var(--line);
    background: var(--surface);
    white-space: nowrap;
    scrollbar-width: none;
  }
  .admin-state {
    flex: 1;
    display: grid;
    place-content: center;
    justify-items: center;
    gap: var(--space-2);
    padding: var(--space-5);
    background: var(--surface);
    color: var(--ink-3);
    font: 13px/1.5 var(--font-sans);
    text-align: center;
  }
  .admin-state h1 {
    margin: 0;
    color: var(--ink);
    font-size: 17px;
    font-weight: 500;
  }
  .admin-state p {
    max-width: 420px;
    margin: 0 0 var(--space-2);
  }
  code {
    font-family: var(--font-mono);
  }
</style>
