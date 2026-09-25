// What the sidebar shows: counts for each section and the spaces you own or were given.
// Loaded when the sidebar first appears and refreshed on page changes (cheap: limit=1 counts).
import { writable } from "svelte/store";
import { listRelics, getUserRelics, getUserBookmarks, spaces as spacesApi } from "../../services/api";

export const sidebarData = writable({
  counts: { recent: null, mine: null, bookmarks: null, spaces: null },
  spaces: [],
});

const MAX_SPACES = 8;
let inFlight = null;

const total = (r) => (r.status === "fulfilled" ? r.value : null);

export function refreshSidebar() {
  if (inFlight) return inFlight;
  inFlight = (async () => {
    const [recent, mine, bookmarks, all, own, shared] = await Promise.allSettled([
      listRelics({ limit: 1 }).then((r) => r.data.total),
      getUserRelics({ limit: 1 }).then((r) => r.data.total),
      getUserBookmarks({ limit: 1 }).then((r) => r.data.total),
      spacesApi.list({ limit: 1 }).then((d) => d.total),
      spacesApi.list({ category: "my", sort_by: "name", sort_order: "asc", limit: MAX_SPACES }),
      spacesApi.list({ category: "shared", sort_by: "name", sort_order: "asc", limit: MAX_SPACES }),
    ]);
    const yours = [...(total(own)?.spaces ?? []), ...(total(shared)?.spaces ?? [])].slice(0, MAX_SPACES);
    sidebarData.set({
      counts: { recent: total(recent), mine: total(mine), bookmarks: total(bookmarks), spaces: total(all) },
      spaces: yours,
    });
  })().finally(() => (inFlight = null));
  return inFlight;
}
