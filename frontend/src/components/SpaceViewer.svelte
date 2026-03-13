<script>
    import { onMount, createEventDispatcher } from 'svelte';
    import { spaces as spacesApi } from '../services/api';
    import { showToast } from '../stores/toastStore';
    import { getTypeLabel, getDefaultItemsPerPage } from '../services/typeUtils';
    import { filterRelics, sortData, calculateTotalPages, paginateData, clampPage } from '../services/utils/paginationUtils';
    import RelicTable from './RelicTable.svelte';

    export let spaceId;
    export let tagFilter = null;

    const dispatch = createEventDispatcher();

    let space = null;
    let relics = [];
    let loading = true;
    let loadingRelics = true;

    // Access management state
    let accessList = [];
    let showAccessModal = false;
    let loadingAccess = false;
    let newAccessClientId = '';
    let newAccessRole = 'viewer';
    let managingAccess = false;

    // Edit state
    let showEditModal = false;
    let editName = '';
    let editVisibility = 'public';
    let updating = false;

    // Add relic state
    let showAddRelicModal = false;
    let newRelicId = '';
    let addingRelic = false;
    let searchTerm = '';
    let currentPage = 1;
    let itemsPerPage = 20;
    let sortBy = 'date';
    let sortOrder = 'desc';

    $: canEdit = space?.role === 'owner' || space?.role === 'editor' || space?.role === 'admin';
    $: isOwner = space?.role === 'owner' || space?.role === 'admin';

    // Search and pagination logic
    $: filteredRelics = filterRelics(relics, searchTerm, getTypeLabel, tagFilter);
    $: sortedRelics = sortData(filteredRelics, sortBy, sortOrder);
    $: totalPages = calculateTotalPages(sortedRelics, itemsPerPage);
    $: paginatedRelics = paginateData(sortedRelics, currentPage, itemsPerPage);

    function goToPage(page) {
        currentPage = clampPage(page, totalPages);
    }

    $: if (spaceId) {
        loadSpace();
    }

    async function loadSpace() {
        loading = true;
        try {
            space = await spacesApi.get(spaceId);
            await loadRelics();
        } catch (error) {
            console.error("Failed to load space:", error);
            showToast("Failed to load space", "error");
            dispatch('navigate', { path: 'spaces' });
        } finally {
            loading = false;
        }
    }

    onMount(() => {
        // Initial load is handled by reactive statement if spaceId is present
    });

    async function loadRelics() {
        loadingRelics = true;
        try {
            const data = await spacesApi.getRelics(spaceId);
            relics = data.relics;
        } catch (error) {
            console.error("Failed to load space relics:", error);
            showToast("Failed to load relics", "error");
        } finally {
            loadingRelics = false;
        }
    }

    async function loadAccessList() {
        if (!isOwner && space.role !== 'editor') return;

        loadingAccess = true;
        try {
            accessList = await spacesApi.getAccessList(spaceId);
        } catch (error) {
            console.error("Failed to load access list:", error);
            showToast("Failed to load access list", "error");
        } finally {
            loadingAccess = false;
        }
    }

    function openEditModal() {
        editName = space.name;
        editVisibility = space.visibility;
        showEditModal = true;
    }

    async function updateSpace() {
        if (!editName.trim()) {
            showToast("Space name is required", "error");
            return;
        }

        updating = true;
        try {
            space = await spacesApi.update(spaceId, {
                name: editName.trim(),
                visibility: editVisibility
            });
            showEditModal = false;
            showToast("Space updated successfully", "success");
        } catch (error) {
            console.error("Failed to update space:", error);
            showToast("Failed to update space", "error");
        } finally {
            updating = false;
        }
    }

    async function deleteSpace() {
        if (!confirm("Are you sure you want to delete this space? This will not delete the relics inside it.")) {
            return;
        }

        updating = true;
        try {
            await spacesApi.delete(spaceId);
            showToast("Space deleted successfully", "success");
            dispatch('navigate', { path: 'spaces' });
        } catch (error) {
            console.error("Failed to delete space:", error);
            showToast("Failed to delete space", "error");
            updating = false;
        }
    }

    async function addRelicToSpace() {
        if (!newRelicId.trim()) {
            showToast("Relic ID is required", "error");
            return;
        }

        addingRelic = true;
        try {
            await spacesApi.addRelic(spaceId, newRelicId.trim());
            await loadRelics();
            showAddRelicModal = false;
            newRelicId = '';
            showToast("Relic added successfully", "success");

            // Update space count
            space = { ...space, relic_count: space.relic_count + 1 };
        } catch (error) {
            console.error("Failed to add relic:", error);
            showToast(error.response?.data?.detail || "Failed to add relic", "error");
        } finally {
            addingRelic = false;
        }
    }

    async function removeRelic(relic) {
        if (!confirm("Remove this relic from the space?")) return;

        try {
            const relicId = relic.id || relic;
            await spacesApi.removeRelic(spaceId, relicId);
            relics = relics.filter(r => r.id !== relicId);
            showToast("Relic removed", "success");

            // Update space count
            space = { ...space, relic_count: Math.max(0, space.relic_count - 1) };
        } catch (error) {
            console.error("Failed to remove relic:", error);
            showToast("Failed to remove relic", "error");
        }
    }

    async function addAccess() {
        if (!newAccessClientId.trim()) {
            showToast("Client ID is required", "error");
            return;
        }

        managingAccess = true;
        try {
            const access = await spacesApi.addAccess(spaceId, {
                client_id: newAccessClientId.trim(),
                role: newAccessRole
            });

            // Update local list
            const index = accessList.findIndex(a => a.client_id === access.client_id);
            if (index >= 0) {
                accessList[index] = access;
            } else {
                accessList = [...accessList, access];
            }

            newAccessClientId = '';
            showToast("Access granted successfully", "success");
        } catch (error) {
            console.error("Failed to grant access:", error);
            showToast(error.response?.data?.detail || "Failed to grant access", "error");
        } finally {
            managingAccess = false;
        }
    }

    async function removeAccess(clientId) {
        if (!confirm("Remove this user's access?")) return;

        try {
            await spacesApi.removeAccess(spaceId, clientId);
            accessList = accessList.filter(a => a.client_id !== clientId);
            showToast("Access removed", "success");
        } catch (error) {
            console.error("Failed to remove access:", error);
            showToast("Failed to remove access", "error");
        }
    }

    function handleTagClick(event) {
        dispatch('tag-click', event.detail);
    }

    function handleRelicClick(relicId) {
        dispatch('navigate', { path: relicId });
    }

    onMount(() => {
        itemsPerPage = getDefaultItemsPerPage();
        loadSpace();
    });
