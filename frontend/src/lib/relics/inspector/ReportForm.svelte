<script>
  // Report a relic to the admins, inline in the inspector's More section.
  import { submitReport } from "../../../services/api";
  import { showToast } from "../../../stores/toastStore";

  let { relicId, ondone } = $props();

  let reason = $state("");
  let sending = $state(false);

  async function send(event) {
    event.preventDefault();
    if (!reason.trim() || sending) return;
    sending = true;
    try {
      await submitReport(relicId, reason.trim());
      showToast("Reported. An admin will take a look.", "success");
      ondone?.();
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t send the report", "error");
    } finally {
      sending = false;
    }
  }
</script>

<form class="report" onsubmit={send}>
  <label class="r-field">
    <span class="r-label">What’s wrong with it?</span>
    <!-- svelte-ignore a11y_autofocus -->
    <span class="r-input"><textarea rows="3" bind:value={reason} placeholder="Spam, malware, personal data, something illegal…" autofocus></textarea></span>
  </label>
  <div class="r-confirm-actions">
    <button type="button" class="r-btn r-btn-secondary r-btn-sm" onclick={ondone}>Cancel</button>
    <button class="r-btn r-btn-danger r-btn-sm" disabled={!reason.trim() || sending}>{sending ? "Sending…" : "Send report"}</button>
  </div>
</form>

<style>
  .report {
    display: grid;
    gap: var(--space-2);
    margin-top: var(--space-2\.5);
  }
  .report textarea {
    resize: vertical;
  }
</style>
