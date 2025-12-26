<script>
    import { onMount } from "svelte";
    import { getRelic } from "../../services/api";
    import RelicTable from "../RelicTable.svelte";
    import { getDefaultItemsPerPage, getTypeLabel } from "../../services/typeUtils";
    import { filterRelics, sortData, calculateTotalPages, paginateData, clampPage } from "../../services/paginationUtils";

    export let processed;
    export let relicId;

    let relics = [];
    let loading = true;
    let error = null;
    let progress = 0;
    let total = 0;
    let searchTerm = '';
    let currentPage = 1;
    let itemsPerPage = 25;
    let sortBy = 'date';
    let sortOrder = 'desc';

    $: title = processed.meta?.title || "Relic Index";
    $: description = processed.meta?.description || "";

    // Pagination logic
    $: filteredRelics = filterRelics(relics, searchTerm, getTypeLabel);
    
    // Apply sorting
    $: sortedRelics = sortData(filteredRelics, sortBy, sortOrder);

    $: totalPages = calculateTotalPages(sortedRelics, itemsPerPage);
    $: paginatedRelics = paginateData(sortedRelics, currentPage, itemsPerPage);

    function goToPage(page) {
        currentPage = clampPage(page, totalPages);
    }

    async function loadRelics() {
        loading = true;
        error = null;
        relics = [];

        // processed.relics is now an array of objects { id, title?, description?, tags? }
        const items = processed.relics || [];
        total = items.length;

        if (total === 0) {
            loading = false;
            return;
        }

        // Fetch relics in batches to avoid overwhelming the server
        const batchSize = 5;
        const results = [];

        for (let i = 0; i < total; i += batchSize) {
            const batch = items.slice(i, i + batchSize);
            const promises = batch.map(async (item) => {
                // Validate ID format - discard invalid IDs
                if (!/^[a-f0-9]{32}$/i.test(item.id)) {
                    console.warn(`[RelicIndex] Invalid ID format, skipping: ${item.id}`);
                    return null;
                }

                try {
                    const response = await getRelic(item.id);
                    const relicData = response.data;

                    // Apply overrides from the index file
                    if (item.title) relicData.name = item.title;
                    if (item.description)
                        relicData.description = item.description;
                    if (item.tags) relicData.tags = item.tags;

                    return relicData;
                } catch (err) {
                    // Discard relics that don't exist or can't be accessed
                    console.warn(`[RelicIndex] Skipping relic ${item.id}:`, err.response?.status || err.message);
                    return null;
                }
            });

            const batchResults = await Promise.all(promises);
            // Filter out null results (invalid or inaccessible relics)
            const validResults = batchResults.filter(r => r !== null);
            results.push(...validResults);
            progress = Math.min(i + batch.length, total);

            // Update relics progressively with only valid results
            relics = [...results];
        }

        loading = false;
    }

    onMount(() => {
        itemsPerPage = getDefaultItemsPerPage();
        loadRelics();
    });
</script>

<div class="space-y-4">
    {#if error}
        <div
            class="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
        >
            {error}
        </div>
    {/if}

    <RelicTable
        data={sortedRelics}
        {loading}
        bind:searchTerm
        bind:currentPage
        bind:itemsPerPage
        bind:sortBy
        bind:sortOrder
        {totalPages}
        paginatedData={paginatedRelics}
        title={loading ? `${title} (${progress}/${total})` : title}
        titleIcon="fa-list-ul"
        titleIconColor="text-purple-600"
        emptyMessage="No valid relics found in this index."
        emptyMessageWithSearch="No matching relics found in this index."
        tableId="relic-index"
        showForkButton={true}
        {goToPage}
    />
</div>
