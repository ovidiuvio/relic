<script>
  // The admin area's side navigation (design system SideNav): its sections with counts, reports
  // waiting in the alert colour, and the version and last backup at the foot. On desktop it takes
  // the place of the app sidebar; phones get the same links as a row in the page bar.
  import Icon from "../ui/Icon.svelte";
  import { ADMIN_SECTIONS, adminPath } from "./sections";
  import { adminStats, lastBackup, backupTime } from "./adminState";
  import { session } from "../../stores/session";
  import { compactNumber, relativeTime } from "../relics/format";

  let { tab } = $props();

  const counts = $derived({
    relics: $adminStats?.total_relics,
    users: $adminStats?.total_users,
    reports: $adminStats?.total_reports,
  });
</script>

<nav class="r-sidenav admin-nav" aria-label="Admin">
  <div class="r-sidenav-head">Admin</div>
  {#each ADMIN_SECTIONS as s (s.key)}
    <a href={adminPath(s.key)} aria-current={tab === s.key ? "page" : undefined}>
      <Icon name={s.icon} />{s.label}
      {#if s.key === "reports" && counts.reports}
        <span class="r-count r-count-alert" title="{counts.reports} waiting">{counts.reports}</span>
      {:else if counts[s.key] != null && s.key !== "reports"}
        <span class="r-count">{compactNumber(counts[s.key])}</span>
      {/if}
    </a>
  {/each}
  <div class="r-sidenav-foot">
    {#if $session.version}<span>Relic {$session.version}</span>{/if}
    {#if $lastBackup !== undefined}
      <span>{$lastBackup ? `Last backup ${relativeTime(backupTime($lastBackup))}` : "No backups yet"}</span>
    {/if}
  </div>
</nav>

<style>
  .admin-nav {
    flex: none;
    min-height: 0;
    overflow-y: auto;
  }
  /* From 1600px it stands where the app sidebar does, under the navbar's wordmark. */
  @media (min-width: 1600px) {
    .admin-nav {
      width: var(--rail-w);
    }
  }
</style>
