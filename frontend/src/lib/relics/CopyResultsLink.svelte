<script>
  // Copies a link to the list as it's filtered: the URL holds every filter and the sort, so
  // whoever opens it sees the same results (theirs, for lists like My relics).
  import Icon from "../ui/Icon.svelte";
  import { copyToClipboard } from "../../services/relicActions";
</script>

<button
  type="button"
  class="r-btn r-btn-ghost r-btn-sm r-btn-icon copy-results"
  onclick={() => copyToClipboard(location.href, "Link to these results copied")}
  title="Copy a link to these results"
  aria-label="Copy a link to these results"
>
  <Icon name="link" />
</button>

<style>
  .copy-results {
    flex: none;
  }
</style>
