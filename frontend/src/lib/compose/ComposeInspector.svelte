<script>
  // The inspector while making a relic (new, upload or fork): the options, the create button,
  // and for new relics how to do the same from the command line.
  // Ctrl+Enter creates from anywhere on the page (the page handles the key).
  import Icon from "../ui/Icon.svelte";
  import Combobox from "../ui/Combobox.svelte";
  import InsSection from "../relics/inspector/InsSection.svelte";
  import VisibilityField from "../relics/fields/VisibilityField.svelte";
  import ExpiryField from "../relics/fields/ExpiryField.svelte";
  import TagsField from "../relics/fields/TagsField.svelte";
  import SpaceField from "../relics/fields/SpaceField.svelte";
  import { getAvailableSyntaxOptions } from "../../services/typeUtils";
  import { copyToClipboard } from "../../services/relicActions";
  import { clockTime } from "../relics/format";

  let {
    title, // mode heading, e.g. "New relic", "Upload 3 files", "Fork"
    subtitle = "",
    form = $bindable(), // { title, syntax, visibility, expiry, tags, spaceId }
    showType = true,
    showSpace = true,
    upload = $bindable(null), // { count, zip } while uploading files
    busy = false,
    submitLabel,
    disabled = false,
    onsubmit,
    savedAt = null, // when the editor's draft was last autosaved
    showCli = false, // the command-line help (new relics)
    onclose,
  } = $props();

  const SYNTAXES = getAvailableSyntaxOptions();
  let tagsField = $state();

  function submit(event) {
    event?.preventDefault();
    tagsField?.flush();
    onsubmit?.();
  }

  // The old form's CLI and curl tabs, complete.
  const origin = location.origin;
  const snippets = [
    { group: "Relic CLI", label: "Install", code: `curl -sSL ${origin}/install.sh | bash` },
    {
      group: "Relic CLI",
      label: "Quick start",
      code: `# Upload a file\nrelic script.py\n\n# Upload from stdin\necho "Hello World" | relic\n\n# Upload with options\nrelic file.txt --name "My File" --access-level public --expires-in 24h\n\n# List your relics\nrelic list\n\n# Download a relic\nrelic get <relic-id>`,
    },
    {
      group: "Relic CLI",
      label: "Configuration (~/.relic/config)",
      code: `# View configuration\nrelic config --list\n\n# Change server\nrelic config core.server ${origin}`,
    },
    { group: "curl", label: "Upload from stdin", code: `echo "Hello World" | curl -X POST ${origin}/api/v1/relics \\\n  -F "file=@-" \\\n  -F "name=greeting"` },
    {
      group: "curl",
      label: "Upload a file",
      code: `curl -X POST ${origin}/api/v1/relics \\\n  -F "file=@script.py" \\\n  -F "name=My Script" \\\n  -F "access_level=public" \\\n  -F "expires_in=24h"`,
    },
    { group: "curl", label: "Pipe command output", code: `ps aux | curl -X POST ${origin}/api/v1/relics \\\n  -F "file=@-" \\\n  -F "name=processes.txt"` },
  ];
</script>

