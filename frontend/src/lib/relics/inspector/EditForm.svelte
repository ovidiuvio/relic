<script>
  // Inspector mode "Edit details" for a relic you own: name, type, visibility, tags, expiry.
  // Replaces the old edit dialog. Ctrl+Enter saves, Esc cancels.
  import Icon from "../../ui/Icon.svelte";
  import Combobox from "../../ui/Combobox.svelte";
  import { updateRelic } from "../../../services/api";
  import { getAvailableSyntaxOptions, getFileTypeDefinition, getContentType } from "../../../services/typeUtils";
  import { showToast } from "../../../stores/toastStore";
  import { tagName, fullDate } from "../format";

  let { relic, onsaved, oncancel } = $props();

  const SYNTAXES = getAvailableSyntaxOptions();

  const VISIBILITY = [
    { value: "public", icon: "globe", label: "Public", hint: "Listed in Recent and search" },
    { value: "private", icon: "lock", label: "Private", hint: "Anyone with the link" },
    { value: "restricted", icon: "users", label: "Restricted", hint: "Only people you add" },
  ];

  // "keep" leaves the current expiry alone; the rest are counted from now.
  const EXPIRY = [
    ["keep", "Keep"],
    ["never", "Never"],
    ["10m", "10 min"],
    ["1h", "1 hour"],
    ["12h", "12 hours"],
    ["24h", "24 hours"],
    ["3d", "3 days"],
    ["7d", "7 days"],
    ["30d", "30 days"],
    ["1y", "1 year"],
  ];

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
  let tagDraft = $state("");
  let saving = $state(false);

  function addTag(raw) {
    const names = raw.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean);
    form.tags = [...new Set([...form.tags, ...names])];
    tagDraft = "";
  }

  function onTagKeydown(event) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      if (tagDraft.trim()) addTag(tagDraft);
    } else if (event.key === "Backspace" && !tagDraft && form.tags.length) {
      form.tags = form.tags.slice(0, -1);
    }
  }

  async function save() {
    if (saving) return;
    if (tagDraft.trim()) addTag(tagDraft);
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
      <span class="r-input"><input bind:value={form.name} placeholder="Untitled" /></span>
    </label>

    <div class="r-field">
      <label class="r-label" for="edit-type">Type <span class="r-label-aside">now {relic.language_hint || relic.content_type}</span></label>
      <Combobox id="edit-type" options={SYNTAXES} bind:value={form.syntax} placeholder="Search languages" />
    </div>

    <div class="r-field" role="radiogroup" aria-labelledby="edit-vis">
      <span class="r-label" id="edit-vis">Visibility</span>
      <div class="r-options">
        {#each VISIBILITY as v (v.value)}
          <label class="r-option">
            <input type="radio" class="r-radio" name="visibility" value={v.value} bind:group={form.access} />
            <b><Icon name={v.icon} />{v.label}</b>
            <small>{v.hint}</small>
          </label>
        {/each}
      </div>
      {#if form.access === "restricted"}
        <span class="r-help">After saving, add people in the inspector’s Access section.</span>
      {/if}
    </div>

    <div class="r-field">
      <label class="r-label" for="edit-tags">Tags</label>
      <span class="r-input">
        {#each form.tags as tag (tag)}
          <span class="r-chip-tag">
            {tag}
            <button type="button" class="edit-untag" onclick={() => (form.tags = form.tags.filter((t) => t !== tag))} aria-label="Remove tag {tag}">
              <Icon name="x" />
            </button>
          </span>
        {/each}
        <input id="edit-tags" bind:value={tagDraft} onkeydown={onTagKeydown} onblur={() => tagDraft.trim() && addTag(tagDraft)} placeholder={form.tags.length ? "Add a tag…" : "config, nginx, production"} />
      </span>
    </div>

    <div class="r-field">
      <span class="r-label">Expires <span class="r-label-aside">now {relic.expires_at ? fullDate(relic.expires_at) : "never"}</span></span>
      <div class="r-pills">
        {#each EXPIRY as [value, label] (value)}
          <button type="button" aria-pressed={form.expiry === value} onclick={() => (form.expiry = value)}>{label}</button>
        {/each}
      </div>
    </div>
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
  .edit-untag {
    display: grid;
    place-items: center;
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink-3);
    cursor: pointer;
  }
  .edit-untag:hover {
    color: var(--danger);
  }
  .edit-hint {
    margin-right: auto;
  }
</style>
