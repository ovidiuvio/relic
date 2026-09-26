<script>
  // The fork tree this relic belongs to, drawn as an indented list with the current relic marked.
  // Deep trees fold below their first level; a node's toggle opens it. Relics this user may not
  // see come without an ID or name and show as a locked "Private" row.
  import Icon from "../../ui/Icon.svelte";
  import { getRelicLineage } from "../../../services/api";
  import { shortDate } from "../format";

  let { relicId } = $props();

  let root = $state(null);
  let currentId = $state(null);
  let truncated = $state(false);
  let totalNodes = $state(0);
  let loading = $state(false);
  let failed = $state(false);
  let folded = $state(new Set());

  async function load(maxNodes = 200) {
    const id = relicId;
    loading = true;
    failed = false;
    try {
      const { data } = await getRelicLineage(id, { max_nodes: maxNodes });
      if (id !== relicId) return;
      root = data.root;
      currentId = data.current_relic_id;
      truncated = !!data.truncated;
      totalNodes = data.total_nodes || 0;
      folded = new Set();
    } catch {
      if (id === relicId) failed = true;
    } finally {
      if (id === relicId) loading = false;
    }
  }

  $effect(() => {
    relicId;
    root = null;
    load();
  });

  // Depth-first rows, skipping the children of folded nodes. Hidden nodes have no ID, so rows
  // are keyed by their path in the tree.
  const rows = $derived.by(() => {
    const out = [];
    const walk = (node, depth, key) => {
      out.push({ node, depth, key });
      if (!folded.has(key)) node.children?.forEach((c, i) => walk(c, depth + 1, c.id ?? `${key}/${i}`));
    };
    if (root) walk(root, 0, root.id ?? "root");
    return out;
  });

  function toggle(key) {
    const next = new Set(folded);
    next.has(key) ? next.delete(key) : next.add(key);
    folded = next;
  }
</script>

{#if failed}
  <p class="ins-note">Couldn’t load the lineage. <button class="r-link" onclick={() => load()}>Try again</button></p>
{:else if !root}
  <p class="ins-note">{loading ? "Loading…" : "No lineage."}</p>
{:else if rows.length === 1}
  <p class="ins-note">An original with no forks yet.</p>
{:else}
  <ul class="ins-tree">
    {#each rows as { node, depth, key } (key)}
      <li style:--depth={depth} class:is-current={node.id && node.id === currentId}>
        {#if node.children?.length}
          <button class="ins-fold" onclick={() => toggle(key)} aria-label={folded.has(key) ? "Show forks" : "Hide forks"} aria-expanded={!folded.has(key)}>
            <Icon name={folded.has(key) ? "chevr" : "chev"} size={12} />
          </button>
        {:else}
          <span class="ins-fold"></span>
        {/if}
        {#if node.hidden}
          <span class="ins-private" title="You don’t have access to this relic"><Icon name="lock" size={12} />{depth ? "Private fork" : "Private relic"}</span>
        {:else}
          <a href="/{node.id}" title={node.id}>{node.name || "Untitled"}</a>
          {#if node.id === currentId}<span class="r-chip">this</span>{/if}
          <span class="ins-when">{shortDate(node.created_at)}</span>
        {/if}
      </li>
    {/each}
  </ul>
  {#if truncated}
    <button class="r-link ins-more" disabled={loading} onclick={() => load(5000)}>
      {loading ? "Loading…" : `Showing ${rows.length} of ${totalNodes}. Load all`}
    </button>
  {/if}
{/if}