<aside class="r-inspector compose" aria-label="Relic options">
  <form class="compose-form" onsubmit={submit}>
    <div class="r-ins-mode">
      <div>
        <h2>{title}</h2>
        {#if subtitle}<p>{subtitle}</p>{/if}
      </div>
      {#if onclose}
        <button type="button" class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={onclose} aria-label="Hide options"><Icon name="x" /></button>
      {/if}
    </div>

    <div class="r-ins-form">
      <label class="r-field">
        <span class="r-label">{upload?.count > 1 && !upload.zip ? "Name (one relic per file keeps file names)" : "Name"}</span>
        <span class="r-input">
          <input bind:value={form.title} placeholder={upload?.count > 1 && upload.zip ? "archive name" : "Untitled"} disabled={upload?.count > 1 && !upload.zip} />
        </span>
      </label>

      {#if upload?.count > 1}
        <label class="compose-zip">
          <input type="checkbox" class="r-check" bind:checked={upload.zip} />
          <span><b>Zip into one relic</b><small>{upload.zip ? `${upload.count} files become one archive, folders kept` : `${upload.count} separate relics`}</small></span>
        </label>
      {/if}

      {#if showType}
        <div class="r-field">
          <label class="r-label" for="compose-type">Type</label>
          <Combobox id="compose-type" options={SYNTAXES} bind:value={form.syntax} placeholder="Search languages" />
        </div>
      {/if}

      <VisibilityField bind:value={form.visibility} name="compose-visibility" note="After creating, add people in the inspector’s Access section." />
      <ExpiryField bind:value={form.expiry} />
      <TagsField bind:this={tagsField} bind:tags={form.tags} id="compose-tags" />
      {#if showSpace}
        <SpaceField bind:value={form.spaceId} id="compose-space" />
      {/if}
    </div>

    <div class="r-ins-save">
      {#if savedAt}<span class="r-help compose-saved">Draft saved {clockTime(savedAt)}</span>{:else}<span class="r-help compose-saved">Ctrl ↵ creates</span>{/if}
      <button class="r-btn r-btn-primary" disabled={busy || disabled}>{busy ? "Creating…" : submitLabel}</button>
    </div>
  </form>

  {#if showCli}
    <div class="compose-extra">
      <InsSection id="compose-cli" title="From the command line" aside="relic · curl">
        <div class="compose-snippets">
          {#each snippets as s, i (s.label)}
            {#if s.group !== snippets[i - 1]?.group}<h3 class="compose-group">{s.group}</h3>{/if}
            <div class="compose-snippet">
              <span>{s.label}</span>
              <pre>{s.code}</pre>
              <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={() => copyToClipboard(s.code, "Copied")} title="Copy" aria-label="Copy {s.label}"><Icon name="copy" /></button>
            </div>
          {/each}
          <p class="ins-note">The CLI sets itself up to use {origin}. With curl, send your key in the <code>X-User-Key</code> header to keep relics on your account.</p>
        </div>
      </InsSection>
    </div>
  {/if}
</aside>

<style>
  .compose {
    height: 100%;
    overflow-y: auto;
  }
  .compose-form {
    display: flex;
    flex-direction: column;
    flex: none;
  }
  .compose-form .r-ins-form {
    overflow: visible;
  }
  .compose-saved {
    margin-right: auto;
  }
  .compose-zip {
    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-2\.5);
    border: 1px solid var(--line-2);
    border-radius: var(--radius-md);
    cursor: pointer;
  }
  .compose-zip .r-check {
    margin-top: 2px;
  }
  .compose-zip span {
    display: grid;
    gap: 1px;
  }
  .compose-zip b {
    font-weight: 500;
  }
  .compose-zip small {
    color: var(--ink-3);
    font-size: 11.5px;
  }
  .compose-extra {
    border-top: 1px solid var(--line);
  }
  .compose-group {
    margin: var(--space-1) 0 0;
    color: var(--ink);
    font-size: 12.5px;
    font-weight: 600;
  }
  .compose-snippet {
    position: relative;
    display: grid;
    gap: 3px;
  }
  .compose-snippet span {
    color: var(--ink-2);
    font-size: 12px;
    font-weight: 500;
  }
  .compose-snippet pre {
    margin: 0;
    padding: 7px 34px 7px 9px;
    overflow-x: auto;
    border-radius: var(--radius-sm);
    background: var(--night);
    color: var(--night-ink);
    font: 11.5px/1.5 var(--font-mono);
    white-space: pre;
  }
  .compose-snippet .r-btn {
    position: absolute;
    right: 3px;
    bottom: 3px;
    color: var(--night-ink);
  }
  .compose-snippet .r-btn:hover {
    background: rgba(255, 255, 255, 0.1);
  }
  code {
    font-family: var(--font-mono);
  }
</style>
