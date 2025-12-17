<script>
  import { createEventDispatcher } from "svelte";
  import { updateRelic } from "../services/api";
  import { showToast } from "../stores/toastStore";

  export let open = false;
  export let relic;
  export let relicId;

  const dispatch = createEventDispatcher();

  let loading = false;
  let form = {
    name: "",
    content_type: "",
    access_level: "",
    expires_in: "never",
  };

  $: if (relic) {
    form = {
      name: relic.name || "",
      content_type: relic.content_type || "",
      access_level: relic.access_level || "public",
      expires_in: relic.expires_at ? "custom" : "never", // Simplification, backend handles raw dates but we can just offer 'never' or keep existing for now.
      // Ideally we would calculate expires_in from expires_at but that's complex without date-fns.
      // For now, let's just let them set a NEW expiry or clear it.
    };
  }

  // expiry options
  const expiryOptions = [
    { value: "never", label: "Never" },
    { value: "1h", label: "1 Hour" },
    { value: "24h", label: "24 Hours" },
    { value: "7d", label: "7 Days" },
    { value: "30d", label: "30 Days" },
  ];

  async function handleSubmit() {
    loading = true;
    try {
      const updateData = { ...form };
      if (updateData.expires_in === "custom") {
        delete updateData.expires_in; // Don't send 'custom', only if they selected a duration.
        // If they left it as 'custom' (meaning existing expiry), we send nothing for expires_in
        // so backend leaves it alone.
      }

      const updatedRelic = await updateRelic(relicId, updateData);
      showToast("Relic updated successfully", "success");
      dispatch("updated", updatedRelic.data);
      open = false;
    } catch (error) {
      console.error("Failed to update relic:", error);
      showToast(error.response?.data?.detail || "Failed to update relic", "error");
    } finally {
      loading = false;
    }
  }

  function close() {
    open = false;
  }
</script>

{#if open}
  <div class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      <!-- Background overlay -->
      <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" on:click={close}></div>

      <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

      <!-- Modal panel -->
      <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
        <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <div class="sm:flex sm:items-start">
            <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-blue-100 sm:mx-0 sm:h-10 sm:w-10">
              <i class="fas fa-edit text-blue-600"></i>
            </div>
            <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
              <h3 class="text-lg leading-6 font-medium text-gray-900" id="modal-title">Edit Relic</h3>
              <div class="mt-4 space-y-4">

                <!-- Name -->
                <div>
                  <label for="name" class="block text-sm font-medium text-gray-700">Name</label>
                  <input
                    type="text"
                    name="name"
                    id="name"
                    bind:value={form.name}
                    class="mt-1 focus:ring-blue-500 focus:border-blue-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md"
                  />
                </div>

                <!-- Content Type -->
                <div>
                  <label for="content_type" class="block text-sm font-medium text-gray-700">Content Type</label>
                  <input
                    type="text"
                    name="content_type"
                    id="content_type"
                    bind:value={form.content_type}
                    class="mt-1 focus:ring-blue-500 focus:border-blue-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md"
                  />
                </div>

                <!-- Visibility -->
                <div>
                  <label for="access_level" class="block text-sm font-medium text-gray-700">Visibility</label>
                  <select
                    id="access_level"
                    name="access_level"
                    bind:value={form.access_level}
                    class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                  >
                    <option value="public">Public</option>
                    <option value="private">Private</option>
                  </select>
                </div>

                <!-- Expiry -->
                <div>
                  <label for="expires_in" class="block text-sm font-medium text-gray-700">Expires</label>
                  <select
                    id="expires_in"
                    name="expires_in"
                    bind:value={form.expires_in}
                    class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                  >
                    {#if relic.expires_at}
                      <option value="custom">Keep existing expiry</option>
                    {/if}
                    {#each expiryOptions as option}
                      <option value={option.value}>{option.label}</option>
                    {/each}
                  </select>
                  {#if relic.expires_at && form.expires_in === 'custom'}
                    <p class="mt-1 text-xs text-gray-500">
                      Currently expires at: {new Date(relic.expires_at).toLocaleString()}
                    </p>
                  {/if}
                </div>

              </div>
            </div>
          </div>
        </div>
        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button
            type="button"
            on:click={handleSubmit}
            disabled={loading}
            class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
          >
            {#if loading}
              <i class="fas fa-spinner fa-spin mr-2"></i> Saving...
            {:else}
              Save Changes
            {/if}
          </button>
          <button
            type="button"
            on:click={close}
            class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}
