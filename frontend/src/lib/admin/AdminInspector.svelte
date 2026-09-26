<script>
  // The inspector frame the admin sections share, in the relic inspector's layout: an identity
  // block (badge, name, a copyable ID, actions, meta pills) over collapsible sections.
  // With nothing selected it shows `emptyText`.
  import Icon from "../ui/Icon.svelte";
  import { copyToClipboard } from "../../services/relicActions";

  let {
    label, // aria-label, e.g. "User details"
    icon,
    badgeClass = "r-t-doc",
    title = null, // null: nothing selected
    titleClass = "",
    copyId = null, // { text, shown?, label } — shown under the title, copies `text`
    emptyText = "Select a row to see its details.",
    onclose = null,
    actions, // snippet
    meta, // snippet
    children, // the sections
  } = $props();
</script>

<aside class="r-inspector" aria-label={label}>
  {#if title == null}
    <div class="ins-empty">
      <Icon name={icon} size={22} />
      <p>{emptyText}</p>
    </div>
  {:else}
    <div class="r-ins-id">
      <div class="r-ins-name">
        <span class="r-badge {badgeClass}"><Icon name={icon} size={11} /></span>
        <h2 class={titleClass}>{title}</h2>
        {#if onclose}
          <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={onclose} title="Hide inspector ( ] )" aria-label="Hide inspector"><Icon name="x" /></button>
        {/if}
      </div>
      {#if copyId}
        <button class="r-ins-fid" title="Copy {copyId.label}" onclick={() => copyToClipboard(copyId.text, `${copyId.label[0].toUpperCase()}${copyId.label.slice(1)} copied`)}>
          {copyId.shown ?? copyId.text}<Icon name="copy" />
        </button>
      {/if}
      {#if actions}<div class="r-ins-actions">{@render actions()}</div>{/if}
      {#if meta}<div class="r-ins-meta">{@render meta()}</div>{/if}
    </div>
    <div class="r-ins-body">{@render children?.()}</div>
  {/if}
</aside>

<style>
  .r-inspector {
    height: 100%;
  }
  .r-ins-name h2 {
    overflow-wrap: anywhere;
  }
  .r-ins-name .r-badge {
    min-width: 24px;
  }
  .r-ins-fid {
    padding: 0;
    border: 0;
    background: none;
    cursor: pointer;
  }
  .ins-empty {
    display: grid;
    justify-items: center;
    gap: var(--space-2);
    margin: auto;
    padding: var(--space-5);
    color: var(--ink-3);
    text-align: center;
  }
  .ins-empty p {
    margin: 0;
  }
  .r-ins-body :global(.ins-note) {
    margin: 0;
    color: var(--ink-3);
    font-size: 12px;
    line-height: 1.5;
  }
  .r-ins-body :global(.ins-log) {
    max-height: 320px;
    margin: 0;
    padding: 8px 10px;
    overflow: auto;
    border-radius: var(--radius-sm);
    background: var(--night);
    color: var(--night-ink);
    font: 11.5px/1.5 var(--font-mono);
    white-space: pre-wrap;
    word-break: break-word;
  }
  .r-ins-body :global(.ins-stack) {
    display: grid;
    gap: var(--space-2\.5);
  }
  .r-ins-body :global(.ins-row) {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-1\.5);
  }
</style>
