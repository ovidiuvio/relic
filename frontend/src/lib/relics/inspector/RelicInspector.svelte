<script>
  // The inspector for a relic selected in a list: identity, actions, meta, and sections
  // (Details, Tags, Lineage, Bookmarked by, Comments) that replace the old modals.
  import Icon from "../../ui/Icon.svelte";
  import InsSection from "./InsSection.svelte";
  import BookmarkersSection from "./BookmarkersSection.svelte";
  import LineageSection from "./LineageSection.svelte";
  import CommentsSection from "./CommentsSection.svelte";
  import { checkBookmark, addBookmark, removeBookmark } from "../../../services/api";
  import { copyRelicContent, downloadRelic, fastForkRelic, copyToClipboard } from "../../../services/relicActions";
  import { isBinaryType } from "../../../services/typeUtils";
  import { showToast } from "../../../stores/toastStore";
  import { typeBadge, tagName, fullDate, shortDate, clockTime, expiryMarker, dayGroup } from "../format";

  let { relic = null, focus = null, ontag, onclose } = $props();

  const VISIBILITY = {
    public: { icon: "globe", label: "Public", hint: "Listed in Recent" },
    private: { icon: "lock", label: "Private", hint: "Anyone with the link" },
    restricted: { icon: "users", label: "Restricted", hint: "Only people you add" },
  };

  // Bookmark state for the selected relic, checked each time the selection changes.
  let bookmarked = $state(false);
  let bookmarkDelta = $state(0);
  let bookmarkBusy = $state(false);

  $effect(() => {
    const id = relic?.id;
    bookmarked = false;
    bookmarkDelta = 0;
    if (!id) return;
    checkBookmark(id)
      .then((r) => {
        if (relic?.id === id) bookmarked = !!r.data.is_bookmarked;
      })
      .catch(() => {});
  });

  async function toggleBookmark() {
    if (bookmarkBusy) return;
    bookmarkBusy = true;
    const was = bookmarked;
    try {
      if (was) await removeBookmark(relic.id);
      else await addBookmark(relic.id);
      bookmarked = !was;
      bookmarkDelta += was ? -1 : 1;
      showToast(was ? "Removed from bookmarks" : "Bookmarked", "success");
    } catch {
      showToast("Couldn’t update the bookmark", "error");
    } finally {
      bookmarkBusy = false;
    }
  }

  const badge = $derived(relic ? typeBadge(relic) : null);
  const vis = $derived(relic ? VISIBILITY[relic.access_level] ?? VISIBILITY.public : null);
  const expiry = $derived(relic ? expiryMarker(relic.expires_at) : null);
  const tags = $derived(relic?.tags?.map(tagName) ?? []);
  const bookmarks = $derived((relic?.bookmark_count ?? 0) + bookmarkDelta);
  const showHint = $derived(!!relic?.language_hint && !["auto", badge?.name.toLowerCase()].includes(relic.language_hint.toLowerCase()));
  const binary = $derived(relic ? isBinaryType(relic.content_type) : false);
  const when = $derived.by(() => {
    if (!relic) return "";
    const g = dayGroup(relic.created_at);
    const day = g.key === "today" || g.key === "yesterday" ? g.label.toLowerCase() : shortDate(relic.created_at);
    return `${day} ${clockTime(relic.created_at)}`;
  });

  const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
</script>

