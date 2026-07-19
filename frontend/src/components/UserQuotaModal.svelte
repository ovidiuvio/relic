<script>
    import { createEventDispatcher } from "svelte";
    import { showToast } from "../stores/toastStore";
    import { setUserQuotas } from "../services/api";
    import { formatBytes } from "../services/typeUtils";

    export let show = false;
    export let user = null;

    const dispatch = createEventDispatcher();

    const FIELDS = [
        {
            column: "quota_max_relics",
            quota: "max_relics",
            label: "Maximum relics",
            help: "Total relics this user may own.",
        },
        {
            column: "quota_max_relics_per_day",
            quota: "max_relics_per_day",
            label: "Maximum relics per day",
            help: "Rolling 24-hour window.",
        },
        {
            column: "quota_max_storage_bytes",
            quota: "max_storage_bytes",
            label: "Maximum storage (bytes)",
            help: "Total bytes across all relics, forks included.",
        },
    ];

    let values = {};
    let saving = false;

    // Reload whenever a different user is opened. An empty string in the input
    // means "inherit the global default", which is deliberately distinct from
    // 0 ("unlimited") — so we cannot use a number for both states.
    $: if (user) {
        values = {};
        for (const field of FIELDS) {
            const override = user.quota_overrides?.[field.column];
            values[field.column] = override === null || override === undefined ? "" : override;
        }
    }

    async function save() {
        saving = true;
        try {
            const payload = {};
            for (const field of FIELDS) {
                const raw = values[field.column];
                payload[field.column] =
                    raw === "" || raw === null ? null : Number(raw);
            }
            await setUserQuotas(user.id, payload);
            showToast("Quotas updated", "success");
            dispatch("saved");
        } catch (error) {
            showToast(
                error.response?.data?.detail || "Failed to update quotas",
                "error",
            );
        } finally {
            saving = false;
        }
    }
</script>

{#if show && user}
    <div
        class="fixed inset-0 bg-black bg-opacity-50 z-[200] flex items-center justify-center p-4"
    >
        <div class="bg-white rounded-lg shadow-xl max-w-lg w-full p-6">
            <h3 class="text-base font-semibold text-gray-900 mb-1">
                Quotas for {user.name || user.public_id || user.id}
            </h3>
            <p class="text-sm text-gray-500 mb-5">
                Leave a field blank to inherit the instance default. Enter
                <span class="font-mono">0</span> for unlimited.
            </p>

            <div class="space-y-4">
                {#each FIELDS as field}
                    <div>
                        <label
                            for="quota-{field.column}"
                            class="block text-sm font-medium text-gray-900"
                        >
                            {field.label}
                        </label>
                        <div class="flex items-center gap-3 mt-1">
                            <input
                                id="quota-{field.column}"
                                type="number"
                                min="0"
                                bind:value={values[field.column]}
                                placeholder="inherit ({user.quotas?.[
                                    field.quota
                                ] || 'unlimited'})"
                                class="w-56 px-2 py-1 text-sm border border-gray-300 rounded font-mono"
                            />
                            <span class="text-xs text-gray-500">
                                {field.help}
                            </span>
                        </div>
                    </div>
                {/each}
            </div>

            <div
                class="mt-5 pt-4 border-t border-gray-200 text-xs text-gray-500"
            >
                Currently using {user.relic_count} relic{user.relic_count === 1
                    ? ""
                    : "s"} and {formatBytes(user.storage_bytes || 0)}.
                {#if user.is_admin}
                    <span class="text-amber-700">
                        This user is an admin, so quotas do not apply to them.
                    </span>
                {/if}
            </div>

            <div class="flex justify-end gap-3 mt-6">
                <button
                    class="maas-btn-secondary"
                    on:click={() => dispatch("cancel")}
                >
                    Cancel
                </button>
                <button
                    class="maas-btn-primary"
                    disabled={saving}
                    on:click={save}
                >
                    {#if saving}<i class="fas fa-spinner fa-spin mr-1"></i>{/if}
                    Save
                </button>
            </div>
        </div>
    </div>
{/if}
