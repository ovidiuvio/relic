<script module>
  // Peeks by relic ID, for this page's lifetime: moving back and forth doesn't refetch.
  const cache = new Map();
</script>

<script>
  // The search dropdown's preview of the highlighted relic: what it is, who and when, its tags and
  // description, and a peek at the content (the first lines of text, or the image). Text reads
  // only the first 8 KB, so a large relic previews as fast as a small one.
  import Icon from "../ui/Icon.svelte";
  import { getRelicRawHead } from "../../services/api";
  import { getFileTypeDefinition, isBinaryType } from "../../services/typeUtils";
  import { typeBadge, tagName, compactBytes, fullDate, relativeTime } from "../relics/format";

  let { relic, label = "" } = $props();

  const MAX_IMAGE = 3 * 1024 * 1024;
  const LINES = 22;

  let peek = $state(null); // { kind: "text", lines, more } | { kind: "image" } | { kind: "none", note }

  function kindOf(r) {
    const def = getFileTypeDefinition(r.content_type);
    if (def.category === "image") return r.size_bytes <= MAX_IMAGE ? "image" : "big-image";
    if (def.category === "excalidraw" || isBinaryType(r.content_type)) return "binary";
    return "text";
  }

  $effect(() => {
    const r = relic;
    if (!r) return;
    const kind = kindOf(r);
    if (kind === "image") return void (peek = { kind: "image" });
    if (kind === "big-image") return void (peek = { kind: "none", note: "Large image: open it to view" });
    if (kind === "binary") return void (peek = { kind: "none", note: `${getFileTypeDefinition(r.content_type).label || "Binary"} file: open it to view` });
    if (cache.has(r.id)) return void (peek = cache.get(r.id));
    peek = null;
    const controller = new AbortController();
    // Wait a moment: arrowing through the list shouldn't fetch every row it passes.
    const timer = setTimeout(async () => {
      try {
        const { text, truncated } = await getRelicRawHead(r.id, 8192, controller.signal);
        const all = text.replace(/\r\n?/g, "\n").split("\n");
        const result = { kind: "text", lines: all.slice(0, LINES), more: truncated || all.length > LINES };
        cache.set(r.id, result);
        if (relic?.id === r.id) peek = result;
      } catch (e) {
        if (controller.signal.aborted) return;
        const note = e.status === 403 ? "Protected: open it to view" : "Couldn’t load a preview";
        if (relic?.id === r.id) peek = { kind: "none", note };
      }
    }, 120);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  });

  const badge = $derived(relic ? typeBadge(relic) : null);
  const tags = $derived((relic?.tags ?? []).map(tagName));
</script>

{#if relic}
  <aside class="preview" aria-label="Preview">
    {#if label}<div class="pv-label">{label}</div>{/if}
    <div class="pv-title">
      <span class="r-type r-t-{badge.cls}">{badge.label}</span>
      <b title={relic.name || "Untitled"} class:is-untitled={!relic.name}>{relic.name || "Untitled"}</b>
    </div>
    <div class="pv-meta">
      <span>{badge.name}</span>
      <span>{compactBytes(relic.size_bytes)}</span>
      <span title={fullDate(relic.created_at)}>{relativeTime(relic.created_at)}</span>
      {#if relic.owner_name}<span>by {relic.owner_name}</span>{/if}
      {#if relic.access_level && relic.access_level !== "public"}<span class="pv-vis"><Icon name="lock" size={12} />{relic.access_level}</span>{/if}
    </div>
    {#if tags.length}
      <div class="pv-tags">{#each tags.slice(0, 6) as t (t)}<span class="r-chip">{t}</span>{/each}</div>
    {/if}
    {#if relic.description}<p class="pv-desc">{relic.description}</p>{/if}

    <div class="pv-peek">
      {#if !peek}
        <p class="pv-note">Loading preview…</p>
      {:else if peek.kind === "text"}
        <pre class:is-cut={peek.more}>{peek.lines.join("\n")}</pre>
      {:else if peek.kind === "image"}
        <img src="/{relic.id}/raw" alt={relic.name || ""} loading="lazy" />
      {:else}
        <p class="pv-note">{peek.note}</p>
      {/if}
    </div>
  </aside>
{/if}

<style>
  .preview {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    min-width: 0;
    padding: var(--space-3) var(--space-4);
    background: var(--subtle);
  }
  .pv-label {
    color: var(--ink-3);
    font: 700 10.5px var(--font-mono);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .pv-title {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
    min-width: 0;
  }
  .pv-title b {
    min-width: 0;
    overflow: hidden;
    font-size: 14px;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .pv-title b.is-untitled {
    color: var(--ink-3);
    font-style: italic;
    font-weight: 400;
  }
  .pv-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 2px var(--space-3);
    color: var(--ink-3);
    font-size: 12px;
  }
  .pv-vis {
    display: inline-flex;
    align-items: center;
    gap: 3px;
  }
  .pv-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .pv-desc {
    display: -webkit-box;
    margin: 0;
    overflow: hidden;
    color: var(--ink-2);
    font-size: 12.5px;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
  }
  .pv-peek {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    background: var(--surface);
  }
  .pv-peek pre {
    margin: 0;
    padding: var(--space-2) var(--space-3);
    overflow: hidden;
    color: var(--ink);
    font: 11.5px/1.5 var(--font-mono);
    white-space: pre;
  }
  .pv-peek pre.is-cut {
    mask-image: linear-gradient(#000 75%, transparent);
  }
  .pv-peek img {
    display: block;
    max-width: 100%;
    max-height: 260px;
    margin: auto;
    object-fit: contain;
  }
  .pv-note {
    margin: 0;
    padding: var(--space-3);
    color: var(--ink-3);
    font-size: 12.5px;
  }
</style>
