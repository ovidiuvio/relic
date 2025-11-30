<script>
  import { getAvailableSyntaxOptions } from "../services/typeUtils";

  export let forkName = "";
  export let forkLanguage = "auto";
  export let forkAccessLevel = "public";
  export let forkExpiration = "never";
  export let isBinary = false;
  export let relic = null;

  const syntaxOptions = getAvailableSyntaxOptions();
</script>

<div class="px-6 py-3 border-b border-gray-200 bg-gray-50 flex-shrink-0">
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:{isBinary ? 'grid-cols-3' : 'grid-cols-4'} gap-4">
    <div>
      <label for="forkName" class="block text-xs font-medium text-gray-600 mb-1">Fork Name</label>
      <input
        type="text"
        id="forkName"
        bind:value={forkName}
        placeholder="My Fork"
        class="w-full px-2 py-1.5 text-sm maas-input border border-gray-300 rounded"
      />
    </div>

    {#if !isBinary}
      <div>
        <label for="forkLanguage" class="block text-xs font-medium text-gray-600 mb-1">Type</label>
        <select
          id="forkLanguage"
          bind:value={forkLanguage}
          class="w-full px-2 py-1.5 text-sm maas-input bg-white"
        >
          {#each syntaxOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </div>
    {/if}

    <div>
      <label for="forkAccessLevel" class="block text-xs font-medium text-gray-600 mb-1">Visibility</label>
      <select
        id="forkAccessLevel"
        bind:value={forkAccessLevel}
        class="w-full px-2 py-1.5 text-sm maas-input bg-white"
      >
        <option value="public">Public</option>
        <option value="private">Private</option>
      </select>
    </div>

    <div>
      <label for="forkExpiration" class="block text-xs font-medium text-gray-600 mb-1">Expires</label>
      <select
        id="forkExpiration"
        bind:value={forkExpiration}
        class="w-full px-2 py-1.5 text-sm maas-input bg-white"
      >
        <option value="never">Never</option>
        <option value="1h">1 Hour</option>
        <option value="24h">24 Hours</option>
        <option value="7d">7 Days</option>
        <option value="30d">30 Days</option>
      </select>
    </div>
  </div>

  {#if relic?.name || relic?.content_type}
    <div class="mt-2 text-xs text-gray-500">
      {#if relic?.name}
        <span class="inline-flex items-center">
          <strong class="mr-1">Original:</strong>
          {relic.name}
        </span>
        {#if relic?.content_type}
          <span class="mx-2">•</span>
        {/if}
      {/if}
      {#if relic?.content_type}
        <span class="inline-flex items-center">
          <strong class="mr-1">Type:</strong>
          {relic.content_type}
        </span>
      {/if}
    </div>
  {/if}
</div>
