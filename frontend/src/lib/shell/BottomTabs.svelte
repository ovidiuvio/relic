<script>
  // Phones only: the app's sections as a bottom tab bar.
  import Icon from "../ui/Icon.svelte";
  import { NAV_ITEMS, ADMIN_ITEM, isActive } from "./navItems";
  import { session } from "../../stores/session";

  let { section } = $props();

  const items = $derived($session.isAdmin ? [...NAV_ITEMS, ADMIN_ITEM] : NAV_ITEMS);
</script>

<nav class="tabs" aria-label="Sections">
  {#each items as item (item.section)}
    <a href={item.path} aria-current={isActive(item, section) ? "page" : undefined}>
      <Icon name={item.icon} size={20} />{item.label}
    </a>
  {/each}
</nav>

<style>
  .tabs {
    display: none;
  }
  @media (max-width: 767px) {
    .tabs {
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: 1fr;
      flex: none;
      height: 56px;
      padding-bottom: env(safe-area-inset-bottom, 0px);
      border-top: 1px solid var(--line);
      background: var(--surface);
    }
    a {
      display: grid;
      justify-items: center;
      align-content: center;
      gap: 3px;
      color: var(--ink-3);
      font-size: 10.5px;
      text-decoration: none;
    }
    a[aria-current="page"] {
      color: var(--accent);
      font-weight: 500;
    }
  }
</style>
