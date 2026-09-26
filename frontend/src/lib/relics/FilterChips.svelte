<script>
  // The owner and exact-type filters as page-bar chips, each with × to clear it. Both come from
  // the URL (?owner= a public ID, ?type= a content type), set by clicking an owner's name or a
  // type badge in the list. The owner's name comes from the rows they own.
  import Icon from "../ui/Icon.svelte";
  import { navigate } from "../../utils/navigation";
  import { isExactType, typeLabel } from "./typeFacets";

  let {
    owner = null, // public ID
    type = null,
    relics = [], // the loaded rows, to name the owner
    hrefFor, // (changes) => URL with those parameters changed
  } = $props();

  const ownerName = $derived(owner ? relics.find((r) => r.owner_public_id === owner)?.owner_name : null);
</script>

{#if owner}
  <span class="r-chip-filter" title="Owner {owner}"><Icon name="user" />{ownerName || owner.slice(0, 8)}<button onclick={() => navigate(hrefFor({ owner: null }))} aria-label="Show every owner"><Icon name="x" /></button></span>
{/if}
{#if isExactType(type)}
  <span class="r-chip-filter" title={type}>{typeLabel(type)}<button onclick={() => navigate(hrefFor({ type: null }))} aria-label="Show every type"><Icon name="x" /></button></span>
{/if}
