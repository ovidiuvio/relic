<script>
    import { createEventDispatcher } from 'svelte';

    export let show = false;
    export let title = '';
    export let message = '';
    export let confirmLabel = 'Confirm';
    export let cancelLabel = 'Cancel';

    const dispatch = createEventDispatcher();
</script>

{#if show}
  <div class="fixed inset-0 bg-black bg-opacity-50 z-[200] flex items-center justify-center p-4">
    <div class="bg-white rounded-lg shadow-xl max-w-sm w-full p-6">
      <h3 class="text-base font-semibold text-gray-900 mb-2">{title}</h3>
      <p class="text-sm text-gray-600 mb-6 whitespace-pre-wrap">{message}</p>
      <div class="flex justify-end gap-3">
        <button class="maas-btn-secondary" on:click={() => dispatch('cancel')}>{cancelLabel}</button>
        <button class="maas-btn-primary" on:click={() => dispatch('confirm')}>{confirmLabel}</button>
      </div>
    </div>
  </div>
{/if}
