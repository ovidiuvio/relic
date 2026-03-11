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

    async function loadSpaces() {
        loading = true;
        try {
            // Fetch spaces where user has editor, owner, or admin role
            const allSpaces = await spacesApi.list();
            spaces = allSpaces.filter(s => ['owner', 'editor', 'admin'].includes(s.role));
            if (spaces.length > 0) {
                selectedSpaceId = spaces[0].id;
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
    <div class="fixed inset-0 bg-black/50 z-[100] flex items-center justify-center p-4 backdrop-blur-sm">
        <div class="bg-white rounded-xl shadow-2xl max-w-md w-full overflow-hidden animate-in fade-in zoom-in duration-200">
            <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                <h3 class="text-lg font-bold text-gray-800">Add to Space</h3>
                <button on:click={() => open = false} class="text-gray-400 hover:text-gray-600 transition-colors">
                    <i class="fas fa-times text-lg"></i>
                </button>
            </div>

            <div class="p-6 space-y-4">
                <div class="flex items-center gap-3 p-3 bg-blue-50 border border-blue-100 rounded-lg">
                    <i class="fas fa-file-alt text-blue-500"></i>
                    <div class="min-w-0">
                        <div class="text-xs font-medium text-blue-600 uppercase tracking-wider">Adding Relic</div>
                        <div class="text-sm font-bold text-blue-900 truncate" title={relicName}>{relicName || 'Untitled'}</div>
                    </div>
                </div>

                <div>
                    <div class="block text-sm font-medium text-gray-700 mb-2">Select Space</div>
                    {#if loading}
                        <div class="flex items-center justify-center py-4">
                            <i class="fas fa-spinner fa-spin text-gray-400"></i>
                        </div>
                    {:else if spaces.length === 0}
                        <div class="text-center py-6 px-4 bg-gray-50 rounded-lg border border-dashed border-gray-300">
                            <i class="fas fa-layer-group text-gray-300 text-2xl mb-2"></i>
                            <p class="text-sm text-gray-500">You don't have any spaces where you can add relics.</p>
                        </div>
                    {:else}
                        <div class="space-y-2 max-h-48 overflow-y-auto pr-1">
                            {#each spaces as space}
                                <label 
                                    for="space-{space.id}"
                                    class="flex items-center p-3 border rounded-lg cursor-pointer transition-all hover:bg-gray-50 {selectedSpaceId === space.id ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500' : 'border-gray-200'}"
                                >
                                    <input 
                                        id="space-{space.id}"
                                        type="radio" 
                                        bind:group={selectedSpaceId} 
                                        value={space.id} 
                                        class="hidden"
                                    >
                                    <i class="fas {space.visibility === 'public' ? 'fa-globe' : 'fa-lock'} text-gray-400 mr-3"></i>
                                    <span class="flex-1 font-medium text-sm text-gray-700 truncate">{space.name}</span>
                                    {#if selectedSpaceId === space.id}
                                        <i class="fas fa-check-circle text-blue-600"></i>
                                    {/if}
                                </label>
                            {/each}
                        </div>
                    {/if}
                </div>
            </div>

            <div class="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-end gap-3">
                <button
                    on:click={() => open = false}
                    class="maas-btn-secondary"
                    disabled={adding}
                >
                    Cancel
                </button>
                <button
                    on:click={handleAdd}
                    class="maas-btn-primary px-6"
                    disabled={adding || !selectedSpaceId || spaces.length === 0}
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

<style>
    .animate-in {
        animation: animate-in 0.2s ease-out;
    }

    @keyframes animate-in {
        from {
            opacity: 0;
            transform: scale(0.95);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }
</style>
