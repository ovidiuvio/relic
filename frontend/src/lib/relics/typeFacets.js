// Type facets for relic lists (design system PageBar): All, Code, Docs, Text, Data, Images,
// Archives, Web. A facet is a family of content types, grouped the way type badges are coloured,
// so a facet and the badges in it always agree.
//
// The list endpoints count relics per content type (?facets=true) and filter by a list of
// content types (?types=). The server has no copy of the type catalogue: the client groups the
// counts into families, and sends a family as its content types.
import { FILE_TYPES } from "../../services/data/fileTypes";
import { CATEGORY_CLASS, typeFamily } from "./format";

export const TYPE_FACETS = [
  { key: "code", label: "Code" },
  { key: "doc", label: "Docs" },
  { key: "text", label: "Text" },
  { key: "data", label: "Data" },
  { key: "image", label: "Images" },
  { key: "archive", label: "Archives" },
  { key: "web", label: "Web" },
];

export const isTypeFacet = (key) => TYPE_FACETS.some((f) => f.key === key);

const base = (contentType) => (contentType || "").split(";", 1)[0].trim().toLowerCase();

/** { code: 12, doc: 3, …, all } from the server's counts per content type. */
export function facetCounts(types) {
  const out = { all: 0 };
  for (const f of TYPE_FACETS) out[f.key] = 0;
  for (const [contentType, n] of Object.entries(types ?? {})) {
    out.all += n;
    const family = typeFamily(contentType);
    if (family in out) out[family] += n;
  }
  return out;
}

/**
 * The ?types= value for a facet: every content type in the catalogue of that family, plus any
 * the list has that the catalogue only matches loosely (text/plain; charset=utf-8 and the like).
 * Sorted, so the same facet always gives the same value.
 */
export function facetTypes(key, types = null) {
  if (!isTypeFacet(key)) return undefined;
  const set = new Set(
    FILE_TYPES.filter((t) => CATEGORY_CLASS[t.category] === key && t.mime).map((t) => base(t.mime))
  );
  for (const contentType of Object.keys(types ?? {})) {
    if (typeFamily(contentType) === key) set.add(base(contentType));
  }
  return [...set].sort().join(",");
}
