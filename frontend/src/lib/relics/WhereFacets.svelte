<script>
  // The Everywhere page's Where facets: all, or only the relics you see for one reason (public,
  // yours, bookmarked, shared with you, in your spaces), each with its count. A link each, so the
  // choice sits in the URL (?source=) like the other filters; reasons you have none of are left
  // out, except the one that's chosen.
  import { navigate } from "../../utils/navigation";

  let {
    active = null, // source key, or null for all
    counts = null, // the API's facets.sources
    total = null,
    hrefFor, // (key | null) => URL with that source
  } = $props();

  const SOURCES = [
    { key: "public", label: "Public" },
    { key: "yours", label: "Yours" },
    { key: "bookmarked", label: "Bookmarked" },
    { key: "shared", label: "Shared with you" },
    { key: "spaces", label: "In your spaces" },
  ];
  const shown = $derived(SOURCES.filter((s) => s.key === active || (counts?.[s.key] ?? 0) > 0));
  const n = (v) => (v ?? 0).toLocaleString("en-US");
</script>

<nav class="r-facets wf-full" aria-label="Where">
  <a href={hrefFor(null)} aria-current={!active ? "true" : undefined}>All{#if total != null}<em>{n(total)}</em>{/if}</a>
  {#each shown as s (s.key)}
    <a href={hrefFor(s.key)} aria-current={active === s.key ? "true" : undefined}>{s.label}{#if counts}<em>{n(counts[s.key])}</em>{/if}</a>
  {/each}
</nav>

<!-- The same choice as a select, for a narrow page bar. -->
<label class="r-pagebar-opt wf-compact">where
  <select value={active ?? ""} onchange={(e) => navigate(hrefFor(e.currentTarget.value || null))} aria-label="Where">
    <option value="">All{#if total != null}{" "}({n(total)}){/if}</option>
    {#each shown as s (s.key)}<option value={s.key}>{s.label}{#if counts}{" "}({n(counts[s.key])}){/if}</option>{/each}
  </select>
</label>

<style>
  .r-facets {
    flex: none;
    white-space: nowrap;
  }
  .wf-compact {
    display: none;
    flex: none;
    color: var(--ink-2);
    font-size: 12.5px;
    white-space: nowrap;
  }
  @container pagebar (max-width: 1000px) {
    .wf-full {
      display: none;
    }
    .wf-compact {
      display: flex;
    }
  }
</style>
