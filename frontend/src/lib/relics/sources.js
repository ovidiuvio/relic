// Why an Everywhere result is visible to you, from the search API's `sources` (public, yours,
// bookmarked, shared, spaces) and `spaces` ([{ id, name }]): as the row's chip and as the
// inspector's "Why you see it" lines.

/** The one reason worth showing on a row, or null for a plain public relic. */
export function sourceChip(relic) {
  const s = relic?.sources ?? [];
  if (s.includes("yours")) return { icon: "user", label: "yours", title: "Yours" };
  if (relic.spaces?.length) {
    const more = relic.spaces.length - 1;
    return { icon: "layers", label: relic.spaces[0].name + (more ? ` +${more}` : ""), title: `In ${relic.spaces.map((x) => x.name).join(", ")}` };
  }
  if (s.includes("shared")) return { icon: "users", label: "shared with you", title: "Restricted, and you’re on its access list" };
  if (s.includes("bookmarked")) return { icon: "bookmark", label: "bookmarked", title: "You bookmarked it" };
  return null;
}

/** Every reason, as sentences: [{ icon, text, space? }]. Empty when the relic has no sources. */
export function whyLines(relic) {
  const s = relic?.sources ?? [];
  const lines = [];
  if (s.includes("yours")) lines.push({ icon: "user", text: "It’s yours." });
  for (const space of relic?.spaces ?? []) lines.push({ icon: "layers", text: "It’s in a space you’re in:", space });
  if (s.includes("shared")) lines.push({ icon: "users", text: "It’s restricted, and you’re on its access list." });
  if (s.includes("bookmarked")) lines.push({ icon: "bookmark", text: "You bookmarked it." });
  if (s.includes("public")) lines.push({ icon: "globe", text: "It’s public: listed for everyone." });
  else if (lines.length && relic.access_level === "private" && !s.includes("yours")) {
    lines.push({ icon: "lock", text: "It’s private: anyone else needs its link." });
  }
  return lines;
}
