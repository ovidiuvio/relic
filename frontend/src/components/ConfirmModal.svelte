<script>
    import { createEventDispatcher } from 'svelte';
    import { modal } from '../utils/modal';

    export let show = false;
    export let title = '';
    export let message = '';
    export let confirmLabel = 'Confirm';
    export let cancelLabel = 'Cancel';
    // Defaults to a destructive style for delete/remove style confirmations.
    export let danger = null;

    const dispatch = createEventDispatcher();

    $: isDanger = danger ?? /^(delete|remove|revoke|leave)\b/i.test(title);
</script>

{#if show}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="fixed inset-0 bg-black/50 z-[200] flex items-center justify-center p-4" on:click|self={() => dispatch('cancel')}>
    <div class="bg-white rounded-lg shadow-xl max-w-sm w-full p-6" role="alertdialog" use:modal={{ onClose: () => dispatch('cancel') }}>
      <h3 class="text-base font-semibold text-gray-900 mb-2">{title}</h3>
      <p class="text-sm text-gray-600 mb-6 whitespace-pre-wrap">{message}</p>
      <div class="flex justify-end gap-3">
        <button class="btn-secondary" on:click={() => dispatch('cancel')}>{cancelLabel}</button>
        <button class={isDanger ? 'btn-danger' : 'btn-primary'} on:click={() => dispatch('confirm')}>{confirmLabel}</button>
      </div>
    </div>
  </div>
{/if}
