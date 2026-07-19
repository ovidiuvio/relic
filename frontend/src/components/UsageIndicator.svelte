<script>
    import { onMount } from "svelte";
    import { getUserUsage } from "../services/api";
    import { formatBytes } from "../services/typeUtils";

    let usage = null;
    let exempt = false;

    // Only dimensions with an actual limit are worth showing.
    $: bounded = usage
        ? Object.entries(usage).filter(([, v]) => !v.unlimited)
        : [];

    const LABELS = {
        relics: "Relics",
        relics_today: "Created today",
        storage_bytes: "Storage",
    };

    function format(key, value) {
        return key === "storage_bytes" ? formatBytes(value) : value;
    }

    function percent(entry) {
        if (!entry.limit) return 0;
        return Math.min(100, Math.round((entry.used / entry.limit) * 100));
    }

    onMount(async () => {
        try {
            const { data } = await getUserUsage();
            usage = data.usage;
            exempt = data.exempt;
        } catch {
            // Anonymous or unreachable — the indicator simply does not render.
        }
    });
</script>

{#if usage && !exempt && bounded.length}
    <div class="flex flex-wrap items-center gap-4 px-3 py-2 mb-3 bg-gray-50 border border-gray-200 rounded text-xs">
        {#each bounded as [key, entry]}
            <div class="flex items-center gap-2">
                <span class="text-gray-500">{LABELS[key] || key}</span>
                <span class="font-mono text-gray-900">
                    {format(key, entry.used)} / {format(key, entry.limit)}
                </span>
                <div class="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div
                        class="h-full rounded-full {percent(entry) >= 90
                            ? 'bg-red-500'
                            : percent(entry) >= 70
                              ? 'bg-amber-500'
                              : 'bg-[#E95420]'}"
                        style="width: {percent(entry)}%"
                    ></div>
                </div>
            </div>
        {/each}
    </div>
{/if}
