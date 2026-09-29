<script>
  // The strip under the page bar in the list and timeline layouts: All, Pinned, Open tasks and
  // the journal's most used tags. Each is a link (?filter= or ?tag=), like the relic type facets.
  let {
    filter = null, // "pinned" | "tasks" | null
    tag = null,
    tags = null, // [{ name, count }] from feed.facets.tags
    hrefFor, // ({ filter?, tag? }) => URL
  } = $props();

  const plain = $derived(!filter && !tag);
</script>

<nav class="r-facets jf" aria-label="Filter entries">
  <a href={hrefFor({ filter: null, tag: null })} class:is-on={plain} aria-current={plain ? "true" : undefined}>All</a>
  <a href={hrefFor({ filter: "pinned", tag: null })} class:is-on={filter === "pinned"} aria-current={filter === "pinned" ? "true" : undefined}>Pinned</a>
  <a href={hrefFor({ filter: "tasks", tag: null })} class:is-on={filter === "tasks"} aria-current={filter === "tasks" ? "true" : undefined}>Open tasks</a>
  {#each tags ?? [] as t (t.name)}
    <a href={hrefFor({ filter: null, tag: t.name })} class:is-on={tag === t.name} aria-current={tag === t.name ? "true" : undefined}>#{t.name}<em>{t.count.toLocaleString("en-US")}</em></a>
  {/each}
</nav>

<style>
  .jf {
    flex: none;
    flex-wrap: wrap;
    gap: var(--space-1) var(--space-4);
    padding: var(--space-2) var(--space-4);
    border-bottom: 1px solid var(--line);
    font-size: 12.5px;
  }
</style>
