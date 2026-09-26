<script>
  // Inspector mode "Edit details" for a relic you own: name, type, visibility, tags, expiry.
  // Replaces the old edit dialog. Ctrl+Enter saves, Esc cancels.
  import Icon from "../../ui/Icon.svelte";
  import Combobox from "../../ui/Combobox.svelte";
  import VisibilityField from "../fields/VisibilityField.svelte";
  import ExpiryField from "../fields/ExpiryField.svelte";
  import TagsField from "../fields/TagsField.svelte";
  import { updateRelic } from "../../../services/api";
  import { getAvailableSyntaxOptions, getFileTypeDefinition, getContentType } from "../../../services/typeUtils";
  import { showToast } from "../../../stores/toastStore";
  import { tagName, fullDate } from "../format";

  let { relic, onsaved, oncancel } = $props();

  const SYNTAXES = getAvailableSyntaxOptions();

  // The form starts from the relic as it is now; later changes to the prop don't reset it.
  const start = () => {
    const def = getFileTypeDefinition(relic.content_type);
    const hint = SYNTAXES.find((o) => o.value === relic.language_hint);
    return {
      name: relic.name || "",
      syntax: hint?.value ?? SYNTAXES.find((o) => o.value === def?.syntax)?.value ?? "auto",
      access: relic.access_level || "public",
      tags: (relic.tags ?? []).map(tagName),
      expiry: "keep",
    };
  };
  let form = $state(start());
  let saving = $state(false);
  let tagsField = $state();

  async function save() {
    if (saving) return;
    tagsField?.flush();
    saving = true;
    try {
      const updates = {
        name: form.name.trim(),
        content_type: form.syntax !== "auto" ? getContentType(form.syntax) : relic.content_type,
        language_hint: form.syntax !== "auto" ? form.syntax : null,
        access_level: form.access,
        tags: form.tags,
      };
      if (form.expiry !== "keep") updates.expires_in = form.expiry;
      const { data } = await updateRelic(relic.id, updates);
      showToast("Relic updated", "success");
      onsaved?.(data);
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t save the changes", "error");
    } finally {
      saving = false;
    }
  }

  function onKeydown(event) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      save();
    } else if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      oncancel?.();
    }
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<form class="edit" onsubmit={(e) => (e.preventDefault(), save())} onkeydown={onKeydown}>
  <div class="r-ins-mode">
    <div>
      <h2>Edit details</h2>
      <p>{relic.name || "Untitled"}</p>
    </div>
    <button type="button" class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={oncancel} aria-label="Close">
      <Icon name="x" />
    </button>
  </div>

  <div class="r-ins-form">
    <label class="r-field">
      <span class="r-label">Name</span>
      <!-- Focus starts here, so Esc cancels and Ctrl+Enter saves straight away. -->
      <!-- svelte-ignore a11y_autofocus -->
      <span class="r-input"><input bind:value={form.name} placeholder="Untitled" autofocus /></span>
    </label>

    <div class="r-field">
      <label class="r-label" for="edit-type">Type <span class="r-label-aside">now {relic.language_hint || relic.content_type}</span></label>
      <Combobox id="edit-type" options={SYNTAXES} bind:value={form.syntax} placeholder="Search languages" />
    </div>

    <VisibilityField bind:value={form.access} name="edit-visibility" note="After saving, add people in the inspector’s Access section." />
    <TagsField bind:this={tagsField} bind:tags={form.tags} id="edit-tags" />
    <ExpiryField bind:value={form.expiry} allowKeep current={relic.expires_at ? fullDate(relic.expires_at) : "never"} />
  </div>

  <div class="r-ins-save">
    <span class="r-help edit-hint">Ctrl ↵ saves</span>
    <button type="button" class="r-btn r-btn-secondary" onclick={oncancel}>Cancel</button>
    <button type="submit" class="r-btn r-btn-primary" disabled={saving}>{saving ? "Saving…" : "Save"}</button>
  </div>
</form>

<style>
  .edit {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }
  .edit-hint {
    margin-right: auto;
  }
</style>
