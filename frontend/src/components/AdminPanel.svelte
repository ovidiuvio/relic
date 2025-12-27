<script>
    import { onMount } from "svelte";
    import { showToast } from "../stores/toastStore";
    import {
        checkAdminStatus,
        getAdminStats,
        getAdminRelics,
        getAdminClients,
        getAdminConfig,
        getAdminBackups,
        createAdminBackup,
        downloadAdminBackup,
        deleteRelic,
        deleteClient,
        getAdminReports,
        deleteReport,
    } from "../services/api";
    import {
        getTypeLabel,
        getTypeIcon,
        getTypeIconColor,
        formatBytes,
        formatTimeAgo,
    } from "../services/typeUtils";
    import {
        shareRelic,
        copyRelicContent,
        downloadRelic,
        viewRaw,
        copyToClipboard,
    } from "../services/relicActions";

    let isAdmin = false;
    let loading = true;
    let activeTab = "relics";

    // Stats
    let stats = {
        total_relics: 0,
        total_clients: 0,
        total_size_bytes: 0,
        public_relics: 0,
        private_relics: 0,
        admin_count: 0,
    };

    // Relics state
    let relics = [];
    let relicsLoading = false;
    let relicsTotal = 0;
    let relicsPage = 1;
    let relicsLimit = 25;
    let relicsFilter = "all";
    let searchTerm = "";

    // Clients state
    let clients = [];
    let clientsLoading = false;
    let clientsTotal = 0;
    let clientsPage = 1;
    let clientsLimit = 25;

    // Config state
    let config = null;
    let configLoading = false;

    // Backups state
    let backups = [];
    let backupsLoading = false;
    let backupsTotal = 0;
    let backupsTotalSize = 0;
    let backupsPage = 1;
    let backupsLimit = 25;
    let backupInProgress = false;

    // Reports state
    let reports = [];
    let reportsLoading = false;
    let reportsTotal = 0;
    let reportsPage = 1;
    let reportsLimit = 25;

    // Selected client for viewing their relics
    let selectedClient = null;

    // Filter relics by search term
    $: filteredRelics = relics.filter((r) => {
        if (!searchTerm) return true;
        const term = searchTerm.toLowerCase();
        return (
            (r.name || "").toLowerCase().includes(term) ||
            r.id.toLowerCase().includes(term) ||
            (r.content_type || "").toLowerCase().includes(term)
        );
    });

    function formatDate(dateStr) {
        if (!dateStr) return "-";
        return new Date(dateStr).toLocaleString();
    }

    async function checkAdmin() {
        try {
            const response = await checkAdminStatus();
            isAdmin = response.data.is_admin;
        } catch (error) {
            console.error("Failed to check admin status:", error);
            isAdmin = false;
        } finally {
            loading = false;
        }
    }

    async function loadStats() {
        try {
            const response = await getAdminStats();
            stats = response.data;
        } catch (error) {
            console.error("Failed to load admin stats:", error);
            showToast("Failed to load statistics", "error");
        }
    }

    async function loadRelics() {
        relicsLoading = true;
        try {
            const accessLevel = relicsFilter === "all" ? null : relicsFilter;
            const offset = (relicsPage - 1) * relicsLimit;
            const clientId = selectedClient ? selectedClient.id : null;
            const response = await getAdminRelics(
                relicsLimit,
                offset,
                accessLevel,
                clientId,
            );
            relics = response.data.relics || [];
            relicsTotal = response.data.total || 0;
        } catch (error) {
            console.error("Failed to load relics:", error);
            showToast("Failed to load relics", "error");
            relics = [];
        } finally {
            relicsLoading = false;
        }
    }

    async function loadClients() {
        clientsLoading = true;
        try {
            const offset = (clientsPage - 1) * clientsLimit;
            const response = await getAdminClients(clientsLimit, offset);
            clients = response.data.clients || [];
            clientsTotal = response.data.total || 0;
        } catch (error) {
            console.error("Failed to load clients:", error);
            showToast("Failed to load clients", "error");
            clients = [];
        } finally {
            clientsLoading = false;
        }
    }

    async function loadConfig() {
        configLoading = true;
        try {
            const response = await getAdminConfig();
            config = response.data;
        } catch (error) {
            console.error("Failed to load config:", error);
            showToast("Failed to load configuration", "error");
            config = null;
        } finally {
            configLoading = false;
        }
    }

    async function loadBackups() {
        backupsLoading = true;
        try {
            const offset = (backupsPage - 1) * backupsLimit;
            const response = await getAdminBackups(backupsLimit, offset);
            backups = response.data.backups || [];
            backupsTotal = response.data.total || 0;
            backupsTotalSize = response.data.total_size_bytes || 0;
        } catch (error) {
            console.error("Failed to load backups:", error);
            showToast("Failed to load backups", "error");
            backups = [];
        } finally {
            backupsLoading = false;
        }
    }

    async function loadReports() {
        reportsLoading = true;
        try {
            const offset = (reportsPage - 1) * reportsLimit;
            const response = await getAdminReports(reportsLimit, offset);
            reports = response.data.reports || [];
            reportsTotal = response.data.total || 0;
        } catch (error) {
            console.error("Failed to load reports:", error);
            showToast("Failed to load reports", "error");
            reports = [];
        } finally {
            reportsLoading = false;
        }
    }

    async function handleBackupNow() {
        backupInProgress = true;
        try {
            const response = await createAdminBackup();
            if (response.data.success) {
                showToast("Backup created successfully", "success");
                await loadBackups();
            } else {
                showToast(response.data.message || "Backup failed", "error");
            }
        } catch (error) {
            console.error("Failed to create backup:", error);
            showToast("Failed to create backup", "error");
        } finally {
            backupInProgress = false;
        }
    }

    async function handleDeleteRelic(relic) {
        if (
            !confirm(
                `Delete "${relic.name || relic.id}"?\n\nThis cannot be undone.`,
            )
        )
            return;
        try {
            await deleteRelic(relic.id);
            showToast("Relic deleted", "success");
            await loadRelics();
            await loadStats();
        } catch (error) {
            console.error("Failed to delete relic:", error);
            showToast("Failed to delete relic", "error");
        }
    }

    async function handleDeleteClient(client) {
        // First confirm they want to delete
        if (
            !confirm(
                `Delete client "${client.id}"?\n\nThis client owns ${client.relic_count} relic(s).`,
            )
        ) {
            return;
        }

        // Ask what to do with relics
        const deleteRelicsChoice = confirm(
            `Also delete their ${client.relic_count} relic(s)?\n\n` +
                `OK = Delete relics too\n` +
                `Cancel = Keep relics (become anonymous)`,
        );

        try {
            await deleteClient(client.id, deleteRelicsChoice);
            showToast("Client deleted", "success");
            await loadClients();
            await loadStats();
        } catch (error) {
            console.error("Failed to delete client:", error);
            showToast(
                error.response?.data?.detail || "Failed to delete client",
                "error",
            );
        }
    }

    async function handleDismissReport(report) {
        if (!confirm("Dismiss this report?")) return;
        try {
            await deleteReport(report.id);
            showToast("Report dismissed", "success");
            await loadReports();
        } catch (error) {
            console.error("Failed to dismiss report:", error);
            showToast("Failed to dismiss report", "error");
        }
    }

    function navigateToRelic(relicId) {
        window.history.pushState({}, "", `/${relicId}`);
        window.dispatchEvent(new PopStateEvent("popstate"));
    }

    function viewClientRelics(client) {
        selectedClient = client;
        activeTab = "relics";
        relicsPage = 1;
        loadRelics();
    }

    function clearClientFilter() {
        selectedClient = null;
        relicsPage = 1;
        loadRelics();
    }

    function refreshAll() {
        loadStats();
        loadRelics();
        loadClients();
        loadConfig();
        loadBackups();
        loadReports();
    }

    // Watch for filter changes
    $: if (relicsFilter && isAdmin) {
        relicsPage = 1;
        loadRelics();
    }

    $: relicsTotalPages = Math.ceil(relicsTotal / relicsLimit);
    $: clientsTotalPages = Math.ceil(clientsTotal / clientsLimit);
    $: backupsTotalPages = Math.ceil(backupsTotal / backupsLimit);
    $: reportsTotalPages = Math.ceil(reportsTotal / reportsLimit);

    onMount(async () => {
        await checkAdmin();
        if (isAdmin) {
            await Promise.all([
                loadStats(),
                loadRelics(),
                loadClients(),
                loadConfig(),
                loadBackups(),
                loadReports(),
            ]);
        }
    });
