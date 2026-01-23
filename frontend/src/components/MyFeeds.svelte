<script>
  import { onMount } from 'svelte';
  import { showToast } from '../stores/toastStore';
  import { getFeeds, createFeed, deleteFeed, getFeed, removeRelicFromFeed } from '../services/api';
  import { getDefaultItemsPerPage, getTypeLabel } from '../services/typeUtils';
  import { filterRelics, sortData, calculateTotalPages, paginateData, clampPage } from '../services/utils/paginationUtils';
  import RelicTable from './RelicTable.svelte';

  export let tagFilter = null;

  let feeds = [];
  let selectedFeed = null;
  let loadingFeeds = true;
  let loadingRelics = false;
  let newFeedName = "";
  let isCreating = false;

  // RelicTable props
  let relics = [];
  let searchTerm = '';
  let currentPage = 1;
  let itemsPerPage = 20;
  let sortBy = 'date';
  let sortOrder = 'desc';

  $: filteredRelics = filterRelics(relics, searchTerm, getTypeLabel);
  $: sortedRelics = sortData(filteredRelics, sortBy, sortOrder);
  $: totalPages = calculateTotalPages(sortedRelics, itemsPerPage);
  $: paginatedRelics = paginateData(sortedRelics, currentPage, itemsPerPage);

  $: customActions = selectedFeed ? [
    {
        icon: 'fa-minus-circle',
        color: 'red',
        title: 'Remove from Feed',
        handler: handleRemoveFromFeed
    }
  ] : [];

  async function loadFeeds() {
    loadingFeeds = true;
    try {
      const response = await getFeeds();
      feeds = response.data.feeds;
      if (feeds.length > 0 && !selectedFeed) {
        selectFeed(feeds[0]);
      }
    } catch (error) {
      console.error('Failed to load feeds:', error);
      showToast('Failed to load feeds', 'error');
    } finally {
      loadingFeeds = false;
    }
  }

  async function selectFeed(feed) {
    selectedFeed = feed;
    loadingRelics = true;
    try {
      const response = await getFeed(feed.id);
      relics = response.data.relics || [];
      // Update the feed in the list with fresh data (e.g. counts)
      feeds = feeds.map(f => f.id === feed.id ? response.data : f);
    } catch (error) {
      console.error('Failed to load feed relics:', error);
      showToast('Failed to load feed content', 'error');
    } finally {
      loadingRelics = false;
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
      selectFeed(newFeed);
    } catch (error) {
      console.error('Failed to create feed:', error);
      showToast('Failed to create feed', 'error');
    } finally {
      isCreating = false;
    }
  }

  async function handleDeleteFeed(feed, event) {
    if (event) event.stopPropagation();
    if (!confirm(`Delete feed "${feed.name}"?`)) return;

    try {
      await deleteFeed(feed.id);
      feeds = feeds.filter(f => f.id !== feed.id);
      showToast('Feed deleted', 'success');
      if (selectedFeed && selectedFeed.id === feed.id) {
        selectedFeed = feeds.length > 0 ? feeds[0] : null;
        if (selectedFeed) selectFeed(selectedFeed);
        else relics = [];
      }
    } catch (error) {
      console.error('Failed to delete feed:', error);
      showToast('Failed to delete feed', 'error');
    }
  }

  async function handleRemoveFromFeed(relic) {
    if (!selectedFeed) return;
    if (!confirm(`Remove "${relic.name}" from feed?`)) return;

    try {
        await removeRelicFromFeed(selectedFeed.id, relic.id);
        relics = relics.filter(r => r.id !== relic.id);
        // Update count in sidebar
        selectedFeed.relic_count = Math.max(0, (selectedFeed.relic_count || 1) - 1);
        feeds = feeds.map(f => f.id === selectedFeed.id ? selectedFeed : f);

        showToast('Relic removed from feed', 'success');
    } catch (error) {
        console.error('Failed to remove relic from feed:', error);
        showToast('Failed to remove relic', 'error');
    }
  }

  function goToPage(page) {
    currentPage = clampPage(page, totalPages);
  }

  onMount(() => {
    itemsPerPage = getDefaultItemsPerPage();
    loadFeeds();
  });
