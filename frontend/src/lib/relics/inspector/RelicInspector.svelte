<script>
  // The inspector for a relic selected in a list: identity, actions, meta, and sections
  // (Details, Tags, Lineage, Bookmarked by, Comments) that replace the old modals.
  // With `editable` (your own relics) it adds the Edit details mode, the Access section for
  // restricted relics, and Delete with an inline confirmation.
  import Icon from "../../ui/Icon.svelte";
  import InsSection from "./InsSection.svelte";
  import BookmarkersSection from "./BookmarkersSection.svelte";
  import LineageSection from "./LineageSection.svelte";
  import CommentsSection from "./CommentsSection.svelte";
  import AccessSection from "./AccessSection.svelte";
  import EditForm from "./EditForm.svelte";
  import SpacesSection from "./SpacesSection.svelte";
  import ReportForm from "./ReportForm.svelte";
  import { checkBookmark, addBookmark, removeBookmark, deleteRelic, updateRelic } from "../../../services/api";
  import { copyRelicContent, downloadRelic, fastForkRelic, copyToClipboard } from "../../../services/relicActions";
  import { isBinaryType } from "../../../services/typeUtils";
  import { showToast } from "../../../stores/toastStore";
  import { typeBadge, tagName, fullDate, shortDate, clockTime, expiryMarker, dayGroup, counterLevel } from "../format";

  let {
    relic = null,
    focus = null, // { id, n }: a section to open, or "edit" / "delete" to start those
    editable = false,
    deletable = editable, // owners, and Relic admins for any relic
    onfork = null, // (relic) instead of a fast fork (the viewer opens the fork form)
    linkUrl = null, // () => the link Copy link copies; the viewer reads the current address, keeping selected lines (#L12)
    ontag,
    onclose,
    onupdated, // (relic) after an edit
    ondeleted, // (relic) after a delete
    onbookmark, // (relic, bookmarked) after the bookmark toggle
  } = $props();

  let mode = $state("view"); // "view" | "edit"
  let confirming = $state(false);
  let deleting = $state(false);
  let reporting = $state(false);

  // A different relic starts in view mode.
  $effect(() => {
    relic?.id;
    mode = "view";
    confirming = false;
    reporting = false;
    opened = null;
  });

  // Requests from the list: the Edit and Delete row actions.
  $effect(() => {
    if (!focus) return;
    focus.n;
    if (focus.id === "edit" && editable) mode = "edit";
    if (focus.id === "delete" && deletable) {
      mode = "view";
      confirming = true;
    }
  });

  async function remove() {
    if (deleting) return;
    deleting = true;
    const gone = relic;
    try {
      await deleteRelic(gone.id);
      showToast(`Deleted “${gone.name || "Untitled"}”`, "success");
      confirming = false;
      ondeleted?.(gone);
    } catch (error) {
      showToast(error.response?.data?.detail || "Couldn’t delete the relic", "error");
    } finally {
      deleting = false;
    }
  }

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
      // A page that reacts to bookmark changes reports them itself (Bookmarks offers Undo).
      if (onbookmark) onbookmark(relic, !was);
      else showToast(was ? "Removed from bookmarks" : "Bookmarked", "success");
    } catch (error) {
      const status = error.response?.status;
      if (status === 409) {
        bookmarked = true;
        showToast("Already bookmarked", "info");
      } else if (status === 401) showToast("Bookmarking needs your user key", "error");
      else showToast("Couldn’t update the bookmark", "error");
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

  // Counters as in the old header, coloured by the list's levels; each opens its section.
  const counters = $derived(
    relic
      ? [
          { key: "views", icon: "eye", n: relic.access_count ?? 0, views: true, label: "views" },
          { key: "bookmarkers", icon: "bookmark", n: bookmarks, label: "bookmarks" },
          { key: "comments", icon: "msg", n: relic.comments_count ?? 0, label: "comments" },
          { key: "lineage", icon: "fork", n: relic.forks_count ?? 0, label: "forks" },
        ].filter((c) => c.n > 0)
      : []
  );
  let opened = $state(null); // a section a counter asked for: { id, n }
  const sectionFocus = $derived(opened ?? focus);

  // Owners remove a tag straight from the Tags section (as the old header's × did).
  async function removeTag(tag) {
    const next = tags.filter((t) => t !== tag);
    try {
      const { data } = await updateRelic(relic.id, { tags: next });
      onupdated?.({ ...relic, tags: data.tags ?? next.map((name) => ({ name })) });
      showToast(`Removed #${tag}`, "success", 3000, {
        label: "Undo",
        run: async () => {
          const { data: back } = await updateRelic(relic.id, { tags: [...next, tag] });
          onupdated?.({ ...relic, tags: back.tags });
        },
      });
    } catch {
      showToast("Couldn’t remove the tag", "error");
    }
  }
</script>

<aside class="r-inspector" aria-label="Relic details">
  {#if relic && mode === "edit"}
    {#key relic.id}
      <EditForm
        {relic}
        oncancel={() => (mode = "view")}
        onsaved={(updated) => {
          mode = "view";
          onupdated?.(updated);
        }}
      />
    {/key}
  {:else if !relic}
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
        {#if editable}
          <button class="r-btn r-btn-ghost r-btn-sm r-btn-icon" onclick={() => (mode = "edit")} title="Edit details (e)" aria-label="Edit details">
            <Icon name="edit" />
          </button>
        {/if}
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
        <button class="r-btn r-btn-primary r-btn-md" onclick={() => copyToClipboard(linkUrl?.() ?? `${location.origin}/${relic.id}`, "Link copied")}>
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
        <button class="r-btn r-btn-secondary r-btn-md" onclick={() => (onfork ? onfork(relic) : fastForkRelic(relic))} title="Fork: make your own copy">
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
        {#if editable}
          <button class="r-pill ins-pill" class:r-pill-accent={relic.access_level === "public"} onclick={() => (mode = "edit")} title="{vis.hint}. Change visibility"><Icon name={vis.icon} />{vis.label}<Icon name="chev" /></button>
        {:else}
          <span class="r-pill" class:r-pill-accent={relic.access_level === "public"} title={vis.hint}><Icon name={vis.icon} />{vis.label}</span>
        {/if}
        {#if expiry}
          <span class="r-pill" class:r-pill-warning={expiry.soon} title={fullDate(relic.expires_at)}><Icon name="clock" />{expiry.text}</span>
        {:else}
          <span class="r-pill"><Icon name="clock" />never expires</span>
        {/if}
        <!-- An owner without a display name is named in Details (by public ID); only ownerless relics are "Anonymous". -->
        <span>{#if editable}You · {:else if relic.owner_name}{relic.owner_name} · {:else if !relic.owner_public_id && !relic.user_id}Anonymous · {/if}{when}</span>
      </div>

      {#if counters.length}
        <div class="ins-counters">
          {#each counters as c (c.key)}
            {#if c.views}
              <span class="ins-count" data-level={counterLevel(c.n, true)} title="{c.n} {c.label}"><Icon name={c.icon} />{c.n}</span>
            {:else}
              <button class="ins-count" data-level={counterLevel(c.n)} title="{c.n} {c.label}: show" onclick={() => (opened = { id: c.key, n: (opened?.n ?? 0) + 1 })}>
                <Icon name={c.icon} />{c.n}
              </button>
            {/if}
          {/each}
        </div>
      {/if}
    </div>

    <div class="r-ins-body">
      <InsSection id="details" title="Details" defaultOpen>
        <dl class="r-kv">
          <dt>Type</dt><dd>{badge.name}{showHint ? ` · ${relic.language_hint}` : ""}</dd>
          <dt>Size</dt><dd>{relic.size_bytes.toLocaleString("en-US")} B</dd>
          <dt>Created</dt><dd>{fullDate(relic.created_at)}</dd>
          {#if relic.expires_at}<dt>Expires</dt><dd>{fullDate(relic.expires_at)}</dd>{/if}
          <dt>Views</dt><dd>{relic.access_count ?? 0}</dd>
          {#if relic.owner_name || relic.owner_public_id}
            <dt>Owner</dt>
            <dd>
              {#if relic.owner_public_id}
                <!-- Without a display name the owner is known by their public ID. -->
                <button class="r-link" class:r-mono={!relic.owner_name} onclick={() => copyToClipboard(relic.owner_public_id, "Public ID copied")} title="Copy the owner's public ID">{relic.owner_name || relic.owner_public_id}</button>
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
              <span class="ins-tag-wrap">
                <button class="r-chip-tag ins-tag" onclick={() => ontag?.(tag)} title="Show relics tagged #{tag}"><Icon name="hash" />{tag}</button>
                {#if editable}
                  <button class="ins-untag" onclick={() => removeTag(tag)} title="Remove tag" aria-label="Remove tag {tag}"><Icon name="x" size={11} /></button>
                {/if}
              </span>
            {/each}
          </div>
        {:else}
          <p class="ins-note">No tags.</p>
        {/if}
      </InsSection>

      {#key relic.id}
        <InsSection id="lineage" focus={sectionFocus} title="Lineage" aside={relic.fork_of ? `a fork · ${plural(relic.forks_count ?? 0, "fork")}` : `original · ${plural(relic.forks_count ?? 0, "fork")}`}>
          <LineageSection relicId={relic.id} />
        </InsSection>

        <InsSection id="bookmarkers" focus={sectionFocus} title="Bookmarked by" aside={bookmarks ? plural(bookmarks, "person", "people") : "nobody yet"}>
          <BookmarkersSection relicId={relic.id} />
        </InsSection>

        <InsSection id="comments" focus={sectionFocus} title="Comments" aside={relic.comments_count ? plural(relic.comments_count, "comment") : "none"}>
          <CommentsSection relicId={relic.id} />
        </InsSection>

        {#if editable && relic.access_level === "restricted"}
          <InsSection id="access" {focus} title="Access" aside="restricted">
            <AccessSection relicId={relic.id} />
          </InsSection>
        {/if}

        <InsSection id="spaces" {focus} title="Spaces" aside="add to a space">
          <SpacesSection relicId={relic.id} />
        </InsSection>

        <InsSection id="more" focus={confirming ? { id: "more", n: focus?.n ?? 0 } : focus} title="More" aside={[editable && "edit", deletable && "delete", "report"].filter(Boolean).join(" · ")}>
            <div class="ins-more-actions">
              {#if editable}
                <button class="r-btn r-btn-secondary r-btn-md" onclick={() => (mode = "edit")}><Icon name="edit" />Edit details</button>
              {/if}
              <button class="r-btn r-btn-secondary r-btn-md" onclick={() => (reporting = true)} disabled={reporting}><Icon name="flag" />Report</button>
              {#if deletable}
                <button class="r-btn r-btn-danger-text r-btn-md" onclick={() => (confirming = true)} disabled={confirming}><Icon name="trash" />Delete</button>
              {/if}
            </div>
            {#if reporting}
              <ReportForm relicId={relic.id} ondone={() => (reporting = false)} />
            {/if}
            {#if confirming}
              <div class="r-confirm ins-confirm">
                <b>Delete “{relic.name || "Untitled"}”?</b>
                <span>It will be deleted for everyone, with its comments and bookmarks. Forks made from it stay. This can’t be undone.</span>
                <div class="r-confirm-actions">
                  <button class="r-btn r-btn-secondary r-btn-sm" onclick={() => (confirming = false)}>Cancel</button>
                  <button class="r-btn r-btn-danger r-btn-sm" onclick={remove} disabled={deleting}>{deleting ? "Deleting…" : "Delete relic"}</button>
                </div>
              </div>
            {/if}
        </InsSection>
      {/key}
    </div>

    <div class="r-ins-foot r-hints">
      <span><kbd class="r-kbd">]</kbd>hide</span>
      <span><kbd class="r-kbd">↵</kbd>open</span>
      <span><kbd class="r-kbd">y</kbd>copy link</span>
      {#if editable}<span><kbd class="r-kbd">e</kbd>edit</span>{/if}
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
  .ins-more-actions {
    display: flex;
    gap: var(--space-1\.5);
  }
  .ins-confirm {
    margin-top: var(--space-2\.5);
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
  .ins-pill {
    border: 0;
    cursor: pointer;
  }
  .ins-pill:hover {
    filter: brightness(0.96);
  }
  .ins-counters {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1) var(--space-3);
    margin-top: var(--space-2);
  }
  .ins-count {
    --level: var(--ink-3);
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 0;
    border: 0;
    background: none;
    color: var(--level);
    font: 12.5px var(--font-mono);
  }
  .ins-count :global(.r-icon) {
    width: 13px;
    height: 13px;
  }
  button.ins-count {
    cursor: pointer;
  }
  button.ins-count:hover {
    text-decoration: underline;
  }
  .ins-count[data-level] {
    font-weight: 700;
  }
  .ins-count[data-level="low"] {
    --level: var(--type-doc);
  }
  .ins-count[data-level="medium"] {
    --level: var(--warning);
  }
  .ins-count[data-level="high"] {
    --level: var(--danger);
  }
  .ins-tag-wrap {
    display: inline-flex;
    align-items: center;
  }
  .ins-untag {
    display: grid;
    place-items: center;
    margin-left: -4px;
    padding: 3px;
    border: 0;
    border-radius: var(--radius-xs);
    background: none;
    color: var(--ink-3);
    cursor: pointer;
  }
  .ins-untag:hover {
    background: var(--danger-soft);
    color: var(--danger);
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

</style>
