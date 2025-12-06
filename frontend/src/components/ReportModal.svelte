<script>
    import { createEventDispatcher } from "svelte";
    import { submitReport } from "../services/api";
    import { showToast } from "../stores/toastStore";

    export let open = false;
    export let relicId = "";
    export let relicName = "";

    let reason = "";
    let isLoading = false;
    const dispatch = createEventDispatcher();

    async function handleSubmit(e) {
        e.preventDefault();
        if (!reason.trim()) {
            showToast("Please provide a reason for the report", "warning");
            return;
        }

        isLoading = true;
        try {
            await submitReport(relicId, reason);
            showToast("Report submitted successfully", "success");
            closeModal();
            reason = ""; // Reset form
        } catch (error) {
            console.error("Failed to submit report:", error);
            showToast(
                error.response?.data?.detail || "Failed to submit report",
                "error",
            );
        } finally {
            isLoading = false;
        }
    }

    function closeModal() {
        open = false;
        dispatch("close");
    }

    function handleBackdropClick(e) {
        if (e.target === e.currentTarget) {
            closeModal();
        }
    }
</script>

{#if open}
    <div
        class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
        on:click={handleBackdropClick}
    >
        <div
            class="bg-white rounded-lg shadow-xl w-full max-w-md overflow-hidden flex flex-col transition-all duration-300"
            on:click|stopPropagation
        >
            <!-- Header -->
            <div
                class="px-6 py-3 border-b border-gray-200 flex items-center justify-between flex-shrink-0"
            >
                <div class="flex items-center gap-3">
                    <h2
                        class="text-lg font-semibold text-gray-900 flex items-center"
                    >
                        <i class="fas fa-flag text-red-600 mr-2"></i>
                        Report Relic
                    </h2>
                </div>
                <button
                    on:click={closeModal}
                    class="text-gray-400 hover:text-gray-600 transition-colors p-1"
                    title="Close"
                >
                    <i class="fas fa-times"></i>
                </button>
            </div>

            <!-- Form -->
            <form on:submit={handleSubmit} class="p-6">
                <div class="mb-4">
                    <p class="text-sm text-gray-600 mb-2">
                        Reporting: <span class="font-medium text-gray-900"
                            >{relicName || relicId}</span
                        >
                    </p>
                    <label
                        for="reason"
                        class="block text-sm font-medium text-gray-700 mb-1"
                    >
                        Reason for reporting
                    </label>
                    <textarea
                        id="reason"
                        bind:value={reason}
                        rows="4"
                        class="w-full border border-gray-300 rounded-md shadow-sm p-2 focus:ring-red-500 focus:border-red-500 sm:text-sm"
                        placeholder="Please describe why this content is inappropriate..."
                        required
                    ></textarea>
                </div>

                <div class="flex justify-end gap-3">
                    <button
                        type="button"
                        on:click={closeModal}
                        disabled={isLoading}
                        class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        disabled={isLoading}
                        class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 shadow-sm disabled:opacity-50 flex items-center"
                    >
                        {#if isLoading}
                            <i class="fas fa-spinner fa-spin mr-2"></i>
                            Submitting...
                        {:else}
                            Submit Report
                        {/if}
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}
