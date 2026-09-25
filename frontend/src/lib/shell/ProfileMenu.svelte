<script>
  // Profile: display name, public ID, key import. Opened from the navbar avatar.
  // Interim: the design moves this into the inspector's You mode once the inspector exists.
  import Icon from "../ui/Icon.svelte";
  import { session, saveDisplayName } from "../../stores/session";
  import { swSetKey } from "../../services/api";
  import { usingSw } from "../../services/api/auth";
  import { showToast } from "../../stores/toastStore";

  let { onclose } = $props();

  let name = $state($session.name);
  let saving = $state(false);

  async function saveName() {
    if (!name.trim() || saving) return;
    saving = true;
    try {
      await saveDisplayName(name.trim());
      showToast("Display name saved", "success");
    } catch (error) {
      console.error("Failed to update name:", error);
      showToast("Couldn’t save the display name", "error");
    } finally {
      saving = false;
    }
  }

  async function copyPublicId() {
    await navigator.clipboard.writeText($session.publicId);
    showToast("Public ID copied", "success");
    onclose();
  }

  function importKey(event) {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
      const userKey = e.target.result.trim();
      if (!/^[a-f0-9]{32}$/i.test(userKey)) {
        showToast("That file doesn’t hold a Relic key: expected 32 hexadecimal characters.", "error");
        return;
      }
      try {
        // Store the key in the service-worker vault (or localStorage in fallback mode).
        await swSetKey(userKey);
        const headers = { "Content-Type": "application/json" };
        if (!usingSw) headers["X-User-Key"] = userKey;
        const response = await fetch("/api/v1/user/register", { method: "POST", headers });
        const data = await response.json();
        if (data.message?.includes("successfully") || data.message?.includes("already registered")) {
          showToast("Key imported. Reloading…", "success");
          setTimeout(() => window.location.reload(), 1500);
        } else {
          showToast("Couldn’t import the key", "error");
        }
      } catch {
        showToast("Couldn’t import the key", "error");
      }
    };
    reader.readAsText(file);
    onclose();
  }
</script>

<div class="profile" id="profile-menu" role="region" aria-label="Profile">
  <div class="profile-sec">
    <label class="r-field">
      <span class="r-label">Display name</span>
      <span class="profile-row">
        <span class="r-input r-input-sm">
          <input
            bind:value={name}
            placeholder="Anonymous"
            onkeydown={(e) => e.key === "Enter" && saveName()}
          />
        </span>
        <button class="r-btn r-btn-primary r-btn-md" onclick={saveName} disabled={saving}>Save</button>
      </span>
      <span class="r-help">Shown on your comments. Required to comment.</span>
    </label>
  </div>

  <div class="profile-sec r-field">
    <span class="r-label">Your public ID</span>
    <span class="profile-row">
      <span class="profile-id">{$session.publicId || "…"}</span>
      <button class="r-btn r-btn-secondary r-btn-md r-btn-icon" onclick={copyPublicId} title="Copy public ID" aria-label="Copy public ID">
        <Icon name="copy" />
      </button>
    </span>
    <span class="r-help">Share it so people can add you to spaces and restricted relics.</span>
  </div>

  <div class="profile-sec">
    <label class="profile-action">
      <Icon name="upload" />
      <span>Import key from a file</span>
      <input type="file" accept=".txt" class="sr-only" onchange={importKey} />
    </label>
    <p class="r-help profile-note">
      <Icon name="shield" size={13} />
      {usingSw
        ? "Your key is stored securely in this browser and can’t be shown again. Import restores it from a backup."
        : "Your key is stored in this browser’s local storage. Import restores it on another device."}
    </p>
  </div>

  <div class="profile-foot">
    <span class="mono-meta">Relic {$session.version}</span>
    <a class="r-link" href="https://github.com/ovidiuvio/relic" target="_blank" rel="noopener noreferrer">GitHub</a>
    <a class="r-link" href="/docs" data-reload>API docs</a>
  </div>
</div>

<style>
  .profile {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    z-index: 50;
    width: 300px;
    background: var(--surface);
    color: var(--ink);
    border: 1px solid var(--line-2);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-popover);
    overflow: hidden;
  }
  .profile-sec {
    display: grid;
    gap: var(--space-1\.5);
    padding: var(--space-3) var(--space-3\.5);
    border-bottom: 1px solid var(--line);
  }
  .profile-row {
    display: flex;
    align-items: center;
    gap: var(--space-1\.5);
  }
  .profile-row .r-input {
    flex: 1;
  }
  .profile-id {
    flex: 1;
    font: 12.5px var(--font-mono);
    user-select: all;
    word-break: break-all;
  }
  .profile-action {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    height: var(--control-md);
    color: var(--ink-2);
    cursor: pointer;
  }
  .profile-action:focus-within {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
    border-radius: var(--radius-xs);
  }
  .profile-note {
    display: flex;
    gap: var(--space-1\.5);
    line-height: 1.4;
  }
  .profile-foot {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-2) var(--space-3\.5);
    background: var(--subtle);
    color: var(--ink-3);
  }
  .profile-foot .mono-meta {
    margin-right: auto;
  }
</style>
