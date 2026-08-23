<script>
    import { onMount } from "svelte";
    import { showToast } from "../stores/toastStore";
    import ConfirmModal from "./ConfirmModal.svelte";
    import {
        getAdminSettings,
        updateAdminSettings,
        resetAdminSettings,
        applyAdminPreset,
    } from "../services/api";
    import { formatBytes } from "../services/typeUtils";

    let sections = [];
    let presets = [];
    let loading = true;
    let saving = false;
    let activeSection = null;

    // Edited values keyed by setting name. Compared against `original` to
    // decide what to send, so an untouched field is never written.
    let edited = {};
    let original = {};

    let showConfirm = false;
    let confirmTitle = "";
    let confirmMessage = "";
    let confirmAction = null;

    const SECTION_ICONS = {
        features: "fa-toggle-on",
        uploads: "fa-upload",
        quotas: "fa-user-shield",
        rate_limits: "fa-tachometer-alt",
        retention: "fa-clock",
        content_safety: "fa-shield-alt",
        api: "fa-code",
    };

    // Short labels keep the tab bar compact; the full label stays in the tooltip.
    const SECTION_SHORT_LABELS = {
        features: "Features",
        uploads: "Uploads",
        quotas: "Quotas",
        rate_limits: "Rate Limits",
        retention: "Retention",
        content_safety: "Safety",
        api: "API",
    };

    const SECTION_DESCRIPTIONS = {
        features: "Instance-wide feature switches and availability modes.",
        uploads: "What can be uploaded, and how large it can be.",
        quotas: "Default per-user ceilings. Individual users can be overridden from the Users tab.",
        rate_limits: "Throttle request volume, keyed by user key or client IP.",
        retention: "How long relics are allowed to live.",
        content_safety: "How user-supplied content is rendered and constrained.",
        api: "Bounds on how much a single API response may contain.",
    };

    // Settings whose values are best picked from a curated list rather than
    // typed freehand. A value outside the list is still shown as an option.
    const EXPIRY_OPTIONS = ["never", "1h", "24h", "7d", "30d", "1y"];
    const SELECT_OPTIONS = {
        max_expiry: EXPIRY_OPTIONS,
        default_expiry: EXPIRY_OPTIONS,
    };

    const UNIT_SUFFIXES = {
        per_minute: "/ min",
        per_hour: "/ hr",
        bytes: "bytes",
        tags: "tags",
        characters: "chars",
        relics: "relics",
        relics_per_day: "/ day",
        comments_per_day: "/ day",
        items: "items",
        nodes: "nodes",
    };

    // Inputs match the Config tab: gray-300 border, rounded, mono values.
    const INPUT_CLASS =
        "px-3 py-1.5 text-sm bg-white border border-gray-300 rounded font-mono focus:border-[#E95420] focus:outline-none focus:ring-1 focus:ring-[#E95420] transition-colors";

    $: dirtyKeys = Object.keys(edited).filter(
        (key) => JSON.stringify(edited[key]) !== JSON.stringify(original[key]),
    );

    $: active = sections.find((s) => s.section === activeSection) || null;

    // Number of unsaved settings per section, for the tab badges.
    $: dirtyBySection = sections.reduce((acc, section) => {
        acc[section.section] = section.settings.filter((s) =>
            dirtyKeys.includes(s.key),
        ).length;
        return acc;
    }, {});

    // Number of customized (non-default) settings per section, for the header.
    $: overriddenBySection = sections.reduce((acc, section) => {
        acc[section.section] = section.settings.filter(
            (s) => s.overridden,
        ).length;
        return acc;
    }, {});

    function optionsFor(setting) {
        const base = SELECT_OPTIONS[setting.key];
        if (!base) return null;
        return base.includes(edited[setting.key])
            ? base
            : [...base, edited[setting.key]];
    }

    // Compact rendering of a setting's built-in default, for reference.
    function formatDefault(setting) {
        const value = setting.default;
        if (setting.type === "bool") return value ? "on" : "off";
        if (setting.type === "list")
            return value.length ? value.join(", ") : "empty";
        if (setting.unit === "bytes")
            return value ? formatBytes(value) : "unlimited";
        return String(value);
    }

    function formatBytesValue(value) {
        const num = Number(value);
        return num ? formatBytes(num) : "unlimited";
    }

    async function load() {
        loading = true;
        try {
            const { data } = await getAdminSettings();
            sections = data.sections;
            presets = data.presets;
            if (!activeSection && sections.length) {
                activeSection = sections[0].section;
            }
            edited = {};
            original = {};
            for (const section of sections) {
                for (const setting of section.settings) {
                    // Lists are edited as comma-separated text
                    const value =
                        setting.type === "list"
                            ? setting.value.join(", ")
                            : setting.value;
                    edited[setting.key] = value;
                    original[setting.key] = value;
                }
            }
        } catch (error) {
            showToast(
                error.response?.data?.detail || "Failed to load settings",
                "error",
            );
        } finally {
            loading = false;
        }
    }

    function toPayloadValue(key, value) {
        const setting = findSetting(key);
        if (setting.type === "list") {
            return value
                .split(",")
                .map((item) => item.trim())
                .filter(Boolean);
        }
        if (setting.type === "int") return Number(value);
        return value;
    }

    function findSetting(key) {
        for (const section of sections) {
            const match = section.settings.find((s) => s.key === key);
            if (match) return match;
        }
        return null;
    }

    async function save() {
        if (!dirtyKeys.length) return;
        saving = true;
        try {
            const payload = {};
            for (const key of dirtyKeys) {
                payload[key] = toPayloadValue(key, edited[key]);
            }
            await updateAdminSettings(payload);
            showToast(`Updated ${dirtyKeys.length} setting(s)`, "success");
            await load();
        } catch (error) {
            showToast(
                error.response?.data?.detail || "Failed to save settings",
                "error",
            );
        } finally {
            saving = false;
        }
    }

    function discard() {
        edited = { ...original };
    }

    function confirmReset(section) {
        confirmTitle = section ? `Reset ${section}?` : "Reset all settings?";
        confirmMessage = section
            ? `Every setting in "${section}" returns to its built-in default.`
            : "Every setting returns to its built-in default. Per-user quota overrides are not affected.";
        confirmAction = () => doReset(section);
        showConfirm = true;
    }

    async function doReset(section) {
        try {
            await resetAdminSettings(section);
            showToast("Settings reset to defaults", "success");
            await load();
        } catch (error) {
            showToast(
                error.response?.data?.detail || "Failed to reset settings",
                "error",
            );
        }
    }

    function confirmPreset(name) {
        confirmTitle = `Apply the "${name}" preset?`;
        confirmMessage =
            name === "hardened"
                ? "Applies tight quotas, forced expiry, required authentication, and disables HTML/SVG rendering. This replaces all current overrides."
                : "Replaces all current overrides with the built-in defaults.";
        confirmAction = () => doPreset(name);
        showConfirm = true;
    }

    async function doPreset(name) {
        try {
            await applyAdminPreset(name);
            showToast(`Applied "${name}" preset`, "success");
            await load();
        } catch (error) {
            showToast(
                error.response?.data?.detail || "Failed to apply preset",
                "error",
            );
        }
    }

    function isDirty(key, value) {
        return JSON.stringify(value) !== JSON.stringify(original[key]);
    }

    // Boolean rows are clickable anywhere, not just on the switch.
    function handleRowClick(event, setting) {
        if (setting.type !== "bool") return;
        if (event.target.closest("button, input, select, a")) return;
        edited[setting.key] = !edited[setting.key];
    }

    onMount(load);
