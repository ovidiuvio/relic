<script>
    import { createEventDispatcher } from 'svelte'
    import { updateRelic } from '../services/api/relics'
    import { getRelicAccess, addRelicAccess, removeRelicAccess } from '../services/api/relics'
    import { showToast } from '../stores/toastStore'

    export let open = false
    export let relic

    const dispatch = createEventDispatcher()

    let selectedLevel = relic.access_level || 'public'
    let saving = false

    // Access list state
    let accessList = []
    let loadingAccess = false
    let managingAccess = false
    let newPublicId = ''
    let accessFetched = false

    $: if (open) {
        selectedLevel = relic.access_level || 'public'
        accessList = []
        accessFetched = false
    }

    $: if (selectedLevel === 'restricted' && !accessFetched && !loadingAccess) {
        fetchAccess()
    }

    async function fetchAccess() {
        loadingAccess = true
        accessFetched = true
        try {
            const res = await getRelicAccess(relic.id)
            accessList = res.data
        } catch {
            showToast('Failed to load access list', 'error')
        } finally {
            loadingAccess = false
        }
    }

    async function save() {
        if (selectedLevel === relic.access_level) { close(); return }
        saving = true
        try {
            const res = await updateRelic(relic.id, { access_level: selectedLevel })
            showToast('Visibility updated', 'success')
            dispatch('update', res.data)
            close()
        } catch {
            showToast('Failed to update visibility', 'error')
        } finally {
            saving = false
        }
    }

    async function addAccess() {
        const publicId = newPublicId.trim()
        if (!publicId) return
        managingAccess = true
        try {
            const res = await addRelicAccess(relic.id, publicId)
            accessList = [...accessList, res.data]
            newPublicId = ''
            showToast('Access granted', 'success')
        } catch (err) {
            showToast(err.response?.data?.detail || 'Failed to add access', 'error')
        } finally {
            managingAccess = false
        }
    }

    async function removeAccess(publicId) {
        try {
            await removeRelicAccess(relic.id, publicId)
            accessList = accessList.filter(e => e.public_id !== publicId)
            showToast('Access removed', 'success')
        } catch {
            showToast('Failed to remove access', 'error')
        }
    }

    function close() { dispatch('close') }

    const levels = [
        {
            value: 'public',
            icon: 'fa-globe',
            label: 'Public',
            description: 'Listed in recents and discoverable by anyone.',
            bg: '#e2f2fd', color: '#217db1', borderActive: '#217db1',
        },
        {
            value: 'private',
            icon: 'fa-lock',
            label: 'Private',
            description: 'Hidden from recents. Only accessible via direct URL.',
            bg: '#fce3eb', color: '#76306c', borderActive: '#76306c',
        },
        {
            value: 'restricted',
            icon: 'fa-user-lock',
            label: 'Restricted',
            description: 'Only you and explicitly allowed clients can view it.',
            bg: '#fef3c7', color: '#b45309', borderActive: '#b45309',
        },
    ]
</script>