</script>

{#if loading}
    <div class="flex justify-center items-center py-12">
        <i class="fas fa-spinner fa-spin text-3xl text-gray-400"></i>
    </div>
{:else if space}
    <div class="space-y-6">
        <div class="bg-white shadow-sm rounded-lg border border-gray-200 overflow-hidden">
            <!-- Space Header -->
            <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50/50">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-3 mb-1">
                            <h1 class="text-xl font-bold text-gray-900 truncate">{space.name}</h1>
                            {#if tagFilter}
                                <div class="flex items-center animate-fade-in">
                                    <div class="h-4 w-[1px] bg-gray-300 mx-1"></div>
                                    <div class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-[#fdf2f8] text-[#772953] border border-[#fbcfe8] shadow-sm ml-1">
                                        <i class="fas fa-tag text-[9px] opacity-70"></i>
                                        <span>{tagFilter}</span>
                                        <button
                                          on:click|stopPropagation={() => dispatch('clear-tag-filter')}
                                          class="ml-1 text-[#772953] hover:text-red-700 transition-colors focus:outline-none flex items-center"
                                          title="Clear tag filter"
                                        >
                                          <i class="fas fa-times-circle text-[10px]"></i>
                                        </button>
                                    </div>
                                </div>
                            {/if}
                            <div class="flex gap-1.5">
                                {#if space.visibility === 'public'}
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-green-100 text-green-800 border border-green-200">
                                        <i class="fas fa-globe mr-1.5"></i> Public
                                    </span>
                                {:else}
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-gray-100 text-gray-600 border border-gray-200">
                                        <i class="fas fa-lock mr-1.5"></i> Private
                                    </span>
                                {/if}
                                {#if space.role === 'owner'}
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-blue-100 text-blue-800 border border-blue-200">
                                        <i class="fas fa-crown mr-1.5"></i> Owner
                                    </span>
                                {:else if space.role === 'admin'}
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-red-100 text-red-800 border border-red-200">
                                        <i class="fas fa-shield-alt mr-1.5"></i> Admin
                                    </span>
                                {:else if space.role === 'editor'}
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-purple-100 text-purple-800 border border-purple-200">
                                        <i class="fas fa-edit mr-1.5"></i> Editor
                                    </span>
                                {/if}
                            </div>
                        </div>
                        <div class="flex items-center gap-3 text-xs text-gray-500 font-mono">
                            <span class="text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">{spaceId}</span>
                            <span class="text-gray-300">•</span>
                            <span class="flex items-center gap-1.5">
                                <i class="far fa-calendar-alt opacity-60"></i>
                                {new Date(space.created_at).toLocaleDateString()}
                            </span>
                            <span class="text-gray-300">•</span>
                            <span class="flex items-center gap-1.5 font-medium text-gray-600">
                                <i class="fas fa-layer-group opacity-60"></i>
                                {space.relic_count} {space.relic_count === 1 ? 'relic' : 'relics'}
                            </span>
                        </div>
                    </div>

                <div class="flex items-center gap-4 flex-shrink-0 ml-4">
                    <!-- Search within Space -->
                    <div class="relative w-64 md:w-80 lg:w-96">
                        <i class="fa-solid fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                        <input
                            type="text"
                            bind:value={searchTerm}
                            placeholder="Find in space..."
                            class="w-full pl-9 pr-3 py-1.5 text-sm maas-input bg-white"
                        />
                    </div>

                    <div class="flex items-center gap-2">
                        {#if canEdit}
                            <button
                                on:click={() => dispatch('navigate', { path: `new?space=${spaceId}` })}
                                class="maas-btn-primary w-[36px] h-[36px] flex items-center justify-center !p-0 shadow-sm"
                                title="New Relic"
                            >
                                <i class="fas fa-plus"></i>
                            </button>
                            <button
                                on:click={() => showAddRelicModal = true}
                                class="maas-btn-primary w-[36px] h-[36px] flex items-center justify-center !p-0 shadow-sm"
                                title="Add Existing"
                            >
                                <i class="fas fa-link"></i>
                            </button>
                            <div class="w-px h-6 bg-gray-200 mx-1"></div>
                        {/if}
                        <button
                            on:click={() => {
                                navigator.clipboard.writeText(`${window.location.origin}/spaces/${spaceId}`).then(() => {
                                    showToast('Space link copied to clipboard!', 'success');
                                });
                            }}
                            class="maas-btn-secondary w-[36px] h-[36px] flex items-center justify-center group shadow-sm bg-white"
                            title="Share Space"
                        >
                            <i class="fas fa-share text-gray-400 group-hover:text-indigo-600 transition-colors"></i>
                        </button>

                        {#if isOwner || space.role === 'admin' || space.role === 'editor'}
                            <button
                                on:click={() => {
                                    showAccessModal = true;
                                    loadAccessList();
                                }}
                                class="maas-btn-secondary w-[36px] h-[36px] flex items-center justify-center group shadow-sm bg-white"
                                title="Manage Access"
                            >
                                <i class="fas fa-users-cog text-gray-400 group-hover:text-purple-600 transition-colors"></i>
                            </button>
                        {/if}

                        {#if isOwner || space.role === 'admin'}
                            <button
                                on:click={openEditModal}
                                class="maas-btn-secondary w-[36px] h-[36px] flex items-center justify-center group shadow-sm bg-white"
                                title="Space Settings"
                            >
                                <i class="fas fa-cog text-gray-400 group-hover:text-blue-600 transition-colors"></i>
                            </button>
                        {/if}
                    </div>
                </div>
            </div>

            <!-- Relics List -->
            <div class="relative">
                {#if loadingRelics}
                    <div class="p-24 text-center">
                        <i class="fas fa-spinner fa-spin text-3xl text-blue-600/30"></i>
                        <p class="text-sm text-gray-400 mt-4">Loading relics...</p>
                    </div>
                {:else if relics.length === 0}
                    <div class="p-24 text-center">
                        <div class="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-6">
                            <i class="fas fa-layer-group text-3xl text-gray-300"></i>
                        </div>
                        <h3 class="text-xl font-bold text-gray-900 mb-2">This space is empty</h3>
                        <p class="text-gray-500 max-w-sm mx-auto mb-8">This space doesn't have any relics yet. Start adding relics to organize your collection.</p>
                        {#if canEdit}
                            <div class="flex gap-4 justify-center">
                                <button
                                    on:click={() => dispatch('navigate', { path: `new?space=${spaceId}` })}
                                    class="maas-btn-primary px-8 py-2.5"
                                >
                                    <i class="fas fa-plus mr-2"></i> New Relic
                                </button>
                                <button
                                    on:click={() => showAddRelicModal = true}
                                    class="maas-btn-secondary px-8 py-2.5"
                                >
                                    <i class="fas fa-link mr-2"></i> Add Existing
                                </button>
                            </div>
                        {/if}
                    </div>
                {:else}
                    <!-- In SpaceViewer, we use RelicTable directly without its internal header to maintain connection -->
                    <div class="relic-table-connected">
                        <RelicTable
                            data={sortedRelics}
                            paginatedData={paginatedRelics}
                            bind:searchTerm
                            bind:currentPage
                            bind:itemsPerPage
                            bind:sortBy
                            bind:sortOrder
                            {totalPages}
                            {goToPage}
                            showHeader={false}
                            embedded={true}
                            on:tag-click={handleTagClick}
                            emptyMessage="No relics in this space."
                            customActions={
                                canEdit ? [
                                    {
                                        icon: 'fa-times',
                                        color: 'red',
                                        title: 'Remove from Space',
                                        handler: removeRelic
                                    }
                                ] : []
                            }
                        />
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if}

<!-- Edit Space Modal -->
{#if showEditModal}
    <div class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h2 class="text-xl font-bold mb-4">Space Settings</h2>

            <div class="space-y-4">
                <div>
                    <label for="editSpaceName" class="block text-sm font-medium text-gray-700 mb-1">Space Name</label>
                    <input
                        id="editSpaceName"
                        type="text"
                        bind:value={editName}
                        class="maas-input w-full"
                    />
                </div>

                <div>
                    <div class="block text-sm font-medium text-gray-700 mb-1">Visibility</div>
                    <div class="grid grid-cols-2 gap-3">
                        <label for="edit-vis-public" class="flex items-center p-3 border rounded-lg cursor-pointer transition-colors {editVisibility === 'public' ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:bg-gray-50'}">
                            <input id="edit-vis-public" type="radio" bind:group={editVisibility} value="public" class="hidden">
                            <i class="fas fa-globe text-green-600 mr-2"></i>
                            <div class="font-medium text-sm">Public</div>
                        </label>
                        <label for="edit-vis-private" class="flex items-center p-3 border rounded-lg cursor-pointer transition-colors {editVisibility === 'private' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'}">
                            <input id="edit-vis-private" type="radio" bind:group={editVisibility} value="private" class="hidden">
                            <i class="fas fa-lock text-gray-600 mr-2"></i>
                            <div class="font-medium text-sm">Private</div>
                        </label>
                    </div>
                </div>
            </div>

            <div class="mt-8 flex justify-between items-center">
                <button
                    on:click={deleteSpace}
                    class="text-red-600 hover:text-red-800 text-sm font-medium transition-colors"
                    disabled={updating}
                >
                    <i class="fas fa-trash-alt mr-1"></i> Delete Space
                </button>

                <div class="flex gap-3">
                    <button
                        on:click={() => showEditModal = false}
                        class="maas-btn-secondary"
                        disabled={updating}
                    >
                        Cancel
                    </button>
                    <button
                        on:click={updateSpace}
                        class="maas-btn-primary"
                        disabled={updating || !editName.trim()}
                    >
                        {#if updating}
                            <i class="fas fa-spinner fa-spin mr-2"></i>
                            Saving...
                        {:else}
                            Save Changes
                        {/if}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}

<!-- Add Relic Modal -->
{#if showAddRelicModal}
    <div class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h2 class="text-xl font-bold mb-4">Add Relic to Space</h2>

            <div class="space-y-4">
                <p class="text-sm text-gray-600">
                    Enter the ID of the relic you want to add to this space. You must have access to the relic to add it.
                </p>
                <div>
                    <label for="addRelicId" class="block text-sm font-medium text-gray-700 mb-1">Relic ID</label>
                    <input
                        id="addRelicId"
                        type="text"
                        bind:value={newRelicId}
                        placeholder="e.g. f47ac10b58cc4372a5670e02b2c3d479"
                        class="maas-input w-full font-mono text-sm"
                        on:keydown={(e) => e.key === 'Enter' && addRelicToSpace()}
                    />
                </div>
            </div>

            <div class="mt-6 flex justify-end gap-3">
                <button
                    on:click={() => showAddRelicModal = false}
                    class="maas-btn-secondary"
                    disabled={addingRelic}
                >
                    Cancel
                </button>
                <button
                    on:click={addRelicToSpace}
                    class="maas-btn-primary"
                    disabled={addingRelic || !newRelicId.trim()}
                >
                    {#if addingRelic}
                        <i class="fas fa-spinner fa-spin mr-2"></i> Adding...
                    {:else}
                        Add Relic
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}

<!-- Manage Access Modal -->
{#if showAccessModal}
    <div class="fixed inset-0 bg-black/50 z-[100] flex items-center justify-center p-4 backdrop-blur-sm">
        <div class="bg-white rounded-xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col animate-in fade-in zoom-in duration-200">
            <!-- Modal Header -->
            <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center text-purple-600">
                        <i class="fas fa-users-cog text-xl"></i>
                    </div>
                    <div>
                        <h2 class="text-lg font-bold text-gray-800 leading-tight">Manage Space Access</h2>
                        <p class="text-xs text-gray-500 font-medium uppercase tracking-wider">{space.name}</p>
                    </div>
                </div>
                <button 
                    on:click={() => showAccessModal = false} 
                    class="w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all"
                >
                    <i class="fas fa-times"></i>
                </button>
            </div>

            <div class="p-6 flex-1 overflow-auto space-y-6">
                {#if isOwner}
                    <div class="bg-gray-50/50 p-5 rounded-xl border border-gray-100 ring-1 ring-black/[0.02]">
                        <h3 class="text-sm font-bold text-gray-800 mb-4 flex items-center gap-2">
                            <i class="fas fa-plus-circle text-purple-500"></i>
                            Grant New Access
                        </h3>
                        <div class="flex items-end gap-3">
                            <div class="flex-1">
                                <label for="grantClientId" class="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5 ml-1">Client ID</label>
                                <input
                                    id="grantClientId"
                                    type="text"
                                    bind:value={newAccessClientId}
                                    placeholder="Enter user's Client Key ID"
                                    class="maas-input w-full font-mono text-sm bg-white"
                                />
                            </div>
                            <div class="w-32">
                                <label for="grantRole" class="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5 ml-1">Role</label>
                                <select id="grantRole" bind:value={newAccessRole} class="maas-input w-full py-[7px] bg-white cursor-pointer">
                                    <option value="viewer">Viewer</option>
                                    <option value="editor">Editor</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                            <button
                                on:click={addAccess}
                                class="maas-btn-primary h-[38px] px-6 flex items-center gap-2 whitespace-nowrap mb-px"
                                disabled={managingAccess || !newAccessClientId.trim()}
                            >
                                {#if managingAccess}
                                    <i class="fas fa-spinner fa-spin"></i>
                                {:else}
                                    <i class="fas fa-user-plus text-xs"></i>
                                    <span>Add User</span>
                                {/if}
                            </button>
                        </div>
                    </div>
                {/if}

                <div class="space-y-3">
                    <h3 class="text-sm font-bold text-gray-800 flex items-center gap-2 px-1">
                        <i class="fas fa-list-ul text-blue-500"></i>
                        Current Access List
                    </h3>

                    {#if loadingAccess}
                        <div class="flex flex-col items-center justify-center py-12 bg-gray-50/30 rounded-xl border border-dashed border-gray-200">
                            <i class="fas fa-spinner fa-spin text-3xl text-blue-500 mb-4"></i>
                            <p class="text-sm text-gray-500">Loading access data...</p>
                        </div>
                    {:else if accessList.length === 0}
                        <div class="text-center py-10 px-4 bg-gray-50/30 rounded-xl border border-dashed border-gray-300">
                            <div class="w-12 h-12 bg-white rounded-full flex items-center justify-center mx-auto mb-3 shadow-sm border border-gray-100">
                                <i class="fas fa-user-lock text-gray-300"></i>
                            </div>
                            <p class="text-sm text-gray-500">No additional users have access to this space yet.</p>
                        </div>
                    {:else}
                        <div class="border border-gray-200 rounded-xl overflow-hidden shadow-sm bg-white">
                            <table class="min-w-full divide-y divide-gray-100">
                                <thead class="bg-gray-50/80">
                                    <tr>
                                        <th class="px-5 py-3 text-left text-[11px] font-bold text-gray-500 uppercase tracking-widest">User Details</th>
                                        <th class="px-5 py-3 text-left text-[11px] font-bold text-gray-500 uppercase tracking-widest w-32">Role</th>
                                        <th class="px-5 py-3 text-right text-[11px] font-bold text-gray-500 uppercase tracking-widest w-24">Actions</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-50">
                                    {#each accessList as access}
                                        <tr class="hover:bg-gray-50/50 transition-colors group">
                                            <td class="px-5 py-3.5 whitespace-nowrap">
                                                <div class="flex items-center gap-3">
                                                    <div class="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center text-blue-600 border border-blue-100">
                                                        <i class="fas fa-user text-xs"></i>
                                                    </div>
                                                    <div class="min-w-0">
                                                        <div class="text-sm font-bold text-gray-900 truncate max-w-[200px]">{access.client_name || 'Anonymous User'}</div>
                                                        <div class="text-[10px] text-gray-400 font-mono mt-0.5 tracking-tight">{access.client_id}</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td class="px-5 py-3.5 whitespace-nowrap">
                                                {#if access.role === 'admin'}
                                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-red-100 text-red-800 border border-red-200">
                                                        <i class="fas fa-shield-alt mr-1.5 scale-90"></i> Admin
                                                    </span>
                                                {:else if access.role === 'editor'}
                                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-purple-100 text-purple-800 border border-purple-200">
                                                        <i class="fas fa-edit mr-1.5 scale-90"></i> Editor
                                                    </span>
                                                {:else}
                                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-gray-100 text-gray-600 border border-gray-200">
                                                        <i class="fas fa-eye mr-1.5 scale-90"></i> Viewer
                                                    </span>
                                                {/if}
                                            </td>
                                            <td class="px-5 py-3.5 whitespace-nowrap text-right">
                                                {#if isOwner}
                                                    <button
                                                        on:click={() => removeAccess(access.client_id)}
                                                        class="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50 transition-all"
                                                        title="Remove Access"
                                                    >
                                                        <i class="fas fa-trash-alt text-xs"></i>
                                                    </button>
                                                {/if}
                                            </td>
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                    {/if}
                </div>
            </div>

            <!-- Modal Footer -->
            <div class="px-6 py-4 bg-gray-50/50 border-t border-gray-100 flex justify-end">
                <button
                    on:click={() => showAccessModal = false}
                    class="maas-btn-secondary px-8 font-semibold shadow-sm"
                >
                    Close
                </button>
            </div>
        </div>
    </div>
{/if}
