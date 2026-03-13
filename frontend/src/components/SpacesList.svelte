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

    let searchTerm = '';
    let sortBy = 'created_at';
    let sortOrder = 'desc';

    $: filteredSpaces = spaces.filter(space => {
        // Apply category filter
        let matchesFilter = true;
        if (filter === 'my') matchesFilter = space.role === 'owner';
        else if (filter === 'shared') matchesFilter = space.role && space.role !== 'owner';
        else if (filter === 'public') matchesFilter = space.visibility === 'public';
        
        if (!matchesFilter) return false;

        // Apply search term
        if (!searchTerm.trim()) return true;
        const term = searchTerm.toLowerCase();
        return (
            space.name.toLowerCase().includes(term) ||
            space.id.toLowerCase().includes(term)
        );
    });

    $: sortedSpaces = [...filteredSpaces].sort((a, b) => {
        let valA = a[sortBy];
        let valB = b[sortBy];
        
        if (sortBy === 'created_at') {
            valA = new Date(valA).getTime();
            valB = new Date(valB).getTime();
        }

        if (sortOrder === 'asc') return valA > valB ? 1 : -1;
        return valA < valB ? 1 : -1;
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

    async function deleteSpace(space) {
        if (!confirm(`Are you sure you want to delete space "${space.name}"?`)) return;
        
        try {
            await spacesApi.delete(space.id);
            spaces = spaces.filter(s => s.id !== space.id);
            showToast("Space deleted", "success");
        } catch (error) {
            console.error("Failed to delete space:", error);
            showToast("Failed to delete space", "error");
        }
    }

    function openSpace(spaceId) {
        dispatch('navigate', { path: 'spaces/' + spaceId });
    }

    function handleSort(column) {
        if (sortBy === column) {
            sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            sortBy = column;
            sortOrder = 'desc';
        }
    }

    function copyToClipboard(text, message) {
        navigator.clipboard.writeText(text).then(() => {
            showToast(message, "success");
        });
    }

    onMount(() => {
        loadSpaces();
    });
</script>

<div class="space-y-6">
    <div class="bg-white shadow-sm rounded-lg border border-gray-200 overflow-hidden">
        <!-- Header -->
        <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50/30">
            <div class="flex items-center gap-3">
                <h2 class="text-lg font-semibold text-gray-900 flex items-center">
                    <i class="fas fa-layer-group text-blue-600 mr-2"></i>
                    Spaces
                </h2>
            </div>
            
            <div class="flex items-center gap-3 flex-1 max-w-2xl ml-8">
                <!-- Search -->
                <div class="relative flex-1">
                    <i class="fa-solid fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                    <input
                        type="text"
                        bind:value={searchTerm}
                        placeholder="Search spaces by name or ID..."
                        class="w-full pl-9 pr-3 py-1.5 text-sm maas-input"
                    />
                </div>

                <!-- Action Buttons -->
                <div class="flex items-center gap-2">
                    <button
                        on:click={() => dispatch('navigate', { path: 'new' })}
                        class="maas-btn-secondary flex items-center gap-2 px-4 py-1.5 whitespace-nowrap"
                        title="Create a new relic globally"
                    >
                        <i class="fas fa-plus"></i>
                        New Relic
                    </button>
                    <button
                        on:click={() => showCreateModal = true}
                        class="maas-btn-primary flex items-center gap-2 px-4 py-1.5 whitespace-nowrap"
                        title="Create a new space to organize relics"
                    >
                        <i class="fas fa-layer-group"></i>
                        New Space
                    </button>
                </div>
            </div>
        </div>

        <!-- Filters Sub-bar -->
        <div class="px-6 py-2 border-b border-gray-100 flex gap-2 bg-white">
            <button
                class="px-3 py-1 rounded-full text-xs font-medium transition-colors {filter === 'all' ? 'bg-gray-800 text-white' : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'}"
                on:click={() => filter = 'all'}
            >
                All
            </button>
            <button
                class="px-3 py-1 rounded-full text-xs font-medium transition-colors {filter === 'my' ? 'bg-blue-600 text-white' : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'}"
                on:click={() => filter = 'my'}
            >
                My Spaces
            </button>
            <button
                class="px-3 py-1 rounded-full text-xs font-medium transition-colors {filter === 'shared' ? 'bg-purple-600 text-white' : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'}"
                on:click={() => filter = 'shared'}
            >
                Shared
            </button>
            <button
                class="px-3 py-1 rounded-full text-xs font-medium transition-colors {filter === 'public' ? 'bg-green-600 text-white' : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'}"
                on:click={() => filter = 'public'}
            >
                Public
            </button>
        </div>

        {#if loading}
            <div class="p-12 text-center">
                <i class="fas fa-spinner fa-spin text-blue-600 text-3xl"></i>
                <p class="text-gray-500 mt-4">Loading spaces...</p>
            </div>
        {:else if sortedSpaces.length === 0}
            <div class="p-16 text-center text-gray-500">
                <i class="fas fa-layer-group text-5xl mb-4 opacity-20"></i>
                <p class="text-lg font-medium text-gray-900">
                    {searchTerm ? `No spaces found matching "${searchTerm}"` : 'No spaces found'}
                </p>
                {#if !searchTerm}
                    <p class="text-sm mt-2">Create a space to start organizing your relics.</p>
                    <button
                        on:click={() => showCreateModal = true}
                        class="mt-6 maas-btn-primary px-6"
                    >
                        Create Space
                    </button>
                {/if}
            </div>
        {:else}
            <div class="overflow-x-auto">
                <table class="w-full maas-table text-sm">
                    <thead>
                        <tr class="text-gray-500 uppercase text-xs tracking-wider bg-gray-50/50 border-b border-gray-200">
                            <th class="cursor-pointer hover:bg-gray-100 transition-colors group px-6 py-3 text-left select-none" on:click={() => handleSort('name')}>
                                <div class="flex items-center gap-1.5">
                                    <span>Name / ID</span>
                                    <i class="fas fa-arrow-up sort-arrow {sortBy === 'name' ? 'active' : ''} {sortOrder === 'desc' && sortBy === 'name' ? 'desc' : ''}"></i>
                                </div>
                            </th>
                            <th class="px-6 py-3 text-left">Role / Visibility</th>
                            <th class="cursor-pointer hover:bg-gray-100 transition-colors group px-6 py-3 text-left select-none" on:click={() => handleSort('relic_count')}>
                                <div class="flex items-center gap-1.5">
                                    <span>Relics</span>
                                    <i class="fas fa-arrow-up sort-arrow {sortBy === 'relic_count' ? 'active' : ''} {sortOrder === 'desc' && sortBy === 'relic_count' ? 'desc' : ''}"></i>
                                </div>
                            </th>
                            <th class="cursor-pointer hover:bg-gray-100 transition-colors group px-6 py-3 text-left select-none" on:click={() => handleSort('created_at')}>
                                <div class="flex items-center gap-1.5">
                                    <span>Created</span>
                                    <i class="fas fa-arrow-up sort-arrow {sortBy === 'created_at' ? 'active' : ''} {sortOrder === 'desc' && sortBy === 'created_at' ? 'desc' : ''}"></i>
                                </div>
                            </th>
                            <th class="px-6 py-3 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        {#each sortedSpaces as space (space.id)}
                            <tr class="hover:bg-blue-50/30 transition-colors group cursor-pointer" on:click={() => openSpace(space.id)}>
                                <td class="px-6 py-4">
                                    <div class="flex items-center gap-3">
                                        <div class="w-8 h-8 rounded bg-gray-100 flex items-center justify-center flex-shrink-0 group-hover:bg-blue-100 transition-colors">
                                            <i class="fas {space.visibility === 'public' ? 'fa-globe text-green-600' : 'fa-lock text-gray-400'} text-sm"></i>
                                        </div>
                                        <div class="min-w-0">
                                            <div class="font-bold text-gray-900 truncate" title={space.name}>{space.name}</div>
                                            <div class="flex items-center gap-1 text-[11px] text-gray-400 font-mono mt-0.5">
                                                <span>{space.id}</span>
                                                <button 
                                                    on:click|stopPropagation={() => copyToClipboard(space.id, 'Space ID copied!')}
                                                    class="hover:text-gray-600 transition-opacity"
                                                >
                                                    <i class="fas fa-copy"></i>
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4">
                                    <div class="flex items-center gap-2">
                                        {#if space.role === 'owner'}
                                            <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-100 text-blue-800 border border-blue-200">
                                                <i class="fas fa-crown mr-1"></i> Owner
                                            </span>
                                        {:else if space.role === 'editor'}
                                            <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-purple-100 text-purple-800 border border-purple-200">
                                                <i class="fas fa-edit mr-1"></i> Editor
                                            </span>
                                        {:else if space.role === 'admin'}
                                            <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-red-100 text-red-800 border border-red-200">
                                                <i class="fas fa-shield-alt mr-1"></i> Admin
                                            </span>
                                        {:else}
                                            <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-gray-100 text-gray-600 border border-gray-200">
                                                <i class="fas fa-eye mr-1"></i> Viewer
                                            </span>
                                        {/if}
                                    </div>
                                </td>
                                <td class="px-6 py-4">
                                    <div class="flex items-center gap-1.5 text-gray-600">
                                        <i class="fas fa-file-alt text-gray-300"></i>
                                        <span class="font-medium">{space.relic_count}</span>
                                    </div>
                                </td>
                                <td class="px-6 py-4 text-gray-500 text-xs">
                                    {new Date(space.created_at).toLocaleDateString()}
                                </td>
                                <td class="px-6 py-4 text-right">
                                    <div class="flex justify-end gap-1">
                                        {#if space.role === 'owner' || space.role === 'admin' || space.role === 'editor'}
                                            <button
                                                on:click|stopPropagation={() => dispatch('navigate', { path: 'new?space=' + space.id })}
                                                class="p-2 text-green-600 hover:bg-green-100 rounded transition-colors"
                                                title="New Relic in this Space"
                                            >
                                                <i class="fas fa-plus text-xs"></i>
                                            </button>
                                        {/if}
                                        <button
                                            on:click|stopPropagation={() => copyToClipboard(`${window.location.origin}/spaces/${space.id}`, 'Space link copied to clipboard!')}
                                            class="p-2 text-indigo-600 hover:bg-indigo-100 rounded transition-colors"
                                            title="Share Space"
                                        >
                                            <i class="fas fa-share text-xs"></i>
                                        </button>
                                        <button
                                            on:click|stopPropagation={() => openSpace(space.id)}
                                            class="p-2 text-blue-600 hover:bg-blue-100 rounded transition-colors"
                                            title="Open Space"
                                        >
                                            <i class="fas fa-external-link-alt text-xs"></i>
                                        </button>
                                        {#if space.role === 'owner' || space.role === 'admin'}
                                            <button
                                                on:click|stopPropagation={() => deleteSpace(space)}
                                                class="p-2 text-red-600 hover:bg-red-100 rounded transition-colors"
                                                title="Delete Space"
                                            >
                                                <i class="fas fa-trash text-xs"></i>
                                            </button>
                                        {/if}
                                    </div>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}
    </div>
</div>

<style>
    .sort-arrow {
        font-size: 9px;
        transition: all 0.2s ease;
        opacity: 0;
        color: #9ca3af;
    }

    .group:hover .sort-arrow {
        opacity: 0.5;
    }

    .sort-arrow.active {
        opacity: 1 !important;
        color: #2563eb !important;
    }

    .sort-arrow.desc {
        transform: rotate(180deg);
    }
</style>

<!-- Create Space Modal -->
{#if showCreateModal}
    <div class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h2 class="text-xl font-bold mb-4">Create New Space</h2>

            <div class="space-y-4">
                <div>
                    <label for="newSpaceName" class="block text-sm font-medium text-gray-700 mb-1">Space Name</label>
                    <input
                        id="newSpaceName"
                        type="text"
                        bind:value={newSpaceName}
                        placeholder="e.g. My Project, Research Notes"
                        class="maas-input w-full"
                        on:keydown={(e) => e.key === 'Enter' && createSpace()}
                    />
                </div>

                <div>
                    <div class="block text-sm font-medium text-gray-700 mb-1">Visibility</div>
                    <div class="grid grid-cols-2 gap-3">
                        <label for="vis-public" class="flex items-center p-3 border rounded-lg cursor-pointer transition-colors {newSpaceVisibility === 'public' ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:bg-gray-50'}">
                            <input id="vis-public" type="radio" bind:group={newSpaceVisibility} value="public" class="hidden">
                            <i class="fas fa-globe text-green-600 mr-2"></i>
                            <div>
                                <div class="font-medium text-sm">Public</div>
                                <div class="text-xs text-gray-500">Visible to everyone</div>
                            </div>
                        </label>
                        <label for="vis-private" class="flex items-center p-3 border rounded-lg cursor-pointer transition-colors {newSpaceVisibility === 'private' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'}">
                            <input id="vis-private" type="radio" bind:group={newSpaceVisibility} value="private" class="hidden">
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