<script>
    import { createEventDispatcher } from 'svelte'
    import { updateRelic } from '../services/api/relics'
    import Toast from './Toast.svelte'
    import { showToast } from '../stores/toastStore'
    import Select from 'svelte-select'
    import { getAvailableSyntaxOptions, getFileTypeDefinition, getContentType } from '../services/typeUtils'

    export let relic
    export let show = false

    const dispatch = createEventDispatcher()
    const syntaxOptions = getAvailableSyntaxOptions()

    let name = ''
    let syntax = 'auto'
    let syntaxValue = { value: 'auto', label: 'Auto-detect' }
    let accessLevel = 'public'
    let expiresIn = 'no-change'
    let loading = false
    let initialized = false

    // Update syntax when syntaxValue changes
    $: syntax = syntaxValue?.value || 'auto'

    // Initialize form when modal is shown
    $: if (show && relic && !initialized) {
        name = relic.name || ''
        accessLevel = relic.access_level || 'public'
        expiresIn = 'no-change'

        // Determine initial syntax value from language_hint or content_type
        syntaxValue = syntaxOptions.find(opt => opt.value === relic.language_hint) ||
                      syntaxOptions.find(opt => {
                          const typeDef = getFileTypeDefinition(relic.content_type)
                          return typeDef && opt.value === typeDef.syntax
                      }) ||
                      { value: 'auto', label: 'Auto-detect' }
        initialized = true
    }

    // Reset initialized flag when modal closes
    $: if (!show) {
        initialized = false
    }

    const expiryOptions = [
        { value: 'no-change', label: 'No change (keep current)' },
        { value: 'never', label: 'Remove expiry (never expire)' },
        { value: '1h', label: '1 hour from now' },
        { value: '24h', label: '24 hours from now' },
        { value: '7d', label: '7 days from now' },
        { value: '30d', label: '30 days from now' }
    ]

    async function handleSubmit() {
        loading = true
        try {
            // Compute content_type and language_hint from syntax (like RelicForm does)
            const contentType = syntax !== 'auto' ? getContentType(syntax) : relic.content_type
            const languageHint = syntax !== 'auto' ? syntax : null

            const updates = {
                name,
                content_type: contentType,
                language_hint: languageHint,
                access_level: accessLevel,
            }

            // Only include expires_in if user wants to change it
            if (expiresIn !== 'no-change') {
                updates.expires_in = expiresIn
            }

            const response = await updateRelic(relic.id, updates)
            showToast('Relic updated successfully', 'success')
            dispatch('update', response.data)
            close()
        } catch (error) {
            console.error('Update failed:', error)
            showToast(error.message || 'Failed to update relic', 'error')
        } finally {
            loading = false
        }
    }

    function close() {
        dispatch('close')
    }
</script>

{#if show}
    <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" on:click|self={close}>
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
            <h2 class="text-xl font-bold text-gray-900 dark:text-white">Edit Relic</h2>

            <div class="space-y-4">
                <!-- Name -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Name
                    </label>
                    <input
                        type="text"
                        bind:value={name}
                        class="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:ring-2 focus:ring-blue-500"
                        placeholder="Relic name"
                    />
                </div>

                <!-- Language / Syntax -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Language / Syntax
                    </label>
                    <Select
                        items={syntaxOptions}
                        bind:value={syntaxValue}
                        placeholder="Select language..."
                        searchable={true}
                        clearable={false}
                        --border-radius="0.375rem"
                        --background="white"
                        --list-background="white"
                        --item-hover-bg="#EFF6FF"
                        --border="1px solid #D1D5DB"
                        --border-focused="1px solid #3B82F6"
                        --border-hover="1px solid #9CA3AF"
                    />
                    <p class="text-xs text-gray-500 mt-1">
                        Current: {relic.content_type || 'text/plain'} {relic.language_hint ? `(${relic.language_hint})` : ''}
                    </p>
                </div>

                <!-- Access Level -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Visibility
                    </label>
                    <div class="flex space-x-4">
                        <label class="inline-flex items-center">
                            <input
                                type="radio"
                                bind:group={accessLevel}
                                value="public"
                                class="form-radio text-blue-600"
                            />
                            <span class="ml-2 text-gray-700 dark:text-gray-300">Public</span>
                        </label>
                        <label class="inline-flex items-center">
                            <input
                                type="radio"
                                bind:group={accessLevel}
                                value="private"
                                class="form-radio text-blue-600"
                            />
                            <span class="ml-2 text-gray-700 dark:text-gray-300">Private</span>
                        </label>
                    </div>
                </div>

                <!-- Expiry -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Expiry
                    </label>
                    <select
                        bind:value={expiresIn}
                        class="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:ring-2 focus:ring-blue-500"
                    >
                        {#each expiryOptions as option}
                            <option value={option.value}>{option.label}</option>
                        {/each}
                    </select>
                    <p class="text-xs text-gray-500 mt-1">
                        Current expiry: {relic.expires_at ? new Date(relic.expires_at).toLocaleString() : 'Never'}
                    </p>
                </div>
            </div>

            <div class="flex justify-end space-x-3 mt-6">
                <button
                    on:click={close}
                    class="px-4 py-2 text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-white"
                >
                    Cancel
                </button>
                <button
                    on:click={handleSubmit}
                    disabled={loading}
                    class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center"
                >
                    {#if loading}
                        <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Saving...
                    {:else}
                        Save Changes
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}
