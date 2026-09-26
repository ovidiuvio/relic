// The search bar's query language: free text plus filter tokens.
//
//   queue handler type:py tag:work by:me in:mine
//
//   type:  a family (code, docs, text, data, images, archives, web), an extension (py), a
//          language (python) or a content type (text/x-python)
//   tag:   one tag
//   by:    me, or an owner's public ID
//   in:    where to search: recent, mine, bookmarks, or a space by name
//
// Values with spaces take quotes: in:"team docs". Anything else, including key:value pairs with
// other keys (a URL, say), is free text. A query maps to a list's URL parameters (?search=,
// ?type=, ?tag=, ?owner=) and back, so the bar always shows what the list is filtered by.
import { FILE_TYPES } from "../../services/data/fileTypes";
import { isTypeFacet, baseType } from "../relics/typeFacets";

export const FILTER_KEYS = ["type", "tag", "by"];
const TOKEN_KEYS = [...FILTER_KEYS, "in"];

const FAMILIES = {
  code: "code", doc: "doc", docs: "doc", text: "text", data: "data",
  image: "image", images: "image", archive: "archive", archives: "archive", web: "web",
};

// A word: runs of anything but spaces and quotes, and quoted runs (which may hold spaces).
const WORD = /(?:[^\s"]+|"[^"]*"?)+/g;
const unquote = (v) => v.replace(/^"|"$/g, "");
const quote = (v) => (/[\s"]/.test(v) ? `"${v.replace(/"/g, "")}"` : v);

/**
 * The query split into segments that cover every character, for drawing the bar:
 * { kind: "text" | "space" | "token", raw, start, end } and, for tokens, { key, value }.
 */
export function segments(text) {
  const out = [];
  let at = 0;
  for (const m of text.matchAll(WORD)) {
    if (m.index > at) out.push({ kind: "space", raw: text.slice(at, m.index), start: at, end: m.index });
    const raw = m[0];
    const t = /^([a-z]+):(.*)$/is.exec(raw);
    const key = t?.[1].toLowerCase();
    const seg = { raw, start: m.index, end: m.index + raw.length };
    out.push(key && TOKEN_KEYS.includes(key) ? { ...seg, kind: "token", key, value: unquote(t[2]) } : { ...seg, kind: "text" });
    at = m.index + raw.length;
  }
  if (at < text.length) out.push({ kind: "space", raw: text.slice(at), start: at, end: text.length });
  return out;
}

/** The query as free text and its tokens (the last of each key wins). */
export function parseQuery(text) {
  const segs = segments(text);
  const tokens = {};
  for (const s of segs) if (s.kind === "token") tokens[s.key] = s.value;
  const search = segs.filter((s) => s.kind === "text").map((s) => s.raw).join(" ");
  return { search, tokens };
}

/** A type: value as the ?type= it means (a family key or a content type), or null. */
export function resolveType(value) {
  const v = (value || "").trim().toLowerCase();
  if (!v) return null;
  if (FAMILIES[v]) return FAMILIES[v];
  if (v.includes("/")) return baseType(v);
  const def =
    FILE_TYPES.find((t) => t.mime && t.extensions?.includes(v)) ??
    FILE_TYPES.find((t) => t.mime && (t.syntax === v || t.label?.toLowerCase() === v));
  return def ? baseType(def.mime) : null;
}

/** A ?type= value as the shortest type: token that means it: code, py, or the content type. */
export function typeToken(type) {
  if (isTypeFacet(type)) return type;
  const def = FILE_TYPES.find((t) => t.mime && baseType(t.mime) === type);
  const ext = def?.extensions?.[0];
  return ext && resolveType(ext) === type ? ext : type;
}

/**
 * The URL filters a query's tokens set, checked against what the scope supports.
 *   ctx: { publicId, filters } — filters: the token keys the scope takes (see searchScope)
 * Returns { params: { search, type, tag, owner }, problems: [message] }.
 */
export function resolveFilters(tokens, ctx) {
  const params = {};
  const problems = [];
  for (const [key, value] of Object.entries(tokens)) {
    if (key === "in") continue;
    if (!ctx.filters.includes(key)) {
      problems.push(`${key}: doesn’t apply here`);
      continue;
    }
    if (key === "type") {
      const type = resolveType(value);
      if (type) params.type = type;
      else problems.push(value ? `No type called “${value}”` : "type: needs a type, like type:py or type:images");
    } else if (key === "tag") {
      const tag = value.trim().toLowerCase();
      if (tag) params.tag = tag;
      else problems.push("tag: needs a tag, like tag:work");
    } else if (key === "by") {
      const v = value.trim().toLowerCase();
      if (v === "me" && ctx.publicId) params.owner = ctx.publicId;
      else if (/^[0-9a-f]{16}$/.test(v)) params.owner = v;
      else problems.push("by: takes me or a public ID");
    }
  }
  return { params, problems };
}

/** The query text for a list's URL filters: free text first, then type:, tag: and by:. */
export function formatQuery({ search, type, tag, owner }, ctx = {}) {
  return [
    search?.trim(),
    type && `type:${quote(typeToken(type))}`,
    tag && `tag:${quote(tag)}`,
    owner && `by:${owner === ctx.publicId ? "me" : owner}`,
  ]
    .filter(Boolean)
    .join(" ");
}

/** Whether two sets of URL filters are the same. */
export function sameFilters(a, b) {
  const norm = (p) => [(p.search || "").trim().replace(/\s+/g, " "), p.type || "", p.tag || "", p.owner || ""].join("\u0000");
  return norm(a) === norm(b);
}

/** Where an in: value points among the built-in lists, or null (it may name a space). */
export function builtinScope(value) {
  const v = (value || "").trim().toLowerCase();
  if (["recent", "public", "everyone", "all"].includes(v)) return "recent";
  if (["mine", "me", "my", "my-relics", "myrelics"].includes(v)) return "my-relics";
  if (["bookmarks", "bookmarked", "saved"].includes(v)) return "my-bookmarks";
  return null;
}
