<script>
    import { onMount, createEventDispatcher } from 'svelte';
    import { spaces as spacesApi } from '../services/api';
    import { showToast } from '../stores/toastStore';
    import { getTypeLabel, getDefaultItemsPerPage } from '../services/typeUtils';
    import { getFilesFromDrop } from '../services/utils/fileProcessing';
    import RelicTable from './RelicTable.svelte';
    import RelicDropModal from './RelicDropModal.svelte';
    import ConfirmModal from './ConfirmModal.svelte';

    export let spaceId;
    export let tagFilter = null;

    const dispatch = createEventDispatcher();

    let space = null;
    let relics = [];
    let loading = true;
    let loadingRelics = true;
    let errorStatus = null;

    // Access management state
    let accessList = [];
    let accessTotal = 0;
    let accessPage = 1;
    const accessLimit = 25;
    let accessSearch = '';
    let accessSearchTimer = null;
    let showAccessModal = false;
    let loadingAccess = false;
    let newAccessClientId = '';
    let newAccessRole = 'viewer';
    let managingAccess = false;

    $: accessTotalPages = Math.max(1, Math.ceil(accessTotal / accessLimit))

    // Edit state
    let showEditModal = false;
    let editName = '';
    let editVisibility = 'public';
    let updating = false;
    let transferPublicId = '';
    let transferring = false;

    // Add relic state
    let showAddRelicModal = false;
    let newRelicId = '';
    let addingRelic = false;
    let searchTerm = '';
    let currentPage = 1;
    let itemsPerPage = 20;
    let sortBy = 'date';
    let sortOrder = 'desc';
    let total = 0;

    // Drop handling state
    let showDropModal = false;
    let droppedFiles = [];
    let isDraggingOver = false;

    // Confirm modal state
    let showConfirm = false;
    let confirmTitle = '';
    let confirmMessage = '';
    let confirmAction = null;

    $: canEdit = space?.role === 'owner' || space?.role === 'editor' || space?.role === 'admin';
    $: isOwner = space?.role === 'owner' || space?.role === 'admin';

    // Server-side pagination
    $: totalPages = Math.max(1, Math.ceil(total / itemsPerPage));

    function goToPage(page) {
        if (page >= 1 && page <= totalPages) loadRelics(page);
    }

    function handleSort(event) {
        sortBy = event.detail.sortBy;
        sortOrder = event.detail.sortOrder;
        loadRelics(1);
    }

    // Reload on search/tagFilter changes, but only after initial load
    let spaceReady = false;
    let searchTimer;
    let prevTagFilter = tagFilter;

    $: if (spaceReady && searchTerm !== undefined) {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => loadRelics(1), 300);
    }

    $: if (spaceReady && tagFilter !== prevTagFilter) {
        prevTagFilter = tagFilter;
        loadRelics(1);
    }

    $: if (spaceId) {
        loadSpace();
    }

    async function loadSpace() {
        loading = true;
        spaceReady = false;
        errorStatus = null;
        try {
            space = await spacesApi.get(spaceId);
            await loadRelics(1);
            spaceReady = true;
        } catch (error) {
            console.error("Failed to load space:", error);
            errorStatus = error.response?.status || 'unknown';
        } finally {
            loading = false;
        }
    }

    onMount(() => {
        // Initial load is handled by reactive statement if spaceId is present
    });

    async function loadRelics(page = 1) {
        loadingRelics = true;
        try {
            const data = await spacesApi.getRelics(spaceId, {
                limit: itemsPerPage,
                offset: (page - 1) * itemsPerPage,
                search: searchTerm || undefined,
                tag: tagFilter || undefined,
                sort_by: sortBy === 'date' ? 'created_at' : sortBy,
                sort_order: sortOrder,
            });
            relics = data.relics;
            total = data.total;
            currentPage = page;
        } catch (error) {
            console.error("Failed to load space relics:", error);
            showToast("Failed to load relics", "error");
        } finally {
            loadingRelics = false;
        }
    }

    async function loadAccessList(page = accessPage) {
        if (!isOwner && space.role !== 'editor') return;

        loadingAccess = true;
        try {
            const accessData = await spacesApi.getAccessList(spaceId, {
                limit: accessLimit,
                offset: (page - 1) * accessLimit,
                search: accessSearch.trim() || undefined,
            });
            accessList = accessData.access || [];
            accessTotal = accessData.total || 0;
            accessPage = page;
        } catch (error) {
            console.error("Failed to load access list:", error);
            showToast("Failed to load access list", "error");
        } finally {
            loadingAccess = false;
        }
    }

    function handleAccessSearch() {
        clearTimeout(accessSearchTimer);
        accessSearchTimer = setTimeout(() => loadAccessList(1), 300);
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

    function transferOwnership() {
        if (!transferPublicId.trim()) {
            showToast("Public ID is required", "error");
            return;
        }
        confirmTitle = 'Transfer Ownership';
        confirmMessage = `Transfer ownership of "${space.name}" to user ${transferPublicId.trim()}? You will become an admin.`;
        confirmAction = async () => {
            showConfirm = false;
            transferring = true;
            try {
                space = await spacesApi.transferOwnership(spaceId, transferPublicId.trim());
                transferPublicId = '';
                showEditModal = false;
                showToast("Ownership transferred successfully", "success");
            } catch (error) {
                showToast(error.response?.data?.detail || "Failed to transfer ownership", "error");
            } finally {
                transferring = false;
            }
        };
        showConfirm = true;
    }

    function deleteSpace() {
        confirmTitle = 'Delete Space';
        confirmMessage = "Are you sure you want to delete this space? This will not delete the relics inside it.";
        confirmAction = async () => {
            showConfirm = false;
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
        };
        showConfirm = true;
    }

    async function addRelicToSpace() {
        if (!newRelicId.trim()) {
            showToast("Relic ID is required", "error");
            return;
        }

        addingRelic = true;
        try {
            await spacesApi.addRelic(spaceId, newRelicId.trim());
            await loadRelics(1);
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

    function removeRelic(relic) {
        confirmTitle = 'Remove Relic';
        confirmMessage = "Remove this relic from the space?";
        confirmAction = async () => {
            showConfirm = false;
            try {
                const relicId = relic.id || relic;
                await spacesApi.removeRelic(spaceId, relicId);
                showToast("Relic removed", "success");
                // Update space count and reload current page
                space = { ...space, relic_count: Math.max(0, space.relic_count - 1) };
                const newPage = relics.length === 1 && currentPage > 1 ? currentPage - 1 : currentPage;
                await loadRelics(newPage);
            } catch (error) {
                console.error("Failed to remove relic:", error);
                showToast("Failed to remove relic", "error");
            }
        };
        showConfirm = true;
    }

    async function addAccess() {
        if (!newAccessClientId.trim()) {
            showToast("Public ID is required", "error");
            return;
        }

        managingAccess = true;
        try {
            await spacesApi.addAccess(spaceId, {
                public_id: newAccessClientId.trim(),
                role: newAccessRole
            });
            newAccessClientId = '';
            showToast("Access granted successfully", "success");
            await loadAccessList(1);
        } catch (error) {
            console.error("Failed to grant access:", error);
            showToast(error.response?.data?.detail || "Failed to grant access", "error");
        } finally {
            managingAccess = false;
        }
    }

    function removeAccess(accessId) {
        confirmTitle = 'Remove Access';
        confirmMessage = "Remove this user's access?";
        confirmAction = async () => {
            showConfirm = false;
            try {
                await spacesApi.removeAccess(spaceId, accessId);
                showToast("Access removed", "success");
                const newPage = accessList.length === 1 && accessPage > 1 ? accessPage - 1 : accessPage;
                await loadAccessList(newPage);
            } catch (error) {
                console.error("Failed to remove access:", error);
                showToast("Failed to remove access", "error");
            }
        };
        showConfirm = true;
    }

    function handleTagClick(event) {
        dispatch('tag-click', event.detail);
    }

    function handleRelicClick(relicId) {
        dispatch('navigate', { path: relicId });
    }

    function handleDragOver(e) {
        e.preventDefault();
        if (!canEdit) return;
        isDraggingOver = true;
    }

    function handleDragLeave(e) {
        e.preventDefault();
        isDraggingOver = false;
    }

    async function handleDrop(e) {
        e.preventDefault();
        isDraggingOver = false;
        
        if (!canEdit) {
            showToast("You don't have permission to add relics to this space", "error");
            return;
        }

        const files = await getFilesFromDrop(e.dataTransfer);
        if (files.length > 0) {
            droppedFiles = files;
            showDropModal = true;
        }
    }

    function handleUploadSuccess() {
        showDropModal = false;
        loadRelics(); // Refresh list
        // Update space count
        loadSpace();
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
    <div 
        class="space-y-6 relative min-h-[400px]"
        on:dragover={handleDragOver}
        on:dragleave={handleDragLeave}
        on:drop={handleDrop}
        role="region"
        aria-label="Space Content and Drop Zone"
    >
        {#if isDraggingOver}
            <div class="absolute inset-0 z-[100] bg-blue-50/80 backdrop-blur-[2px] border-4 border-dashed border-blue-400 rounded-lg flex flex-col items-center justify-center animate-in fade-in duration-200">
                <div class="w-20 h-20 bg-white rounded-full shadow-xl flex items-center justify-center text-blue-500 mb-6 border-4 border-blue-100">
                    <i class="fas fa-cloud-upload-alt text-4xl animate-bounce"></i>
                </div>
                <h3 class="text-2xl font-bold text-blue-700">Drop files to upload</h3>
                <p class="text-blue-500 font-medium mt-2">Uploading directly to {space.name}</p>
            </div>
        {/if}
        <div class="bg-white shadow-sm rounded-lg border border-gray-200 overflow-hidden">
            <!-- Space Header -->
            <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-3 mb-1">
                        <h2 class="text-lg font-semibold text-gray-900 flex items-center truncate">
                            <i class="fas fa-layer-group text-blue-600 mr-2"></i>
                            {space.name}
                        </h2>
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
                                    accessSearch = '';
                                    accessPage = 1;
                                    showAccessModal = true;
                                    loadAccessList(1);
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
                            data={relics}
                            paginatedData={relics}
                            total={total}
                            bind:searchTerm
                            bind:currentPage
                            bind:itemsPerPage
                            {sortBy}
                            {sortOrder}
                            {totalPages}
                            {goToPage}
                            showHeader={false}
                            embedded={true}
                            on:sort={handleSort}
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
{:else if errorStatus === 403}
    <div class="flex items-center justify-center py-16">
        <div class="text-center max-w-sm">
            <div class="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center mx-auto mb-4 border border-amber-200">
                <i class="fas fa-user-lock text-amber-500 text-2xl"></i>
            </div>
            <h2 class="text-lg font-bold text-gray-800 mb-1">Access Restricted</h2>
            <p class="text-sm text-gray-500">You don't have permission to view this space.</p>
        </div>
    </div>
{:else if errorStatus === 404}
    <div class="flex items-center justify-center py-16">
        <div class="text-center max-w-sm">
            <div class="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4 border border-gray-200">
                <i class="fas fa-search text-gray-400 text-2xl"></i>
            </div>
            <h2 class="text-lg font-bold text-gray-800 mb-1">Space Not Found</h2>
            <p class="text-sm text-gray-500">This space doesn't exist or may have been deleted.</p>
        </div>
    </div>
{:else if errorStatus}
    <div class="flex items-center justify-center py-16">
        <div class="text-center max-w-sm">
            <div class="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4 border border-gray-200">
                <i class="fas fa-exclamation-triangle text-gray-400 text-2xl"></i>
            </div>
            <h2 class="text-lg font-bold text-gray-800 mb-1">Failed to Load Space</h2>
            <p class="text-sm text-gray-500">Something went wrong. Please try again.</p>
        </div>
    </div>
{/if}

{#if showDropModal}
    <RelicDropModal
        files={droppedFiles}
        spaceId={spaceId}
        spaceName={space.name}
        on:close={() => showDropModal = false}
        on:success={handleUploadSuccess}
    />
{/if}

<ConfirmModal
  show={showConfirm}
  title={confirmTitle}
  message={confirmMessage}
  on:confirm={confirmAction}
  on:cancel={() => showConfirm = false}
/>

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

                <div class="pt-2 border-t border-gray-100">
                    <label class="block text-sm font-medium text-gray-700 mb-1">Transfer Ownership</label>
                    <div class="flex gap-2">
                        <input
                            type="text"
                            bind:value={transferPublicId}
                            placeholder="New owner's Public ID"
                            class="flex-1 maas-input font-mono text-sm"
                        />
                        <button
                            on:click={transferOwnership}
                            disabled={transferring || !transferPublicId.trim()}
                            class="maas-btn-secondary px-3 text-sm whitespace-nowrap disabled:opacity-50"
                        >
                            {#if transferring}
                                <i class="fas fa-spinner fa-spin"></i>
                            {:else}
                                Transfer
                            {/if}
                        </button>
                    </div>
                    <p class="text-[10px] text-gray-500 mt-1">You will become an admin after transfer.</p>
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
                                <label for="grantClientId" class="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5 ml-1">Public ID</label>
                                <input
                                    id="grantClientId"
                                    type="text"
                                    bind:value={newAccessClientId}
                                    placeholder="Enter user's Public ID (e.g. 7f2a-3b1c-9d2e-ab4f)"
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
                    <div class="flex items-center justify-between px-1">
                        <h3 class="text-sm font-bold text-gray-800 flex items-center gap-2">
                            <i class="fas fa-list-ul text-blue-500"></i>
                            Current Access List
                        </h3>
                        {#if accessTotal > 0}
                            <span class="text-xs text-gray-400">{accessTotal} {accessTotal === 1 ? 'user' : 'users'}</span>
                        {/if}
                    </div>

                    {#if accessTotal > accessLimit || accessSearch}
                        <div class="relative">
                            <i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs"></i>
                            <input
                                type="text"
                                bind:value={accessSearch}
                                on:input={handleAccessSearch}
                                placeholder="Filter by name or ID..."
                                class="maas-input w-full pl-8 py-1.5 text-sm bg-white"
                            />
                            {#if loadingAccess}
                                <i class="fas fa-spinner fa-spin absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs"></i>
                            {/if}
                        </div>
                    {/if}

                    {#if loadingAccess && accessList.length === 0}
                        <div class="flex flex-col items-center justify-center py-12 bg-gray-50/30 rounded-xl border border-dashed border-gray-200">
                            <i class="fas fa-spinner fa-spin text-3xl text-blue-500 mb-4"></i>
                            <p class="text-sm text-gray-500">Loading access data...</p>
                        </div>
                    {:else if accessList.length === 0}
                        <div class="text-center py-10 px-4 bg-gray-50/30 rounded-xl border border-dashed border-gray-300">
                            <div class="w-12 h-12 bg-white rounded-full flex items-center justify-center mx-auto mb-3 shadow-sm border border-gray-100">
                                <i class="fas fa-user-lock text-gray-300"></i>
                            </div>
                            <p class="text-sm text-gray-500">
                                {#if accessSearch}
                                    No users match "{accessSearch}".
                                {:else}
                                    No additional users have access to this space yet.
                                {/if}
                            </p>
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
                                                        <div class="text-[10px] text-gray-400 font-mono mt-0.5 tracking-tight">{access.public_id || '—'}</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td class="px-5 py-3.5 whitespace-nowrap">
                                                {#if access.role === 'owner'}
                                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-blue-100 text-blue-800 border border-blue-200">
                                                        <i class="fas fa-crown mr-1.5 scale-90"></i> Owner
                                                    </span>
                                                {:else if access.role === 'admin'}
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
                                                {#if isOwner && access.role !== 'owner'}
                                                    <button
                                                        on:click={() => removeAccess(access.id)}
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

                        {#if accessTotalPages > 1}
                            <div class="flex items-center justify-between pt-1">
                                <span class="text-xs text-gray-400">Page {accessPage} of {accessTotalPages}</span>
                                <div class="flex items-center gap-1">
                                    <button
                                        on:click={() => loadAccessList(accessPage - 1)}
                                        disabled={accessPage <= 1 || loadingAccess}
                                        class="w-7 h-7 rounded-lg flex items-center justify-center border border-gray-200 text-gray-400 hover:text-gray-700 hover:bg-gray-50 transition-all disabled:opacity-30"
                                    >
                                        <i class="fas fa-chevron-left text-[10px]"></i>
                                    </button>
                                    <button
                                        on:click={() => loadAccessList(accessPage + 1)}
                                        disabled={accessPage >= accessTotalPages || loadingAccess}
                                        class="w-7 h-7 rounded-lg flex items-center justify-center border border-gray-200 text-gray-400 hover:text-gray-700 hover:bg-gray-50 transition-all disabled:opacity-30"
                                    >
                                        <i class="fas fa-chevron-right text-[10px]"></i>
                                    </button>
                                </div>
                            </div>
                        {/if}
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
