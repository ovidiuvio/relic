<script>
  // The page bar's type facets (All, Code, Docs, …). Each is a link, so the type sits in the URL
  // (?type=code) like the tag and search filters. Counts show once the list is filtered, as the
  // design system has it; a facet with nothing in it is dimmed but still works.
  import { TYPE_FACETS, facetCounts } from "./typeFacets";
  import { navigate } from "../../utils/navigation";

  let {
    active = null, // facet key, or null for All
    types = null, // the server's counts per content type (feed.facets.types)
    showCounts = false,
    hrefFor, // (key | null) => URL with that facet
    compact = false, // always the sentence-style select (a page bar with other facets)
  } = $props();

  const counts = $derived(types ? facetCounts(types) : null);
  const n = (v) => (v ?? 0).toLocaleString("en-US");
</script>

<nav class="r-facets tf-full" class:is-hidden={compact} aria-label="Type">
  <a href={hrefFor(null)} aria-current={!active ? "true" : undefined}>All{#if showCounts && counts}<em>{n(counts.all)}</em>{/if}</a>
  {#each TYPE_FACETS as f (f.key)}
    <a href={hrefFor(f.key)} aria-current={active === f.key ? "true" : undefined} class:is-empty={counts && !counts[f.key]}>
      {f.label}{#if showCounts && counts}<em>{n(counts[f.key])}</em>{/if}
    </a>
  {/each}
</nav>

<!-- The same choice as a sentence-style option, for a narrow page bar. -->
<label class="r-pagebar-opt tf-compact" class:is-shown={compact}>type
  <select value={active ?? ""} onchange={(e) => navigate(hrefFor(e.currentTarget.value || null))} aria-label="Type">
    <option value="">All{#if showCounts && counts}{" "}({n(counts.all)}){/if}</option>
    {#each TYPE_FACETS as f (f.key)}
      <option value={f.key}>{f.label}{#if showCounts && counts}{" "}({n(counts[f.key])}){/if}</option>
    {/each}
  </select>
</label>

<style>
  .r-facets {
    flex: none;
    white-space: nowrap;
  }
  .tf-compact {
    display: none;
    flex: none;
    color: var(--ink-2);
    font-size: 12.5px;
    white-space: nowrap;
  }
  .tf-full.is-hidden {
    display: none;
  }
  .tf-compact.is-shown {
    display: flex;
  }
  @container pagebar (max-width: 900px) {
    .tf-full {
      display: none;
    }
    .tf-compact {
      display: flex;
    }
  }
</style>
