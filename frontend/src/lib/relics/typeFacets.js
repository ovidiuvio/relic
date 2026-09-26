// Type facets for relic lists (design system PageBar): All, Code, Docs, Text, Data, Images,
// Archives, Web. A facet is a family of content types, grouped the way type badges are coloured,
// so a facet and the badges in it always agree.
//
// The list endpoints count relics per content type (?facets=true) and filter by a list of
// content types (?types=). The server has no copy of the type catalogue: the client groups the
// counts into families, and sends a family as its content types.
//
// The page's ?type= is a family key (code) or one exact content type (text/x-python), set by
// clicking a relic's type badge. An exact type shows as a chip, with its family's facet marked.
import { FILE_TYPES } from "../../services/data/fileTypes";
import { getFileTypeDefinition } from "../../services/typeUtils";
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

/** A content type without parameters, lowercased: "text/plain; charset=utf-8" → "text/plain". */
export const baseType = (contentType) => (contentType || "").split(";", 1)[0].trim().toLowerCase();
const base = baseType;

/** ?type= holds one exact content type rather than a family. */
export const isExactType = (type) => !!type && type.includes("/");

/** The facet to mark for ?type=: the family itself, or an exact type's family. */
export const facetKeyOf = (type) => (isExactType(type) ? typeFamily(type) : type);

/** An exact type's name for its chip: "Python", or the content type if the catalogue has none. */
export function typeLabel(type) {
  const def = getFileTypeDefinition(type);
  return def.category !== "unknown" && def.label ? def.label : type;
}

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
  if (isExactType(key)) return base(key);
  if (!isTypeFacet(key)) return undefined;
  const set = new Set(
    FILE_TYPES.filter((t) => CATEGORY_CLASS[t.category] === key && t.mime).map((t) => base(t.mime))
  );
  for (const contentType of Object.keys(types ?? {})) {
    if (typeFamily(contentType) === key) set.add(base(contentType));
  }
  return [...set].sort().join(",");
}
