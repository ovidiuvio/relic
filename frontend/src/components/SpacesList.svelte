<script>
    import { onMount, createEventDispatcher } from 'svelte';
    import { spaces as spacesApi } from '../services/api';
    import { showToast } from '../stores/toastStore';

    const dispatch = createEventDispatcher();

    let spaces = [];
    let loading = true;
    let showCreateModal = false;
    let newSpaceName = '';
    let newSpaceVisibility = 'public';
    let creating = false;

    let filter = 'all'; // all, my, shared, public

    $: filteredSpaces = spaces.filter(space => {
        if (filter === 'my') return space.role === 'owner';
        if (filter === 'shared') return space.role && space.role !== 'owner';
        if (filter === 'public') return space.visibility === 'public';
        return true; // all
    });

    async function loadSpaces() {
        loading = true;
        try {
            spaces = await spacesApi.list();
        } catch (error) {
            console.error("Failed to load spaces:", error);
            showToast("Failed to load spaces", "error");
        } finally {
            loading = false;
        }
    }

    async function createSpace() {
        if (!newSpaceName.trim()) {
            showToast("Space name is required", "error");
            return;
        }

        creating = true;
        try {
            const space = await spacesApi.create({
                name: newSpaceName.trim(),
                visibility: newSpaceVisibility
            });
            spaces = [space, ...spaces];
            showCreateModal = false;
            newSpaceName = '';
            newSpaceVisibility = 'public';
            showToast("Space created successfully", "success");
        } catch (error) {
            console.error("Failed to create space:", error);
            showToast("Failed to create space", "error");
        } finally {
            creating = false;
        }
    }

    function openSpace(spaceId) {
        dispatch('navigate', { spaceId });
    }

    onMount(() => {
        loadSpaces();
    });
</script>

<div class="space-y-6">
    <div class="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm border border-gray-200">
        <h1 class="text-2xl font-bold text-gray-800">Spaces</h1>
        <button
            on:click={() => showCreateModal = true}
            class="maas-btn-primary flex items-center gap-2"
        >
            <i class="fas fa-plus"></i>
            New Space
        </button>
    </div>

    <!-- Filters -->
    <div class="flex gap-2">
        <button
            class="px-4 py-2 rounded-full text-sm font-medium transition-colors {filter === 'all' ? 'bg-gray-800 text-white' : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'}"
            on:click={() => filter = 'all'}
        >
            All Spaces
        </button>
        <button
            class="px-4 py-2 rounded-full text-sm font-medium transition-colors {filter === 'my' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'}"
            on:click={() => filter = 'my'}
        >
            My Spaces
        </button>
        <button
            class="px-4 py-2 rounded-full text-sm font-medium transition-colors {filter === 'shared' ? 'bg-purple-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'}"
            on:click={() => filter = 'shared'}
        >
            Shared with Me
        </button>
        <button
            class="px-4 py-2 rounded-full text-sm font-medium transition-colors {filter === 'public' ? 'bg-green-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'}"
            on:click={() => filter = 'public'}
        >
            Public
        </button>
    </div>

    {#if loading}
        <div class="flex justify-center items-center py-12">
            <i class="fas fa-spinner fa-spin text-3xl text-gray-400"></i>
        </div>
    {:else if filteredSpaces.length === 0}
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <i class="fas fa-layer-group text-4xl text-gray-300 mb-4"></i>
            <h3 class="text-lg font-medium text-gray-900 mb-2">No spaces found</h3>
            <p class="text-gray-500 mb-6">Create a space to organize your relics or collaborate with others.</p>
            {#if filter === 'all' || filter === 'my'}
                <button
                    on:click={() => showCreateModal = true}
                    class="maas-btn-primary"
                >
                    Create Space
                </button>
            {/if}
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each filteredSpaces as space (space.id)}
                <div
                    class="bg-white rounded-lg shadow-sm border border-gray-200 hover:border-gray-300 hover:shadow-md transition-all cursor-pointer overflow-hidden flex flex-col h-48"
                    on:click={() => openSpace(space.id)}
                >
                    <div class="p-5 flex-1 flex flex-col">
                        <div class="flex justify-between items-start mb-2">
                            <h3 class="text-lg font-bold text-gray-900 truncate pr-2" title={space.name}>{space.name}</h3>
                            <div class="flex shrink-0">
                                {#if space.visibility === 'public'}
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-green-100 text-green-800" title="Public Space">
                                        <i class="fas fa-globe mr-1"></i> Public
                                    </span>
                                {:else}
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-800" title="Private Space">
                                        <i class="fas fa-lock mr-1"></i> Private
                                    </span>
                                {/if}
                            </div>
                        </div>

                        <div class="mt-auto">
                            <div class="flex items-center text-sm text-gray-500 mb-3">
                                <i class="fas fa-file-alt w-5 text-center mr-1"></i>
                                {space.relic_count} {space.relic_count === 1 ? 'relic' : 'relics'}
                            </div>

                            <div class="flex items-center justify-between text-xs text-gray-400 border-t border-gray-100 pt-3">
                                <span>{new Date(space.created_at).toLocaleDateString()}</span>
                                {#if space.role === 'owner'}
                                    <span class="text-blue-600 font-medium"><i class="fas fa-crown mr-1"></i>Owner</span>
                                {:else if space.role === 'editor'}
                                    <span class="text-purple-600 font-medium"><i class="fas fa-edit mr-1"></i>Editor</span>
                                {:else if space.role === 'viewer'}
                                    <span class="text-gray-500 font-medium"><i class="fas fa-eye mr-1"></i>Viewer</span>
                                {/if}
                            </div>
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>

<!-- Create Space Modal -->
{#if showCreateModal}
    <div class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h2 class="text-xl font-bold mb-4">Create New Space</h2>

            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Space Name</label>
                    <input
                        type="text"
                        bind:value={newSpaceName}
                        placeholder="e.g. My Project, Research Notes"
                        class="maas-input w-full"
                        on:keydown={(e) => e.key === 'Enter' && createSpace()}
                    />
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Visibility</label>
                    <div class="grid grid-cols-2 gap-3">
                        <label class="flex items-center p-3 border rounded-lg cursor-pointer transition-colors {newSpaceVisibility === 'public' ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:bg-gray-50'}">
                            <input type="radio" bind:group={newSpaceVisibility} value="public" class="hidden">
                            <i class="fas fa-globe text-green-600 mr-2"></i>
                            <div>
                                <div class="font-medium text-sm">Public</div>
                                <div class="text-xs text-gray-500">Visible to everyone</div>
                            </div>
                        </label>
                        <label class="flex items-center p-3 border rounded-lg cursor-pointer transition-colors {newSpaceVisibility === 'private' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'}">
                            <input type="radio" bind:group={newSpaceVisibility} value="private" class="hidden">
                            <i class="fas fa-lock text-gray-600 mr-2"></i>
                            <div>
                                <div class="font-medium text-sm">Private</div>
                                <div class="text-xs text-gray-500">Only invited users</div>
                            </div>
                        </label>
                    </div>
                </div>
            </div>

            <div class="mt-6 flex justify-end gap-3">
                <button
                    on:click={() => showCreateModal = false}
                    class="maas-btn-secondary"
                    disabled={creating}
                >
                    Cancel
                </button>
                <button
                    on:click={createSpace}
                    class="maas-btn-primary"
                    disabled={creating || !newSpaceName.trim()}
                >
                    {#if creating}
                        <i class="fas fa-spinner fa-spin mr-2"></i>
                        Creating...
                    {:else}
                        Create Space
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}