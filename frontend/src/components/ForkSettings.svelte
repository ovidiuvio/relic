<script>
  import Select from "svelte-select";
  import { getAvailableSyntaxOptions } from "../services/typeUtils";

  export let forkName = "";
  export let forkLanguage = "auto";
  export let forkAccessLevel = "public";
  export let forkExpiration = "never";
  export let forkTags = "";
  export let isBinary = false;
  export let relic = null;

  const syntaxOptions = getAvailableSyntaxOptions();

  // Find the currently selected option for svelte-select
  $: selectedType = syntaxOptions.find((opt) => opt.value === forkLanguage) || syntaxOptions[0];

  function handleTypeChange(event) {
    forkLanguage = event.detail?.value || "auto";
  }
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
      <div class="fork-type-select">
        <label for="forkLanguage" class="block text-xs font-medium text-gray-600 mb-1">Type</label>
        <Select
          items={syntaxOptions}
          value={selectedType}
          on:change={handleTypeChange}
          itemId="value"
          label="label"
          placeholder="Search or select language..."
          searchable={true}
          clearable={false}
          showChevron={true}
          --border="1px solid #AEA79F"
          --border-radius="2px"
          --border-focused="1px solid #E95420"
          --font-size="0.875rem"
          --padding="0.15rem 0.5rem"
          --height="24px"
          --placeholder-color="rgb(156 163 175)"
          --item-padding="0.5rem 0.75rem"
          --background="white"
          --list-background="white"
          --list-border="1px solid #AEA79F"
          --list-border-radius="2px"
          --list-shadow="0 4px 6px -1px rgb(0 0 0 / 0.1)"
          --input-color="rgb(17 24 39)"
          --item-color="rgb(17 24 39)"
          --item-hover-bg="rgb(243 244 246)"
          --item-is-active-bg="rgb(229 231 235)"
          --item-is-active-color="rgb(17 24 39)"
          --chevron-height="20px"
          --chevron-width="20px"
          --chevron-color="rgb(107, 114, 128)"
        />
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

    <div class="sm:col-span-2 lg:col-span-1">
      <label for="forkTags" class="block text-xs font-medium text-gray-600 mb-1">Tags (comma separated)</label>
      <input
        type="text"
        id="forkTags"
        bind:value={forkTags}
        placeholder="tag1, tag2..."
        class="w-full px-2 py-1.5 text-sm maas-input border border-gray-300 rounded"
      />
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