</script>

<div class="px-4 sm:px-0">
    {#if loading}
        <div class="p-8 text-center">
            <i class="fas fa-spinner fa-spin text-[#772953] text-2xl"></i>
            <p class="text-sm text-gray-500 mt-2">Loading...</p>
        </div>
    {:else if !isAdmin}
        <div
            class="bg-white shadow-sm rounded-lg border border-gray-200 p-8 text-center"
        >
            <i class="fas fa-lock text-gray-300 text-4xl mb-4"></i>
            <h2 class="text-lg font-semibold text-gray-900 mb-2">
                Access Denied
            </h2>
            <p class="text-gray-600">You don't have admin privileges.</p>
            <p class="text-xs text-gray-500 mt-4">
                Configure via <code class="bg-gray-100 px-1 rounded"
                    >ADMIN_CLIENT_IDS</code
                > env variable.
            </p>
        </div>
    {:else}
        <!-- Stats Row -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div
                class="bg-white shadow-sm rounded-lg border border-gray-200 p-4"
            >
                <div class="flex items-center gap-3">
                    <i class="fas fa-archive text-[#772953] text-xl"></i>
                    <div>
                        <p class="text-2xl font-semibold text-gray-900">
                            {stats.total_relics}
                        </p>
                        <p class="text-xs text-gray-500">Total Relics</p>
                    </div>
                </div>
            </div>
            <div
                class="bg-white shadow-sm rounded-lg border border-gray-200 p-4"
            >
                <div class="flex items-center gap-3">
                    <i class="fas fa-users text-[#0E8420] text-xl"></i>
                    <div>
                        <p class="text-2xl font-semibold text-gray-900">
                            {stats.total_clients}
                        </p>
                        <p class="text-xs text-gray-500">Clients</p>
                    </div>
                </div>
            </div>
            <div
                class="bg-white shadow-sm rounded-lg border border-gray-200 p-4"
            >
                <div class="flex items-center gap-3">
                    <i class="fas fa-database text-[#E95420] text-xl"></i>
                    <div>
                        <p class="text-2xl font-semibold text-gray-900">
                            {formatBytes(stats.total_size_bytes)}
                        </p>
                        <p class="text-xs text-gray-500">Storage</p>
                    </div>
                </div>
            </div>
            <div
                class="bg-white shadow-sm rounded-lg border border-gray-200 p-4"
            >
                <div class="flex items-center gap-3">
                    <i class="fas fa-shield-alt text-[#772953] text-xl"></i>
                    <div>
                        <p class="text-2xl font-semibold text-gray-900">
                            {stats.admin_count}
                        </p>
                        <p class="text-xs text-gray-500">Admins</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tabs -->
        <div class="bg-white shadow-sm rounded-lg border border-gray-200">
            <div
                class="px-6 py-4 border-b border-gray-200 flex items-center justify-between"
            >
                <div class="flex items-center gap-6">
                    <button
                        on:click={() => (activeTab = "relics")}
                        class="text-sm font-medium pb-1 border-b-2 transition-colors {activeTab ===
                        'relics'
                            ? 'border-[#E95420] text-[#E95420]'
                            : 'border-transparent text-gray-500 hover:text-gray-700'}"
                    >
                        <i class="fas fa-archive mr-2"></i>Relics
                    </button>
                    <button
                        on:click={() => (activeTab = "clients")}
                        class="text-sm font-medium pb-1 border-b-2 transition-colors {activeTab ===
                        'clients'
                            ? 'border-[#E95420] text-[#E95420]'
                            : 'border-transparent text-gray-500 hover:text-gray-700'}"
                    >
                        <i class="fas fa-users mr-2"></i>Clients
                    </button>
                    <button
                        on:click={() => (activeTab = "reports")}
                        class="text-sm font-medium pb-1 border-b-2 transition-colors {activeTab ===
                        'reports'
                            ? 'border-[#E95420] text-[#E95420]'
                            : 'border-transparent text-gray-500 hover:text-gray-700'}"
                    >
                        <i class="fas fa-flag mr-2"></i>Reports
                    </button>
                    <button
                        on:click={() => (activeTab = "backups")}
                        class="text-sm font-medium pb-1 border-b-2 transition-colors {activeTab ===
                        'backups'
                            ? 'border-[#E95420] text-[#E95420]'
                            : 'border-transparent text-gray-500 hover:text-gray-700'}"
                    >
                        <i class="fas fa-history mr-2"></i>Backups
                    </button>
                    <button
                        on:click={() => (activeTab = "config")}
                        class="text-sm font-medium pb-1 border-b-2 transition-colors {activeTab ===
                        'config'
                            ? 'border-[#E95420] text-[#E95420]'
                            : 'border-transparent text-gray-500 hover:text-gray-700'}"
                    >
                        <i class="fas fa-cog mr-2"></i>Config
                    </button>
                </div>
                <button
                    on:click={refreshAll}
                    class="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                >
                    <i class="fas fa-sync-alt mr-1"></i>Refresh
                </button>
            </div>

            <!-- Relics Tab -->
            {#if activeTab === "relics"}
                <div
                    class="px-6 py-3 border-b border-gray-200 flex items-center gap-4 bg-gray-50"
                >
                    {#if selectedClient}
                        <div
                            class="flex items-center gap-2 bg-purple-50 border border-purple-200 px-3 py-1.5 rounded text-sm"
                        >
                            <i class="fas fa-user text-purple-600"></i>
                            <span class="text-purple-800 font-mono"
                                >{selectedClient.id}</span
                            >
                            <button
                                on:click={clearClientFilter}
                                class="text-purple-600 hover:text-purple-800 ml-1"
                                title="Clear"
                            >
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    {/if}
                    <select
                        bind:value={relicsFilter}
                        class="px-3 py-1.5 text-sm border border-gray-300 rounded bg-white"
                    >
                        <option value="all">All</option>
                        <option value="public">Public</option>
                        <option value="private">Private</option>
                    </select>
                    <div class="relative flex-1 max-w-md">
                        <i
                            class="fa-solid fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
                        ></i>
                        <input
                            type="text"
                            bind:value={searchTerm}
                            placeholder="Filter by name, type, or id..."
                            class="w-full pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded"
                        />
                    </div>
                </div>

                {#if relicsLoading}
                    <div class="p-8 text-center">
                        <i
                            class="fas fa-spinner fa-spin text-[#772953] text-2xl"
                        ></i>
                    </div>
                {:else if filteredRelics.length === 0}
                    <div class="p-8 text-center text-gray-500">
                        <i class="fas fa-inbox text-4xl mb-2"></i>
                        <p>No relics found</p>
                    </div>
                {:else}
                    <div class="overflow-x-auto">
                        <table class="w-full maas-table text-sm">
                            <thead>
                                <tr
                                    class="text-gray-500 uppercase text-xs tracking-wider bg-gray-50"
                                >
                                    <th>Title / ID</th><th>Owner</th><th
                                        >Created</th
                                    ><th>Size</th><th class="w-40">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each filteredRelics as relic (relic.id)}
                                    <tr class="hover:bg-gray-50">
                                        <td>
                                            <div
                                                class="flex items-center gap-1.5"
                                            >
                                                {#if relic.access_level === "private"}
                                                    <i
                                                        class="fas fa-lock text-xs"
                                                        style="color: #76306c;"
                                                        title="Private"
                                                    ></i>
                                                {:else}
                                                    <i
                                                        class="fas fa-globe text-xs"
                                                        style="color: #217db1;"
                                                        title="Public"
                                                    ></i>
                                                {/if}
                                                <i
                                                    class="fas {getTypeIcon(
                                                        relic.content_type,
                                                    )} {getTypeIconColor(
                                                        relic.content_type,
                                                    )} text-sm"
                                                    title={getTypeLabel(
                                                        relic.content_type,
                                                    )}
                                                ></i>
                                                <a
                                                    href="/{relic.id}"
                                                    class="font-medium text-[#0066cc] hover:underline truncate"
                                                    >{relic.name ||
                                                        "Untitled"}</a
                                                >
                                                <!-- Views & Bookmarks (Top Row) -->
                                                <div class="flex items-center gap-2 ml-3 text-[10px] text-gray-400/80 whitespace-nowrap mt-[1px]">
                                                    <span class="flex items-center gap-1" title="Views">
                                                        <i class="fas fa-eye text-[9px] translate-y-[0.5px]"></i>
                                                        {relic.access_count || 0}
                                                    </span>
                                                    <span class="flex items-center gap-1" title="Bookmarks">
                                                        <i class="fas fa-bookmark text-[9px] translate-y-[0.5px]"></i>
                                                        {relic.bookmark_count || 0}
                                                    </span>
                                                </div>
                                            </div>
                                            <div
                                                class="flex items-center group gap-1 mt-1"
                                            >
                                                <span
                                                    class="text-xs text-gray-400 font-mono"
                                                    >{relic.id}</span
                                                >
                                                <button
                                                    on:click|stopPropagation={() =>
                                                        copyToClipboard(relic.id, 'Relic ID copied to clipboard!')}
                                                    class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-gray-600 transition-all"
                                                    title="Copy ID"
                                                >
                                                    <i
                                                        class="fas fa-copy text-xs"
                                                    ></i>
                                                </button>
                                            </div>
                                        </td>
                                        <td>
                                            {#if relic.client_id}
                                                <button
                                                    on:click={() =>
                                                        viewClientRelics({
                                                            id: relic.client_id,
                                                        })}
                                                    class="text-xs font-mono text-purple-600 hover:text-purple-800 hover:underline"
                                                    title="View client's relics"
                                                >
                                                    {relic.client_id}
                                                </button>
                                            {:else}
                                                <span
                                                    class="text-gray-400 text-xs"
                                                    >anonymous</span
                                                >
                                            {/if}
                                        </td>
                                        <td class="text-gray-500 text-xs"
                                            >{formatTimeAgo(
                                                relic.created_at,
                                            )}</td
                                        >
                                        <td class="font-mono text-xs"
                                            >{formatBytes(relic.size_bytes)}</td
                                        >
                                        <td>
                                            <div
                                                class="flex items-center gap-1"
                                            >
                                                <button
                                                    on:click|stopPropagation={() =>
                                                        shareRelic(relic.id)}
                                                    class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                                    title="Share"
                                                    ><i
                                                        class="fas fa-share text-xs"
                                                    ></i></button
                                                >
                                                <button
                                                    on:click|stopPropagation={() =>
                                                        copyRelicContent(
                                                            relic.id,
                                                        )}
                                                    class="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                                                    title="Copy"
                                                    ><i
                                                        class="fas fa-copy text-xs"
                                                    ></i></button
                                                >
                                                <button
                                                    on:click|stopPropagation={() =>
                                                        viewRaw(relic.id)}
                                                    class="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors"
                                                    title="Raw"
                                                    ><i
                                                        class="fas fa-code text-xs"
                                                    ></i></button
                                                >
                                                <button
                                                    on:click|stopPropagation={() =>
                                                        downloadRelic(
                                                            relic.id,
                                                            relic.name,
                                                            relic.content_type,
                                                        )}
                                                    class="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
                                                    title="Download"
                                                    ><i
                                                        class="fas fa-download text-xs"
                                                    ></i></button
                                                >
                                                <button
                                                    on:click|stopPropagation={() =>
                                                        handleDeleteRelic(
                                                            relic,
                                                        )}
                                                    class="p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                                                    title="Delete"
                                                    ><i
                                                        class="fas fa-trash text-xs"
                                                    ></i></button
                                                >
                                            </div>
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                    <div
                        class="px-6 py-3 border-t border-gray-200 bg-gray-50 text-xs text-gray-500 flex justify-between items-center"
                    >
                        <span
                            >{relicsTotal} relic{relicsTotal !== 1
                                ? "s"
                                : ""}</span
                        >
                        {#if relicsTotalPages > 1}
                            <div class="flex items-center gap-2">
                                <span
                                    >Page {relicsPage} of {relicsTotalPages}</span
                                >
                                <button
                                    on:click={() => {
                                        relicsPage = Math.max(
                                            1,
                                            relicsPage - 1,
                                        );
                                        loadRelics();
                                    }}
                                    disabled={relicsPage === 1}
                                    class="px-3 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
                                    ><i class="fas fa-chevron-left text-xs"
                                    ></i></button
                                >
                                <button
                                    on:click={() => {
                                        relicsPage = Math.min(
                                            relicsTotalPages,
                                            relicsPage + 1,
                                        );
                                        loadRelics();
                                    }}
                                    disabled={relicsPage === relicsTotalPages}
                                    class="px-3 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
                                    ><i class="fas fa-chevron-right text-xs"
                                    ></i></button
                                >
                            </div>
                        {/if}
                    </div>
                {/if}
            {/if}

            <!-- Reports Tab -->
            {#if activeTab === "reports"}
                {#if reportsLoading}
                    <div class="p-8 text-center">
                        <i
                            class="fas fa-spinner fa-spin text-[#772953] text-2xl"
                        ></i>
                    </div>
                {:else if reports.length === 0}
                    <div class="p-8 text-center text-gray-500">
                        <i
                            class="fas fa-check-circle text-4xl mb-2 text-green-500"
                        ></i>
                        <p>No active reports</p>
                    </div>
                {:else}
                    <div class="overflow-x-auto">
                        <table class="w-full maas-table text-sm">
                            <thead>
                                <tr
                                    class="text-gray-500 uppercase text-xs tracking-wider bg-gray-50"
                                >
                                    <th>Relic</th>
                                    <th>Reason</th>
                                    <th>Reported</th>
                                    <th class="w-32">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each reports as report (report.id)}
                                    <tr class="hover:bg-gray-50">
                                        <td>
                                            <div class="flex flex-col">
                                                <a
                                                    href="/{report.relic_id}"
                                                    class="font-medium text-[#0066cc] hover:underline"
                                                >
                                                    {report.relic_name ||
                                                        "Unknown Relic"}
                                                </a>
                                                <span
                                                    class="text-xs text-gray-400 font-mono"
                                                    >{report.relic_id}</span
                                                >
                                            </div>
                                        </td>
                                        <td
                                            class="text-gray-700 max-w-md truncate"
                                            title={report.reason}
                                        >
                                            {report.reason}
                                        </td>
                                        <td class="text-xs text-gray-500">
                                            {formatTimeAgo(report.created_at)}
                                        </td>
                                        <td>
                                            <div
                                                class="flex items-center gap-1"
                                            >
                                                <button
                                                    on:click={() =>
                                                        navigateToRelic(
                                                            report.relic_id,
                                                        )}
                                                    class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                                    title="View Relic"
                                                >
                                                    <i
                                                        class="fas fa-external-link-alt text-xs"
                                                    ></i>
                                                </button>
                                                <button
                                                    on:click={() =>
                                                        handleDismissReport(
                                                            report,
                                                        )}
                                                    class="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                                                    title="Dismiss Report"
                                                >
                                                    <i
                                                        class="fas fa-check text-xs"
                                                    ></i>
                                                </button>
                                                <button
                                                    on:click={() =>
                                                        handleDeleteRelic({
                                                            id: report.relic_id,
                                                            name: report.relic_name,
                                                        })}
                                                    class="p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                                                    title="Delete Relic"
                                                >
                                                    <i
                                                        class="fas fa-trash text-xs"
                                                    ></i>
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                    <div
                        class="px-6 py-3 border-t border-gray-200 bg-gray-50 text-xs text-gray-500 flex justify-between items-center"
                    >
                        <span
                            >{reportsTotal} report{reportsTotal !== 1
                                ? "s"
                                : ""}</span
                        >
                        {#if reportsTotalPages > 1}
                            <div class="flex items-center gap-2">
                                <span
                                    >Page {reportsPage} of {reportsTotalPages}</span
                                >
                                <button
                                    on:click={() => {
                                        reportsPage = Math.max(
                                            1,
                                            reportsPage - 1,
                                        );
                                        loadReports();
                                    }}
                                    disabled={reportsPage === 1}
                                    class="px-3 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
                                >
                                    <i class="fas fa-chevron-left text-xs"></i>
                                </button>
                                <button
                                    on:click={() => {
                                        reportsPage = Math.min(
                                            reportsTotalPages,
                                            reportsPage + 1,
                                        );
                                        loadReports();
                                    }}
                                    disabled={reportsPage === reportsTotalPages}
                                    class="px-3 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
                                >
                                    <i class="fas fa-chevron-right text-xs"></i>
                                </button>
                            </div>
                        {/if}
                    </div>
                {/if}
            {/if}

            <!-- Clients Tab -->
            {#if activeTab === "clients"}
                {#if clientsLoading}
                    <div class="p-8 text-center">
                        <i
                            class="fas fa-spinner fa-spin text-[#772953] text-2xl"
                        ></i>
                    </div>
                {:else if clients.length === 0}
                    <div class="p-8 text-center text-gray-500">
                        <i class="fas fa-users text-4xl mb-2"></i>
                        <p>No clients found</p>
                    </div>
                {:else}
                    <div class="overflow-x-auto">
                        <table class="w-full maas-table text-sm">
                            <thead
                                ><tr
                                    class="text-gray-500 uppercase text-xs tracking-wider bg-gray-50"
                                    ><th>Client ID</th><th>Relics</th><th
                                        >Role</th
                                    ><th>Created</th><th class="w-24"
                                        >Actions</th
                                    ></tr
                                ></thead
                            >
                            <tbody>
                                {#each clients as client (client.id)}
                                    <tr class="hover:bg-gray-50">
                                        <td class="font-mono text-sm"
                                            >{client.id}</td
                                        >
                                        <td
                                            ><button
                                                on:click={() =>
                                                    viewClientRelics(client)}
                                                class="text-xs text-blue-600 hover:text-blue-800 hover:underline"
                                                title="View relics"
                                                ><i class="fas fa-archive mr-1"
                                                ></i>{client.relic_count} relics</button
                                            ></td
                                        >
                                        <td>
                                            {#if client.is_admin}
                                                <span
                                                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                                                    style="background-color: #f3e5f5; color: #772953;"
                                                    ><i
                                                        class="fas fa-shield-alt mr-1"
                                                    ></i>admin</span
                                                >
                                            {:else}
                                                <span
                                                    class="text-gray-500 text-sm"
                                                    >user</span
                                                >
                                            {/if}
                                        </td>
                                        <td class="text-xs text-gray-500"
                                            >{formatDate(client.created_at)}</td
                                        >
                                        <td>
                                            {#if !client.is_admin}
                                                <button
                                                    on:click={() =>
                                                        handleDeleteClient(
                                                            client,
                                                        )}
                                                    class="p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                                                    title="Delete client"
                                                    ><i
                                                        class="fas fa-trash text-xs"
                                                    ></i></button
                                                >
                                            {:else}
                                                <span
                                                    class="p-1.5 text-gray-300"
                                                    title="Cannot delete admin"
                                                    ><i
                                                        class="fas fa-trash text-xs"
                                                    ></i></span
                                                >
                                            {/if}
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                    <div
                        class="px-6 py-3 border-t border-gray-200 bg-gray-50 text-xs text-gray-500 flex justify-between items-center"
                    >
                        <span
                            >{clientsTotal} client{clientsTotal !== 1
                                ? "s"
                                : ""}</span
                        >
                        {#if clientsTotalPages > 1}
                            <div class="flex items-center gap-2">
                                <span
                                    >Page {clientsPage} of {clientsTotalPages}</span
                                >
                                <button
                                    on:click={() => {
                                        clientsPage = Math.max(
                                            1,
                                            clientsPage - 1,
                                        );
                                        loadClients();
                                    }}
                                    disabled={clientsPage === 1}
                                    class="px-3 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
                                    ><i class="fas fa-chevron-left text-xs"
                                    ></i></button
                                >
                                <button
                                    on:click={() => {
                                        clientsPage = Math.min(
                                            clientsTotalPages,
                                            clientsPage + 1,
                                        );
                                        loadClients();
                                    }}
                                    disabled={clientsPage === clientsTotalPages}
                                    class="px-3 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
                                    ><i class="fas fa-chevron-right text-xs"
                                    ></i></button
                                >
                            </div>
                        {/if}
                    </div>
                {/if}
            {/if}

            <!-- Backups Tab -->
            {#if activeTab === "backups"}
                <div
                    class="px-6 py-3 border-b border-gray-200 flex items-center justify-between bg-gray-50"
                >
                    <span class="text-sm text-gray-600"
                        >Database backups stored in S3</span
                    >
                    <button
                        on:click={handleBackupNow}
                        disabled={backupInProgress}
                        class="px-3 py-1.5 text-sm bg-[#E95420] text-white rounded hover:bg-[#c7451a] transition-colors disabled:opacity-50 flex items-center gap-2"
                    >
                        {#if backupInProgress}
                            <i class="fas fa-spinner fa-spin"></i>Creating...
                        {:else}
                            <i class="fas fa-plus"></i>Backup Now
                        {/if}
                    </button>
                </div>
                {#if backupsLoading}
                    <div class="p-8 text-center">
                        <i
                            class="fas fa-spinner fa-spin text-[#772953] text-2xl"
                        ></i>
                    </div>
                {:else if backups.length === 0}
                    <div class="p-8 text-center text-gray-500">
                        <i class="fas fa-history text-4xl mb-2"></i>
                        <p>No backups found</p>
                    </div>
                {:else}
                    <div class="overflow-x-auto">
                        <table class="w-full maas-table text-sm">
                            <thead
                                ><tr
                                    class="text-gray-500 uppercase text-xs tracking-wider bg-gray-50"
                                    ><th>Backup</th><th>Timestamp</th><th
                                        >Size</th
                                    ><th class="w-24">Actions</th></tr
                                ></thead
                            >
                            <tbody>
                                {#each backups as backup}
                                    <tr class="hover:bg-gray-50">
                                        <td>
                                            <div
                                                class="flex items-center gap-2"
                                            >
                                                <i
                                                    class="fas fa-file-archive text-[#E95420]"
                                                ></i>
                                                <span class="font-mono text-sm"
                                                    >{backup.filename}</span
                                                >
                                            </div>
                                        </td>
                                        <td class="text-xs text-gray-500"
                                            >{formatDate(backup.timestamp)}</td
                                        >
                                        <td class="font-mono text-xs"
                                            >{formatBytes(
                                                backup.size_bytes,
                                            )}</td
                                        >
                                        <td>
                                            <button
                                                on:click={() =>
                                                    downloadAdminBackup(
                                                        backup.filename,
                                                    )}
                                                class="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
                                                title="Download backup"
                                                ><i
                                                    class="fas fa-download text-xs"
                                                ></i></button
                                            >
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                    <div
                        class="px-6 py-3 border-t border-gray-200 bg-gray-50 text-xs text-gray-500 flex justify-between items-center"
                    >
                        <span
                            >{backupsTotal} backup{backupsTotal !== 1
                                ? "s"
                                : ""} • Total: {formatBytes(
                                backupsTotalSize,
                            )}</span
                        >
                        {#if backupsTotalPages > 1}
                            <div class="flex items-center gap-2">
                                <span
                                    >Page {backupsPage} of {backupsTotalPages}</span
                                >
                                <button
                                    on:click={() => {
                                        backupsPage = Math.max(
                                            1,
                                            backupsPage - 1,
                                        );
                                        loadBackups();
                                    }}
                                    disabled={backupsPage === 1}
                                    class="px-3 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
                                    ><i class="fas fa-chevron-left text-xs"
                                    ></i></button
                                >
                                <button
                                    on:click={() => {
                                        backupsPage = Math.min(
                                            backupsTotalPages,
                                            backupsPage + 1,
                                        );
                                        loadBackups();
                                    }}
                                    disabled={backupsPage === backupsTotalPages}
                                    class="px-3 py-1 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
                                    ><i class="fas fa-chevron-right text-xs"
                                    ></i></button
                                >
                            </div>
                        {/if}
                    </div>
                {/if}
            {/if}

            <!-- Config Tab -->
            {#if activeTab === "config"}
                {#if configLoading}
                    <div class="p-8 text-center">
                        <i
                            class="fas fa-spinner fa-spin text-[#772953] text-2xl"
                        ></i>
                    </div>
                {:else if !config}
                    <div class="p-8 text-center text-gray-500">
                        <i class="fas fa-cog text-4xl mb-2"></i>
                        <p>Failed to load configuration</p>
                    </div>
                {:else}
                    <div class="p-6 space-y-6">
                        {#each Object.entries(config) as [section, values]}
                            <div>
                                <h3
                                    class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3 flex items-center gap-2"
                                >
                                    {#if section === "app"}<i
                                            class="fas fa-cube text-gray-400"
                                        ></i>
                                    {:else if section === "database"}<i
                                            class="fas fa-database text-gray-400"
                                        ></i>
                                    {:else if section === "storage"}<i
                                            class="fas fa-cloud text-gray-400"
                                        ></i>
                                    {:else if section === "upload"}<i
                                            class="fas fa-upload text-gray-400"
                                        ></i>
                                    {:else if section === "backup"}<i
                                            class="fas fa-history text-gray-400"
                                        ></i>
                                    {:else if section === "admin"}<i
                                            class="fas fa-shield-alt text-gray-400"
                                        ></i>
                                    {:else if section === "cors"}<i
                                            class="fas fa-globe text-gray-400"
                                        ></i>
                                    {:else}<i class="fas fa-cog text-gray-400"
                                        ></i>
                                    {/if}
                                    {section}
                                </h3>
                                <div
                                    class="bg-gray-50 rounded-lg border border-gray-200 divide-y divide-gray-200"
                                >
                                    {#each Object.entries(values) as [key, value]}
                                        <div
                                            class="px-4 py-2 flex justify-between items-center"
                                        >
                                            <span
                                                class="text-sm text-gray-600 font-mono"
                                                >{key}</span
                                            >
                                            <span
                                                class="text-sm text-gray-900 font-mono"
                                            >
                                                {#if typeof value === "boolean"}
                                                    <span
                                                        class="px-2 py-0.5 rounded text-xs {value
                                                            ? 'bg-green-100 text-green-800'
                                                            : 'bg-gray-100 text-gray-600'}"
                                                    >
                                                        {value
                                                            ? "true"
                                                            : "false"}
                                                    </span>
                                                {:else if Array.isArray(value)}
                                                    {value.length > 0
                                                        ? value.join(", ")
                                                        : "(empty)"}
                                                {:else}
                                                    {value}
                                                {/if}
                                            </span>
                                        </div>
                                    {/each}
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}
            {/if}
        </div>
    {/if}
</div>
