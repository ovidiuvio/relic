<script>
  // Comments grouped by the line they're on; each group links to that line in the viewer.
  import { getCommentsPaginated } from "../../../services/api";
  import { shortDate } from "../format";

  let { relicId } = $props();

  let comments = $state([]);
  let total = $state(0);
  let loading = $state(false);
  let failed = $state(false);

  async function load(offset = 0) {
    const id = relicId;
    loading = true;
    failed = false;
    try {
      const data = await getCommentsPaginated(id, { limit: 200, offset });
      if (id !== relicId) return;
      comments = offset ? [...comments, ...data.comments] : data.comments;
      total = data.total;
    } catch {
      if (id === relicId) failed = true;
    } finally {
      if (id === relicId) loading = false;
    }
  }

  $effect(() => {
    relicId;
    comments = [];
    load(0);
  });

  const byLine = $derived.by(() => {
    const groups = new Map();
    for (const c of comments) {
      if (!groups.has(c.line_number)) groups.set(c.line_number, []);
      groups.get(c.line_number).push(c);
    }
    return [...groups.entries()].sort((a, b) => a[0] - b[0]);
  });
</script>

{#if failed}
  <p class="ins-note">Couldn’t load comments. <button class="r-link" onclick={() => load(0)}>Try again</button></p>
{:else if !comments.length}
  <p class="ins-note">{loading ? "Loading…" : "No comments yet. Open the relic and click a line number to add one."}</p>
{:else}
  <div class="ins-comments">
    {#each byLine as [line, items] (line)}
      <div class="ins-thread">
        <a class="ins-line" href="/{relicId}#L{line}">Line {line}</a>
        {#each items as c (c.id)}
          <div class="ins-comment" class:is-reply={c.parent_id}>
            <div class="ins-comment-head"><b>{c.author_name || "Anonymous"}</b><span class="ins-when">{shortDate(c.created_at)}</span></div>
            <p>{c.content}</p>
          </div>
        {/each}
      </div>
    {/each}
  </div>
  {#if comments.length < total}
    <button class="r-link ins-more" disabled={loading} onclick={() => load(comments.length)}>Show more</button>
  {/if}
{/if}
