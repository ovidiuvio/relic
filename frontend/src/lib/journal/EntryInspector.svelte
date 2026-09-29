<script>
  // The inspector for the selected journal entry: identity and actions, its outline, and the
  // file it is stored in. Deleting confirms inline, as everywhere in the app.
  import Icon from "../ui/Icon.svelte";
  import InsSection from "../relics/inspector/InsSection.svelte";
  import { copyToClipboard } from "../../services/relicActions";
  import { compactBytes, fullDate, relativeTime } from "../relics/format";
  import { longDate } from "./dates";
  import { outline } from "./text";
  import { getFileTypeDefinition } from "../../services/typeUtils";
  import JournalSettings from "./JournalSettings.svelte";

  let {
    entry = null, // detail: the body is what the outline reads
    journal = null,
    readonly = false,
    onpin, // (pinned) => void
    ondelete, // () => void, after the confirmation
    ongoto, // (heading) => void
    onopen = null, // () => void: shown in the list, timeline and calendar layouts, which have no editor
    links = [], // [{ target, res }]: the [[links]] and ![[embeds]] in the text, resolved
    backlinks = [], // other entries that link here: [{ id, title, section }]
    revisions = null, // [{ id, created_at, word_count }] or null while loading (owner only)
    onopenentry, // (entryId) => void
    onkeep, // () => void: keep the current text as a version
    onrestore, // (revisionId) => void
    tab = "entry", // "entry" | "journal"
    ontab, // (tab) => void
    onjournalchanged, // (patch) => void: the journal was renamed or its visibility changed
    onjournaldeleted, // () => void
    onjournalimported, // () => void
    onclose, // for drawers
  } = $props();

  let confirming = $state(false);
  let busy = $state(false);
  $effect(() => {
    entry?.id;
    confirming = false;
  });

  const headings = $derived(entry ? outline(entry.body ?? "") : []);

  async function remove() {
    busy = true;
    try {
      await ondelete?.();
    } finally {
      busy = false;
      confirming = false;
    }
  }
</script>

