// What the search panel offers while you type: the filter keys that match the word under the
// caret (ty → type:), or values for the token you're in (type:p → py, pdf…; tag:, by:, in:).
// Picking one replaces that word or token.
import { FILE_TYPES } from "../../services/data/fileTypes";
import { segments } from "./query";
import { facetCounts, baseType } from "../relics/typeFacets";

/** One line of help per filter key, for the panel's "Narrow with" row. */
export const KEY_HELP = {
  type: { example: "type:py", text: "file type" },
  tag: { example: "tag:work", text: "a tag" },
  by: { example: "by:me", text: "owner" },
  in: { example: "in:mine", text: "where" },
  after: { example: "after:7d", text: "since" },
  before: { example: "before:2026-01-01", text: "until" },
  size: { example: "size:>1mb", text: "size" },
  is: { example: "is:private", text: "visibility" },
  from: { example: "from:shared", text: "why you see it" },
};

const VISIBILITY_VALUES = [
  ["public", "listed in Recent"],
  ["private", "anyone with the link"],
  ["restricted", "only people added"],
];
const SOURCE_VALUES = [
  ["yours", "relics you own"],
  ["bookmarked", "relics you bookmarked"],
  ["shared", "restricted, shared with you"],
  ["spaces", "in spaces you’re in"],
  ["public", "listed for everyone"],
];

const FAMILY_KEY = { code: "code", docs: "doc", text: "text", data: "data", images: "image", archives: "archive", web: "web" };

function dateValues(key, now = new Date()) {
  const since = key === "after";
  const monthStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const monthName = now.toLocaleString("en-US", { month: "long" });
  return [
    ["today", since ? "created today" : "before today"],
    ["yesterday", since ? "since yesterday" : "before yesterday"],
    ["mon", since ? "since Monday" : "before Monday"],
    ["7d", since ? "in the last 7 days" : "more than 7 days ago"],
    ["30d", since ? "in the last 30 days" : "more than 30 days ago"],
    [monthStart, since ? `since the start of ${monthName}` : `before ${monthName}`],
    ["1y", since ? "in the last year" : "more than a year ago"],
  ];
}

const SIZE_VALUES = [
  [">1mb", "over 1 MB"],
  [">100mb", "over 100 MB"],
  ["<10kb", "under 10 KB"],
  ["<1mb", "under 1 MB"],
  ["1mb..10mb", "1 to 10 MB"],
];

const FAMILIES = [
  ["code", "Code"], ["docs", "Docs"], ["text", "Text"], ["data", "Data"],
  ["images", "Images"], ["archives", "Archives"], ["web", "Web"],
];

const LISTS = [
  ["everywhere", "Everywhere", "everything you can see"],
  ["recent", "Recent", "public relics"],
  ["mine", "My relics", "yours"],
  ["bookmarks", "Bookmarks", "what you saved"],
];

const quote = (v) => (/\s/.test(v) ? `"${v}"` : v);

/** The word or token the caret is in or just after; an empty word between words. */
export function caretContext(text, caret) {
  for (const s of segments(text)) {
    if (s.kind !== "space" && caret >= s.start && caret <= s.end) return s;
  }
  return { kind: "text", raw: "", start: caret, end: caret };
}

/**
 * Suggestions for the caret's context:
 *   { heading, items: [{ label, detail, count?, insert, from, to, done }] }
 * `done` says the token is complete (the panel then shows the next thing to type).
 *   data: { keys, tags: [{ name, count }], typeCounts: { contentType: count }, inResults,
 *           spaces: [{ id, name }], scopeLabel }
 * With typeCounts, types show how many relics each would give (inResults: counted in the
 * results of the rest of the query, not the whole list).
 */
