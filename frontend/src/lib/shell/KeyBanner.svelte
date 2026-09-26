<script>
  // First visit: the new Relic key, shown once, as a banner under the navbar on every page.
  // It can't be shown again (the browser keeps it out of reach), so the banner stays until the
  // key is copied or downloaded and then confirmed, and leaving the page before that asks first.
  import Icon from "../ui/Icon.svelte";
  import { triggerDownload } from "../../services/utils/download";

  let { userKey, onsaved } = $props();

  let saved = $state(false); // copied or downloaded
  let copyState = $state(null); // "copied" | "failed"

  function download() {
    triggerDownload(userKey, `relic-user-key-${userKey.slice(0, 8)}.txt`, "text/plain");
    saved = true;
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(userKey);
      copyState = "copied";
      saved = true;
    } catch {
      copyState = "failed";
    }
  }

  function onBeforeUnload(event) {
    event.preventDefault();
  }
</script>

<svelte:window onbeforeunload={onBeforeUnload} />

<div class="r-banner r-banner-warning key-banner" role="alert">
  <Icon name="key" />
  <span class="key-text"><b>Save your Relic key.</b> It proves your relics are yours and can’t be shown again or recovered.</span>
  <code class="key-value" title="Your key">{userKey}</code>
  <span class="key-actions">
    <button class="r-btn r-btn-secondary" onclick={copy}><Icon name="copy" />{copyState === "copied" ? "Copied" : copyState === "failed" ? "Copy failed" : "Copy"}</button>
    <button class="r-btn r-btn-secondary" onclick={download}><Icon name="download" />Download</button>
    <button class="r-btn r-btn-primary" onclick={onsaved} disabled={!saved} title={saved ? "" : "Copy or download it first"}>I’ve saved it</button>
  </span>
</div>

<style>
  .key-banner {
    flex: none;
    flex-wrap: wrap;
    height: auto;
    min-height: 44px;
    padding-top: 6px;
    padding-bottom: 6px;
  }
  .key-banner > :global(.r-icon) {
    flex: none;
    width: 16px;
    height: 16px;
  }
  .key-text b {
    font-weight: 600;
  }
  .key-value {
    padding: 2px 8px;
    border: 1px solid var(--warning-line);
    border-radius: var(--radius-sm);
    background: var(--surface);
    color: var(--ink);
    font: 12.5px var(--font-mono);
    user-select: all;
  }
  .key-actions {
    display: flex;
    gap: var(--space-1\.5);
    margin-left: auto;
  }
  .key-actions :global(.r-icon) {
    width: 13px;
    height: 13px;
  }
  @media (max-width: 767px) {
    .key-banner > :global(.r-icon) {
      display: none;
    }
    .key-value {
      word-break: break-all;
    }
    .key-actions {
      margin-left: 0;
    }
  }
</style>
