<script>
  // Admin · Config: the administrators (add by public ID, remove runtime admins) and the server's
  // settings as its environment set them, read-only. Two views of one list, like Jobs; the
  // inspector shows the selected admin or setting, and holds the Add admin form.
  import Icon from "../ui/Icon.svelte";
  import DataList from "../ui/DataList.svelte";
  import PageBar from "../shell/PageBar.svelte";
  import Workbench from "../shell/Workbench.svelte";
  import ConfigInspector from "./ConfigInspector.svelte";
  import { InspectorPanel } from "../shell/inspectorPanel.svelte.js";
  import { layout } from "../shell/layout";
  import { refreshAdminStats } from "./adminState";
  import { CONFIG_SECTIONS, configRows, settingValue } from "./config";
  import { getAdmins, getAdminConfig } from "../../services/api";
  import { copyToClipboard } from "../../services/relicActions";

  const ADMIN_COLUMNS = [
    { key: "name", label: "Name", width: "minmax(0, 1fr)" },
    { key: "public_id", label: "Public ID", width: "minmax(0, 200px)", mono: true, hide: "phone" },
    { key: "role", label: "Role", width: "110px" },
    { key: "source", label: "Granted by", width: "150px", hide: "narrow" },
  ];
  const SETTING_COLUMNS = [
    { key: "key", label: "Setting", width: "minmax(0, 260px)", mono: true },
    { key: "section", label: "Section", width: "90px", hide: "phone" },
    { key: "value", label: "Value", width: "minmax(0, 1fr)" },
  ];

  const panel = new InspectorPanel();
  let view = $state("admins"); // "admins" | "settings"
  let section = $state(""); // settings filter
  let admins = $state.raw([]);
  let config = $state.raw(null);
  let loading = $state(true);
  let error = $state(false);
  let mode = $state("view"); // "view" | "add"
  let selectedAdmin = $state(null);
  let selectedSetting = $state(null);
  let confirm = $state(null);

  async function load() {
    loading = true;
    const [a, c] = await Promise.allSettled([getAdmins(), getAdminConfig()]);
    // An admin's row key: their public ID, or a placeholder for a super admin who hasn't
    // registered (their user ID is their secret key, so it stays out of the page).
    if (a.status === "fulfilled") admins = (a.value.data.admins || []).map((x, i) => ({ ...x, key: x.public_id || `unregistered-${i}` }));
    if (c.status === "fulfilled") config = c.value.data;
    error = a.status === "rejected" || c.status === "rejected";
    loading = false;
  }
  load();

  const settings = $derived(configRows(config));
  const shownSettings = $derived(section ? settings.filter((s) => s.section === section) : settings);
  const admin = $derived(admins.find((a) => a.key === selectedAdmin) ?? null);
  const setting = $derived(settings.find((s) => s.key === selectedSetting) ?? null);

  $effect(() => {
    if (!$layout.dock || mode === "add") return;
    if (view === "admins" && admins.length && !admin) selectedAdmin = admins[0].key;
    if (view === "settings" && shownSettings.length && !shownSettings.some((s) => s.key === selectedSetting)) selectedSetting = shownSettings[0].key;
  });

  function show(next) {
    view = next;
    mode = "view";
  }

  function selectAdmin(a) {
    selectedAdmin = a.key;
    mode = "view";
    confirm = null;
    if (!$layout.dock) panel.show(false);
  }

  function selectSetting(s) {
    selectedSetting = s.key;
    mode = "view";
    if (!$layout.dock) panel.show(false);
  }

  function startAdd() {
    view = "admins";
    mode = "add";
    panel.show($layout.dock);
  }

  async function onAdded(publicId) {
    mode = "view";
    await load();
    selectedAdmin = publicId;
    refreshAdminStats();
  }

  async function onRemoved() {
    selectedAdmin = null;
    await load();
    refreshAdminStats();
  }

  function askRemove(a) {
    selectAdmin(a);
    panel.show($layout.dock);
    confirm = { n: (confirm?.n ?? 0) + 1 };
  }

  const adminActions = [
    { icon: "copy", title: "Copy public ID", run: (a) => copyToClipboard(a.public_id, "Public ID copied"), when: (a) => !!a.public_id },
    { icon: "x", title: "Remove admin", run: askRemove, when: (a) => !a.is_super_admin },
  ];
  const settingActions = [{ icon: "copy", title: "Copy value", run: (s) => copyToClipboard(settingValue(s.value), "Value copied") }];

  function onKeydown(event) {
    if (event.key === "n") {
      event.preventDefault();
      startAdd();
    }
  }
</script>

<Workbench
  {panel}
  hasSelection={mode === "add" || (view === "admins" ? !!admin : !!setting)}
  label="Config"
  phoneDrawer
  onkeydown={onKeydown}
