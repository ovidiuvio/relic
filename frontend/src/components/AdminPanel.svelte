<script>
    import { onMount, onDestroy } from "svelte";
    import { showToast } from "../stores/toastStore";
    import ConfirmModal from "./ConfirmModal.svelte";
    import {
        checkAdminStatus,
        getAdminStats,
        getAdminRelics,
        getAdminUsers,
        getAdminConfig,
        getAdminBackups,
        createAdminBackup,
        downloadAdminBackup,
        restoreAdminBackup,
        restoreFromUpload,
        createRelic,
        deleteRelic,
        deleteUser,
        grantAdmin,
        revokeAdmin,
        getAdmins,
        addAdmin,
        getAdminReports,
        deleteReport,
        getAdminJobs,
        runAdminJob,
        pauseAdminJob,
        resumeAdminJob,
    } from "../services/api";
    import {
        getTypeLabel,
        getTypeIcon,
        getTypeIconColor,
        formatBytes,
        formatTimeAgo,
        getDefaultItemsPerPage,
        hasViewer,
    } from "../services/typeUtils";

    import {
        shareRelic,
        copyRelicContent,
        downloadRelic,
        viewRaw,
        copyToClipboard,
    } from "../services/relicActions";
    import { triggerDownload } from "../services/utils/download";

    let isAdmin = false;
    let loading = true;
    let pollTimeouts = [];
    let jobsAutoRefreshId = null;
    onDestroy(() => {
        pollTimeouts.forEach(clearTimeout);
        if (jobsAutoRefreshId) clearInterval(jobsAutoRefreshId);
    });
    let activeTab = "stats";
    $: {
        // Auto-refresh jobs tab every 30s while active
        if (jobsAutoRefreshId) { clearInterval(jobsAutoRefreshId); jobsAutoRefreshId = null; }
        if (activeTab === "jobs") {
            jobsAutoRefreshId = setInterval(() => { if (!jobsLoading) loadJobs(); }, 30_000);
        }
    }

    // Stats
    let stats = {
        total_relics: 0,
        total_users: 0,
        total_size_bytes: 0,
        public_relics: 0,
        private_relics: 0,
        restricted_relics: 0,
        total_comments: 0,
        total_bookmarks: 0,
        total_reports: 0,
        total_spaces: 0,
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
    let tagFilter = null;
    let relicsSortBy = 'created_at';
    let relicsSortOrder = 'desc';

    // Users state
    let users = [];
    let usersLoading = false;
    let usersTotal = 0;
    let usersPage = 1;
    let usersLimit = 25;
    let usersSortBy = 'created_at';
    let usersSortOrder = 'desc';
    let usersSearch = '';
    let revealedKeys = new Set();

    // Config state
    let config = null;
    let configLoading = false;

    // Admins management (Config tab)
    let admins = [];
    let adminsLoading = false;
    let newAdminPublicId = "";
    let addingAdmin = false;

    // Backups state
    let backups = [];
    let backupsLoading = false;
    let backupsTotal = 0;
    let backupsTotalSize = 0;
    let backupsPage = 1;
    let backupsLimit = 25;
    let backupInProgress = false;

    // Restore state
    let restoreModalOpen = false;
    let restoreTarget = null;   // { source: 's3', filename, timestamp, size_bytes } | { source: 'upload', filename, size_bytes, file }
    let restoreInProgress = false;
    let restoreLogs = null;     // { stdout, stderr } shown after restore completes
    let uploadFileInput;

    // Reports state
    let reports = [];
    let reportsLoading = false;
    let reportsTotal = 0;
    let reportsPage = 1;
    let reportsLimit = 25;
    let reportsSortBy = 'created_at';
    let reportsSortOrder = 'desc';

    // Jobs state
    let jobs = [];
    let jobsHistory = [];
    let expandedTracebacks = {};
    let expandedLogs = {};
    let jobsLoading = false;
    let jobsRunning = false;
    let jobsActionInProgress = {};
    let jobsSubTab = 'scheduled'; // 'scheduled' | 'history'
    let jobsHistoryFilter = '';   // Filter history by job_id
    let jobsHistoryStatus = '';   // Filter history by status
    let jobsHistoryPage = 1;
    let jobsHistoryLimit = 25;
    $: filteredHistory = jobsHistory.filter(run => {
        if (jobsHistoryFilter && run.job_id !== jobsHistoryFilter) return false;
        if (jobsHistoryStatus && run.status !== jobsHistoryStatus) return false;
        return true;
    });
    $: jobsHistoryTotalPages = Math.ceil(filteredHistory.length / jobsHistoryLimit);
    $: paginatedHistory = filteredHistory.slice().reverse().slice((jobsHistoryPage - 1) * jobsHistoryLimit, jobsHistoryPage * jobsHistoryLimit);

    // Selected user for viewing their relics
    let selectedUser = null;

    // Confirm modal state
    let showConfirm = false;
    let confirmTitle = '';
    let confirmMessage = '';
    let confirmAction = null;
    let showDeleteRelicsConfirm = false;
    let confirmUserToDelete = null;

    $: filteredRelics = relics;

    function handleRelicsSort(column) {
        if (relicsSortBy === column) {
            relicsSortOrder = relicsSortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            relicsSortBy = column;
            relicsSortOrder = 'desc';
        }
        relicsPage = 1;
        loadRelics();
    }

    function handleUsersSort(column) {
        if (usersSortBy === column) {
            usersSortOrder = usersSortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            usersSortBy = column;
            usersSortOrder = 'desc';
        }
        usersPage = 1;
        loadUsers();
    }

    function handleReportsSort(column) {
        if (reportsSortBy === column) {
            reportsSortOrder = reportsSortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            reportsSortBy = column;
            reportsSortOrder = 'desc';
        }
        reportsPage = 1;
        loadReports();
    }

    function formatDate(dateStr) {
        if (!dateStr) return "-";
        return new Date(dateStr).toLocaleString();
    }

    function formatTriggerJob(job) {
        // Prefer the structured ``trigger_info`` payload (added after the bug
        // review); fall back to legacy regex parsing of ``job.trigger`` for
        // backward compatibility with old responses.
        const info = job && job.trigger_info;
        if (info && info.type) {
            if (info.type === 'interval') {
                const secs = info.seconds;
                if (secs == null) return info.repr || 'Interval';
                if (secs >= 3600 && secs % 3600 === 0) return `Every ${secs / 3600} hour${secs / 3600 === 1 ? '' : 's'}`;
                if (secs >= 60 && secs % 60 === 0) return `Every ${secs / 60} minute${secs / 60 === 1 ? '' : 's'}`;
                return `Every ${secs} second${secs === 1 ? '' : 's'}`;
            }
            if (info.type === 'cron') {
                const f = info.fields || {};
                const hour = f['hour'];
                const minute = f['minute'];
                const dayOfWeek = f['day_of_week'];
                const day = f['day'];
                let timeStr = '';
                if (hour && hour !== '*' && minute && minute !== '*') {
                    timeStr = ` at ${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
                } else if (minute && minute !== '*') {
                    timeStr = ` at minute ${minute}`;
                }
                const dowIsStar = dayOfWeek === undefined || dayOfWeek === '*';
                const dayIsStar = day === undefined || day === '*';
                if (dowIsStar && dayIsStar) return `Daily${timeStr}`;
                if (!dowIsStar) {
                    const pretty = dayOfWeek.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join('-');
                    return `Weekly on ${pretty}${timeStr}`;
                }
                return `Monthly on day ${day}${timeStr}`;
            }
            if (info.type === 'date') {
                if (!info.run_date) return 'One-time task';
                const [d, t] = info.run_date.split('T');
                return `Once on ${d} at ${t.slice(0, 5)}`;
            }
            return info.repr || (job && job.trigger) || 'Unknown';
        }
        return (job && job.trigger) || "Not scheduled";
    }

    function toggleTraceback(runId) {
        expandedTracebacks = { ...expandedTracebacks, [runId]: !expandedTracebacks[runId] };
    }

    function toggleLogs(runId) {
        expandedLogs = { ...expandedLogs, [runId]: !expandedLogs[runId] };
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
            const userId = selectedUser ? selectedUser.id : null;
            const response = await getAdminRelics(
                relicsLimit,
                offset,
                accessLevel,
                userId,
                searchTerm || null,
                tagFilter || null,
                relicsSortBy,
                relicsSortOrder,
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

    async function loadUsers() {
        usersLoading = true;
        try {
            const offset = (usersPage - 1) * usersLimit;
            const response = await getAdminUsers(usersLimit, offset, usersSortBy, usersSortOrder, usersSearch || null);
            users = response.data.users || [];
            usersTotal = response.data.total || 0;
        } catch (error) {
            console.error("Failed to load users:", error);
            showToast("Failed to load users", "error");
            users = [];
        } finally {
            usersLoading = false;
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

    async function loadAdmins() {
        adminsLoading = true;
        try {
            const response = await getAdmins();
            admins = response.data.admins || [];
        } catch (error) {
            console.error("Failed to load admins:", error);
            showToast("Failed to load admins", "error");
            admins = [];
        } finally {
            adminsLoading = false;
        }
    }

    async function handleAddAdmin() {
        const publicId = newAdminPublicId.trim();
        if (!publicId || addingAdmin) return;
        addingAdmin = true;
        try {
            await addAdmin(publicId);
            showToast("Admin added", "success");
            newAdminPublicId = "";
            await Promise.all([loadAdmins(), loadStats(), loadUsers()]);
        } catch (error) {
            console.error("Failed to add admin:", error);
            showToast(
                error.response?.data?.detail || "Failed to add admin",
                "error",
            );
        } finally {
            addingAdmin = false;
        }
    }

    async function handleRemoveAdmin(admin) {
        try {
            await revokeAdmin(admin.user_id);
            showToast("Admin removed", "success");
            await Promise.all([loadAdmins(), loadStats(), loadUsers()]);
        } catch (error) {
            console.error("Failed to remove admin:", error);
            showToast(
                error.response?.data?.detail || "Failed to remove admin",
                "error",
            );
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
            const response = await getAdminReports(reportsLimit, offset, reportsSortBy, reportsSortOrder);
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

    async function loadJobs() {
        jobsLoading = true;
        try {
            const response = await getAdminJobs();
            jobs = response.data.jobs || [];
            jobsHistory = response.data.history || [];
            jobsRunning = response.data.running;
        } catch (error) {
            console.error("Failed to load background jobs:", error);
            showToast("Failed to load background jobs", "error");
            jobs = [];
            jobsHistory = [];
        } finally {
            jobsLoading = false;
        }
    }

    async function handleRunJob(jobId) {
        jobsActionInProgress = { ...jobsActionInProgress, [jobId]: 'run' };
        try {
            const response = await runAdminJob(jobId);
            if (response.data.success) {
                showToast(response.data.message || `Job ${jobId} triggered successfully`, "success");
                // Refresh immediately (entry is created synchronously server-
                // side now) and again after a short delay so the terminal
                // status / duration / logs appear without manual reload.
                await loadJobs();
                pollJobRun(jobId, response.data.run_id);
            } else {
                showToast(response.data.message || `Failed to trigger job ${jobId}`, "error");
            }
        } catch (error) {
            if (error.response?.status === 409) {
                showToast(error.response?.data?.detail || `Job ${jobId} is already running`, "warning");
            } else {
                console.error(`Failed to run job ${jobId}:`, error);
                showToast(error.response?.data?.detail || `Failed to run job ${jobId}`, "error");
            }
        } finally {
            jobsActionInProgress = { ...jobsActionInProgress, [jobId]: null };
        }
    }

    function pollJobRun(jobId, runId) {
        // Poll for terminal state up to ~30s. Cheap, server-debounced refresh
        // gives the UI a live feel without SSE/WebSockets.
        const deadline = Date.now() + 30_000;
        const tick = async () => {
            if (Date.now() > deadline) {
                await loadJobs();
                return;
            }
            await loadJobs();
            const run = jobsHistory.find(r => r.run_id === runId);
            if (run && (run.status === 'success' || run.status === 'failed')) {
                if (run.status === 'failed') {
                    showToast(`Job '${run.job_name || jobId}' failed`, "error");
                }
                return;
            }
            pollTimeouts.push(setTimeout(tick, 1500));
        };
        pollTimeouts.push(setTimeout(tick, 1200));
    }

    async function handleTogglePauseJob(job) {
        const action = job.paused ? 'resume' : 'pause';
        jobsActionInProgress = { ...jobsActionInProgress, [job.id]: action };
        try {
            const response = job.paused ? await resumeAdminJob(job.id) : await pauseAdminJob(job.id);
            if (response.data.success) {
                showToast(response.data.message || `Job ${job.id} ${job.paused ? 'resumed' : 'paused'} successfully`, "success");
                await loadJobs();
            } else {
                showToast(response.data.message || `Action failed`, "error");
            }
        } catch (error) {
            console.error(`Failed to ${action} job ${job.id}:`, error);
            showToast(error.response?.data?.detail || `Failed to ${action} job`, "error");
        } finally {
            jobsActionInProgress = { ...jobsActionInProgress, [job.id]: null };
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

    function openRestoreModal(backup) {
        restoreTarget = { source: 's3', ...backup };
        restoreModalOpen = true;
    }

    function closeRestoreModal() {
        if (restoreInProgress) return;
        restoreModalOpen = false;
        restoreTarget = null;
        restoreLogs = null;
    }

    function handleUploadFileChange(event) {
        const file = event.target.files[0];
        if (!file) return;
        // Reset input so same file can be re-selected if needed
        event.target.value = '';
        if (!file.name.endsWith('.sql.gz')) {
            showToast("File must be a .sql.gz backup", "error");
            return;
        }
        restoreTarget = { source: 'upload', filename: file.name, size_bytes: file.size, file };
        restoreModalOpen = true;
    }

    function buildFullLog() {
        if (!restoreLogs) return '';
        const parts = [];
        if (restoreLogs.log) parts.push('=== Process Log ===\n' + restoreLogs.log);
        if (restoreLogs.stdout) parts.push('=== psql Output ===\n' + restoreLogs.stdout);
        if (restoreLogs.stderr) parts.push('=== Errors / Warnings ===\n' + restoreLogs.stderr);
        return parts.join('\n\n');
    }

    function downloadRestoreLogs() {
        const filename = `restore-log-${restoreTarget?.filename ?? 'upload'}-${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.txt`;
        triggerDownload(buildFullLog(), filename, 'text/plain');
    }

    async function saveRestoreLogsAsRelic() {
        const content = buildFullLog();
        const filename = `restore-log-${restoreTarget?.filename ?? 'upload'}-${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.txt`;
        const file = new File([content], filename, { type: 'text/plain' });
        try {
            const response = await createRelic({ file, name: filename, access_level: 'restricted' });
            const relicId = response.data.id;
            showToast('Logs saved as restricted relic', 'success');
            window.open(`/${relicId}`, '_blank');
        } catch (err) {
            showToast(err.response?.data?.detail || 'Failed to save relic', 'error');
        }
    }

    async function confirmRestore() {
        if (!restoreTarget) return;
        restoreInProgress = true;
        restoreLogs = null;
        try {
            const response = restoreTarget.source === 'upload'
                ? await restoreFromUpload(restoreTarget.file)
                : await restoreAdminBackup(restoreTarget.filename);
            restoreLogs = { log: response.data.log || '', stdout: response.data.stdout || '', stderr: response.data.stderr || '' };
            showToast("Database restored successfully", "success");
            await loadBackups();
        } catch (err) {
            const detail = err.response?.data?.detail || "Restore failed";
            restoreLogs = { log: '', stdout: '', stderr: detail };
            showToast(detail, "error");
        } finally {
            restoreInProgress = false;
        }
    }

    function handleDeleteRelic(relic) {
        confirmTitle = 'Delete Relic';
        confirmMessage = `Delete "${relic.name || relic.id}"?\n\nThis cannot be undone.`;
        confirmAction = async () => {
            showConfirm = false;
            try {
                await deleteRelic(relic.id);
                showToast("Relic deleted", "success");
                await loadRelics();
                await loadStats();
            } catch (error) {
                console.error("Failed to delete relic:", error);
                showToast("Failed to delete relic", "error");
            }
        };
        showConfirm = true;
    }

    function handleDeleteUser(user) {
        confirmTitle = 'Delete User';
        confirmMessage = `Delete user "${user.id}"?\n\nThis user owns ${user.relic_count} relic(s).`;
        confirmUserToDelete = user;
        confirmAction = () => {
            showConfirm = false;
            showDeleteRelicsConfirm = true;
        };
        showConfirm = true;
    }

    async function handleToggleAdmin(user) {
        try {
            if (user.is_admin) {
                await revokeAdmin(user.id);
                showToast("Admin privileges revoked", "success");
            } else {
                await grantAdmin(user.id);
                showToast("Admin privileges granted", "success");
            }
            // loadAdmins() only needed when the Config tab (admins table) is visible
            const refreshes = [loadUsers(), loadStats()];
            if (activeTab === "config") refreshes.push(loadAdmins());
            await Promise.all(refreshes);
        } catch (error) {
            console.error("Failed to update admin status:", error);
            showToast(
                error.response?.data?.detail || "Failed to update admin status",
                "error",
            );
        }
    }

    async function performDeleteUser(deleteRelicsChoice) {
        showDeleteRelicsConfirm = false;
        if (!confirmUserToDelete) return;

        try {
            await deleteUser(confirmUserToDelete.id, deleteRelicsChoice);
            showToast("User deleted", "success");
            await loadUsers();
            await loadStats();
        } catch (error) {
            console.error("Failed to delete user:", error);
            showToast(
                error.response?.data?.detail || "Failed to delete user",
                "error",
            );
        } finally {
            confirmUserToDelete = null;
        }
    }

    function handleDismissReport(report) {
        confirmTitle = 'Dismiss Report';
        confirmMessage = 'Dismiss this report?';
        confirmAction = async () => {
            showConfirm = false;
            try {
                await deleteReport(report.id);
                showToast("Report dismissed", "success");
                await loadReports();
            } catch (error) {
                console.error("Failed to dismiss report:", error);
                showToast("Failed to dismiss report", "error");
            }
        };
        showConfirm = true;
    }

    function navigateToRelic(relicId) {
        window.history.pushState({}, "", `/${relicId}`);
        window.dispatchEvent(new PopStateEvent("popstate"));
    }

    function viewUserRelics(user) {
        selectedUser = user;
        activeTab = "relics";
        relicsPage = 1;
        loadRelics();
    }

    function clearUserFilter() {
        selectedUser = null;
        relicsPage = 1;
        loadRelics();
    }

    function refreshAll() {
        loadStats();
        loadRelics();
        loadUsers();
        loadConfig();
        loadAdmins();
        loadBackups();
        loadReports();
        loadJobs();
    }

    // Watch for filter/search changes
    $: if (relicsFilter && isAdmin) {
        relicsPage = 1;
        loadRelics();
    }

    let _searchDebounce;
    $: if (searchTerm !== undefined && isAdmin) {
        clearTimeout(_searchDebounce);
        _searchDebounce = setTimeout(() => {
            relicsPage = 1;
            loadRelics();
        }, 300);
    }

    let _usersSearchDebounce;
    $: if (usersSearch !== undefined && isAdmin) {
        clearTimeout(_usersSearchDebounce);
        _usersSearchDebounce = setTimeout(() => {
            usersPage = 1;
            loadUsers();
        }, 300);
    }

    let _prevTagFilter = null;
    $: if (isAdmin && tagFilter !== _prevTagFilter) {
        _prevTagFilter = tagFilter;
        relicsPage = 1;
        loadRelics();
    }

    $: relicsTotalPages = Math.ceil(relicsTotal / relicsLimit);
    $: usersTotalPages = Math.ceil(usersTotal / usersLimit);
    $: backupsTotalPages = Math.ceil(backupsTotal / backupsLimit);
    $: reportsTotalPages = Math.ceil(reportsTotal / reportsLimit);

    onMount(async () => {
        const perPage = getDefaultItemsPerPage();
        relicsLimit = perPage;
        usersLimit = perPage;
        backupsLimit = perPage;
        reportsLimit = perPage;
        await checkAdmin();
        if (isAdmin) {
            await Promise.all([
                loadStats(),
                loadRelics(),
                loadUsers(),
                loadConfig(),
                loadAdmins(),
                loadBackups(),
                loadReports(),
                loadJobs(),
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
                    >ADMIN_USER_IDS</code
                > env variable.
            </p>
        </div>
    {:else}

        <!-- Tabs -->
        <div class="bg-white shadow-sm rounded-lg border border-gray-200 overflow-hidden">
            <div
                class="px-6 py-4 border-b border-gray-200 flex items-center justify-between"
            >
                <div class="flex items-center gap-6">
                    <button
                        on:click={() => (activeTab = "stats")}
                        class="text-sm font-medium pb-1 border-b-2 transition-colors {activeTab ===
                        'stats'
                            ? 'border-[#E95420] text-[#E95420]'
                            : 'border-transparent text-gray-500 hover:text-gray-700'}"
                    >
                        <i class="fas fa-chart-line mr-2"></i>Overview
                    </button>
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
                        on:click={() => (activeTab = "users")}
                        class="text-sm font-medium pb-1 border-b-2 transition-colors {activeTab ===
                        'users'
                            ? 'border-[#E95420] text-[#E95420]'
                            : 'border-transparent text-gray-500 hover:text-gray-700'}"
                    >
                        <i class="fas fa-users mr-2"></i>Users
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
                        on:click={() => { activeTab = "jobs"; loadJobs(); }}
                        class="text-sm font-medium pb-1 border-b-2 transition-colors {activeTab ===
                        'jobs'
                            ? 'border-[#E95420] text-[#E95420]'
                            : 'border-transparent text-gray-500 hover:text-gray-700'}"
                    >
                        <i class="fas fa-tasks mr-2"></i>Jobs
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

            <!-- Overview Tab -->
            {#if activeTab === "stats"}
                <div class="p-6">
                    <div class="bg-white border border-gray-200 rounded-lg overflow-hidden">
                        <table class="w-full maas-table text-sm">
                            <thead>
                                <tr class="text-[#666] uppercase text-[11px] font-semibold tracking-wider bg-gray-50 border-b-2 border-[#cdcdcd]">
                                    <th class="px-6 py-3 text-left border-none">Category</th>
                                    <th class="px-6 py-3 text-left border-none">Metric</th>
                                    <th class="px-6 py-3 text-left border-none">Value</th>
                                    <th class="px-6 py-3 text-left border-none">Detailed Breakdown</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-gray-100">
                                <tr class="hover:bg-gray-50/50 transition-colors">
                                    <td class="px-6 py-4 font-medium text-gray-900">
                                        <div class="flex items-center gap-3">
                                            <i class="fas fa-archive text-[#772953] w-5 text-center"></i>
                                            <span>Relics</span>
                                        </div>
                                    </td>
                                    <td class="px-6 py-4 text-gray-600">Total System Relics</td>
                                    <td class="px-6 py-4 font-mono font-semibold text-gray-900 text-base">{stats.total_relics}</td>
                                    <td class="px-6 py-4">
                                        <div class="flex flex-wrap gap-2 text-[11px] font-medium">
                                            <span class="px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-100 flex items-center gap-1">
                                                <i class="fas fa-globe"></i> {stats.public_relics} Public
                                            </span>
                                            <span class="px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-100 flex items-center gap-1">
                                                <i class="fas fa-lock"></i> {stats.private_relics} Private
                                            </span>
                                            <span class="px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-100 flex items-center gap-1">
                                                <i class="fas fa-user-lock"></i> {stats.restricted_relics} Restricted
                                            </span>
                                        </div>
                                    </td>
                                </tr>
                                <tr class="hover:bg-gray-50/50 transition-colors">
                                    <td class="px-6 py-4 font-medium text-gray-900">
                                        <div class="flex items-center gap-3">
                                            <i class="fas fa-users text-[#0E8420] w-5 text-center"></i>
                                            <span>Users</span>
                                        </div>
                                    </td>
                                    <td class="px-6 py-4 text-gray-600">Total Registered Users</td>
                                    <td class="px-6 py-4 font-mono font-semibold text-gray-900 text-base">{stats.total_users}</td>
                                    <td class="px-6 py-4">
                                        <div class="flex items-center gap-2 text-[11px] font-medium">
                                            <span class="px-2 py-0.5 rounded bg-green-50 text-green-700 border border-green-100">
                                                <i class="fas fa-shield-alt mr-1"></i> {stats.admin_count} Admins
                                            </span>
                                            <span class="text-gray-400 font-normal">
                                                {stats.total_users - stats.admin_count} standard users
                                            </span>
                                        </div>
                                    </td>
                                </tr>
                                <tr class="hover:bg-gray-50/50 transition-colors">
                                    <td class="px-6 py-4 font-medium text-gray-900">
                                        <div class="flex items-center gap-3">
                                            <i class="fas fa-layer-group text-[#217db1] w-5 text-center"></i>
                                            <span>Spaces</span>
                                        </div>
                                    </td>
                                    <td class="px-6 py-4 text-gray-600">Collaborative Spaces</td>
                                    <td class="px-6 py-4 font-mono font-semibold text-gray-900 text-base">{stats.total_spaces}</td>
                                    <td class="px-6 py-4">
                                        <span class="text-[11px] text-gray-400">Shared workspace environments</span>
                                    </td>
                                </tr>
                                <tr class="hover:bg-gray-50/50 transition-colors">
                                    <td class="px-6 py-4 font-medium text-gray-900">
                                        <div class="flex items-center gap-3">
                                            <i class="fas fa-database text-[#E95420] w-5 text-center"></i>
                                            <span>Storage</span>
                                        </div>
                                    </td>
                                    <td class="px-6 py-4 text-gray-600">Combined Data Footprint</td>
                                    <td class="px-6 py-4 font-mono font-semibold text-gray-900 text-base">{formatBytes(stats.total_size_bytes)}</td>
                                    <td class="px-6 py-4">
                                        <div class="flex items-center gap-1.5 text-[11px] text-gray-500">
                                            <i class="fas fa-info-circle opacity-50"></i>
                                            <span>Average relic size: <b>{formatBytes(stats.total_size_bytes / (stats.total_relics || 1))}</b></span>
                                        </div>
                                    </td>
                                </tr>
                                <tr class="hover:bg-gray-50/50 transition-colors">
                                    <td class="px-6 py-4 font-medium text-gray-900">
                                        <div class="flex items-center gap-3">
                                            <i class="fas fa-comments text-gray-400 w-5 text-center"></i>
                                            <span>Interaction</span>
                                        </div>
                                    </td>
                                    <td class="px-6 py-4 text-gray-600">User Engagement</td>
                                    <td class="px-6 py-4 font-mono font-semibold text-gray-900 text-base">{stats.total_comments + stats.total_bookmarks}</td>
                                    <td class="px-6 py-4">
                                        <div class="flex items-center gap-4 text-[11px] font-medium">
                                            <span class="flex items-center gap-1 text-gray-600">
                                                <i class="fas fa-comment-alt text-gray-300"></i> {stats.total_comments} Comments
                                            </span>
                                            <span class="flex items-center gap-1 text-gray-600">
                                                <i class="fas fa-bookmark text-gray-300"></i> {stats.total_bookmarks} Bookmarks
                                            </span>
                                        </div>
                                    </td>
                                </tr>
                                <tr class="hover:bg-gray-50/50 transition-colors">
                                    <td class="px-6 py-4 font-medium text-gray-900">
                                        <div class="flex items-center gap-3">
                                            <i class="fas fa-flag text-red-400 w-5 text-center"></i>
                                            <span>Reports</span>
                                        </div>
                                    </td>
                                    <td class="px-6 py-4 text-gray-600">Pending Issues</td>
                                    <td class="px-6 py-4 font-mono font-semibold text-red-600 text-base">{stats.total_reports}</td>
                                    <td class="px-6 py-4">
                                        {#if stats.total_reports > 0}
                                            <span class="text-[11px] px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-100 flex items-center gap-1 w-fit animate-pulse">
                                                <i class="fas fa-exclamation-triangle"></i> Action Required
                                            </span>
                                        {:else}
                                            <span class="text-[11px] text-gray-400">No pending reports</span>
                                        {/if}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            {/if}

            <!-- Relics Tab -->
            {#if activeTab === "relics"}
                <div
                    class="px-6 py-3 border-b border-gray-200 flex items-center gap-4 bg-gray-50"
                >
                    {#if selectedUser}
                        <div
                            class="flex items-center gap-2 bg-purple-50 border border-purple-200 px-3 py-1.5 rounded text-sm"
                        >
                            <i class="fas fa-user text-purple-600"></i>
                            <span class="text-purple-800 font-mono"
                                >{selectedUser.public_id || selectedUser.id}</span
                            >
                            <button
                                on:click={clearUserFilter}
                                class="text-purple-600 hover:text-purple-800 ml-1"
                                title="Clear"
                            >
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    {/if}
                    <select
                        bind:value={relicsFilter}
                        class="px-3 pr-8 py-1.5 text-sm border border-gray-300 rounded bg-white"
                    >
                        <option value="all">All Levels</option>
                        <option value="public">Public</option>
                        <option value="private">Private</option>
                        <option value="restricted">Restricted</option>
                    </select>


                    <div class="relative flex-1 max-w-md group">
                        <i
                            class="fa-solid fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
                        ></i>
                        <input
                            type="text"
                            bind:value={searchTerm}
                            placeholder="Filter by name, type, or id..."
                            class="w-full pl-9 pr-9 py-1.5 text-sm border border-gray-300 rounded"
                        />
                        {#if searchTerm}
                            <button
                                on:click={() => searchTerm = ''}
                                class="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-red-500 transition-colors focus:outline-none"
                                title="Clear search" aria-label="Clear search"
                            >
                                <i class="fas fa-times-circle"></i>
                            </button>
                        {/if}
                    </div>
                    {#if tagFilter}
                        <div class="flex items-center">
                            <div class="h-4 w-[1px] bg-gray-300 mx-2"></div>
                            <div class="inline-flex items-center gap-1.5 px-[6px] py-[2px] rounded text-[10px] font-medium bg-[#fdf2f8] text-[#772953] border border-[#fbcfe8] leading-[10px] shadow-sm">
                                <i class="fas fa-tag text-[9px] opacity-70"></i>
                                <span>{tagFilter}</span>
                                <button
                                    on:click|stopPropagation={() => tagFilter = null}
                                    class="ml-1 text-[#772953] hover:text-red-700 transition-colors focus:outline-none flex items-center"
                                    title="Clear tag filter"
                                >
                                    <i class="fas fa-times-circle text-[10px]"></i>
                                </button>
                            </div>
                        </div>
                    {/if}
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
                                <tr class="text-[#666] uppercase text-[11px] font-semibold tracking-wider bg-gray-50 border-b-2 border-[#cdcdcd]">
                                    <th class="cursor-pointer hover:bg-[#efefef] transition-colors group px-4 py-2.5 text-left select-none border-none" on:click={() => handleRelicsSort('name')}>
                                        <div class="flex items-center gap-1.5">
                                            <span class={relicsSortBy === 'name' ? 'text-[#772953]' : ''}>Title / ID</span>
                                            <i class="fas fa-arrow-up sort-arrow {relicsSortBy === 'name' ? 'opacity-100 text-[#772953]' : 'opacity-0 text-gray-400 group-hover:opacity-50'} {relicsSortBy === 'name' && relicsSortOrder === 'desc' ? 'desc' : ''}"></i>
                                        </div>
                                    </th>
                                    <th class="px-4 py-2.5 text-left border-none">Owner</th>
                                    <th class="cursor-pointer hover:bg-[#efefef] transition-colors group px-4 py-2.5 text-left select-none border-none" on:click={() => handleRelicsSort('created_at')}>
                                        <div class="flex items-center gap-1.5">
                                            <span class={relicsSortBy === 'created_at' ? 'text-[#772953]' : ''}>Created</span>
                                            <i class="fas fa-arrow-up sort-arrow {relicsSortBy === 'created_at' ? 'opacity-100 text-[#772953]' : 'opacity-0 text-gray-400 group-hover:opacity-50'} {relicsSortBy === 'created_at' && relicsSortOrder === 'desc' ? 'desc' : ''}"></i>
                                        </div>
                                    </th>
                                    <th class="cursor-pointer hover:bg-[#efefef] transition-colors group px-4 py-2.5 text-left select-none border-none" on:click={() => handleRelicsSort('size_bytes')}>
                                        <div class="flex items-center gap-1.5">
                                            <span class={relicsSortBy === 'size_bytes' ? 'text-[#772953]' : ''}>Size</span>
                                            <i class="fas fa-arrow-up sort-arrow {relicsSortBy === 'size_bytes' ? 'opacity-100 text-[#772953]' : 'opacity-0 text-gray-400 group-hover:opacity-50'} {relicsSortBy === 'size_bytes' && relicsSortOrder === 'desc' ? 'desc' : ''}"></i>
                                        </div>
                                    </th>
                                    <th class="px-4 py-2.5 text-right border-none w-40">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each filteredRelics as relic (relic.id)}
                                    <tr class="hover:bg-gray-50 group">
                                        <td>
                                            <div
                                                class="flex items-center gap-1.5"
                                            >
                                                {#if relic.access_level === "private"}
                                                    <i
                                                        class="fas fa-lock text-[13px]"
                                                        style="color: #76306c;"
                                                        title="Private"
                                                    ></i>
                                                {:else if relic.access_level === "restricted"}
                                                    <i
                                                        class="fas fa-user-lock text-[13px]"
                                                        style="color: #b45309;"
                                                        title="Restricted"
                                                    ></i>
                                                {:else}
                                                    <i
                                                        class="fas fa-globe text-[13px]"
                                                        style="color: #217db1;"
                                                        title="Public"
                                                    ></i>
                                                {/if}
                                                <i
                                                    class="fas {getTypeIcon(
                                                        relic.content_type,
                                                    )} {getTypeIconColor(
                                                        relic.content_type,
                                                    )} text-[13px]"
                                                    title={getTypeLabel(
                                                        relic.content_type,
                                                    )}
                                                ></i>
                                                {#if hasViewer(relic.content_type)}
                                                    <a
                                                        href="/{relic.id}"
                                                        class="font-medium text-[#0066cc] hover:underline truncate text-[13px] leading-tight"
                                                        >{relic.name ||
                                                            "Untitled"}</a
                                                    >
                                                {:else}
                                                    <span
                                                        class="font-medium text-gray-700 truncate text-[13px] leading-tight cursor-default"
                                                        title="No dedicated viewer available for this type"
                                                        >{relic.name ||
                                                            "Untitled"}</span
                                                    >
                                                {/if}
                                                <!-- Views, Bookmarks, Comments & Forks (Top Row) -->
                                                <div class="flex items-center gap-2.5 ml-4 text-[10px] text-gray-400/80 whitespace-nowrap mt-[1px]">
                                                    {#if relic.access_count}
                                                        <span class="flex items-center gap-0.5" title="Views">
                                                            <i class="fas fa-eye text-[9px] translate-y-[0.5px]"></i>
                                                            <span>{relic.access_count}</span>
                                                        </span>
                                                    {/if}
                                                    {#if relic.bookmark_count}
                                                        <span class="flex items-center gap-0.5" title="Bookmarks">
                                                            <i class="fas fa-bookmark text-[9px] translate-y-[0.5px]"></i>
                                                            <span>{relic.bookmark_count}</span>
                                                        </span>
                                                    {/if}
                                                    {#if relic.comments_count}
                                                        <span class="flex items-center gap-0.5" title="Comments">
                                                            <i class="fas fa-comment-alt text-[9px] translate-y-[0.5px]"></i>
                                                            <span>{relic.comments_count}</span>
                                                        </span>
                                                    {/if}
                                                    {#if relic.forks_count}
                                                        <span class="flex items-center gap-0.5" title="Forks">
                                                            <i class="fas fa-code-branch text-[9px] translate-y-[0.5px]"></i>
                                                            <span>{relic.forks_count}</span>
                                                        </span>
                                                    {/if}
                                                </div>
                                            </div>
                                            <div
                                                class="flex items-center group gap-1 mt-0.5 leading-tight"
                                            >
                                                <span
                                                    class="text-[11px] text-gray-400 font-mono"
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

                                            {#if relic.tags && relic.tags.length > 0}
                                                <div class="flex items-center flex-wrap gap-1 mt-1">
                                                    {#each relic.tags as tag}
                                                        <button
                                                            on:click|stopPropagation={() => tagFilter = typeof tag === 'string' ? tag : tag.name}
                                                            class="inline-flex items-center px-[6px] py-[2px] rounded text-[10px] font-medium bg-gray-100 text-[#666] hover:bg-gray-200 transition-colors border border-gray-200 leading-[10px]"
                                                        >
                                                            <i class="fas fa-tag mr-1 text-[10px] opacity-60"></i>
                                                            {typeof tag === 'string' ? tag : tag.name}
                                                        </button>
                                                    {/each}
                                                </div>
                                            {/if}
                                        </td>

                                        <td>
                                            {#if relic.user_id}
                                                <div class="flex flex-col">
                                                    {#if relic.owner_name}
                                                        <span class="text-xs font-semibold text-gray-700 leading-normal">{relic.owner_name}</span>
                                                    {/if}
                                                    <div class="flex items-center gap-1 group/owner">
                                                        <button
                                                            on:click={() => viewUserRelics({ id: relic.user_id, public_id: relic.user_public_id })}
                                                            class="text-[10px] font-mono text-gray-400 hover:text-gray-600 hover:underline leading-tight"
                                                            title="View user's relics"
                                                        >
                                                            {relic.user_public_id || 'anonymous'}
                                                        </button>
                                                        {#if relic.user_public_id}
                                                            <button
                                                                on:click|stopPropagation={() => copyToClipboard(relic.user_public_id, 'Owner ID copied!')}
                                                                class="opacity-0 group-hover/owner:opacity-100 text-gray-400 hover:text-gray-600 transition-all"
                                                                title="Copy owner ID"
                                                            >
                                                                <i class="fas fa-copy text-[10px]"></i>
                                                            </button>
                                                        {/if}
                                                    </div>
                                                </div>
                                            {:else}
                                                <span class="text-gray-400 text-xs">anonymous</span>
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
                                        <td class="text-right">
                                            <div
                                                class="flex items-center justify-end gap-1 opacity-40 group-hover:opacity-100 transition-opacity duration-200"
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
                    <div class="px-4 py-[0.6rem] border-t border-[#ddd] bg-gray-50 flex justify-between items-center">
                        <div class="flex items-center gap-4">
                            <div class="text-[11px] text-[#999]">
                                <span class="font-medium text-[#666]">{relicsTotal}</span> relic{relicsTotal !== 1 ? "s" : ""}
                            </div>
                            <div class="flex items-center gap-2 border-l border-gray-200 pl-4 text-[11px]">
                                <span class="text-[#999]">Show:</span>
                                <select
                                    bind:value={relicsLimit}
                                    on:change={() => { relicsPage = 1; loadRelics(); }}
                                    class="text-[11px] pl-2 pr-6 py-0.5 border border-[#ddd] rounded-sm bg-white text-[#666] focus:outline-none"
                                >
                                    <option value={10}>10</option>
                                    <option value={15}>15</option>
                                    <option value={20}>20</option>
                                    <option value={50}>50</option>
                                    <option value={100}>100</option>
                                    <option value={250}>250</option>
                                </select>
                            </div>
                        </div>
                        {#if relicsTotalPages > 1}
                            <div class="flex items-center gap-0.5 whitespace-nowrap">
                                <span class="text-[11px] text-[#999] mr-2">Page {relicsPage} of {relicsTotalPages}</span>
                                <button
                                    on:click={() => { relicsPage = Math.max(1, relicsPage - 1); loadRelics(); }}
                                    disabled={relicsPage === 1}
                                    class="h-[26px] min-w-[26px] flex items-center justify-center rounded hover:bg-[#e8e8e8] disabled:opacity-25 disabled:cursor-not-allowed transition-colors text-[#555]"
                                ><i class="fas fa-chevron-left text-[11px]"></i></button>
                                <button
                                    on:click={() => { relicsPage = Math.min(relicsTotalPages, relicsPage + 1); loadRelics(); }}
                                    disabled={relicsPage === relicsTotalPages}
                                    class="h-[26px] min-w-[26px] flex items-center justify-center rounded hover:bg-[#e8e8e8] disabled:opacity-25 disabled:cursor-not-allowed transition-colors text-[#555]"
                                ><i class="fas fa-chevron-right text-[11px]"></i></button>
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
                                <tr class="text-[#666] uppercase text-[11px] font-semibold tracking-wider bg-gray-50 border-b-2 border-[#cdcdcd]">
                                    <th class="px-4 py-2.5 text-left border-none">Relic</th>
                                    <th class="px-4 py-2.5 text-left border-none">Owner</th>
                                    <th class="cursor-pointer hover:bg-[#efefef] transition-colors group px-4 py-2.5 text-left select-none border-none" on:click={() => handleReportsSort('reason')}>
                                        <div class="flex items-center gap-1.5">
                                            <span class={reportsSortBy === 'reason' ? 'text-[#772953]' : ''}>Reason</span>
                                            <i class="fas fa-arrow-up sort-arrow {reportsSortBy === 'reason' ? 'opacity-100 text-[#772953]' : 'opacity-0 text-gray-400 group-hover:opacity-50'} {reportsSortBy === 'reason' && reportsSortOrder === 'desc' ? 'desc' : ''}"></i>
                                        </div>
                                    </th>
                                    <th class="cursor-pointer hover:bg-[#efefef] transition-colors group px-4 py-2.5 text-left select-none border-none" on:click={() => handleReportsSort('created_at')}>
                                        <div class="flex items-center gap-1.5">
                                            <span class={reportsSortBy === 'created_at' ? 'text-[#772953]' : ''}>Reported</span>
                                            <i class="fas fa-arrow-up sort-arrow {reportsSortBy === 'created_at' ? 'opacity-100 text-[#772953]' : 'opacity-0 text-gray-400 group-hover:opacity-50'} {reportsSortBy === 'created_at' && reportsSortOrder === 'desc' ? 'desc' : ''}"></i>
                                        </div>
                                    </th>
                                    <th class="px-4 py-2.5 text-center border-none w-32">Actions</th>
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
                                        <td>
                                            {#if report.relic_owner_id}
                                                <div class="flex flex-col">
                                                    <button
                                                        on:click={() =>
                                                            viewUserRelics({
                                                                id: report.relic_owner_id,
                                                                public_id: report.relic_owner_public_id,
                                                            })}
                                                        class="font-medium text-purple-600 hover:text-purple-800 hover:underline text-left leading-tight"
                                                        title="View user's relics"
                                                    >
                                                        {report.relic_owner_name || "Anonymous"}
                                                    </button>
                                                    <span class="text-xs text-gray-400 font-mono">{report.relic_owner_public_id || 'anonymous'}</span>
                                                </div>
                                            {:else}
                                                <span
                                                    class="text-gray-400 text-xs"
                                                    >anonymous</span
                                                >
                                            {/if}
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
                                        <td class="text-right">
                                            <div
                                                class="flex items-center justify-end gap-1"
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
                    <div class="px-4 py-[0.6rem] border-t border-[#ddd] bg-gray-50 flex justify-between items-center">
                        <div class="flex items-center gap-4">
                            <div class="text-[11px] text-[#999]">
                                <span class="font-medium text-[#666]">{reportsTotal}</span> report{reportsTotal !== 1 ? "s" : ""}
                            </div>
                            <div class="flex items-center gap-2 border-l border-gray-200 pl-4 text-[11px]">
                                <span class="text-[#999]">Show:</span>
                                <select
                                    bind:value={reportsLimit}
                                    on:change={() => { reportsPage = 1; loadReports(); }}
                                    class="text-[11px] pl-2 pr-6 py-0.5 border border-[#ddd] rounded-sm bg-white text-[#666] focus:outline-none"
                                >
                                    <option value={10}>10</option>
                                    <option value={15}>15</option>
                                    <option value={20}>20</option>
                                    <option value={50}>50</option>
                                    <option value={100}>100</option>
                                    <option value={250}>250</option>
                                </select>
                            </div>
                        </div>
                        {#if reportsTotalPages > 1}
                            <div class="flex items-center gap-0.5 whitespace-nowrap">
                                <span class="text-[11px] text-[#999] mr-2">Page {reportsPage} of {reportsTotalPages}</span>
                                <button
                                    on:click={() => { reportsPage = Math.max(1, reportsPage - 1); loadReports(); }}
                                    disabled={reportsPage === 1}
                                    class="h-[26px] min-w-[26px] flex items-center justify-center rounded hover:bg-[#e8e8e8] disabled:opacity-25 disabled:cursor-not-allowed transition-colors text-[#555]"
                                ><i class="fas fa-chevron-left text-[11px]"></i></button>
                                <button
                                    on:click={() => { reportsPage = Math.min(reportsTotalPages, reportsPage + 1); loadReports(); }}
                                    disabled={reportsPage === reportsTotalPages}
                                    class="h-[26px] min-w-[26px] flex items-center justify-center rounded hover:bg-[#e8e8e8] disabled:opacity-25 disabled:cursor-not-allowed transition-colors text-[#555]"
                                ><i class="fas fa-chevron-right text-[11px]"></i></button>
                            </div>
                        {/if}
                    </div>
                {/if}
            {/if}

            <!-- Users Tab -->
            {#if activeTab === "users"}
                <div class="px-6 py-3 border-b border-gray-200 flex items-center gap-4 bg-gray-50">
                    <div class="relative flex-1 max-w-md group">
                        <i class="fa-solid fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                        <input
                            type="text"
                            bind:value={usersSearch}
                            placeholder="Filter by name, public ID, or key..."
                            class="w-full pl-9 pr-9 py-1.5 text-sm border border-gray-300 rounded"
                        />
                        {#if usersSearch}
                            <button
                                on:click={() => usersSearch = ''}
                                class="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-red-500 transition-colors focus:outline-none"
                                title="Clear search" aria-label="Clear search"
                            >
                                <i class="fas fa-times-circle"></i>
                            </button>
                        {/if}
                    </div>
                </div>
                {#if usersLoading}
                    <div class="p-8 text-center">
                        <i
                            class="fas fa-spinner fa-spin text-[#772953] text-2xl"
                        ></i>
                    </div>
                {:else if users.length === 0}
                    <div class="p-8 text-center text-gray-500">
                        <i class="fas fa-users text-4xl mb-2"></i>
                        <p>No users found</p>
                    </div>
                {:else}
                    <div class="overflow-x-auto">
                        <table class="w-full maas-table text-sm">
                            <thead>
                                <tr class="text-[#666] uppercase text-[11px] font-semibold tracking-wider bg-gray-50 border-b-2 border-[#cdcdcd]">
                                    <th class="cursor-pointer hover:bg-[#efefef] transition-colors group px-4 py-2.5 text-left select-none border-none" on:click={() => handleUsersSort('name')}>
                                        <div class="flex items-center gap-1.5">
                                            <span class={usersSortBy === 'name' ? 'text-[#772953]' : ''}>User / Name</span>
                                            <i class="fas fa-arrow-up sort-arrow {usersSortBy === 'name' ? 'opacity-100 text-[#772953]' : 'opacity-0 text-gray-400 group-hover:opacity-50'} {usersSortBy === 'name' && usersSortOrder === 'desc' ? 'desc' : ''}"></i>
                                        </div>
                                    </th>
                                    <th class="px-4 py-2.5 text-left border-none">Private Key</th>
                                    <th class="cursor-pointer hover:bg-[#efefef] transition-colors group px-4 py-2.5 text-left select-none border-none" on:click={() => handleUsersSort('relic_count')}>
                                        <div class="flex items-center gap-1.5">
                                            <span class={usersSortBy === 'relic_count' ? 'text-[#772953]' : ''}>Relics</span>
                                            <i class="fas fa-arrow-up sort-arrow {usersSortBy === 'relic_count' ? 'opacity-100 text-[#772953]' : 'opacity-0 text-gray-400 group-hover:opacity-50'} {usersSortBy === 'relic_count' && usersSortOrder === 'desc' ? 'desc' : ''}"></i>
                                        </div>
                                    </th>
                                    <th class="px-4 py-2.5 text-left border-none">Role</th>
                                    <th class="cursor-pointer hover:bg-[#efefef] transition-colors group px-4 py-2.5 text-left select-none border-none" on:click={() => handleUsersSort('created_at')}>
                                        <div class="flex items-center gap-1.5">
                                            <span class={usersSortBy === 'created_at' ? 'text-[#772953]' : ''}>Created</span>
                                            <i class="fas fa-arrow-up sort-arrow {usersSortBy === 'created_at' ? 'opacity-100 text-[#772953]' : 'opacity-0 text-gray-400 group-hover:opacity-50'} {usersSortBy === 'created_at' && usersSortOrder === 'desc' ? 'desc' : ''}"></i>
                                        </div>
                                    </th>
                                    <th class="px-4 py-2.5 text-right border-none w-24">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each users as user (user.id)}
                                    <tr class="hover:bg-gray-50 group">
                                        <td>
                                            <div class="flex items-center gap-2">
                                                <i class="fas fa-user-circle text-gray-400 text-[13px]"></i>
                                                <div>
                                                    <div class="font-medium text-[13px] leading-tight text-gray-900">{user.name || "Anonymous"}</div>
                                                    <div class="flex items-center gap-1 group/pid">
                                                        <span class="text-[11px] text-gray-400 font-mono">{user.public_id || '-'}</span>
                                                        {#if user.public_id}
                                                            <button
                                                                on:click|stopPropagation={() => copyToClipboard(user.public_id, "Public ID copied to clipboard!")}
                                                                class="opacity-0 group-hover/pid:opacity-100 text-gray-400 hover:text-gray-600 transition-all"
                                                                title="Copy Public ID"
                                                            >
                                                                <i class="fas fa-copy text-[10px]"></i>
                                                            </button>
                                                        {/if}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            {#if user.id}
                                                <div class="flex items-center gap-1">
                                                    <span class="text-xs font-mono text-gray-600">{revealedKeys.has(user.id) ? user.id : '•'.repeat(user.id.length)}</span>
                                                    <button
                                                        on:click|stopPropagation={() => { if (revealedKeys.has(user.id)) { revealedKeys.delete(user.id); } else { revealedKeys.add(user.id); } revealedKeys = revealedKeys; }}
                                                        class="text-gray-400 hover:text-gray-600 transition-colors"
                                                        title={revealedKeys.has(user.id) ? 'Hide key' : 'Show key'}
                                                    >
                                                        <i class="fas {revealedKeys.has(user.id) ? 'fa-eye-slash' : 'fa-eye'} text-xs"></i>
                                                    </button>
                                                    {#if revealedKeys.has(user.id)}
                                                        <button
                                                            on:click|stopPropagation={() => copyToClipboard(user.id, "Private Key copied to clipboard!")}
                                                            class="text-gray-400 hover:text-gray-600 transition-colors"
                                                            title="Copy Private Key"
                                                        >
                                                            <i class="fas fa-copy text-xs"></i>
                                                        </button>
                                                    {/if}
                                                </div>
                                            {:else}
                                                <span class="text-gray-400 text-xs italic">not set</span>
                                            {/if}
                                        </td>
                                        <td>
                                            <button
                                                on:click={() => viewUserRelics(user)}
                                                class="text-xs text-blue-600 hover:text-blue-800 hover:underline"
                                                title="View relics"
                                            >
                                                <i class="fas fa-archive mr-1"></i>{user.relic_count} relics
                                            </button>
                                        </td>
                                        <td>
                                            {#if user.is_super_admin}
                                                <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium" style="background-color: #f3e5f5; color: #772953;" title="Defined via ADMIN_USER_IDS (cannot be revoked at runtime)">
                                                    <i class="fas fa-shield-alt mr-1"></i>super admin
                                                </span>
                                            {:else if user.is_admin}
                                                <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium" style="background-color: #f3e5f5; color: #772953;">
                                                    <i class="fas fa-shield-alt mr-1"></i>admin
                                                </span>
                                            {:else}
                                                <span class="text-gray-500 text-xs">user</span>
                                            {/if}
                                        </td>
                                        <td class="text-gray-500 text-xs">{formatTimeAgo(user.created_at)}</td>
                                        <td class="text-right">
                                            <div class="flex justify-end gap-1 opacity-40 group-hover:opacity-100 transition-opacity duration-200">
                                                {#if !user.is_super_admin}
                                                    {#if user.is_admin}
                                                        <button
                                                            on:click={() => handleToggleAdmin(user)}
                                                            class="p-1.5 text-amber-600 hover:text-amber-700 hover:bg-amber-50 rounded transition-colors"
                                                            title="Remove admin"
                                                        >
                                                            <i class="fas fa-user-minus text-xs"></i>
                                                        </button>
                                                    {:else}
                                                        <button
                                                            on:click={() => handleToggleAdmin(user)}
                                                            class="p-1.5 text-purple-600 hover:text-purple-700 hover:bg-purple-50 rounded transition-colors"
                                                            title="Make admin"
                                                        >
                                                            <i class="fas fa-user-shield text-xs"></i>
                                                        </button>
                                                    {/if}
                                                    {#if !user.is_admin}
                                                        <button
                                                            on:click={() => handleDeleteUser(user)}
                                                            class="p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                                                            title="Delete User"
                                                        >
                                                            <i class="fas fa-trash text-xs"></i>
                                                        </button>
                                                    {/if}
                                                {/if}
                                            </div>
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                    <div class="px-4 py-[0.6rem] border-t border-[#ddd] bg-gray-50 flex justify-between items-center">
                        <div class="flex items-center gap-4">
                            <div class="text-[11px] text-[#999]">
                                <span class="font-medium text-[#666]">{usersTotal}</span> user{usersTotal !== 1 ? "s" : ""}
                            </div>
                            <div class="flex items-center gap-2 border-l border-gray-200 pl-4 text-[11px]">
                                <span class="text-[#999]">Show:</span>
                                <select
                                    bind:value={usersLimit}
                                    on:change={() => { usersPage = 1; loadUsers(); }}
                                    class="text-[11px] pl-2 pr-6 py-0.5 border border-[#ddd] rounded-sm bg-white text-[#666] focus:outline-none"
                                >
                                    <option value={10}>10</option>
                                    <option value={15}>15</option>
                                    <option value={20}>20</option>
                                    <option value={50}>50</option>
                                    <option value={100}>100</option>
                                    <option value={250}>250</option>
                                </select>
                            </div>
                        </div>
                        {#if usersTotalPages > 1}
                            <div class="flex items-center gap-0.5 whitespace-nowrap">
                                <span class="text-[11px] text-[#999] mr-2">Page {usersPage} of {usersTotalPages}</span>
                                <button
                                    on:click={() => { usersPage = Math.max(1, usersPage - 1); loadUsers(); }}
                                    disabled={usersPage === 1}
                                    class="h-[26px] min-w-[26px] flex items-center justify-center rounded hover:bg-[#e8e8e8] disabled:opacity-25 disabled:cursor-not-allowed transition-colors text-[#555]"
                                ><i class="fas fa-chevron-left text-[11px]"></i></button>
                                <button
                                    on:click={() => { usersPage = Math.min(usersTotalPages, usersPage + 1); loadUsers(); }}
                                    disabled={usersPage === usersTotalPages}
                                    class="h-[26px] min-w-[26px] flex items-center justify-center rounded hover:bg-[#e8e8e8] disabled:opacity-25 disabled:cursor-not-allowed transition-colors text-[#555]"
                                ><i class="fas fa-chevron-right text-[11px]"></i></button>
                            </div>
                        {/if}
                    </div>
                {/if}
            {/if}

            <!-- Backups Tab -->
            {#if activeTab === "backups"}
                <input
                    type="file"
                    accept=".sql.gz"
                    class="hidden"
                    bind:this={uploadFileInput}
                    on:change={handleUploadFileChange}
                />
                <div
                    class="px-6 py-3 border-b border-gray-200 flex items-center justify-between bg-gray-50"
                >
                    <span class="text-sm text-gray-600"
                        >Database backups stored in S3</span
                    >
                    <div class="flex items-center gap-2">
                        <button
                            on:click={() => uploadFileInput.click()}
                            class="px-3 py-1.5 text-sm bg-white border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition-colors flex items-center gap-2"
                        >
                            <i class="fas fa-upload"></i>Restore from file
                        </button>
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
                            <thead>
                                <tr class="text-[#666] uppercase text-[11px] font-semibold tracking-wider bg-gray-50 border-b-2 border-[#cdcdcd]">
                                    <th class="px-4 py-2.5 text-left border-none">Backup</th>
                                    <th class="px-4 py-2.5 text-left border-none">Timestamp</th>
                                    <th class="px-4 py-2.5 text-left border-none">Size</th>
                                    <th class="px-4 py-2.5 text-center border-none w-32">Actions</th>
                                </tr>
                            </thead>
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
                                        <td class="px-4 py-2.5 text-right">
                                            <div class="flex items-center justify-end gap-1">
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
                                                <button
                                                    on:click={() =>
                                                        openRestoreModal(backup)}
                                                    class="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                                                    title="Restore database from this backup"
                                                    ><i
                                                        class="fas fa-undo text-xs"
                                                    ></i></button
                                                >
                                            </div>
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                    <div class="px-4 py-[0.6rem] border-t border-[#ddd] bg-gray-50 flex justify-between items-center">
                        <div class="flex items-center gap-4">
                            <div class="text-[11px] text-[#999]">
                                <span class="font-medium text-[#666]">{backupsTotal}</span> backup{backupsTotal !== 1 ? "s" : ""} • Total: {formatBytes(backupsTotalSize)}
                            </div>
                            <div class="flex items-center gap-2 border-l border-gray-200 pl-4 text-[11px]">
                                <span class="text-[#999]">Show:</span>
                                <select
                                    bind:value={backupsLimit}
                                    on:change={() => { backupsPage = 1; loadBackups(); }}
                                    class="text-[11px] pl-2 pr-6 py-0.5 border border-[#ddd] rounded-sm bg-white text-[#666] focus:outline-none"
                                >
                                    <option value={10}>10</option>
                                    <option value={15}>15</option>
                                    <option value={20}>20</option>
                                    <option value={50}>50</option>
                                    <option value={100}>100</option>
                                    <option value={250}>250</option>
                                </select>
                            </div>
                        </div>
                        {#if backupsTotalPages > 1}
                            <div class="flex items-center gap-0.5 whitespace-nowrap">
                                <span class="text-[11px] text-[#999] mr-2">Page {backupsPage} of {backupsTotalPages}</span>
                                <button
                                    on:click={() => { backupsPage = Math.max(1, backupsPage - 1); loadBackups(); }}
                                    disabled={backupsPage === 1}
                                    class="h-[26px] min-w-[26px] flex items-center justify-center rounded hover:bg-[#e8e8e8] disabled:opacity-25 disabled:cursor-not-allowed transition-colors text-[#555]"
                                ><i class="fas fa-chevron-left text-[11px]"></i></button>
                                <button
                                    on:click={() => { backupsPage = Math.min(backupsTotalPages, backupsPage + 1); loadBackups(); }}
                                    disabled={backupsPage === backupsTotalPages}
                                    class="h-[26px] min-w-[26px] flex items-center justify-center rounded hover:bg-[#e8e8e8] disabled:opacity-25 disabled:cursor-not-allowed transition-colors text-[#555]"
                                ><i class="fas fa-chevron-right text-[11px]"></i></button>
                            </div>
                        {/if}
                    </div>
                {/if}
            {/if}

            <!-- Jobs Tab -->
            {#if activeTab === "jobs"}
                <div
                    class="px-6 py-3 border-b border-gray-200 flex items-center justify-between bg-gray-50"
                >
                    <div class="flex items-center gap-3">
                        <span class="text-sm text-gray-600">Background scheduler & periodic tasks</span>
                        <span class="h-4 w-[1px] bg-gray-300"></span>
                        <div class="flex items-center gap-1.5 text-xs font-semibold">
                            {#if jobsRunning}
                                <span class="flex h-2 w-2 relative">
                                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                    <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                                </span>
                                <span class="text-green-700">Scheduler Active</span>
                            {:else}
                                <span class="inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                                <span class="text-red-700">Scheduler Stopped</span>
                            {/if}
                        </div>
                    </div>
                    <button
                        on:click={loadJobs}
                        disabled={jobsLoading}
                        class="px-3 py-1.5 text-sm bg-white border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition-colors flex items-center gap-2"
                    >
                        {#if jobsLoading}
                            <i class="fas fa-spinner fa-spin"></i>Refreshing...
                        {:else}
                            <i class="fas fa-sync-alt"></i>Refresh Scheduler
                        {/if}
                    </button>
                </div>

                <!-- Sub-tab Navigation -->
                <div class="px-6 py-2 border-b border-gray-200 bg-white flex items-center justify-between">
                    <div class="flex items-center gap-4">
                        <button
                            on:click={() => jobsSubTab = 'scheduled'}
                            class="text-xs font-medium py-1.5 px-3 rounded-md transition-colors flex items-center gap-1.5 {jobsSubTab === 'scheduled' ? 'bg-[#772953] text-white' : 'text-gray-600 hover:bg-gray-100'}"
                        >
                            <i class="fas fa-clock text-[10px]"></i> Scheduled Tasks ({jobs.length})
                        </button>
                        <button
                            on:click={() => jobsSubTab = 'history'}
                            class="text-xs font-medium py-1.5 px-3 rounded-md transition-colors flex items-center gap-1.5 {jobsSubTab === 'history' ? 'bg-[#772953] text-white' : 'text-gray-600 hover:bg-gray-100'}"
                        >
                            <i class="fas fa-history text-[10px]"></i> Execution History & Logs ({jobsHistory.length})
                        </button>
                    </div>
                    
                    {#if jobsSubTab === 'history'}
                        <div class="text-[10px] text-gray-400 font-sans italic">
                            Retaining up to 500 recent job runs in-memory
                        </div>
                    {/if}
                </div>

                <!-- Scheduled Tasks Sub-Tab -->
                {#if jobsSubTab === 'scheduled'}
                    <div class="px-4 py-2 bg-yellow-50 border-b border-yellow-100 text-yellow-800 text-xs flex items-center gap-2">
                        <i class="fas fa-info-circle"></i>
                        Note: Paused job states are currently stored in-memory and will be lost on server restart.
                    </div>
                    {#if jobsLoading && jobs.length === 0}
                        <div class="p-8 text-center">
                            <i class="fas fa-spinner fa-spin text-[#772953] text-2xl"></i>
                        </div>
                    {:else if jobs.length === 0}
                        <div class="p-8 text-center text-gray-500">
                            <i class="fas fa-tasks text-4xl mb-2"></i>
                            <p>No scheduled jobs found</p>
                        </div>
                    {:else}
                        <div class="overflow-x-auto">
                            <table class="w-full maas-table text-sm">
                                <thead>
                                    <tr class="text-[#666] uppercase text-[11px] font-semibold tracking-wider bg-gray-50 border-b-2 border-[#cdcdcd]">
                                        <th class="pl-6 pr-4 py-2.5 text-left border-none">Job Info</th>
                                        <th class="px-4 py-2.5 text-left border-none">Target Function</th>
                                        <th class="px-4 py-2.5 text-left border-none">Schedule / Trigger</th>
                                        <th class="px-4 py-2.5 text-left border-none">Next Execution</th>
                                        <th class="pl-4 pr-6 py-2.5 text-right border-none w-36">Actions</th>
                                    </tr>
                                </thead>
                                <tbody class="font-mono text-[11px]">
                                    {#each jobs as job}
                                        <tr class="group hover:bg-gray-50/50 transition-colors">
                                            <td class="pl-6 pr-4 align-top">
                                                <div class="flex items-start gap-2.5">
                                                    <div class="h-7 w-7 rounded-lg bg-purple-50 text-[#772953] flex items-center justify-center border border-purple-100 flex-shrink-0 mt-0.5">
                                                        {#if job.id.startsWith('backup')}
                                                            <i class="fas fa-database text-[10px]"></i>
                                                        {:else}
                                                            <i class="fas fa-clock text-[10px]"></i>
                                                        {/if}
                                                    </div>
                                                    <div>
                                                        <span class="font-semibold text-gray-700 font-sans text-xs block">{job.name}</span>
                                                        <span class="text-[10px] text-gray-400 mt-0.5 block">{job.id}</span>
                                                    </div>
                                                </div>
                                            </td>
                                            <td class="px-4 text-gray-500 align-top font-mono">{job.func}</td>
                                            <td class="px-4 align-top">
                                                 <span class="px-1.5 py-0.5 rounded text-[10px] font-sans font-medium bg-blue-50 text-blue-700 border border-blue-100 inline-flex items-center gap-1" title={job.trigger}>
                                                     <i class="fas fa-calendar-alt text-[9px]"></i> {formatTriggerJob(job)}
                                                 </span>
                                            </td>
                                            <td class="px-4 align-top">
                                                {#if job.paused}
                                                    <span class="px-1.5 py-0.5 rounded text-[10px] font-sans font-medium bg-amber-50 text-amber-700 border border-amber-100 inline-flex items-center gap-1">
                                                        <i class="fas fa-pause-circle text-[9px]"></i> Paused / Disabled
                                                    </span>
                                                {:else if job.next_run_time}
                                                    <div class="text-gray-500 whitespace-nowrap">
                                                        {formatDate(job.next_run_time)}
                                                    </div>
                                                    <div class="text-[10px] text-gray-400 mt-0.5 font-sans">
                                                        {formatTimeAgo(job.next_run_time)}
                                                    </div>
                                                {:else}
                                                    <span class="text-gray-400 italic font-sans">Not scheduled</span>
                                                {/if}
                                            </td>
                                            <td class="pl-4 pr-6 text-right align-top">
                                                <div class="flex items-center justify-end gap-1 opacity-40 group-hover:opacity-100 transition-opacity duration-200">
                                                    <!-- View History Button -->
                                                    <button
                                                        on:click={() => {
                                                            jobsHistoryFilter = job.id;
                                                            jobsSubTab = 'history';
                                                        }}
                                                        class="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                                                        title="View History Runs"
                                                    >
                                                        <i class="fas fa-history text-xs"></i>
                                                    </button>

                                                    <button
                                                        on:click={() => {
                                                            confirmTitle = 'Run Job Manually';
                                                            confirmMessage = `Trigger a manual run of ${job.name || job.id}?`;
                                                            confirmAction = () => { showConfirm = false; handleRunJob(job.id); };
                                                            showConfirm = true;
                                                        }}
                                                        disabled={jobsActionInProgress[job.id] === 'run' || job.paused}
                                                        class="p-1.5 transition-colors rounded {job.paused ? 'text-gray-300 cursor-not-allowed' : 'text-gray-400 hover:text-green-600 hover:bg-green-50'}"
                                                        title={job.paused ? "Cannot run paused job" : "Run Now"}
                                                    >
                                                        {#if jobsActionInProgress[job.id] === 'run'}
                                                            <i class="fas fa-spinner fa-spin text-xs"></i>
                                                        {:else}
                                                            <i class="fas fa-play text-xs"></i>
                                                        {/if}
                                                    </button>
 
                                                    {#if job.paused}
                                                        <button
                                                            on:click={() => handleTogglePauseJob(job)}
                                                            disabled={jobsActionInProgress[job.id] === 'resume'}
                                                            class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                                            title="Resume"
                                                        >
                                                            {#if jobsActionInProgress[job.id] === 'resume'}
                                                                <i class="fas fa-spinner fa-spin text-xs"></i>
                                                            {:else}
                                                                <i class="fas fa-play-circle text-xs"></i>
                                                            {/if}
                                                        </button>
                                                    {:else}
                                                        <button
                                                            on:click={() => handleTogglePauseJob(job)}
                                                            disabled={jobsActionInProgress[job.id] === 'pause'}
                                                            class="p-1.5 text-gray-400 hover:text-amber-600 hover:bg-amber-50 rounded transition-colors"
                                                            title="Pause"
                                                        >
                                                            {#if jobsActionInProgress[job.id] === 'pause'}
                                                                <i class="fas fa-spinner fa-spin text-xs"></i>
                                                            {:else}
                                                                <i class="fas fa-pause text-xs"></i>
                                                            {/if}
                                                        </button>
                                                    {/if}
                                                </div>
                                            </td>
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                    {/if}
                {:else if jobsSubTab === 'history'}
                    <!-- Execution History Sub-Tab -->
                    <div class="px-6 py-2.5 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                        <div class="flex items-center gap-1.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                            <i class="fas fa-terminal text-gray-400"></i> Execution Records
                        </div>
                        <div class="flex items-center gap-3">
                            <div class="flex items-center gap-2">
                                <span class="text-xs text-gray-500 font-sans">Task:</span>
                                <select
                                    bind:value={jobsHistoryFilter}
                                    on:change={() => jobsHistoryPage = 1}
                                    class="text-xs border border-gray-300 rounded px-2.5 py-1 bg-white text-gray-700 font-sans"
                                >
                                    <option value="">All Tasks</option>
                                    {#each jobs as j}
                                        <option value={j.id}>{j.name}</option>
                                    {/each}
                                </select>
                            </div>
                            <div class="flex items-center gap-2">
                                <span class="text-xs text-gray-500 font-sans">Status:</span>
                                <select
                                    bind:value={jobsHistoryStatus}
                                    on:change={() => jobsHistoryPage = 1}
                                    class="text-xs border border-gray-300 rounded px-2.5 py-1 bg-white text-gray-700 font-sans"
                                >
                                    <option value="">All</option>
                                    <option value="success">Success</option>
                                    <option value="failed">Failed</option>
                                    <option value="running">Running</option>
                                </select>
                            </div>
                            <button
                                on:click={loadJobs}
                                disabled={jobsLoading}
                                class="px-3 py-1 text-xs bg-white border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition-colors flex items-center gap-1.5"
                                title="Refresh execution logs"
                            >
                                {#if jobsLoading}
                                    <i class="fas fa-spinner fa-spin text-[10px]"></i>Refreshing...
                                {:else}
                                    <i class="fas fa-sync-alt text-[10px]"></i>Refresh
                                {/if}
                            </button>
                        </div>
                    </div>

                    {#if jobsHistoryFilter || jobsHistoryStatus}
                        <div class="px-6 py-2 bg-indigo-50 border-b border-indigo-100 flex items-center justify-between text-xs text-indigo-700">
                            <span class="flex items-center gap-1.5 font-medium">
                                <i class="fas fa-filter"></i>
                                {#if jobsHistoryFilter}Task: <span class="font-mono bg-indigo-100 px-1.5 py-0.5 rounded font-semibold text-indigo-800">{jobsHistoryFilter}</span>{/if}
                                {#if jobsHistoryFilter && jobsHistoryStatus}&nbsp;•&nbsp;{/if}
                                {#if jobsHistoryStatus}Status: <span class="font-mono bg-indigo-100 px-1.5 py-0.5 rounded font-semibold text-indigo-800">{jobsHistoryStatus}</span>{/if}
                                <span class="text-indigo-400 font-normal ml-1">({filteredHistory.length} result{filteredHistory.length !== 1 ? 's' : ''})</span>
                            </span>
                            <button
                                on:click={() => { jobsHistoryFilter = ''; jobsHistoryStatus = ''; jobsHistoryPage = 1; }}
                                class="text-[10px] bg-white border border-indigo-200 text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 px-2 py-0.5 rounded transition-colors font-medium flex items-center gap-1"
                            >
                                <i class="fas fa-times"></i> Clear Filters
                            </button>
                        </div>
                    {/if}

                    {#if filteredHistory.length === 0}
                        <div class="mx-6 my-8 border border-dashed border-gray-200 rounded-lg p-8 text-center text-gray-500 text-xs">
                            <i class="fas fa-terminal text-2xl mb-1.5 opacity-50 block text-gray-400"></i>
                            <p>No task executions recorded {jobsHistoryFilter || jobsHistoryStatus ? 'matching these filters' : ''} in this session.</p>
                        </div>
                    {:else}
                        <div class="overflow-x-auto">
                            <table class="w-full maas-table text-sm">
                                <thead>
                                    <tr class="text-[#666] uppercase text-[11px] font-semibold tracking-wider bg-gray-50 border-b-2 border-[#cdcdcd]">
                                        <th class="pl-6 pr-4 py-2.5 text-left border-none">Job Name</th>
                                        <th class="px-4 py-2.5 text-left border-none">Trigger Type</th>
                                        <th class="px-4 py-2.5 text-left border-none">Started</th>
                                        <th class="px-4 py-2.5 text-left border-none">Duration</th>
                                        <th class="px-4 py-2.5 text-left border-none">Status</th>
                                        <th class="pl-4 pr-6 py-2.5 text-left border-none">Details / Logs</th>
                                    </tr>
                                </thead>
                                <tbody class="font-mono text-[11px]">
                                    {#each paginatedHistory as run (run.run_id)}
                                        <tr class="hover:bg-gray-50/50">
                                            <td class="pl-6 pr-4 align-top font-sans">
                                                <div class="font-semibold text-gray-700 text-xs">{run.job_name}</div>
                                                <div class="text-[10px] text-gray-400 mt-0.5 font-mono">{run.job_id}</div>
                                            </td>
                                            <td class="px-4 align-top">
                                                {#if run.trigger_type === 'manual'}
                                                    <span class="inline-flex items-center gap-1 text-[10px] font-sans px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 font-medium">
                                                        <i class="fas fa-hand-pointer text-[9px]"></i> Manual
                                                    </span>
                                                {:else}
                                                    <span class="inline-flex items-center gap-1 text-[10px] font-sans px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 font-medium">
                                                        <i class="fas fa-clock text-[9px]"></i> Scheduled
                                                    </span>
                                                {/if}
                                            </td>
                                            <td class="px-4 text-gray-500 whitespace-nowrap align-top">
                                                {formatDate(run.start_time)}
                                            </td>
                                            <td class="px-4 text-gray-600 font-sans align-top">
                                                {#if run.duration !== null}
                                                    {run.duration.toFixed(3)}s
                                                {:else}
                                                    -
                                                {/if}
                                            </td>
                                            <td class="px-4 align-top">
                                                {#if run.status === 'running'}
                                                    <span class="inline-flex items-center gap-1 text-[10px] font-sans px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-medium">
                                                        <i class="fas fa-spinner fa-spin text-[9px]"></i> Running
                                                    </span>
                                                {:else if run.status === 'success'}
                                                    <span class="inline-flex items-center gap-1 text-[10px] font-sans px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-medium">
                                                        <i class="fas fa-check-circle text-[9px]"></i> Success
                                                    </span>
                                                {:else}
                                                    <span class="inline-flex items-center gap-1 text-[10px] font-sans px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 font-medium">
                                                        <i class="fas fa-times-circle text-[9px]"></i> Failed
                                                    </span>
                                                {/if}
                                            </td>
                                            <td class="pl-4 pr-6 text-gray-700 align-top">
                                                <div class="max-w-xs md:max-w-md break-words">
                                                    <div class="flex flex-col gap-1.5">
                                                        {#if run.status === 'running'}
                                                            <span class="text-gray-400 italic font-sans text-[11px]">Executing task...</span>
                                                        {:else if run.status === 'success'}
                                                            <span class="text-emerald-600 font-medium font-sans text-[11px]"><i class="fas fa-check mr-1"></i>Completed successfully</span>
                                                        {:else}
                                                            <div class="text-rose-600 font-medium font-sans text-[11px] break-words" title={run.error}>
                                                                <i class="fas fa-exclamation-triangle mr-1"></i>{run.error}
                                                            </div>
                                                        {/if}

                                                        <!-- Show Captured Logs if available -->
                                                        {#if run.logs && run.logs.length > 0}
                                                            <div>
                                                                    <button
                                                                        on:click={() => toggleLogs(run.run_id)}
                                                                        class="text-[10px] text-blue-600 hover:text-blue-800 hover:underline font-sans flex items-center gap-1 p-0 bg-transparent border-none cursor-pointer"
                                                                    >
                                                                        <i class="fas {expandedLogs[run.run_id] ? 'fa-chevron-up' : 'fa-chevron-down'} text-[8px]"></i>
                                                                        {expandedLogs[run.run_id] ? 'Hide' : 'View'} Execution Logs ({run.logs.length})
                                                                    </button>
                                                                    {#if expandedLogs[run.run_id]}
                                                                        <div class="relative group/logs">
                                                                            <button
                                                                                on:click={() => copyToClipboard(run.logs.join('\n'), 'Logs copied to clipboard')}
                                                                                class="absolute top-1.5 right-1.5 p-1 text-gray-400 hover:text-gray-600 bg-white/80 hover:bg-white rounded border border-gray-200 opacity-0 group-hover/logs:opacity-100 transition-opacity"
                                                                                title="Copy logs"
                                                                            >
                                                                                <i class="fas fa-copy text-[9px]"></i>
                                                                            </button>
                                                                            <pre class="mt-1.5 p-2 bg-gray-50 border border-gray-200 rounded text-[10px] text-gray-600 overflow-x-auto max-h-48 whitespace-pre-wrap break-all font-mono leading-relaxed">{run.logs.join('\n')}</pre>
                                                                        </div>
                                                                    {/if}
                                                            </div>
                                                        {/if}

                                                        <!-- Show traceback if available and failed -->
                                                        {#if run.status === 'failed' && run.traceback}
                                                            <div>
                                                                <button
                                                                    on:click={() => toggleTraceback(run.run_id)}
                                                                    class="text-[10px] text-red-600 hover:text-red-800 hover:underline font-sans flex items-center gap-1 p-0 bg-transparent border-none cursor-pointer"
                                                                >
                                                                    <i class="fas {expandedTracebacks[run.run_id] ? 'fa-chevron-up' : 'fa-chevron-down'} text-[8px]"></i>
                                                                    {expandedTracebacks[run.run_id] ? 'Hide' : 'View'} Stack Trace
                                                                </button>
                                                                {#if expandedTracebacks[run.run_id]}
                                                                    <div class="relative group/tb">
                                                                        <button
                                                                            on:click={() => copyToClipboard(run.traceback, 'Stack trace copied to clipboard')}
                                                                            class="absolute top-1.5 right-1.5 p-1 text-rose-400 hover:text-rose-600 bg-white/80 hover:bg-white rounded border border-rose-200 opacity-0 group-hover/tb:opacity-100 transition-opacity"
                                                                            title="Copy stack trace"
                                                                        >
                                                                            <i class="fas fa-copy text-[9px]"></i>
                                                                        </button>
                                                                        <pre class="mt-1.5 p-2 bg-rose-50/50 border border-rose-100 rounded text-[10px] text-rose-700 overflow-x-auto max-h-48 whitespace-pre-wrap break-all font-mono leading-relaxed">{run.traceback}</pre>
                                                                    </div>
                                                                {/if}
                                                            </div>
                                                        {/if}
                                                    </div>
                                                </div>
                                            </td>
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                        <div class="px-4 py-[0.6rem] border-t border-[#ddd] bg-gray-50 flex justify-between items-center">
                            <div class="flex items-center gap-4">
                                <div class="text-[11px] text-[#999]">
                                    <span class="font-medium text-[#666]">{filteredHistory.length}</span> run{filteredHistory.length !== 1 ? "s" : ""}
                                </div>
                                <div class="flex items-center gap-2 border-l border-gray-200 pl-4 text-[11px]">
                                    <span class="text-[#999]">Show:</span>
                                    <select
                                        bind:value={jobsHistoryLimit}
                                        on:change={() => jobsHistoryPage = 1}
                                        class="text-[11px] pl-2 pr-6 py-0.5 border border-[#ddd] rounded-sm bg-white text-[#666] focus:outline-none"
                                    >
                                        <option value={10}>10</option>
                                        <option value={15}>15</option>
                                        <option value={20}>20</option>
                                        <option value={25}>25</option>
                                        <option value={50}>50</option>
                                        <option value={100}>100</option>
                                    </select>
                                </div>
                            </div>
                            {#if jobsHistoryTotalPages > 1}
                                <div class="flex items-center gap-0.5 whitespace-nowrap">
                                    <span class="text-[11px] text-[#999] mr-2">Page {jobsHistoryPage} of {jobsHistoryTotalPages}</span>
                                    <button
                                        on:click={() => jobsHistoryPage = Math.max(1, jobsHistoryPage - 1)}
                                        disabled={jobsHistoryPage === 1}
                                        class="h-[26px] min-w-[26px] flex items-center justify-center rounded hover:bg-[#e8e8e8] disabled:opacity-25 disabled:cursor-not-allowed transition-colors text-[#555]"
                                    ><i class="fas fa-chevron-left text-[11px]"></i></button>
                                    <button
                                        on:click={() => jobsHistoryPage = Math.min(jobsHistoryTotalPages, jobsHistoryPage + 1)}
                                        disabled={jobsHistoryPage === jobsHistoryTotalPages}
                                        class="h-[26px] min-w-[26px] flex items-center justify-center rounded hover:bg-[#e8e8e8] disabled:opacity-25 disabled:cursor-not-allowed transition-colors text-[#555]"
                                    ><i class="fas fa-chevron-right text-[11px]"></i></button>
                                </div>
                            {/if}
                        </div>
                    {/if}
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
                        <!-- Administrators management -->
                        <div>
                            <h3
                                class="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3 flex items-center gap-2"
                            >
                                <i class="fas fa-shield-alt text-gray-400"></i>
                                Administrators
                                {#if admins.length}
                                    <span
                                        class="text-xs font-normal text-gray-400 normal-case"
                                        >({admins.length})</span
                                    >
                                {/if}
                            </h3>

                            <form
                                on:submit|preventDefault={handleAddAdmin}
                                class="flex gap-2 mb-3"
                            >
                                <input
                                    type="text"
                                    bind:value={newAdminPublicId}
                                    placeholder="Add admin by Public ID"
                                    class="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded font-mono"
                                />
                                <button
                                    type="submit"
                                    disabled={!newAdminPublicId.trim() ||
                                        addingAdmin}
                                    class="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                                >
                                    {#if addingAdmin}<i
                                            class="fas fa-spinner fa-spin mr-1"
                                        ></i>{:else}<i
                                            class="fas fa-user-plus mr-1"
                                        ></i>{/if}Add admin
                                </button>
                            </form>

                            <div
                                class="overflow-x-auto border border-gray-200 rounded-lg"
                            >
                                <table class="w-full maas-table text-sm">
                                    <thead>
                                        <tr
                                            class="text-[#666] uppercase text-[11px] font-semibold tracking-wider bg-gray-50 border-b-2 border-[#cdcdcd]"
                                        >
                                            <th
                                                class="px-4 py-2 text-left border-none"
                                                >Name</th
                                            >
                                            <th
                                                class="px-4 py-2 text-left border-none"
                                                >Identifier</th
                                            >
                                            <th
                                                class="px-4 py-2 text-left border-none"
                                                >Role</th
                                            >
                                            <th
                                                class="px-4 py-2 text-right border-none w-16"
                                                >Actions</th
                                            >
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {#if adminsLoading}
                                            <tr
                                                ><td
                                                    colspan="4"
                                                    class="px-4 py-6 text-center text-gray-400"
                                                    ><i
                                                        class="fas fa-spinner fa-spin"
                                                    ></i></td
                                                ></tr
                                            >
                                        {:else if admins.length === 0}
                                            <tr
                                                ><td
                                                    colspan="4"
                                                    class="px-4 py-6 text-center text-gray-400"
                                                    >No administrators</td
                                                ></tr
                                            >
                                        {:else}
                                            {#each admins as admin (admin.user_id)}
                                                <tr class="hover:bg-gray-50 group">
                                                    <td>
                                                        <div
                                                            class="flex items-center gap-2"
                                                        >
                                                            <i
                                                                class="fas fa-user-circle text-gray-400 text-[13px]"
                                                            ></i>
                                                            <span
                                                                class="text-[13px] text-gray-900"
                                                                >{admin.name ||
                                                                    "Unnamed user"}</span
                                                            >
                                                        </div>
                                                    </td>
                                                    <td
                                                        class="font-mono text-[11px] text-gray-500"
                                                        >{admin.public_id ||
                                                            admin.user_id}</td
                                                    >
                                                    <td>
                                                        <span
                                                            class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium"
                                                            style="background-color: #f3e5f5; color: #772953;"
                                                            title={admin.is_super_admin
                                                                ? "Defined via ADMIN_USER_IDS (cannot be revoked at runtime)"
                                                                : "Runtime-granted admin"}
                                                        >
                                                            <i
                                                                class="fas fa-shield-alt mr-1"
                                                            ></i>{admin.is_super_admin
                                                                ? "super admin"
                                                                : "admin"}
                                                        </span>
                                                    </td>
                                                    <td class="text-right">
                                                        {#if !admin.is_super_admin}
                                                            <button
                                                                on:click={() =>
                                                                    handleRemoveAdmin(
                                                                        admin,
                                                                    )}
                                                                class="p-1.5 text-amber-600 hover:text-amber-700 hover:bg-amber-50 rounded transition-colors opacity-40 group-hover:opacity-100"
                                                                title="Remove admin"
                                                                aria-label="Remove admin"
                                                            >
                                                                <i
                                                                    class="fas fa-user-minus text-xs"
                                                                ></i>
                                                            </button>
                                                        {/if}
                                                    </td>
                                                </tr>
                                            {/each}
                                        {/if}
                                    </tbody>
                                </table>
                            </div>
                            <p class="text-xs text-gray-400 mt-2">
                                Super admins are set via the <code
                                    class="bg-gray-100 px-1 rounded"
                                    >ADMIN_USER_IDS</code
                                > env var and can't be removed here. Others can be
                                added or removed at runtime.
                            </p>
                        </div>

                        {#each Object.entries(config).filter(([section]) => section !== "admin") as [section, values]}
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

<ConfirmModal
  show={showConfirm}
  title={confirmTitle}
  message={confirmMessage}
  on:confirm={confirmAction}
  on:cancel={() => showConfirm = false}
/>

<ConfirmModal
  show={showDeleteRelicsConfirm && !!confirmUserToDelete}
  title="Delete Relics Too?"
  message="Also delete their {confirmUserToDelete?.relic_count} relic(s)?"
  confirmLabel="Delete relics too"
  cancelLabel="Keep relics (become anonymous)"
  on:confirm={() => performDeleteUser(true)}
  on:cancel={() => performDeleteUser(false)}
/>

{#if restoreModalOpen && restoreTarget}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div
        class="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4"
        on:click={closeRestoreModal}
    >
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div
            class="bg-white rounded-lg shadow-xl w-full {restoreLogs !== null ? 'max-w-4xl' : 'max-w-md'}"
            on:click|stopPropagation
        >
            {#if restoreLogs !== null}
                <!-- Log view: shown after restore completes -->
                <div class="px-6 py-4 border-b border-gray-200 bg-gray-50 rounded-t-lg flex items-center gap-3">
                    {#if restoreLogs.stderr && !restoreLogs.stdout}
                        <i class="fas fa-times-circle text-red-600 text-xl"></i>
                        <h2 class="text-lg font-semibold text-gray-900">Restore Failed</h2>
                    {:else}
                        <i class="fas fa-check-circle text-green-600 text-xl"></i>
                        <h2 class="text-lg font-semibold text-gray-900">Restore Complete</h2>
                    {/if}
                </div>
                <div class="px-6 py-4 space-y-3">
                    {#if restoreLogs.log}
                        <div>
                            <p class="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Process Log</p>
                            <pre class="bg-gray-900 text-cyan-300 text-xs rounded p-3 overflow-auto max-h-40 whitespace-pre-wrap">{restoreLogs.log}</pre>
                        </div>
                    {/if}
                    {#if restoreLogs.stdout}
                        <div>
                            <p class="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">psql Output</p>
                            <pre class="bg-gray-900 text-green-400 text-xs rounded p-3 overflow-auto max-h-48 whitespace-pre-wrap break-all">{restoreLogs.stdout}</pre>
                        </div>
                    {/if}
                    {#if restoreLogs.stderr}
                        <div>
                            <p class="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Errors / Warnings</p>
                            <pre class="bg-gray-900 text-yellow-300 text-xs rounded p-3 overflow-auto max-h-48 whitespace-pre-wrap break-all">{restoreLogs.stderr}</pre>
                        </div>
                    {/if}
                    {#if !restoreLogs.log && !restoreLogs.stdout && !restoreLogs.stderr}
                        <p class="text-sm text-gray-500 italic">No output.</p>
                    {/if}
                </div>
                <div class="px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-lg flex justify-between items-center">
                    <div class="flex items-center gap-2">
                        <button
                            type="button"
                            on:click={() => copyToClipboard(buildFullLog(), 'Logs copied to clipboard')}
                            class="px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-1.5"
                            title="Copy all logs to clipboard"
                        >
                            <i class="fas fa-copy text-xs"></i>Copy
                        </button>
                        <button
                            type="button"
                            on:click={downloadRestoreLogs}
                            class="px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-1.5"
                            title="Download logs as .txt"
                        >
                            <i class="fas fa-download text-xs"></i>Download
                        </button>
                        <button
                            type="button"
                            on:click={saveRestoreLogsAsRelic}
                            class="px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-1.5"
                            title="Save logs as a restricted relic"
                        >
                            <i class="fas fa-lock text-xs"></i>Save as relic
                        </button>
                    </div>
                    <button
                        type="button"
                        on:click={closeRestoreModal}
                        class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                        Close
                    </button>
                </div>
            {:else}
                <!-- Confirmation view -->
                <div class="px-6 py-4 border-b border-red-200 bg-red-50 rounded-t-lg flex items-center gap-3">
                    <i class="fas fa-exclamation-triangle text-red-600 text-xl"></i>
                    <h2 class="text-lg font-semibold text-red-900">Restore Database</h2>
                </div>

                <div class="px-6 py-5 space-y-4">
                    <div class="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">
                        <p class="font-semibold mb-1">This action is irreversible.</p>
                        <p>All current data will be permanently replaced with the contents of this backup.</p>
                    </div>

                    <div class="bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm">
                        <p class="text-gray-500 text-xs uppercase tracking-wider mb-2">
                            {restoreTarget.source === 'upload' ? 'File to restore' : 'Backup to restore'}
                        </p>
                        <p class="font-mono text-gray-900 break-all">{restoreTarget.filename}</p>
                        <p class="text-gray-500 text-xs mt-1">
                            {#if restoreTarget.source === 'upload'}
                                Local upload &bull; {formatBytes(restoreTarget.size_bytes)}
                            {:else}
                                {formatDate(restoreTarget.timestamp)} &bull; {formatBytes(restoreTarget.size_bytes)}
                            {/if}
                        </p>
                    </div>

                    <p class="text-sm text-gray-600">
                        Active database connections will be terminated. The service will remain up
                        and new connections will reflect the restored state immediately.
                    </p>
                </div>

                <div class="px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-lg flex justify-end gap-3">
                    <button
                        type="button"
                        on:click={closeRestoreModal}
                        disabled={restoreInProgress}
                        class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        on:click={confirmRestore}
                        disabled={restoreInProgress}
                        class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
                    >
                        {#if restoreInProgress}
                            <i class="fas fa-spinner fa-spin"></i>Restoring...
                        {:else}
                            <i class="fas fa-undo"></i>Restore Database
                        {/if}
                    </button>
                </div>
            {/if}
        </div>
    </div>
{/if}


<style>
    .sort-arrow {
        font-size: 9px;
        transition: all 0.2s ease;
    }

    .sort-arrow.desc {
        transform: rotate(180deg);
    }
</style>
