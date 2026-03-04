<script>
    import { onMount, createEventDispatcher } from 'svelte';
    import { spaces as spacesApi } from '../services/api';
    import { showToast } from '../stores/toastStore';
    import RelicTable from './RelicTable.svelte';

    export let spaceId;

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

    $: canEdit = space?.role === 'owner' || space?.role === 'editor';
    $: isOwner = space?.role === 'owner';

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

    async function removeRelic(relicId) {
        if (!confirm("Remove this relic from the space?")) return;

        try {
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
        // Tag clicking in spaces might navigate differently or just filter
        console.log("Tag clicked in space:", event.detail);
        // For now, let's just show a toast or implement basic filtering
    }

    function handleRelicClick(relicId) {
        dispatch('navigate', { path: relicId });
    }

    onMount(() => {
        loadSpace();
    });
</script>

{#if loading}
    <div class="flex justify-center items-center py-12">
        <i class="fas fa-spinner fa-spin text-3xl text-gray-400"></i>
    </div>
{:else if space}
    <div class="space-y-6">
        <!-- Header -->
        <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <div class="flex justify-between items-start">
                <div>
                    <div class="flex items-center gap-3 mb-2">
                        <button
                            on:click={() => dispatch('navigate', { path: 'spaces' })}
                            class="text-gray-400 hover:text-gray-600 transition-colors"
                            title="Back to Spaces"
                        >
                            <i class="fas fa-arrow-left"></i>
                        </button>
                        <h1 class="text-2xl font-bold text-gray-900">{space.name}</h1>
                        {#if space.visibility === 'public'}
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                <i class="fas fa-globe mr-1.5"></i> Public
                            </span>
                        {:else}
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                <i class="fas fa-lock mr-1.5"></i> Private
                            </span>
                        {/if}
                    </div>

                    <div class="flex items-center gap-4 text-sm text-gray-500 ml-8">
                        <span>Created {new Date(space.created_at).toLocaleDateString()}</span>
                        <span>•</span>
                        <span>{space.relic_count} relics</span>
                        <span>•</span>
                        <span class="capitalize">Role: {space.role || 'viewer'}</span>
                    </div>
                </div>

                <div class="flex gap-2">
                    {#if canEdit}
                        <button
                            on:click={() => showAddRelicModal = true}
                            class="maas-btn-primary flex items-center gap-2"
                        >
                            <i class="fas fa-plus"></i>
                            Add Relic
                        </button>
                    {/if}

                    {#if isOwner || space.role === 'editor'}
                        <button
                            on:click={() => {
                                showAccessModal = true;
                                loadAccessList();
                            }}
                            class="maas-btn-secondary flex items-center gap-2"
                            title="Manage Access"
                        >
                            <i class="fas fa-users"></i>
                        </button>
                    {/if}

                    {#if isOwner}
                        <button
                            on:click={openEditModal}
                            class="maas-btn-secondary flex items-center gap-2"
                            title="Space Settings"
                        >
                            <i class="fas fa-cog"></i>
                        </button>
                    {/if}
                </div>
            </div>
        </div>

        <!-- Relics List -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            {#if loadingRelics}
                <div class="flex justify-center items-center py-12">
                    <i class="fas fa-spinner fa-spin text-2xl text-gray-400"></i>
                </div>
            {:else if relics.length === 0}
                <div class="p-12 text-center">
                    <i class="fas fa-box-open text-4xl text-gray-300 mb-4"></i>
                    <h3 class="text-lg font-medium text-gray-900 mb-2">This space is empty</h3>
                    <p class="text-gray-500 mb-6">Add existing relics to organize them in this space.</p>
                    {#if canEdit}
                        <button
                            on:click={() => showAddRelicModal = true}
                            class="maas-btn-primary"
                        >
                            Add Relic
                        </button>
                    {/if}
                </div>
            {:else}
                <!-- Reuse the RelicTable component but add remove button functionality -->
                <RelicTable
                    data={relics}
                    paginatedData={relics}
                    title="Relics"
                    on:tag-click={handleTagClick}
                    emptyMessage="No relics in this space."
                    customActions={
                        canEdit ? [
                            {
                                icon: 'fa-times',
                                color: 'text-red-500 hover:text-red-700 hover:bg-red-50',
                                title: 'Remove from Space',
                                action: removeRelic
                            }
                        ] : []
                    }
                />
            {/if}
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
                    <label class="block text-sm font-medium text-gray-700 mb-1">Space Name</label>
                    <input
                        type="text"
                        bind:value={editName}
                        class="maas-input w-full"
                    />
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Visibility</label>
                    <div class="grid grid-cols-2 gap-3">
                        <label class="flex items-center p-3 border rounded-lg cursor-pointer transition-colors {editVisibility === 'public' ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:bg-gray-50'}">
                            <input type="radio" bind:group={editVisibility} value="public" class="hidden">
                            <i class="fas fa-globe text-green-600 mr-2"></i>
                            <div class="font-medium text-sm">Public</div>
                        </label>
                        <label class="flex items-center p-3 border rounded-lg cursor-pointer transition-colors {editVisibility === 'private' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'}">
                            <input type="radio" bind:group={editVisibility} value="private" class="hidden">
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
                    <label class="block text-sm font-medium text-gray-700 mb-1">Relic ID</label>
                    <input
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
    <div class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6 max-h-[90vh] flex flex-col">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-bold">Manage Space Access</h2>
                <button on:click={() => showAccessModal = false} class="text-gray-400 hover:text-gray-600">
                    <i class="fas fa-times text-lg"></i>
                </button>
            </div>

            {#if isOwner}
                <div class="bg-gray-50 p-4 rounded-lg border border-gray-200 mb-6">
                    <h3 class="text-sm font-bold text-gray-700 mb-2">Grant Access</h3>
                    <div class="flex items-end gap-3">
                        <div class="flex-1">
                            <label class="block text-xs font-medium text-gray-600 mb-1">Client ID</label>
                            <input
                                type="text"
                                bind:value={newAccessClientId}
                                placeholder="Enter user's Client Key ID"
                                class="maas-input w-full font-mono text-sm"
                            />
                        </div>
                        <div class="w-32">
                            <label class="block text-xs font-medium text-gray-600 mb-1">Role</label>
                            <select bind:value={newAccessRole} class="maas-input w-full py-[9px]">
                                <option value="viewer">Viewer</option>
                                <option value="editor">Editor</option>
                            </select>
                        </div>
                        <button
                            on:click={addAccess}
                            class="maas-btn-primary mb-px"
                            disabled={managingAccess || !newAccessClientId.trim()}
                        >
                            {#if managingAccess}
                                <i class="fas fa-spinner fa-spin"></i>
                            {:else}
                                Add
                            {/if}
                        </button>
                    </div>
                </div>
            {/if}

            <div class="flex-1 overflow-auto">
                <h3 class="text-sm font-bold text-gray-700 mb-3">Current Access</h3>

                {#if loadingAccess}
                    <div class="flex justify-center py-8">
                        <i class="fas fa-spinner fa-spin text-2xl text-gray-400"></i>
                    </div>
                {:else if accessList.length === 0}
                    <div class="text-center py-8 text-gray-500 bg-gray-50 rounded-lg border border-gray-200 border-dashed">
                        No additional users have access to this space.
                    </div>
                {:else}
                    <div class="border border-gray-200 rounded-lg overflow-hidden">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">Role</th>
                                    <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider w-20">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
                                {#each accessList as access}
                                    <tr>
                                        <td class="px-4 py-3 whitespace-nowrap">
                                            <div class="text-sm font-medium text-gray-900">{access.client_name || 'Anonymous User'}</div>
                                            <div class="text-xs text-gray-500 font-mono mt-0.5">{access.client_id}</div>
                                        </td>
                                        <td class="px-4 py-3 whitespace-nowrap">
                                            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {access.role === 'editor' ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'}">
                                                {access.role}
                                            </span>
                                        </td>
                                        <td class="px-4 py-3 whitespace-nowrap text-right">
                                            {#if isOwner}
                                                <button
                                                    on:click={() => removeAccess(access.client_id)}
                                                    class="text-red-500 hover:text-red-700 p-1 transition-colors"
                                                    title="Remove Access"
                                                >
                                                    <i class="fas fa-trash-alt"></i>
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

            <div class="mt-6 flex justify-end">
                <button
                    on:click={() => showAccessModal = false}
                    class="maas-btn-secondary"
                >
                    Close
                </button>
            </div>
        </div>
    </div>
{/if}