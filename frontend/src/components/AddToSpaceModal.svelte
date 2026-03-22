<script>
    import { spaces as spacesApi } from '../services/api';
    import { showToast } from '../stores/toastStore';

    export let open = false;
    export let relicId;
    export let relicName;

    const EDIT_ROLES = ['owner', 'editor', 'admin'];
    const ROLE_WEIGHT = { owner: 3, admin: 2, editor: 1 };

    const FILTERS = [
        { id: 'all',    label: 'All' },
        { id: 'my',     label: 'My Spaces' },
        { id: 'shared', label: 'Shared' },
        { id: 'public', label: 'Public' },
    ];

    let spaces = [];
    let totalAvailable = null; // total matching spaces (across all categories or in single category)
    let loading = false;
    let adding = false;
    let selectedSpaceId = '';
    let searchTerm = '';
    let activeFilter = 'all';
    let searchTimer = null;
    let initialized = false;

    $: sortedSpaces = [...spaces].sort((a, b) => {
        const wd = (ROLE_WEIGHT[b.role] || 0) - (ROLE_WEIGHT[a.role] || 0);
        return wd !== 0 ? wd : a.name.localeCompare(b.name);
    });

    $: if (sortedSpaces.length > 0 && !sortedSpaces.find(s => s.id === selectedSpaceId)) {
        selectedSpaceId = sortedSpaces[0].id;
    }
    $: if (!sortedSpaces.find(s => s.id === selectedSpaceId)) {
        selectedSpaceId = '';
    }

    function mergeDeduped(...lists) {
        const seen = new Set();
        const result = [];
        for (const list of lists) {
            for (const s of list) {
                if (!seen.has(s.id)) {
                    seen.add(s.id);
                    result.push(s);
                }
            }
        }
        return result;
    }

    async function loadAll(term) {
        const PAGE = 25;
        const [ownedRes, sharedPrivRes, pubRes] = await Promise.all([
            spacesApi.list({ category: 'my',     search: term || undefined, limit: PAGE }),
            spacesApi.list({ category: 'shared', search: term || undefined, visibility: 'private', limit: PAGE }),
            spacesApi.list({ category: 'public', search: term || undefined, limit: PAGE }),
        ]);
        const owned      = (ownedRes.spaces   || []).filter(s => EDIT_ROLES.includes(s.role));
        const sharedPriv = (sharedPrivRes.spaces || []).filter(s => EDIT_ROLES.includes(s.role));
        const pub        = (pubRes.spaces      || []).filter(s => EDIT_ROLES.includes(s.role));
        const merged = mergeDeduped(owned, sharedPriv, pub);
        const anyTruncated = (ownedRes.total || 0) > PAGE
            || (sharedPrivRes.total || 0) > PAGE
            || (pubRes.total || 0) > PAGE;
        totalAvailable = anyTruncated ? '>' + merged.length : null;
        return merged;
    }

    async function loadCategory(category, term) {
        const PAGE = 50;
        const data = await spacesApi.list({ category, search: term || undefined, limit: PAGE });
        const filtered = (data.spaces || []).filter(s => EDIT_ROLES.includes(s.role));
        totalAvailable = (data.total || 0) > filtered.length ? data.total : null;
        return filtered;
    }

    async function reload() {
        loading = true;
        try {
            const term = searchTerm.trim() || undefined;
            spaces = activeFilter === 'all'
                ? await loadAll(term)
                : await loadCategory(activeFilter, term);
        } catch (error) {
            console.error("Failed to load spaces:", error);
            showToast("Failed to load spaces", "error");
        } finally {
            loading = false;
        }
    }

    function handleSearchInput() {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(reload, 300);
    }

    function selectFilter(id) {
        activeFilter = id;
        searchTerm = '';
        reload();
    }

    $: if (open && !initialized) {
        initialized = true;
        reload();
    }

    $: if (!open) {
        initialized = false;
        searchTerm = '';
        spaces = [];
        totalAvailable = null;
        selectedSpaceId = '';
        activeFilter = 'all';
        clearTimeout(searchTimer);
    }

    async function handleAdd() {
        if (!selectedSpaceId) {
            showToast("Please select a space", "error");
            return;
        }
        adding = true;
        try {
            await spacesApi.addRelic(selectedSpaceId, relicId);
            const spaceName = spaces.find(s => s.id === selectedSpaceId)?.name;
            showToast(`Added to space: ${spaceName}`, "success");
            open = false;
        } catch (error) {
            const detail = error.response?.data?.detail || "Failed to add relic to space";
            showToast(detail, "error");
        } finally {
            adding = false;
        }
    }
</script>