<aside class="r-inspector" aria-label="Relic details">
  {#if !relic}
    <div class="ins-empty">
      <Icon name="panel" size={22} />
      <p>Select a relic to see its details.</p>
      <p class="r-hints"><span><kbd class="r-kbd">↑</kbd><kbd class="r-kbd">↓</kbd>move</span><span><kbd class="r-kbd">↵</kbd>open</span></p>
    </div>
  {:else}
    <div class="r-ins-id">
      <div class="r-ins-name">
        <span class="r-badge r-t-{badge.cls}" title={badge.name}>{badge.label}</span>
        <h2><a href="/{relic.id}" title="Open">{relic.name || "Untitled"}</a></h2>
        {#if onclose}
          <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={onclose} title="Hide inspector ( ] )" aria-label="Hide inspector">
            <Icon name="x" />
          </button>
        {/if}
      </div>
      {#if relic.description}<p class="r-ins-desc">{relic.description}</p>{/if}
      <button class="r-ins-fid" title="Copy ID" onclick={() => copyToClipboard(relic.id, "Relic ID copied")}>
        {relic.id.match(/.{1,8}/g).join(" ")}
        <Icon name="copy" />
      </button>

      <div class="r-ins-actions">
        <button class="r-btn r-btn-primary r-btn-md" onclick={() => copyToClipboard(`${location.origin}/${relic.id}`, "Link copied")}>
          <Icon name="link" />Copy link
        </button>
        <button class="r-btn r-btn-secondary r-btn-md r-btn-icon" onclick={() => copyRelicContent(relic.id)} disabled={binary} title={binary ? "Binary content can’t be copied as text" : "Copy content"} aria-label="Copy content">
          <Icon name="copy" />
        </button>
        <a class="r-btn r-btn-secondary r-btn-md r-btn-icon" href="/{relic.id}/raw" target="_blank" rel="noopener" title="Open the raw content" aria-label="Raw">
          <Icon name="raw" />
        </a>
        <button class="r-btn r-btn-secondary r-btn-md r-btn-icon" onclick={() => downloadRelic(relic.id, relic.name, relic.content_type)} title="Download" aria-label="Download">
          <Icon name="download" />
        </button>
        <button class="r-btn r-btn-secondary r-btn-md" onclick={() => fastForkRelic(relic)} title="Fork: make your own copy">
          <Icon name="fork" />Fork
        </button>
        <button
          class="r-btn r-btn-secondary r-btn-md"
          aria-pressed={bookmarked}
          onclick={toggleBookmark}
          disabled={bookmarkBusy}
          title={bookmarked ? "Remove bookmark" : "Bookmark"}
        >
          <Icon name="bookmark" />{bookmarks}
        </button>
      </div>

      <div class="r-ins-meta">
        <span class="r-pill" class:r-pill-accent={relic.access_level === "public"} title={vis.hint}><Icon name={vis.icon} />{vis.label}</span>
        {#if expiry}
          <span class="r-pill" class:r-pill-warning={expiry.soon} title={fullDate(relic.expires_at)}><Icon name="clock" />{expiry.text}</span>
        {:else}
          <span class="r-pill"><Icon name="clock" />never expires</span>
        {/if}
        <span>{relic.owner_name || "Anonymous"} · {when}</span>
      </div>
    </div>

    <div class="r-ins-body">
      <InsSection id="details" title="Details" defaultOpen>
        <dl class="r-kv">
          <dt>Type</dt><dd>{badge.name}{showHint ? ` · ${relic.language_hint}` : ""}</dd>
          <dt>Size</dt><dd>{relic.size_bytes.toLocaleString("en-US")} B</dd>
          <dt>Created</dt><dd>{fullDate(relic.created_at)}</dd>
          {#if relic.expires_at}<dt>Expires</dt><dd>{fullDate(relic.expires_at)}</dd>{/if}
          <dt>Views</dt><dd>{relic.access_count ?? 0}</dd>
          {#if relic.owner_name}
            <dt>Owner</dt>
            <dd>
              {#if relic.owner_public_id}
                <button class="r-link" onclick={() => copyToClipboard(relic.owner_public_id, "Public ID copied")} title="Copy the owner's public ID">{relic.owner_name}</button>
              {:else}{relic.owner_name}{/if}
            </dd>
          {/if}
          {#if relic.fork_of}
            <dt>Forked from</dt><dd><a class="r-link" href="/{relic.fork_of}">{relic.fork_of.slice(0, 8)}<Icon name="chevr" /></a></dd>
          {/if}
        </dl>
      </InsSection>

      <InsSection id="tags" {focus} title="Tags" aside={tags.length ? `${tags.length}` : "none"}>
        {#if tags.length}
          <div class="ins-tags">
            {#each tags as tag (tag)}
              <button class="r-chip-tag ins-tag" onclick={() => ontag?.(tag)} title="Show relics tagged #{tag}"><Icon name="hash" />{tag}</button>
            {/each}
          </div>
        {:else}
          <p class="ins-note">No tags.</p>
        {/if}
      </InsSection>

      {#key relic.id}
        <InsSection id="lineage" {focus} title="Lineage" aside={relic.fork_of ? `a fork · ${plural(relic.forks_count ?? 0, "fork")}` : `original · ${plural(relic.forks_count ?? 0, "fork")}`}>
          <LineageSection relicId={relic.id} />
        </InsSection>

        <InsSection id="bookmarkers" {focus} title="Bookmarked by" aside={bookmarks ? plural(bookmarks, "person", "people") : "nobody yet"}>
          <BookmarkersSection relicId={relic.id} />
        </InsSection>

        <InsSection id="comments" {focus} title="Comments" aside={relic.comments_count ? plural(relic.comments_count, "comment") : "none"}>
          <CommentsSection relicId={relic.id} />
        </InsSection>
      {/key}
    </div>

    <div class="r-ins-foot r-hints">
      <span><kbd class="r-kbd">]</kbd>hide</span>
      <span><kbd class="r-kbd">↵</kbd>open</span>
      <span><kbd class="r-kbd">y</kbd>copy link</span>
    </div>
  {/if}
</aside>

<style>
  .r-inspector {
    height: 100%;
  }
  .r-ins-name h2 a {
    color: inherit;
    text-decoration: none;
    overflow-wrap: anywhere;
  }
  .r-ins-name h2 a:hover {
    text-decoration: underline;
    text-decoration-color: var(--line-2);
  }
  .r-ins-fid {
    padding: 0;
    border: 0;
    background: none;
    cursor: pointer;
  }
  .r-ins-fid:hover {
    color: var(--ink-2);
  }
  .r-kv dd button.r-link {
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
  .ins-tags {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1\.5);
  }
  .ins-tag {
    padding-right: 8px;
    border: 0;
    cursor: pointer;
  }
  .ins-tag:hover {
    background: var(--accent-soft);
    color: var(--accent);
  }

  /* Shared by the section components. */
  .r-inspector :global(.ins-note) {
    margin: 0;
    color: var(--ink-3);
    font-size: 12.5px;
  }
  .r-inspector :global(.ins-more) {
    margin-top: var(--space-2);
    padding: 0;
    border: 0;
    background: none;
    cursor: pointer;
  }
  .r-inspector :global(.ins-when) {
    margin-left: auto;
    color: var(--ink-3);
    font: 12px var(--font-mono);
    white-space: nowrap;
  }
  .r-inspector :global(.ins-people),
  .r-inspector :global(.ins-tree) {
    display: grid;
    gap: 2px;
    margin: 0;
    padding: 0;
    list-style: none;
    font-size: 12.5px;
  }
  .r-inspector :global(.ins-people li),
  .r-inspector :global(.ins-tree li) {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    min-height: 24px;
  }
  .r-inspector :global(.ins-person) {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .r-inspector :global(.ins-pid) {
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink-3);
    font: 12px var(--font-mono);
    cursor: pointer;
  }
  .r-inspector :global(.ins-pid:hover) {
    color: var(--accent);
  }
  .r-inspector :global(.ins-tree li) {
    padding-left: calc(var(--depth) * 14px);
  }
  .r-inspector :global(.ins-tree a) {
    min-width: 0;
    overflow: hidden;
    color: var(--ink);
    text-overflow: ellipsis;
    white-space: nowrap;
    text-decoration: none;
  }
  .r-inspector :global(.ins-tree a:hover) {
    color: var(--accent);
  }
  .r-inspector :global(.ins-tree li.is-current a) {
    font-weight: 500;
  }
  .r-inspector :global(.ins-fold) {
    display: grid;
    place-items: center;
    flex: none;
    width: 16px;
    height: 16px;
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink-3);
    cursor: pointer;
  }
  .r-inspector :global(.ins-comments) {
    display: grid;
    gap: var(--space-3);
  }
  .r-inspector :global(.ins-thread) {
    display: grid;
    gap: var(--space-1\.5);
  }
  .r-inspector :global(.ins-line) {
    color: var(--accent);
    font: 500 12px var(--font-mono);
    text-decoration: none;
  }
  .r-inspector :global(.ins-comment) {
    padding: var(--space-1\.5) var(--space-2\.5);
    border-radius: var(--radius-sm);
    background: var(--surface);
    font-size: 12.5px;
  }
  .r-inspector :global(.ins-comment.is-reply) {
    margin-left: var(--space-3\.5);
  }
  .r-inspector :global(.ins-comment-head) {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
  }
  .r-inspector :global(.ins-comment-head b) {
    font-weight: 500;
  }
  .r-inspector :global(.ins-comment p) {
    margin: 2px 0 0;
    color: var(--ink-2);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
</style>
