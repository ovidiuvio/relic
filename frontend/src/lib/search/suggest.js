// What the search panel offers while you type: the filter keys that match the word under the
// caret (ty → type:), or values for the token you're in (type:p → py, pdf…; tag:, by:, in:).
// Picking one replaces that word or token.
import { FILE_TYPES } from "../../services/data/fileTypes";
import { segments } from "./query";

/** One line of help per filter key, for the panel's "Narrow with" row. */
export const KEY_HELP = {
  type: { example: "type:py", text: "file type" },
  tag: { example: "tag:work", text: "a tag" },
  by: { example: "by:me", text: "owner" },
  in: { example: "in:mine", text: "where" },
};

const FAMILIES = [
  ["code", "Code"], ["docs", "Docs"], ["text", "Text"], ["data", "Data"],
  ["images", "Images"], ["archives", "Archives"], ["web", "Web"],
];

const LISTS = [
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
 *   data: { keys, tags: [{ name, count }], spaces: [{ id, name }], scopeLabel }
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
    const items = [];
    const seen = new Set();
    for (const [key, label] of FAMILIES) {
      if (starts(key)) items.push({ label: `type:${key}`, detail: `${label}, every kind`, ...at(`type:${key}`) });
    }
    for (const t of FILE_TYPES) {
      const ext = t.extensions?.[0];
      if (!t.mime || !ext || seen.has(t.mime)) continue;
      if (v && !(t.extensions.some(starts) || starts(t.label || ""))) continue;
      if (!v && !["py", "js", "json", "md", "txt", "csv", "pdf", "zip", "png", "html", "yaml", "sh"].includes(ext)) continue;
      seen.add(t.mime);
      const shown = t.extensions.find(starts) ?? ext;
      items.push({ label: `type:${shown}`, detail: t.label, ...at(`type:${shown}`) });
    }
    return { heading: "Types", items: items.slice(0, 9) };
  }
  if (ctx.key === "tag") {
    const items = (data.tags ?? [])
      .filter((t) => !v || t.name.toLowerCase().includes(v))
      .slice(0, 9)
      .map((t) => ({ label: `tag:${t.name}`, detail: "", count: t.count, ...at(`tag:${quote(t.name)}`) }));
    return { heading: data.tags ? `Top tags in ${data.scopeLabel}` : "Tags", items };
  }
  if (ctx.key === "by") {
    const items = "me".startsWith(v) ? [{ label: "by:me", detail: "your relics", ...at("by:me") }] : [];
    return { heading: "Owner", items, note: "or someone’s public ID: click their name in a list" };
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