{#if open}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div role="presentation" class="fixed inset-0 bg-black bg-opacity-50 z-[100] flex items-center justify-center p-4 transition-opacity" on:click|self={() => open = false}>
        <div class="bg-white rounded-lg shadow-xl max-w-md w-full flex flex-col overflow-hidden max-h-[90vh]">

            <!-- Header -->
            <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50/30">
                <div>
                    <h3 class="text-xl font-bold text-gray-900">Add to Space</h3>
                    <div class="text-sm text-gray-600 mt-1 truncate" title={relicName}>
                        <span class="font-medium text-gray-500">Relic:</span> {relicName || 'Untitled Relic'}
                    </div>
                </div>
                <button on:click={() => open = false} class="text-gray-400 hover:text-gray-600 transition-colors self-start mt-1">
                    <i class="fas fa-times text-lg"></i>
                </button>
            </div>

            <!-- Filter tabs -->
            <div class="px-6 pt-4 pb-0 flex gap-1.5 bg-white">
                {#each FILTERS as f}
                    <button
                        on:click={() => selectFilter(f.id)}
                        class="px-3 py-1 rounded-full text-xs font-medium transition-colors whitespace-nowrap
                            {activeFilter === f.id
                                ? f.id === 'all'    ? 'bg-gray-800 text-white'
                                : f.id === 'my'     ? 'bg-blue-600 text-white'
                                : f.id === 'shared' ? 'bg-purple-600 text-white'
                                :                     'bg-green-600 text-white'
                                : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'}"
                    >
                        {f.label}
                    </button>
                {/each}
            </div>

            <!-- Body -->
            <div class="p-6 pb-4 flex flex-col min-h-0 bg-white">
                <div>
                    <div class="relative mb-3 flex-shrink-0">
                        <i class="fa-solid fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                        <input
                            type="text"
                            bind:value={searchTerm}
                            on:input={handleSearchInput}
                            placeholder="Search by name or ID..."
                            class="w-full pl-9 pr-8 py-2 text-sm maas-input"
                            autocomplete="off"
                        />
                        {#if loading}
                            <i class="fas fa-spinner fa-spin absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs"></i>
                        {/if}
                    </div>
                </div>

                <!-- Spaces List -->
                <div class="flex-1 overflow-y-auto pr-1 min-h-[220px] max-h-[320px]">
                    {#if loading && spaces.length === 0}
                        <div class="flex items-center justify-center py-8">
                            <i class="fas fa-spinner fa-spin text-blue-600 text-2xl"></i>
                        </div>
                    {:else if spaces.length === 0 && !loading}
                        <div class="text-center py-8 px-4 bg-gray-50 rounded-lg border border-dashed border-gray-300">
                            <i class="fas fa-layer-group text-gray-300 text-3xl mb-3"></i>
                            {#if searchTerm}
                                <p class="text-sm text-gray-600">No editable spaces match <strong>"{searchTerm}"</strong>.</p>
                            {:else}
                                <p class="text-sm text-gray-600">No editable spaces found in this category.</p>
                            {/if}
                        </div>
                    {:else}
                        <div class="space-y-2">
                            {#each sortedSpaces as space (space.id)}
                                <label
                                    class="flex items-center p-3 border rounded-lg cursor-pointer transition-colors {selectedSpaceId === space.id ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500' : 'border-gray-200 hover:bg-gray-50'}"
                                >
                                    <input type="radio" bind:group={selectedSpaceId} value={space.id} class="hidden">

                                    <i class="fas {space.visibility === 'public' ? 'fa-globe' : 'fa-lock'} {selectedSpaceId === space.id ? 'text-blue-500' : 'text-gray-400'} mr-3"></i>

                                    <div class="flex-1 min-w-0">
                                        <div class="font-medium text-sm text-gray-900 truncate">{space.name}</div>
                                        <div class="text-[11px] text-gray-500 flex items-center gap-1.5 mt-0.5">
                                            <span class="capitalize font-semibold {space.role === 'owner' ? 'text-blue-700' : space.role === 'admin' ? 'text-red-700' : 'text-purple-700'}">{space.role}</span>
                                            <span class="text-gray-300">&bull;</span>
                                            <span class="font-mono">{space.id.substring(0, 8)}</span>
                                        </div>
                                    </div>

                                    {#if selectedSpaceId === space.id}
                                        <i class="fas fa-check-circle text-blue-600 ml-3"></i>
                                    {/if}
                                </label>
                            {/each}
                        </div>
                    {/if}
                </div>
                {#if totalAvailable && spaces.length > 0}
                    <p class="text-[11px] text-gray-400 mt-2 text-center">
                        Showing {spaces.length} of {totalAvailable} spaces — search by name or ID to find more
                    </p>
                {/if}
            </div>

            <!-- Footer -->
            <div class="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3 rounded-b-lg">
                <button on:click={() => open = false} class="maas-btn-secondary" disabled={adding}>
                    Cancel
                </button>
                <button on:click={handleAdd} class="maas-btn-primary" disabled={adding || !selectedSpaceId}>
                    {#if adding}
                        <i class="fas fa-spinner fa-spin mr-2"></i> Adding...
                    {:else}
                        Add to Space
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}