<aside class="r-inspector" aria-label={tab === "journal" ? "Journal settings" : "Entry details"}>
  {#if ontab && journal}
    <div class="jin-tabs">
      <div class="r-seg" role="tablist" aria-label="Inspector">
        <button role="tab" aria-selected={tab === "entry"} class:is-on={tab === "entry"} onclick={() => ontab("entry")}><Icon name="file" />Entry</button>
        <button role="tab" aria-selected={tab === "journal"} class:is-on={tab === "journal"} onclick={() => ontab("journal")}><Icon name="book" />Journal</button>
      </div>
      {#if onclose}<button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={onclose} title="Hide inspector ( ] )" aria-label="Hide inspector"><Icon name="x" /></button>{/if}
    </div>
  {/if}
  {#if tab === "journal" && journal}
    <JournalSettings {journal} {readonly} onchanged={onjournalchanged} ondeleted={onjournaldeleted} onimported={onjournalimported} />
  {:else if !entry}
    <div class="ins-empty">
      <Icon name="book" size={22} />
      <p>Select an entry to see its outline and details.</p>
      <p class="r-hints"><span><kbd class="r-kbd">↑</kbd><kbd class="r-kbd">↓</kbd>move</span><span><kbd class="r-kbd">]</kbd>inspector</span></p>
    </div>
  {:else}
    <div class="r-ins-id">
      <div class="r-ins-name">
        <span class="r-badge r-t-doc" title="Journal entry"><Icon name="book" size={11} /></span>
        <h2>{entry.title || "Untitled"}</h2>
        {#if onclose && !ontab}
          <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={onclose} title="Hide inspector ( ] )" aria-label="Hide inspector"><Icon name="x" /></button>
        {/if}
      </div>
      <button class="r-ins-fid" title="Copy file path" onclick={() => copyToClipboard(entry.path, "Path copied")}>
        <span class="r-ins-fid-text">{journal?.name ? `${journal.name} / ` : ""}{entry.path}</span><Icon name="copy" />
      </button>
      <div class="r-ins-actions">
        {#if onopen}
          <button class="r-btn r-btn-primary r-btn-md" onclick={onopen}><Icon name="edit" />{readonly ? "Read" : "Open"}</button>
        {/if}
        {#if !readonly}
          <button class="r-btn r-btn-secondary r-btn-md" onclick={() => onpin?.(!entry.pinned)}><Icon name="pin" />{entry.pinned ? "Unpin" : "Pin"}</button>
        {/if}
        <button class="r-btn r-btn-secondary r-btn-md" onclick={() => copyToClipboard(entry.body ?? "", "Markdown copied")}><Icon name="copy" />Copy Markdown</button>
      </div>
    </div>

    <div class="r-ins-body">
      <InsSection id="journal-outline" title="Outline" aside={headings.length ? String(headings.length) : ""} defaultOpen>
        <div class="jin-outline">
          {#each headings as h}
            <button class="jin-h jin-h{h.level}" onclick={() => ongoto?.(h)}>{h.text}</button>
          {:else}
            <p class="jin-empty">Add a heading with # to build an outline.</p>
          {/each}
        </div>
      </InsSection>

      <InsSection id="journal-details" title="Details" defaultOpen>
        <dl class="r-kv">
          <dt>Date</dt><dd>{longDate(entry.entry_date)}</dd>
          <dt>File</dt><dd class="jin-path">{entry.path}</dd>
          <dt>Words</dt><dd>{entry.word_count.toLocaleString("en-US")}</dd>
          <dt>Size</dt><dd>{compactBytes(entry.size_bytes)}</dd>
          <dt>Tasks</dt><dd>{entry.total_tasks ? `${entry.open_tasks} open of ${entry.total_tasks}` : "None"}</dd>
          <dt>Tags</dt>
          <dd>{#if entry.tags.length}{#each entry.tags as tag}<span class="jin-tag">#{tag}</span>{/each}{:else}None{/if}</dd>
          <dt>Written</dt><dd>{entry.created_at ? fullDate(entry.created_at) : "—"}</dd>
          <dt>Edited</dt><dd>{entry.updated_at ? fullDate(entry.updated_at) : "—"}</dd>
          <dt>Visible to</dt><dd><Icon name="lock" size={13} /> {readonly ? "Anyone with the journal link" : "Only you"}</dd>
        </dl>
      </InsSection>

      <InsSection id="journal-links" title="Links" aside={links.length + backlinks.length ? String(links.length + backlinks.length) : ""} defaultOpen>
        <div class="jin-links">
          {#each links as l (l.target)}
            {#if l.res?.kind === "relic"}
              <a class="jin-link" href="/{l.res.id}"><i class="jin-dot" style="background:var(--type-{getFileTypeDefinition(l.res.content_type).category === 'image' ? 'image' : 'doc'})"></i><span>{l.res.name || l.res.id}<small>Relic · {compactBytes(l.res.size_bytes)}</small></span></a>
            {:else if l.res?.kind === "entry"}
              <button class="jin-link" onclick={() => onopenentry?.(l.res.id)}><Icon name="file" size={14} /><span>{l.res.title}<small>Links out</small></span></button>
            {:else}
              <div class="jin-link is-missing"><Icon name="link" size={14} /><span>{l.target}<small>{l.res ? "Nothing with this name" : "Looking…"}</small></span></div>
            {/if}
          {/each}
          {#each backlinks as b (b.id)}
            <button class="jin-link" onclick={() => onopenentry?.(b.id)}><Icon name="link" size={14} /><span>{b.title || "Untitled"}<small>Mentions this{b.section ? ` · under ${b.section}` : ""}</small></span></button>
          {/each}
          {#if !links.length && !backlinks.length}
            <p class="jin-empty">Link with [[Entry title]], or embed a relic with ![[relic name]] or its ID.</p>
          {/if}
        </div>
      </InsSection>

      {#if !readonly}
        <InsSection id="journal-history" title="History" aside={revisions?.length ? String(revisions.length) : ""}>
          <div class="jin-links">
            <button class="r-btn r-btn-secondary r-btn-sm jin-keep" onclick={() => onkeep?.()}><Icon name="history" />Keep this version</button>
            {#each revisions ?? [] as r (r.id)}
              <div class="jin-rev">
                <span title={fullDate(r.created_at)}>{relativeTime(r.created_at)}<small>{r.word_count.toLocaleString("en-US")} words</small></span>
                <button class="r-btn r-btn-ghost r-btn-sm" onclick={() => onrestore?.(r.id)}>Restore</button>
              </div>
            {:else}
              <p class="jin-empty">{revisions ? "No earlier versions yet. One is kept when you edit after a pause." : "Loading…"}</p>
            {/each}
          </div>
        </InsSection>

        <InsSection id="journal-danger" title="Delete" defaultOpen>
          <div class="jin-danger">
            {#if confirming}
              <div class="r-confirm">
                <b>Delete “{entry.title || "Untitled"}”?</b>
                <span>The entry and its file are removed from the journal. This can’t be undone.</span>
                <div class="r-confirm-actions">
                  <button class="r-btn r-btn-secondary r-btn-sm" onclick={() => (confirming = false)}>Keep</button>
                  <button class="r-btn r-btn-danger r-btn-sm" onclick={remove} disabled={busy}>{busy ? "Deleting…" : "Delete entry"}</button>
                </div>
              </div>
            {:else}
              <button class="r-btn r-btn-danger-text r-btn-md" onclick={() => (confirming = true)}><Icon name="trash" />Delete entry</button>
            {/if}
          </div>
        </InsSection>
      {/if}
    </div>
  {/if}
</aside>

<style>
  .jin-tabs {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    border-bottom: 1px solid var(--line);
    background: var(--surface);
  }
  .jin-outline {
    display: grid;
    padding: 0 var(--space-4) var(--space-3);
  }
  .jin-h {
    display: block;
    padding: 3px 6px;
    margin-inline: -6px;
    overflow: hidden;
    border: 0;
    border-radius: var(--radius-xs);
    background: none;
    color: var(--ink-2);
    font: inherit;
    text-align: left;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
  }
  .jin-h:hover {
    background: var(--hover);
    color: var(--accent);
  }
  .jin-h2 {
    padding-left: 18px;
  }
  .jin-h3 {
    padding-left: 30px;
    color: var(--ink-3);
  }
  .jin-links {
    display: grid;
    gap: 2px;
    padding: 0 var(--space-4) var(--space-3);
  }
  .jin-link {
    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
    padding: 5px 6px;
    margin-inline: -6px;
    border: 0;
    border-radius: var(--radius-sm);
    background: none;
    color: var(--ink);
    font: inherit;
    text-align: left;
    text-decoration: none;
    cursor: pointer;
  }
  .jin-link:hover {
    background: var(--hover);
  }
  .jin-link.is-missing {
    color: var(--ink-3);
    cursor: default;
  }
  .jin-link :global(.r-icon) {
    flex: none;
    margin-top: 3px;
    color: var(--ink-3);
  }
  .jin-link span {
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .jin-link small,
  .jin-rev small {
    display: block;
    color: var(--ink-3);
    font-size: 11px;
  }
  .jin-dot {
    flex: none;
    width: 9px;
    height: 9px;
    margin-top: 6px;
    border-radius: 2px;
  }
  .jin-keep {
    justify-self: start;
    margin-bottom: var(--space-1);
  }
  .jin-rev {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
    padding: 2px 0;
  }
  .jin-empty {
    margin: 0;
    color: var(--ink-3);
    font-size: 12px;
  }
  .jin-path {
    font: 12px var(--font-mono);
  }
  .jin-tag {
    margin-right: 6px;
    color: var(--accent);
    font-weight: 500;
  }
  .jin-danger {
    display: grid;
    gap: var(--space-2);
    padding: 0 var(--space-4) var(--space-3);
  }
  .jin-danger .r-btn {
    justify-self: start;
  }
</style>