</script>

<div class="p-6 space-y-5">
    <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
            <h2 class="text-lg font-semibold text-gray-900">Limits & Policy</h2>
            <p class="text-sm text-gray-500 mt-0.5">
                Changes take effect within a few seconds. Admin access is never
                restricted by these settings.
            </p>
        </div>
        <div class="flex items-center gap-2">
            <span
                class="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mr-1"
                >Presets</span
            >
            {#each presets as preset}
                <button
                    on:click={() => confirmPreset(preset)}
                    class="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50 transition-colors capitalize text-gray-700"
                    title="Apply the {preset} preset"
                >
                    <i
                        class="fas {preset === 'hardened'
                            ? 'fa-shield-alt'
                            : 'fa-undo'} text-gray-400 mr-1.5"
                    ></i>{preset}
                </button>
            {/each}
            <span class="w-px h-5 bg-gray-300 mx-1"></span>
            <button
                on:click={() => confirmReset(null)}
                class="px-3 py-1.5 text-sm border border-gray-300 rounded transition-colors text-gray-700 hover:text-red-600 hover:border-red-200 hover:bg-red-50"
                title="Reset every setting to its built-in default"
            >
                <i class="fas fa-undo mr-1.5"></i>Reset all
            </button>
        </div>
    </div>

    {#if loading}
        <div class="p-8 text-center">
            <i class="fas fa-spinner fa-spin text-[#772953] text-2xl"></i>
        </div>
    {:else}
        {#if dirtyKeys.length}
            <div
                class="sticky top-3 z-10 flex items-center justify-between gap-3 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg shadow-sm"
            >
                <span class="text-sm text-amber-900">
                    <i class="fas fa-exclamation-circle mr-1.5"></i>
                    {dirtyKeys.length} unsaved change{dirtyKeys.length === 1
                        ? ""
                        : "s"}
                </span>
                <div class="flex gap-2">
                    <button on:click={discard} class="maas-btn-secondary">
                        Discard
                    </button>
                    <button
                        on:click={save}
                        disabled={saving}
                        class="maas-btn-primary disabled:opacity-50"
                    >
                        {#if saving}<i class="fas fa-spinner fa-spin mr-1"></i
                            >{/if}Save changes
                    </button>
                </div>
            </div>
        {/if}

        <!-- Section tabs -->
        <div class="flex flex-wrap gap-1 border-b border-gray-200">
            {#each sections as section}
                <button
                    on:click={() => (activeSection = section.section)}
                    title={section.label}
                    class="px-3 pb-2 text-[13px] font-medium border-b-2 -mb-px transition-colors {activeSection ===
                    section.section
                        ? 'border-[#E95420] text-[#E95420]'
                        : 'border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300'}"
                >
                    <i
                        class="fas {SECTION_ICONS[section.section] ||
                            'fa-cog'} mr-1.5"
                    ></i>{SECTION_SHORT_LABELS[section.section] ||
                        section.label}
                    {#if dirtyBySection[section.section]}
                        <span
                            class="ml-1.5 px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800 align-middle"
                        >
                            {dirtyBySection[section.section]}
                        </span>
                    {/if}
                </button>
            {/each}
        </div>

        {#if active}
            <div>
                <div class="flex items-center justify-between mb-3">
                    <h3
                        class="text-sm font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-2"
                    >
                        <i
                            class="fas {SECTION_ICONS[active.section] ||
                                'fa-cog'} text-gray-400"
                        ></i>
                        {active.label}
                        <span
                            class="text-xs font-normal text-gray-400 normal-case"
                        >
                            ({active.settings.length} settings{overriddenBySection[
                                active.section
                            ]
                                ? ` · ${overriddenBySection[active.section]} customized`
                                : ""})
                        </span>
                    </h3>
                    <button
                        on:click={() => confirmReset(active.section)}
                        class="text-xs text-gray-500 hover:text-gray-700 transition-colors"
                    >
                        <i class="fas fa-undo mr-1"></i>Reset section
                    </button>
                </div>

                <div
                    class="bg-gray-50 rounded-lg border border-gray-200 divide-y divide-gray-200 overflow-hidden"
                >
                    {#each active.settings as setting}
                        <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
                        <div
                            on:click={(e) => handleRowClick(e, setting)}
                            class="px-4 py-3 flex items-center justify-between gap-6 transition-colors {setting.type ===
                            'bool'
                                ? 'cursor-pointer hover:bg-gray-100/80'
                                : 'hover:bg-gray-100/50'}"
                        >
                            <div class="min-w-0 flex-1">
                                <div class="flex items-center gap-2">
                                    <span
                                        class="text-sm font-medium text-gray-900"
                                        >{setting.label}</span
                                    >
                                    {#if setting.overridden}
                                        <span
                                            class="px-1.5 py-px rounded-full text-[10px] font-medium bg-blue-50 text-blue-600 border border-blue-100"
                                            title="Changed from the built-in default"
                                        >
                                            custom
                                        </span>
                                    {/if}
                                    {#if isDirty(setting.key, edited[setting.key])}
                                        <span
                                            class="px-1.5 py-px rounded-full text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200"
                                        >
                                            unsaved
                                        </span>
                                    {/if}
                                </div>
                                <p class="text-xs text-gray-500 mt-0.5">
                                    {setting.help}
                                </p>
                                {#if setting.overridden || setting.unit === "bytes"}
                                    <p
                                        class="text-[11px] text-gray-400 mt-0.5 font-mono truncate"
                                    >
                                        {#if setting.overridden}
                                            Default: {formatDefault(
                                                setting,
                                            )}{/if}
                                        {#if setting.unit === "bytes"}
                                            {#if setting.overridden}
                                                ·
                                            {/if}= {formatBytesValue(
                                                edited[setting.key],
                                            )}
                                        {/if}
                                    </p>
                                {/if}
                            </div>

                            <div class="shrink-0 flex justify-end">
                                {#if setting.type === "bool"}
                                    <button
                                        type="button"
                                        role="switch"
                                        aria-checked={!!edited[setting.key]}
                                        aria-label={setting.label}
                                        on:click={() =>
                                            (edited[setting.key] =
                                                !edited[setting.key])}
                                        class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E95420]/40 {edited[
                                            setting.key
                                        ]
                                            ? 'bg-[#E95420]'
                                            : 'bg-gray-300'}"
                                    >
                                        <span
                                            class="inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform {edited[
                                                setting.key
                                            ]
                                                ? 'translate-x-[22px]'
                                                : 'translate-x-[2px]'}"
                                        ></span>
                                    </button>
                                {:else if optionsFor(setting)}
                                    <select
                                        bind:value={edited[setting.key]}
                                        aria-label={setting.label}
                                        class="{INPUT_CLASS} w-48"
                                    >
                                        {#each optionsFor(setting) as option}
                                            <option value={option}
                                                >{option}</option
                                            >
                                        {/each}
                                    </select>
                                {:else if setting.type === "int"}
                                    <div class="flex items-center gap-1.5">
                                        <input
                                            type="number"
                                            min={setting.min ?? undefined}
                                            max={setting.max ?? undefined}
                                            bind:value={edited[setting.key]}
                                            aria-label={setting.label}
                                            class="{INPUT_CLASS} w-36"
                                        />
                                        {#if UNIT_SUFFIXES[setting.unit]}
                                            <span
                                                class="text-xs text-gray-400 whitespace-nowrap"
                                                >{UNIT_SUFFIXES[
                                                    setting.unit
                                                ]}</span
                                            >
                                        {/if}
                                    </div>
                                {:else}
                                    <input
                                        type="text"
                                        bind:value={edited[setting.key]}
                                        aria-label={setting.label}
                                        placeholder={setting.type === "list"
                                            ? "comma separated"
                                            : ""}
                                        class="{INPUT_CLASS} w-96 max-w-[40vw]"
                                    />
                                {/if}
                            </div>
                        </div>
                    {/each}
                </div>

                {#if SECTION_DESCRIPTIONS[active.section]}
                    <p class="text-xs text-gray-400 mt-2">
                        {SECTION_DESCRIPTIONS[active.section]}
                    </p>
                {/if}
            </div>
        {/if}
    {/if}
</div>

<ConfirmModal
    show={showConfirm}
    title={confirmTitle}
    message={confirmMessage}
    confirmLabel="Apply"
    on:confirm={() => {
        showConfirm = false;
        if (confirmAction) confirmAction();
    }}
    on:cancel={() => (showConfirm = false)}
/>
