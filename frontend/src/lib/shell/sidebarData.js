// What the sidebar shows: counts for each section and the spaces you own or were given.
// Loaded when the sidebar first appears and refreshed on page changes (cheap: limit=1 counts).
import { writable } from "svelte/store";
import { listRelics, getUserRelics, getUserBookmarks, listMyJournals, spaces as spacesApi } from "../../services/api";

export const sidebarData = writable({
  counts: { recent: null, mine: null, bookmarks: null, journals: null, spaces: null },
  spaces: [],
  journals: [], // your journals: { id, name, entry_count, access_level }
});

const MAX_SPACES = 8;
let inFlight = null;

const total = (r) => (r.status === "fulfilled" ? r.value : null);

export function refreshSidebar() {
  if (inFlight) return inFlight;
  inFlight = (async () => {
    const [recent, mine, bookmarks, journals, all, own, shared] = await Promise.allSettled([
      listRelics({ limit: 1 }).then((r) => r.data.total),
      getUserRelics({ limit: 1 }).then((r) => r.data.total),
      getUserBookmarks({ limit: 1 }).then((r) => r.data.total),
      // Entries across your journals: what you have written, which is what the section holds.
      listMyJournals(),
      spacesApi.list({ limit: 1 }).then((d) => d.total),
      spacesApi.list({ category: "my", sort_by: "name", sort_order: "asc", limit: MAX_SPACES }),
      spacesApi.list({ category: "shared", sort_by: "name", sort_order: "asc", limit: MAX_SPACES }),
    ]);
    // Own and shared spaces sorted together, so neither crowds the other out of the cut.
    const yours = [...(total(own)?.spaces ?? []), ...(total(shared)?.spaces ?? [])]
      .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }))
      .slice(0, MAX_SPACES);
    sidebarData.set({
      counts: { recent: total(recent), mine: total(mine), bookmarks: total(bookmarks), journals: total(journals)?.reduce((sum, j) => sum + j.entry_count, 0) ?? null, spaces: total(all) },
      spaces: yours,
      journals: total(journals) ?? [],
    });
  })().finally(() => (inFlight = null));
  return inFlight;
}
