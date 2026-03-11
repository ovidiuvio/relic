<script>
    import { onMount } from 'svelte';
    import { spaces as spacesApi } from '../services/api';
    import { showToast } from '../stores/toastStore';

    export let open = false;
    export let relicId;
    export let relicName;

    let spaces = [];
    let loading = false;
    let adding = false;
    let selectedSpaceId = '';
    let searchTerm = '';

    $: filteredSpaces = spaces.filter(space => {
        if (!searchTerm.trim()) return true;
        const term = searchTerm.toLowerCase();
        return space.name.toLowerCase().includes(term) || space.id.toLowerCase().includes(term);
    }).sort((a, b) => {
        // Sort user spaces (owner) first, then shared spaces
        const roleWeight = { 'owner': 3, 'admin': 2, 'editor': 1, 'viewer': 0 };
        const weightA = roleWeight[a.role] || 0;
        const weightB = roleWeight[b.role] || 0;
        
        if (weightA !== weightB) {
            return weightB - weightA;
        }
        // Then sort by name alphabetically
        return a.name.localeCompare(b.name);
    });

    // Reset selection if the selected space gets filtered out, or to pick the very first one
    $: if (filteredSpaces.length > 0 && !filteredSpaces.find(s => s.id === selectedSpaceId)) {
        selectedSpaceId = filteredSpaces[0].id;
    }

    async function loadSpaces() {
        loading = true;
        searchTerm = '';
        try {
            // Fetch spaces where user has editor, owner, or admin role
            const allSpaces = await spacesApi.list();
            spaces = allSpaces.filter(s => ['owner', 'editor', 'admin'].includes(s.role));
            if (spaces.length > 0) {
                // Preselect the highest weighted one
                const sorted = [...spaces].sort((a, b) => {
                    const roleWeight = { 'owner': 3, 'admin': 2, 'editor': 1 };
                    return (roleWeight[b.role] || 0) - (roleWeight[a.role] || 0);
                });
                selectedSpaceId = sorted[0].id;
            } else {
                selectedSpaceId = '';
            }
        } catch (error) {
            console.error("Failed to load spaces:", error);
            showToast("Failed to load spaces", "error");
        } finally {
            loading = false;
        }
    }

    async function handleAdd() {
        if (!selectedSpaceId) {
            showToast("Please select a space", "error");
            return;
        }

        adding = true;
        try {
            await spacesApi.addRelic(selectedSpaceId, relicId);
            showToast(`Added to space: ${spaces.find(s => s.id === selectedSpaceId)?.name}`, "success");
            open = false;
        } catch (error) {
            console.error("Failed to add relic to space:", error);
            const detail = error.response?.data?.detail || "Failed to add relic to space";
            showToast(detail, "error");
        } finally {
            adding = false;
        }
    }

    $: if (open) {
        loadSpaces();
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

            <!-- Body -->
            <div class="p-6 flex flex-col min-h-0 bg-white">
                <div>
                    <label for="searchSpace" class="block text-sm font-medium text-gray-700 mb-2">Select Space</label>
                    <div class="relative mb-4 flex-shrink-0">
                        <i class="fa-solid fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                        <input
                            id="searchSpace"
                            type="text"
                            bind:value={searchTerm}
                            placeholder="Search spaces by name or ID..."
                            class="w-full pl-9 pr-3 py-2 text-sm maas-input"
                        />
                    </div>
                </div>

                <!-- Spaces List -->
                <div class="flex-1 overflow-y-auto pr-1 min-h-[250px] max-h-[350px]">
                    {#if loading}
                        <div class="flex items-center justify-center py-8">
                            <i class="fas fa-spinner fa-spin text-blue-600 text-2xl"></i>
                        </div>
                    {:else if spaces.length === 0}
                        <div class="text-center py-8 px-4 bg-gray-50 rounded-lg border border-dashed border-gray-300">
                            <i class="fas fa-layer-group text-gray-300 text-3xl mb-3"></i>
                            <p class="text-sm text-gray-600">You don't have any spaces where you can add relics.</p>
                        </div>
                    {:else if filteredSpaces.length === 0}
                        <div class="text-center py-8 px-4">
                            <p class="text-sm text-gray-600">No spaces match your search.</p>
                        </div>
                    {:else}
                        <div class="space-y-2">
                            {#each filteredSpaces as space (space.id)}
                                <label 
                                    class="flex items-center p-3 border rounded-lg cursor-pointer transition-colors {selectedSpaceId === space.id ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500' : 'border-gray-200 hover:bg-gray-50'}"
                                >
                                    <input 
                                        type="radio" 
                                        bind:group={selectedSpaceId} 
                                        value={space.id} 
                                        class="hidden"
                                    >
                                    
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
            </div>

            <!-- Footer -->
            <div class="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3 rounded-b-lg">
                <button
                    on:click={() => open = false}
                    class="maas-btn-secondary"
                    disabled={adding}
                >
                    Cancel
                </button>
                <button
                    on:click={handleAdd}
                    class="maas-btn-primary"
                    disabled={adding || !selectedSpaceId || filteredSpaces.length === 0}
                >
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