</script>

<div class="grid grid-cols-1 md:grid-cols-4 gap-6 px-4 sm:px-0 h-full">
    <!-- Sidebar -->
    <div class="md:col-span-1 bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col h-[calc(100vh-8rem)]">
        <div class="p-4 border-b border-gray-200">
            <h2 class="text-lg font-bold text-gray-800 mb-4"><i class="fas fa-rss text-orange-500 mr-2"></i>Feeds</h2>

            <form on:submit|preventDefault={handleCreateFeed} class="flex gap-2">
                <input
                    type="text"
                    bind:value={newFeedName}
                    placeholder="New Feed Name"
                    class="flex-1 text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:border-orange-500"
                    maxlength="50"
                />
                <button
                    type="submit"
                    disabled={isCreating || !newFeedName.trim()}
                    class="bg-orange-600 text-white px-3 py-1 rounded hover:bg-orange-700 disabled:opacity-50 text-sm"
                >
                    <i class="fas fa-plus"></i>
                </button>
            </form>
        </div>

        <div class="flex-1 overflow-y-auto p-2 space-y-1">
            {#if loadingFeeds}
                <div class="flex justify-center py-4">
                    <i class="fas fa-spinner fa-spin text-orange-500"></i>
                </div>
            {:else if feeds.length === 0}
                <div class="text-center text-gray-500 py-4 text-sm">
                    No feeds yet. Create one!
                </div>
            {:else}
                {#each feeds as feed}
                    <div
                        class="group flex items-center justify-between p-2 rounded cursor-pointer {selectedFeed && selectedFeed.id === feed.id ? 'bg-orange-50 text-orange-800 border-l-4 border-orange-500' : 'hover:bg-gray-50 text-gray-700'}"
                        on:click={() => selectFeed(feed)}
                    >
                        <div class="flex-1 truncate">
                            <div class="font-medium truncate">{feed.name}</div>
                            <div class="text-xs text-gray-400">{feed.relic_count || 0} relics</div>
                        </div>
                        <button
                            on:click={(e) => handleDeleteFeed(feed, e)}
                            class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 p-1"
                            title="Delete Feed"
                        >
                            <i class="fas fa-trash text-xs"></i>
                        </button>
                    </div>
                {/each}
            {/if}
        </div>
    </div>

    <!-- Main Content -->
    <div class="md:col-span-3">
        {#if selectedFeed}
            <RelicTable
                data={sortedRelics}
                loading={loadingRelics}
                bind:searchTerm
                bind:currentPage
                bind:itemsPerPage
                bind:sortBy
                bind:sortOrder
                {totalPages}
                paginatedData={paginatedRelics}
                title={selectedFeed.name}
                titleIcon="fa-rss"
                titleIconColor="text-orange-500"
                {tagFilter}
                emptyMessage="No relics in this feed"
                emptyMessageWithSearch="No relics found"
                emptyIcon="fa-box-open"
                emptyAction="Browse recent relics to add some!"
                tableId="feed-relics"
                onEdit={null}
                onDelete={null}
                customActions={customActions}
                on:tag-click
                {goToPage}
            />
        {:else if !loadingFeeds && feeds.length > 0}
            <div class="h-full flex flex-col items-center justify-center text-gray-400 bg-white rounded-lg border border-gray-200 p-12">
                <i class="fas fa-arrow-left text-4xl mb-4"></i>
                <p>Select a feed to view its relics</p>
            </div>
        {:else if !loadingFeeds}
            <div class="h-full flex flex-col items-center justify-center text-gray-400 bg-white rounded-lg border border-gray-200 p-12">
                <i class="fas fa-plus-circle text-4xl mb-4"></i>
                <p>Create a feed to get started</p>
            </div>
        {/if}
    </div>
</div>
