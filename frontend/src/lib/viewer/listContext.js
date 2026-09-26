// The list a relic was opened from, so the viewer can step to the previous and next relic in it
// and link back. Relic lists remember themselves as a relic is opened from them; the viewer shows
// the controls only when the relic it shows is in that list.
//
//   { label: "Recent", path: "/recent?tag=x", source }
//   source: { items: relic[], hasMore?: boolean, more?(): Promise } (a PagedFeed fits)
import { writable, get } from "svelte/store";

export const listContext = writable(null);

export function rememberList(label, path, source) {
  listContext.set({ label, path, source });
}

/** Where `id` sits in the remembered list: { index, count, prev, next, hasMore } or null. */
export function position(ctx, id) {
  const items = ctx?.source?.items ?? [];
  const index = items.findIndex((r) => r.id === id);
  if (index < 0) return null;
  return {
    index,
    count: items.length,
    prev: items[index - 1] ?? null,
    next: items[index + 1] ?? null,
    hasMore: !!ctx.source.hasMore,
  };
}

/** The next relic after `id`, loading more of the list first when it ends there. */
export async function nextAfter(id) {
  const ctx = get(listContext);
  let pos = position(ctx, id);
  if (pos && !pos.next && pos.hasMore && ctx.source.more) {
    await ctx.source.more();
    pos = position(ctx, id);
  }
  return pos?.next ?? null;
}

/** A relic ID from a link's path ("/<32 hex>"), or null. */
export function relicIdFromHref(href) {
  const m = /^\/([a-f0-9]{32})(?:[/?#]|$)/i.exec(href || "");
  return m ? m[1] : null;
}
