<script>
  // Toasts, bottom centre, in the design system's dark style. A toast can carry one action
  // (usually Undo); using it dismisses the toast.
  import Icon from "./Icon.svelte";
  import { toastStore, dismissToast } from "../../stores/toastStore";

  const ICONS = { success: "check", error: "info", warning: "info", info: "info" };
</script>

<div class="toasts" role="status" aria-live="polite">
  {#each $toastStore as toast (toast.id)}
    <div class="r-toast" data-type={toast.type}>
      <Icon name={ICONS[toast.type] ?? "info"} />
      <span>{toast.message}</span>
      {#if toast.action}
        <button
          onclick={() => {
            dismissToast(toast.id);
            toast.action.run();
          }}>{toast.action.label}</button
        >
      {/if}
    </div>
  {/each}
</div>

<style>
  .toasts {
    position: fixed;
    bottom: calc(24px + env(safe-area-inset-bottom, 0px));
    left: 50%;
    z-index: 300;
    display: grid;
    justify-items: center;
    gap: var(--space-2);
    transform: translateX(-50%);
    pointer-events: none;
  }
  .r-toast {
    max-width: min(560px, calc(100vw - 32px));
    pointer-events: auto;
    animation: toast-in 0.18s ease-out;
  }
  .r-toast[data-type="error"] > :global(.r-icon),
  .r-toast[data-type="warning"] > :global(.r-icon) {
    color: var(--night-amber);
  }
  @keyframes toast-in {
    from {
      transform: translateY(8px);
      opacity: 0;
    }
  }
  /* Clear the bottom tab bar on phones. */
  @media (max-width: 767px) {
    .toasts {
      bottom: calc(68px + env(safe-area-inset-bottom, 0px));
    }
  }
</style>
