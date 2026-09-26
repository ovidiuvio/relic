// Querying a search scope's list directly (for the dropdown's matches and the tag suggestions),
// the same way the scope's own page does. Returns { relics, total, facets }.
import { listRelics, searchEverywhere, getUserRelics, getUserBookmarks, getAdminRelics, spaces as spacesApi } from "../../services/api";
import { facetTypes } from "../relics/typeFacets";
import { rangeParams } from "./ranges";

const shape = (data, rows = "relics") => ({ relics: data?.[rows] ?? [], total: data?.total ?? 0, facets: data?.facets ?? null });

/**
 * filters: { search, type, tag, owner } as in the URL; options: { limit, facets, relevance }
 * (relevance: best name matches first, when there's text to match).
 * Resolves to null for a scope that isn't a relic list (spaces, users).
 */
export function fetchScope(scope, filters = {}, { limit = 7, facets = false, relevance = false } = {}) {
  const params = {
    limit,
    search: filters.search || undefined,
    tag: filters.tag || undefined,
    owner: filters.owner || undefined,
    types: facetTypes(filters.type || null),
    facets: facets || undefined,
    sort_by: relevance && filters.search ? "relevance" : undefined,
    ...rangeParams(filters),
  };
  const key = scope.key;
  if (key === "everywhere") return searchEverywhere(params).then((r) => shape(r.data));
  if (key === "recent") return listRelics(params).then((r) => shape(r.data));
  if (key === "my-relics") return getUserRelics(params).then((r) => shape(r.data));
  if (key === "my-bookmarks") return getUserBookmarks(params).then((r) => shape(r.data, "bookmarks"));
  if (key.startsWith("space:")) return spacesApi.getRelics(key.slice(6), params).then((d) => shape(d));
  if (key === "admin-relics") {
    return getAdminRelics(limit, 0, null, null, params.search, params.tag, "created_at", "desc", { types: params.types, facets, ...rangeParams(filters) }).then((r) => shape(r.data));
  }
  return Promise.resolve(null);
}