>
  {#snippet pagebar({ inspectorOpen, toggleInspector })}
    <PageBar title="Config" {inspectorOpen} ontoggleinspector={toggleInspector}>
      {#snippet filters()}
        <nav class="r-facets" aria-label="View">
          <a href="/admin/config" aria-current={view === "admins" ? "true" : undefined} onclick={(e) => (e.preventDefault(), show("admins"))}>Administrators <em>{admins.length}</em></a>
          <a href="/admin/config" aria-current={view === "settings" ? "true" : undefined} onclick={(e) => (e.preventDefault(), show("settings"))}>Server settings <em>{settings.length}</em></a>
        </nav>
        {#if view === "settings"}
          <span class="r-pagebar-sep"></span>
          <label class="r-pagebar-opt">Section
            <select bind:value={section}>
              <option value="">All</option>
              {#each Object.entries(CONFIG_SECTIONS) as [key, label] (key)}
                {#if settings.some((s) => s.section === key)}<option value={key}>{label}</option>{/if}
              {/each}
            </select>
          </label>
        {/if}
      {/snippet}
      {#snippet actions()}
        {#if view === "admins"}
          <button class="r-btn r-btn-secondary r-btn-md" onclick={startAdd} title="Add admin (n)"><Icon name="plus" />Add admin</button>
        {/if}
        <button class="r-btn r-btn-ghost r-btn-icon" onclick={load} disabled={loading} title="Refresh" aria-label="Refresh"><Icon name="history" /></button>
      {/snippet}
    </PageBar>
  {/snippet}

  {#if view === "admins"}
    <DataList
      label="Administrators"
      rows={admins}
      rowId={(a) => a.key}
      columns={ADMIN_COLUMNS}
      loading={loading && !admins.length}
      selectedId={mode === "add" ? null : selectedAdmin}
      actions={adminActions}
      emptyText={error ? "Couldn’t load the administrators." : "No administrators."}
      emptyAction={error ? { label: "Retry", run: load } : null}
      onselect={selectAdmin}
    >
      {#snippet cell(a, c)}
        {#if c.key === "name"}
          <span class="cell-text" class:is-unnamed={!a.name}>{a.name || "—"}</span>
        {:else if c.key === "public_id"}
          {a.public_id || "not registered"}
        {:else if c.key === "role"}
          <span class="r-pill r-pill-accent role"><Icon name="shield" />{a.is_super_admin ? "super admin" : "admin"}</span>
        {:else if c.key === "source"}
          <span class="muted">{a.is_super_admin ? "ADMIN_USER_IDS" : "an admin, here"}</span>
        {/if}
      {/snippet}
    </DataList>
  {:else}
    <DataList
      label="Server settings"
      rows={shownSettings}
      rowId={(s) => s.key}
      columns={SETTING_COLUMNS}
      loading={loading && !settings.length}
      selectedId={selectedSetting}
      actions={settingActions}
      emptyText={error ? "Couldn’t load the configuration." : "No settings."}
      emptyAction={error ? { label: "Retry", run: load } : null}
      onselect={selectSetting}
    >
      {#snippet cell(s, c)}
        {#if c.key === "key"}
          {s.key}
        {:else if c.key === "section"}
          <span class="muted">{s.sectionLabel}</span>
        {:else if c.key === "value"}
          {#if typeof s.value === "boolean"}<span class="r-pill role" class:r-pill-accent={s.value}>{s.value ? "on" : "off"}</span>
          {:else}<span class="cell-text value" title={settingValue(s.value)}>{settingValue(s.value)}</span>{/if}
        {/if}
      {/snippet}
    </DataList>
  {/if}

  {#snippet inspector({ close })}
    <ConfigInspector
      {mode}
      admin={view === "admins" ? admin : null}
      setting={view === "settings" && mode !== "add" ? setting : null}
      {confirm}
      onadded={onAdded}
      onremoved={onRemoved}
      oncanceladd={() => (mode = "view")}
      onclose={close}
    />
  {/snippet}

  {#snippet status()}
    <span><Icon name="shield" />{admins.length} {admins.length === 1 ? "admin" : "admins"}</span>
    <span>{settings.length} settings, read-only</span>
    {#if error}<span class="status-error">Couldn’t load. <button class="r-link" onclick={load}>Retry</button></span>{/if}
    <span class="r-gap"></span>
    <span class="r-hints">{#if view === "admins"}<span><kbd class="r-kbd">n</kbd>add admin</span>{/if}<span><kbd class="r-kbd">]</kbd>inspector</span></span>
  {/snippet}
</Workbench>

<style>
  .cell-text {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .is-unnamed {
    color: var(--ink-3);
  }
  .value {
    color: var(--ink-2);
    font: 12.5px var(--font-mono);
  }
  .muted {
    color: var(--ink-3);
    font-size: 12.5px;
  }
  .role {
    height: 18px;
    font-size: 11.5px;
  }
</style>
