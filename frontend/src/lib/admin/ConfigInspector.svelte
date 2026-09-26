<script>
  // The Config section's inspector: an administrator (details, Remove confirmed inline), the
  // Add admin form, or one server setting with its full value.
  import Icon from "../ui/Icon.svelte";
  import AdminInspector from "./AdminInspector.svelte";
  import InsSection from "../relics/inspector/InsSection.svelte";
  import { addAdmin, revokeAdmin } from "../../services/api";
  import { copyToClipboard } from "../../services/relicActions";
  import { showToast } from "../../stores/toastStore";
  import { settingValue } from "./config";

  let {
    mode = "view", // "view" | "add"
    admin = null,
    setting = null, // { key, section, sectionLabel, value }
    confirm = null, // { n } from the row's Remove
    onadded, // () after Add admin
    onremoved, // (admin)
    oncanceladd,
    onclose = null,
  } = $props();

  let publicId = $state("");
  let busy = $state(false);
  let confirming = $state(false);

  $effect(() => {
    admin?.key;
    confirming = false;
  });
  $effect(() => {
    if (!confirm || !admin || admin.is_super_admin) return;
    confirm.n;
    confirming = true;
  });

  async function add(event) {
    event.preventDefault();
    const id = publicId.trim();
    if (!id || busy) return;
    busy = true;
    try {
      await addAdmin(id);
      showToast("Admin added", "success");
      publicId = "";
      onadded?.(id);
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t add the admin", "error");
    } finally {
      busy = false;
    }
  }

  async function remove() {
    busy = true;
    try {
      await revokeAdmin(admin.user_id);
      showToast("Admin rights removed", "success");
      onremoved?.(admin);
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t remove the admin", "error");
    } finally {
      busy = false;
      confirming = false;
    }
  }

  const shown = $derived(setting ? settingValue(setting.value) : "");
</script>

{#if mode === "add"}
  <aside class="r-inspector" aria-label="Add admin">
    <form class="add" onsubmit={add}>
      <div class="r-ins-mode">
        <div>
          <h2>Add admin</h2>
          <p>Give someone the Admin area</p>
        </div>
        <button type="button" class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={oncanceladd} aria-label="Cancel"><Icon name="x" /></button>
      </div>
      <div class="r-ins-form">
        <label class="r-field">
          <span class="r-label">Public ID</span>
          <!-- svelte-ignore a11y_autofocus -->
          <span class="r-input"><input bind:value={publicId} placeholder="e.g. 2cac0130e76925fb" autocomplete="off" spellcheck="false" autofocus /></span>
          <span class="r-help">They find it in their profile menu. Admins can see and delete every relic, manage users and restore backups.</span>
        </label>
      </div>
      <div class="r-ins-save">
        <button type="button" class="r-btn r-btn-secondary" onclick={oncanceladd}>Cancel</button>
        <button class="r-btn r-btn-primary" disabled={!publicId.trim() || busy}>{busy ? "Adding…" : "Add admin"}</button>
      </div>
    </form>
  </aside>
{:else if setting}
  <AdminInspector label="Setting" icon="sliders" badgeClass="r-t-code" title={setting.key} titleClass="setting-title" {onclose}>
    {#snippet actions()}
      <button class="r-btn r-btn-primary r-btn-md" onclick={() => copyToClipboard(shown, "Value copied")}><Icon name="copy" />Copy value</button>
    {/snippet}
    {#snippet meta()}
      <span class="r-pill">{setting.sectionLabel}</span>
      {#if typeof setting.value === "boolean"}<span class="r-pill" class:r-pill-accent={setting.value}>{setting.value ? "on" : "off"}</span>{/if}
    {/snippet}
    <InsSection id="admin-setting-value" title="Value" aside={Array.isArray(setting.value) ? `${setting.value.length} ${setting.value.length === 1 ? "item" : "items"}` : ""} defaultOpen>
      {#if Array.isArray(setting.value) && setting.value.length}
        <ul class="values">{#each setting.value as v}<li class="r-mono">{v}</li>{/each}</ul>
      {:else}
        <p class="value r-mono">{shown}</p>
      {/if}
      <p class="ins-note">Set by the server’s environment. Change it there and restart the server.</p>
    </InsSection>
  </AdminInspector>
{:else}
  <AdminInspector
    label="Administrator"
    icon="shield"
    title={admin ? admin.name || admin.public_id || "—" : null}
    titleClass={admin && !admin.name ? "is-unnamed" : ""}
    copyId={admin?.public_id ? { text: admin.public_id, label: "public ID" } : null}
    emptyText="Select an administrator, or a setting."
    {onclose}
  >
    {#snippet actions()}
      {#if !admin.is_super_admin}
        <button class="r-btn r-btn-danger-text r-btn-md" onclick={() => (confirming = true)} disabled={confirming}><Icon name="x" />Remove admin</button>
      {/if}
    {/snippet}
    {#snippet meta()}
      <span class="r-pill r-pill-accent"><Icon name="shield" />{admin.is_super_admin ? "Super admin" : "Admin"}</span>
    {/snippet}

    {#if confirming}
      <div class="r-confirm ins-confirm">
        <b>Remove {admin.name ? `${admin.name}’s` : "their"} admin rights?</b>
        <span>They keep their account and relics, and lose the Admin area.</span>
        <div class="r-confirm-actions">
          <button class="r-btn r-btn-secondary r-btn-sm" onclick={() => (confirming = false)} disabled={busy}>Cancel</button>
          <button class="r-btn r-btn-danger r-btn-sm" onclick={remove} disabled={busy}>{busy ? "Removing…" : "Remove admin"}</button>
        </div>
      </div>
    {/if}

    <InsSection id="admin-admin-details" title="Details" defaultOpen>
      <dl class="r-kv">
        <dt>Name</dt><dd>{admin.name || "Not set"}</dd>
        <dt>Public ID</dt><dd class="r-mono">{admin.public_id || "Not registered yet"}</dd>
        <dt>Role</dt><dd>{admin.is_super_admin ? "Super admin" : "Admin"}</dd>
        <dt>Granted by</dt><dd>{admin.is_super_admin ? "ADMIN_USER_IDS" : "An admin, here"}</dd>
      </dl>
      {#if admin.is_super_admin}
        <p class="ins-note">Super admins come from the <code>ADMIN_USER_IDS</code> variable and can’t be removed here.{#if !admin.public_id} This one hasn’t used Relic yet.{/if}</p>
      {/if}
    </InsSection>
  </AdminInspector>
{/if}

<style>
  .add {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }
  .r-inspector {
    height: 100%;
  }
  .add input {
    font-family: var(--font-mono);
  }
  .ins-confirm {
    margin: var(--space-3) var(--space-4) 0;
  }
  :global(.r-ins-name h2.setting-title) {
    font-family: var(--font-mono);
    font-size: 14px;
    overflow-wrap: anywhere;
  }
  .value {
    margin: 0 0 var(--space-2);
    font-size: 12.5px;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
  }
  .values {
    display: grid;
    gap: 4px;
    margin: 0 0 var(--space-2);
    padding: 0;
    list-style: none;
    font-size: 12.5px;
    overflow-wrap: anywhere;
  }
  code {
    font-family: var(--font-mono);
  }
</style>
