<script>
  // A user in the admin inspector: who they are, their relics, their private key (hidden until
  // shown), admin rights, and Delete with its question about their relics asked inline.
  import Icon from "../ui/Icon.svelte";
  import AdminInspector from "./AdminInspector.svelte";
  import InsSection from "../relics/inspector/InsSection.svelte";
  import { deleteUser, grantAdmin, revokeAdmin } from "../../services/api";
  import { copyToClipboard } from "../../services/relicActions";
  import { showToast } from "../../stores/toastStore";
  import { fullDate } from "../relics/format";

  let {
    user = null,
    confirm = null, // { n } from the list's Delete action: open the confirmation
    onrelics, // (user) show their relics
    onchanged, // (user) after a role change
    ondeleted, // (user)
    onclose = null,
  } = $props();

  let showKey = $state(false);
  let confirming = $state(false);
  let busy = $state(false);

  // A different user starts with the key hidden and no confirmation open.
  $effect(() => {
    user?.id;
    showKey = false;
    confirming = false;
  });
  $effect(() => {
    if (confirm && user && !user.is_admin) {
      confirm.n;
      confirming = true;
    }
  });

  const role = $derived(user?.is_super_admin ? "Super admin" : user?.is_admin ? "Admin" : "User");

  async function toggleAdmin() {
    busy = true;
    try {
      if (user.is_admin) await revokeAdmin(user.id);
      else await grantAdmin(user.id);
      showToast(user.is_admin ? "Admin rights removed" : "Admin rights granted", "success");
      onchanged?.({ ...user, is_admin: !user.is_admin });
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t change admin rights", "error");
    } finally {
      busy = false;
    }
  }

  async function remove(deleteRelics) {
    busy = true;
    try {
      await deleteUser(user.id, deleteRelics);
      showToast(deleteRelics ? "User and their relics deleted" : "User deleted, their relics kept", "success");
      ondeleted?.(user);
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t delete the user", "error");
    } finally {
      busy = false;
      confirming = false;
    }
  }
</script>

<AdminInspector
  label="User details"
  icon="user"
  title={user ? user.name || user.public_id || "—" : null}
  titleClass={user && !user.name ? "is-unnamed" : ""}
  copyId={user?.public_id ? { text: user.public_id, label: "public ID" } : null}
  emptyText="Select a user to see their details."
  {onclose}
>
  {#snippet actions()}
    <button class="r-btn r-btn-primary r-btn-md" onclick={() => onrelics?.(user)}><Icon name="file" />View relics</button>
    {#if !user.is_super_admin}
      <button class="r-btn r-btn-secondary r-btn-md" onclick={toggleAdmin} disabled={busy}>
        <Icon name="shield" />{user.is_admin ? "Remove admin" : "Make admin"}
      </button>
    {/if}
  {/snippet}
  {#snippet meta()}
    <span class="r-pill" class:r-pill-accent={user.is_admin}>{#if user.is_admin}<Icon name="shield" />{/if}{role}</span>
    <span>{user.relic_count.toLocaleString("en-US")} {user.relic_count === 1 ? "relic" : "relics"}</span>
  {/snippet}

  <InsSection id="admin-user-details" title="Details" defaultOpen>
    <dl class="r-kv">
      <dt>Name</dt><dd>{user.name || "Not set"}</dd>
      <dt>Public ID</dt><dd class="r-mono">{user.public_id || "Not set"}</dd>
      <dt>Role</dt><dd title={user.is_super_admin ? "Set with ADMIN_USER_IDS; can’t be removed here" : ""}>{role}</dd>
      <dt>Relics</dt><dd><button class="r-link" onclick={() => onrelics?.(user)}>{user.relic_count.toLocaleString("en-US")}</button></dd>
      <dt>Joined</dt><dd>{fullDate(user.created_at)}</dd>
    </dl>
    {#if user.is_super_admin}
      <p class="ins-note">Super admins are set with the <code>ADMIN_USER_IDS</code> variable and can’t be removed or deleted here.</p>
    {/if}
  </InsSection>

  <InsSection id="admin-user-key" title="Private key" aside="secret">
    <div class="ins-stack">
      <div class="ins-key">
        <span class="r-mono">{showKey ? user.id : "•".repeat(Math.min(user.id.length, 32))}</span>
        <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={() => (showKey = !showKey)} title={showKey ? "Hide key" : "Show key"} aria-label={showKey ? "Hide key" : "Show key"}>
          <Icon name={showKey ? "eyeoff" : "eye"} />
        </button>
        {#if showKey}
          <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={() => copyToClipboard(user.id, "Private key copied")} title="Copy key" aria-label="Copy key"><Icon name="copy" /></button>
        {/if}
      </div>
      <p class="ins-note">Whoever has this key is this user. Share it only with them.</p>
    </div>
  </InsSection>

  {#if !user.is_admin}
    <InsSection id="admin-user-more" focus={confirming ? { id: "admin-user-more", n: confirm?.n ?? 0 } : null} title="More" aside="delete">
      <div class="ins-stack">
        <button class="r-btn r-btn-danger-text r-btn-md ins-delete" onclick={() => (confirming = true)} disabled={confirming}><Icon name="trash" />Delete user</button>
        {#if confirming}
          <div class="r-confirm">
            <b>Delete {user.name ? `“${user.name}”` : "this user"}?</b>
            <span>
              Their bookmarks go, spaces they own pass to you and their comments stay without an author.
              {#if user.relic_count}They own {user.relic_count.toLocaleString("en-US")} {user.relic_count === 1 ? "relic" : "relics"}: delete {user.relic_count === 1 ? "it" : "those"} too, or keep {user.relic_count === 1 ? "it" : "them"} without an owner?{/if}
              This can’t be undone.
            </span>
            <div class="r-confirm-actions">
              <button class="r-btn r-btn-secondary r-btn-sm" onclick={() => (confirming = false)} disabled={busy}>Cancel</button>
              {#if user.relic_count}
                <button class="r-btn r-btn-secondary r-btn-sm" onclick={() => remove(false)} disabled={busy}>Keep relics</button>
                <button class="r-btn r-btn-danger r-btn-sm" onclick={() => remove(true)} disabled={busy}>{busy ? "Deleting…" : "Delete relics too"}</button>
              {:else}
                <button class="r-btn r-btn-danger r-btn-sm" onclick={() => remove(false)} disabled={busy}>{busy ? "Deleting…" : "Delete user"}</button>
              {/if}
            </div>
          </div>
        {/if}
      </div>
    </InsSection>
  {/if}
</AdminInspector>

<style>
  :global(.r-ins-name h2.is-unnamed) {
    color: var(--ink-2);
    font-family: var(--font-mono);
    font-size: 14px;
  }
  .r-kv .r-link {
    padding: 0;
    border: 0;
    background: none;
    font: inherit;
    cursor: pointer;
  }
  .ins-key {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    min-width: 0;
  }
  .ins-key .r-mono {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .ins-delete {
    justify-self: start;
  }
  code {
    font-family: var(--font-mono);
  }
</style>
