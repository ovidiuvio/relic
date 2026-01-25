<script>
  import { onMount, createEventDispatcher } from 'svelte';
  import { getFeeds, createFeed, addRelicToFeed } from '../services/api';
  import { showToast } from '../stores/toastStore';

  export let open = false;
  export let relicId;
  export let relicName;

  const dispatch = createEventDispatcher();

  let feeds = [];
  let loading = true;
  let newFeedName = "";
  let isCreating = false;
  let isAdding = false;

  async function loadFeeds() {
    loading = true;
    try {
      const response = await getFeeds();
      feeds = response.data.feeds;
    } catch (error) {
      console.error('Failed to load feeds:', error);
      showToast('Failed to load feeds', 'error');
    } finally {
      loading = false;
    }
  }

  async function handleCreateFeed() {
    if (!newFeedName.trim()) return;
    isCreating = true;
    try {
      const response = await createFeed({ name: newFeedName });
      const newFeed = response.data;
      feeds = [newFeed, ...feeds];
      newFeedName = "";
      showToast('Feed created', 'success');
    } catch (error) {
      console.error('Failed to create feed:', error);
      showToast('Failed to create feed', 'error');
    } finally {
      isCreating = false;
    }
  }

  async function handleAddToFeed(feed) {
    if (isAdding) return;
    isAdding = true;
    try {
        await addRelicToFeed(feed.id, relicId);
        showToast(`Added "${relicName}" to feed "${feed.name}"`, 'success');
        dispatch('close');
        open = false;
    } catch (error) {
        console.error('Failed to add to feed:', error);
        if (error.response && error.response.status === 409) {
             showToast(`"${relicName}" is already in feed "${feed.name}"`, 'info');
        } else {
             showToast('Failed to add to feed', 'error');
        }
    } finally {
        isAdding = false;
    }
  }

  function close() {
    open = false;
    dispatch('close');
  }

  $: if (open) {
    loadFeeds();
  }
</script>

{#if open}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" on:click={close}>
    <div class="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 overflow-hidden" on:click|stopPropagation>
      <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
        <h3 class="text-lg font-bold text-gray-800">Add to Feed</h3>
        <button on:click={close} class="text-gray-500 hover:text-gray-700">
          <i class="fas fa-times"></i>
        </button>
      </div>

      <div class="p-6">
        <p class="text-sm text-gray-600 mb-4">Select a feed to add <span class="font-bold">{relicName}</span>:</p>

        <!-- Create new feed -->
        <form on:submit|preventDefault={handleCreateFeed} class="flex gap-2 mb-4">
            <input
                type="text"
                bind:value={newFeedName}
                placeholder="New Feed Name"
                class="flex-1 text-sm border border-gray-300 rounded px-3 py-2 focus:outline-none focus:border-orange-500"
                maxlength="50"
            />
            <button
                type="submit"
                disabled={isCreating || !newFeedName.trim()}
                class="bg-gray-800 text-white px-4 py-2 rounded hover:bg-black disabled:opacity-50 text-sm font-medium"
            >
                <i class="fas fa-plus mr-1"></i> Create
            </button>
        </form>

        <div class="max-h-60 overflow-y-auto border border-gray-200 rounded-lg">
            {#if loading}
                <div class="flex justify-center py-8">
                    <i class="fas fa-spinner fa-spin text-orange-500 text-xl"></i>
                </div>
            {:else if feeds.length === 0}
                <div class="text-center text-gray-500 py-8 text-sm">
                    No feeds available. Create one above!
                </div>
            {:else}
                <div class="divide-y divide-gray-100">
                    {#each feeds as feed}
                        <button
                            on:click={() => handleAddToFeed(feed)}
                            disabled={isAdding}
                            class="w-full text-left px-4 py-3 hover:bg-orange-50 transition-colors flex items-center justify-between group"
                        >
                            <span class="font-medium text-gray-700 group-hover:text-orange-800">{feed.name}</span>
                            <span class="text-xs text-gray-400 group-hover:text-orange-600">{feed.relic_count || 0} relics</span>
                        </button>
                    {/each}
                </div>
            {/if}
        </div>
      </div>
    </div>
  </div>
{/if}
