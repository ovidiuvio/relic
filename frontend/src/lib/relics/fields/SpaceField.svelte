<script>
  // Which space a new relic goes into: none, or one you can add to (owner, admin, editor).
  import Combobox from "../../ui/Combobox.svelte";
  import { spaces as spacesApi } from "../../../services/api";

  let { value = $bindable(null), id = "space" } = $props();

  const EDITABLE = ["owner", "admin", "editor"];
  let options = $state([{ value: null, label: "No space" }]);

  (async () => {
    try {
      const [mine, shared] = await Promise.all([
        spacesApi.list({ category: "my", sort_by: "name", sort_order: "asc", limit: 100 }),
        spacesApi.list({ category: "shared", sort_by: "name", sort_order: "asc", limit: 100 }),
      ]);
      const list = [...mine.spaces, ...shared.spaces].filter((s) => EDITABLE.includes(s.role));
      // A space passed in (?space=) that isn't in the first 100 still shows by its ID.
      if (value && !list.some((s) => s.id === value)) {
        try {
          const s = await spacesApi.get(value);
          if (EDITABLE.includes(s.role)) list.unshift(s);
        } catch {
          // Unknown or inaccessible space: leave it unset.
        }
      }
      options = [
        { value: null, label: "No space" },
        ...list.map((s) => ({ value: s.id, label: `${s.name}${s.visibility === "private" ? " (private)" : ""}` })),
      ];
    } catch {
      // Without the list the relic can still be created, just not into a space.
    }
  })();
</script>

<div class="r-field">
  <label class="r-label" for={id}>Space</label>
  <Combobox {id} {options} bind:value placeholder="No space" />
</div>