{#if open}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="fixed inset-0 bg-black/50 z-[100] flex items-center justify-center p-4 backdrop-blur-sm" on:click|self={close}>
        <div class="bg-white rounded-xl shadow-2xl max-w-lg w-full overflow-hidden flex flex-col" role="dialog" aria-modal="true">

            <!-- Header -->
            <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600">
                        <i class="fas fa-shield-alt text-xl" aria-hidden="true"></i>
                    </div>
                    <div>
                        <h2 class="text-lg font-bold text-gray-800 leading-tight">Visibility & Access</h2>
                        <p class="text-xs text-gray-500 font-medium uppercase tracking-wider truncate max-w-xs">{relic.name || relic.id}</p>
                    </div>
                </div>
                <button aria-label="Close modal" on:click={close} class="w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all">
                    <i class="fas fa-times" aria-hidden="true"></i>
                </button>
            </div>

            <div class="p-6 space-y-5 overflow-auto">

                <!-- Visibility Picker -->
                <div class="space-y-2">
                    {#each levels as level}
                        {@const active = selectedLevel === level.value}
                        <button
                            aria-pressed={active}
                            on:click={() => selectedLevel = level.value}
                            class="w-full flex items-center gap-4 px-4 py-3 rounded-xl border-2 text-left transition-all"
                            style="border-color: {active ? level.borderActive : '#e5e7eb'}; background: {active ? level.bg : 'white'};"
                        >
                            <div class="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0" style="background: {level.bg}; color: {level.color};">
                                <i class="fas {level.icon} text-sm" aria-hidden="true"></i>
                            </div>
                            <div class="flex-1 min-w-0">
                                <div class="text-sm font-bold" style="color: {active ? level.color : '#374151'};">{level.label}</div>
                                <div class="text-xs text-gray-500 mt-0.5">{level.description}</div>
                            </div>
                            {#if active}
                                <i class="fas fa-check-circle flex-shrink-0" style="color: {level.color};" aria-hidden="true"></i>
                            {/if}
                        </button>
                    {/each}
                </div>

                <!-- Access List (only when Restricted) -->
                {#if selectedLevel === 'restricted'}
                    <div class="space-y-3 pt-1 border-t border-gray-100">
                        <h3 class="text-sm font-bold text-gray-700 flex items-center gap-2">
                            <i class="fas fa-users text-amber-500" aria-hidden="true"></i>
                            Allowed Clients
                        </h3>

                        <!-- Add user row -->
                        <div class="flex gap-2">
                            <input
                                type="text"
                                bind:value={newPublicId}
                                placeholder="Enter user's Public ID"
                                class="maas-input flex-1 font-mono text-sm bg-white"
                                on:keydown={(e) => e.key === 'Enter' && addAccess()}
                            />
                            <button
                                on:click={addAccess}
                                disabled={managingAccess || !newPublicId.trim()}
                                class="maas-btn-primary px-4 flex items-center gap-1.5 whitespace-nowrap"
                            >
                                {#if managingAccess}
                                    <i class="fas fa-spinner fa-spin text-xs" aria-hidden="true"></i>
                                {:else}
                                    <i class="fas fa-user-plus text-xs" aria-hidden="true"></i>
                                    <span>Add</span>
                                {/if}
                            </button>
                        </div>

                        <!-- List -->
                        {#if loadingAccess}
                            <div class="text-center py-6 text-gray-400 text-sm">
                                <i class="fas fa-spinner fa-spin mr-2" aria-hidden="true"></i>Loading...
                            </div>
                        {:else if accessList.length === 0}
                            <div class="text-center py-6 px-4 bg-gray-50 rounded-xl border border-dashed border-gray-200">
                                <i class="fas fa-user-lock text-gray-300 text-2xl mb-2" aria-hidden="true"></i>
                                <p class="text-xs text-gray-500">No users added yet. Only you can view this relic.</p>
                            </div>
                        {:else}
                            <div class="border border-gray-200 rounded-xl overflow-hidden bg-white">
                                <table class="min-w-full divide-y divide-gray-100">
                                    <tbody class="divide-y divide-gray-50">
                                        {#each accessList as entry}
                                            <tr class="hover:bg-gray-50 transition-colors">
                                                <td class="px-4 py-2.5">
                                                    <div class="flex items-center gap-2.5">
                                                        <div class="w-7 h-7 rounded-full bg-amber-50 flex items-center justify-center text-amber-600 border border-amber-100 flex-shrink-0">
                                                            <i class="fas fa-user text-[10px]" aria-hidden="true"></i>
                                                        </div>
                                                        <div>
                                                            <div class="text-sm font-semibold text-gray-900">{entry.client_name || 'Anonymous'}</div>
                                                            <div class="text-[10px] text-gray-400 font-mono">{entry.public_id || '—'}</div>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td class="px-4 py-2.5 text-xs text-gray-400 whitespace-nowrap">
                                                    {new Date(entry.created_at).toLocaleDateString()}
                                                </td>
                                                <td class="px-4 py-2.5 text-right">
                                                    <button
                                                        aria-label="Remove access"
                                                        on:click={() => removeAccess(entry.public_id)}
                                                        class="w-7 h-7 rounded-lg flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50 transition-all ml-auto"
                                                        title="Remove access"
                                                    >
                                                        <i class="fas fa-trash-alt text-[10px]" aria-hidden="true"></i>
                                                    </button>
                                                </td>
                                            </tr>
                                        {/each}
                                    </tbody>
                                </table>
                            </div>
                        {/if}
                    </div>
                {/if}

            </div>

            <!-- Footer -->
            <div class="px-6 py-4 bg-gray-50/50 border-t border-gray-100 flex justify-end gap-3">
                <button on:click={close} class="maas-btn-secondary px-6">Cancel</button>
                <button
                    on:click={save}
                    disabled={saving}
                    class="maas-btn-primary px-6 flex items-center gap-2"
                >
                    {#if saving}
                        <i class="fas fa-spinner fa-spin text-xs" aria-hidden="true"></i> Saving...
                    {:else}
                        <i class="fas fa-check text-xs" aria-hidden="true"></i> Save
                    {/if}
                </button>
            </div>

        </div>
    </div>
{/if}
