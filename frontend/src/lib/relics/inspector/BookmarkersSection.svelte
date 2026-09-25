<script>
  // Who bookmarked this relic, newest first, 25 at a time. Public IDs copy on click.
  import { getRelicBookmarkers } from "../../../services/api";
  import { copyToClipboard } from "../../../services/relicActions";
  import { shortDate } from "../format";

  let { relicId } = $props();

  let people = $state([]);
  let total = $state(0);
  let loading = $state(false);
  let failed = $state(false);

  async function load(offset = 0) {
    const id = relicId;
    loading = true;
    failed = false;
    try {
      const data = await getRelicBookmarkers(id, { limit: 25, offset });
      if (id !== relicId) return;
      people = offset ? [...people, ...data.bookmarkers] : data.bookmarkers;
      total = data.total;
    } catch {
      if (id === relicId) failed = true;
    } finally {
      if (id === relicId) loading = false;
    }
  }

  $effect(() => {
    relicId;
    people = [];
    load(0);
  });
</script>

{#if failed}
  <p class="ins-note">Couldn’t load who bookmarked this. <button class="r-link" onclick={() => load(0)}>Try again</button></p>
{:else if !people.length}
  <p class="ins-note">{loading ? "Loading…" : "Nobody has bookmarked this yet."}</p>
{:else}
  <ul class="ins-people">
    {#each people as p (p.public_id)}
      <li>
        <span class="ins-person">{p.name}</span>
        <button class="ins-pid" title="Copy public ID" onclick={() => copyToClipboard(p.public_id, "Public ID copied")}>{p.public_id.slice(0, 8)}</button>
        <span class="ins-when">{shortDate(p.bookmarked_at)}</span>
      </li>
    {/each}
  </ul>
  {#if people.length < total}
    <button class="r-link ins-more" disabled={loading} onclick={() => load(people.length)}>
      {loading ? "Loading…" : `Show ${Math.min(25, total - people.length)} more`}
    </button>
  {/if}
{/if}
