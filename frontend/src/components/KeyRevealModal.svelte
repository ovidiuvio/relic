<script>
    import { createEventDispatcher } from 'svelte';
    import { triggerDownload } from '../services/utils/download';

    export let show = false;
    export let clientKey = '';

    const dispatch = createEventDispatcher();

    let keySaved = false;
    let copied = false;

    function download() {
        triggerDownload(clientKey, `relic-client-key-${clientKey.substring(0, 8)}.txt`, 'text/plain');
        keySaved = true;
    }

    let copyFailed = false;

    function copy() {
        navigator.clipboard.writeText(clientKey).then(() => {
            copied = true;
            copyFailed = false;
            keySaved = true;
        }).catch(() => {
            copyFailed = true;
        });
    }

    function confirm() {
        dispatch('confirm');
    }
</script>

{#if show}
  <div class="fixed inset-0 bg-black bg-opacity-60 z-[200] flex items-center justify-center p-4">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full">
      <div class="p-6 border-b border-gray-200">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
            <i class="fas fa-key text-amber-600"></i>
          </div>
          <h3 class="text-lg font-semibold text-gray-900">Save Your Relic Key</h3>
        </div>
        <p class="text-sm text-gray-600 mt-2">
          This key is your identity. It proves ownership of your relics and cannot be recovered if lost.
          Save it now — you will not see it again.
        </p>
      </div>

      <div class="p-6">
        <div class="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4">
          <label class="block text-xs font-medium text-gray-500 mb-1">Your Key</label>
          <code class="text-sm font-mono text-gray-900 break-all select-all">{clientKey}</code>
        </div>

        <div class="flex gap-3">
          <button
            on:click={download}
            class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            <i class="fas fa-download"></i>
            Download
          </button>
          <button
            on:click={copy}
            class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
          >
            <i class="fas fa-copy"></i>
            {copied ? 'Copied!' : copyFailed ? 'Copy failed' : 'Copy'}
          </button>
        </div>
      </div>

      <div class="px-6 pb-6">
        <button
          on:click={confirm}
          disabled={!keySaved}
          class="w-full px-4 py-2.5 rounded-lg text-sm font-medium transition-colors
            {keySaved
              ? 'bg-gray-900 text-white hover:bg-gray-800'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'}"
        >
          {keySaved ? 'I\'ve saved my key' : 'Download or copy your key first'}
        </button>
      </div>
    </div>
  </div>
{/if}