export function suggest(text, caret, data) {
  const ctx = caretContext(text, caret);
  const at = (insert, done = true) => ({ insert: done ? `${insert} ` : insert, from: ctx.start, to: ctx.end, done });

  if (ctx.kind === "text") {
    const word = ctx.raw.toLowerCase();
    if (!word || !/^[a-z]+$/.test(word)) return { heading: null, items: [] };
    const items = data.keys
      .filter((k) => k.startsWith(word) && k !== word)
      .map((k) => ({ label: `${k}:`, detail: KEY_HELP[k].text, ...at(`${k}:`, false) }));
    return { heading: "Filters", items };
  }

  const v = ctx.value.toLowerCase();
  const starts = (s) => s.toLowerCase().startsWith(v);
  if (ctx.key === "type") {
    const counts = data.typeCounts ?? null;
    const family = counts ? facetCounts(counts) : null;
    const countOf = (mime) => (counts ? counts[baseType(mime)] ?? 0 : null);
    const items = [];
    const seen = new Set();
    for (const [key, label] of FAMILIES) {
      if (!starts(key)) continue;
      const count = family ? family[FAMILY_KEY[key]] : null;
      if (!v && count === 0) continue; // an empty family isn't worth offering
      items.push({ label: `type:${key}`, detail: `${label}, every kind`, count, ...at(`type:${key}`) });
    }
    const typed = [];
    for (const t of FILE_TYPES) {
      const ext = t.extensions?.[0];
      if (!t.mime || !ext || seen.has(baseType(t.mime))) continue;
      const count = countOf(t.mime);
      if (v && !(t.extensions.some(starts) || starts(t.label || ""))) continue;
      // Nothing typed yet: the types these results have, or a few common ones.
      if (!v && (counts ? !count : !["py", "js", "json", "md", "txt", "csv", "pdf", "zip", "png", "html", "yaml", "sh"].includes(ext))) continue;
      seen.add(baseType(t.mime));
      const shown = t.extensions.find(starts) ?? ext;
      typed.push({ label: `type:${shown}`, detail: t.label, count, ...at(`type:${shown}`) });
    }
    if (counts) {
      items.sort((a, b) => b.count - a.count);
      typed.sort((a, b) => b.count - a.count);
    }
    const heading = counts ? (data.inResults ? "Types in these results" : `Types in ${data.scopeLabel}`) : "Types";
    const all = [...items, ...typed].slice(0, 9);
    const note = counts && !all.length ? (v ? `No type starting with “${ctx.value}” here` : "Nothing here to narrow by type") : null;
    return { heading, items: all, note };
  }
  if (ctx.key === "after" || ctx.key === "before") {
    const items = dateValues(ctx.key)
      .filter(([value]) => value.startsWith(v))
      .map(([value, detail]) => ({ label: `${ctx.key}:${value}`, detail, ...at(`${ctx.key}:${value}`) }));
    return { heading: ctx.key === "after" ? "Created since" : "Created before", items, note: "or a date: 2026-09-01, 2026-09, 2026; or 12h, 3d, 2w, 6m, 1y ago" };
  }
  if (ctx.key === "size") {
    const items = SIZE_VALUES.filter(([value]) => value.startsWith(v)).map(([value, detail]) => ({ label: `size:${value}`, detail, ...at(`size:${value}`) }));
    return { heading: "Size", items, note: "> >= < <= a size, or a range: 1mb..5mb (b, kb, mb, gb)" };
  }
  if (ctx.key === "tag") {
    const counted = (data.tags ?? []).filter((t) => !v || t.name.toLowerCase().includes(v));
    const known = new Set(counted.map((t) => t.name));
    // Tags you can see beyond the counted top ones (what you've typed may be a rare one).
    const more = (data.moreTags ?? []).filter((t) => !known.has(t.name));
    const items = [
      ...counted.map((t) => ({ label: `tag:${t.name}`, detail: "", count: t.count, ...at(`tag:${quote(t.name)}`) })),
      ...more.map((t) => ({ label: `tag:${t.name}`, detail: data.inResults || data.tags ? "elsewhere" : "", count: data.inResults || data.tags ? null : t.count, ...at(`tag:${quote(t.name)}`) })),
    ].slice(0, 9);
    const note = data.tags && !items.length ? (v ? `No tag like “${ctx.value}” you can see` : `None of ${data.inResults ? "these results" : "these relics"} has a tag`) : null;
    return { heading: !data.tags ? "Tags" : data.inResults ? "Tags in these results" : `Top tags in ${data.scopeLabel}`, items, note };
  }
  if (ctx.key === "is" || ctx.key === "from") {
    const values = ctx.key === "is" ? VISIBILITY_VALUES : SOURCE_VALUES;
    const items = values.filter(([value]) => value.startsWith(v)).map(([value, detail]) => ({ label: `${ctx.key}:${value}`, detail, ...at(`${ctx.key}:${value}`) }));
    return { heading: ctx.key === "is" ? "Visibility" : "Why you see it (Everywhere)", items };
  }
  if (ctx.key === "by") {
    const items = "me".startsWith(v) ? [{ label: "by:me", detail: "your relics", ...at("by:me") }] : [];
    return { heading: "Owner", items, note: "or a name (by:\"Mara Ionescu\") or a public ID; clicking a name in a list does it too" };
  }
  if (ctx.key === "in") {
    const items = [
      ...LISTS.filter(([key, label]) => starts(key) || starts(label)).map(([key, label, detail]) => ({ label: `in:${key}`, detail: `${label}, ${detail}`, ...at(`in:${key}`) })),
      ...(data.spaces ?? [])
        .filter((s) => s.name && (s.name.toLowerCase().includes(v) || s.id.startsWith(v)))
        .slice(0, 8)
        .map((s) => ({ label: `in:${quote(s.name)}`, detail: "space", ...at(`in:${quote(s.name)}`) })),
    ];
    return { heading: "Lists and spaces", items };
  }
  return { heading: null, items: [] };
}

/** The query with a suggestion applied, and where the caret goes. */
export function applySuggestion(text, item) {
  let after = text.slice(item.to);
  if (item.insert.endsWith(" ") && after.startsWith(" ")) after = after.slice(1);
  const next = text.slice(0, item.from) + item.insert + after;
  return { text: next, caret: item.from + item.insert.length };
}
