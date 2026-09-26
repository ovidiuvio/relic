// Formatting for relic lists and the inspector, per the design system's RelicList spec.
import { getFileTypeDefinition } from "../../services/typeUtils";

/** 58597 → "58.6K"; small numbers stay as they are. */
export function compactNumber(n) {
  if (n == null) return "";
  if (n < 1000) return String(n);
  if (n < 1e6) return `${(n / 1e3).toFixed(n < 1e4 ? 1 : 0).replace(/\.0$/, "")}K`;
  return `${(n / 1e6).toFixed(1).replace(/\.0$/, "")}M`;
}

/** 7 → "7B", 1337 → "1.3K", 1468006 → "1.4M". */
export function compactBytes(bytes) {
  if (bytes == null) return "";
  const units = ["B", "K", "M", "G", "T"];
  let i = 0;
  let v = bytes;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return i === 0 ? `${v}B` : `${v < 10 ? v.toFixed(1).replace(/\.0$/, "") : Math.round(v)}${units[i]}`;
}

/** 24-hour clock time, "14:52". */
export function clockTime(date) {
  const d = new Date(date);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/** "14 Jul": fits the list's narrow time column. */
export function dayMonth(date) {
  const d = new Date(date);
  return `${String(d.getDate()).padStart(2, " ")} ${d.toLocaleDateString("en-US", { month: "short" })}`;
}

/** "Sep 24" this year, "Sep 24, 2025" before. */
export function shortDate(date) {
  const d = new Date(date);
  const opts = { month: "short", day: "numeric" };
  if (d.getFullYear() !== new Date().getFullYear()) opts.year = "numeric";
  return d.toLocaleDateString("en-US", opts);
}

/** "2026-09-25 14:52" for the inspector's details. */
export function fullDate(date) {
  const d = new Date(date);
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${clockTime(d)}`;
}

const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

/**
 * The day header a date falls under: Today, Yesterday, weekday names for this week,
 * then month and year. Returns { key, label, date } where date is the grey part.
 */
export function dayGroup(date, now = new Date()) {
  const d = new Date(date);
  const days = Math.round((startOfDay(now) - startOfDay(d)) / 86400000);
  const monthDay = d.toLocaleDateString("en-US", { month: "long", day: "numeric" });
  if (days <= 0) return { key: "today", label: "Today", date: monthDay };
  if (days === 1) return { key: "yesterday", label: "Yesterday", date: monthDay };
  if (days < 7) return { key: `d${days}`, label: d.toLocaleDateString("en-US", { weekday: "long" }), date: monthDay };
  const key = `m${d.getFullYear()}-${d.getMonth()}`;
  return { key, label: d.toLocaleDateString("en-US", { month: "long", year: "numeric" }), date: "" };
}

// File-type categories onto the design system's eight type colours.
const CATEGORY_CLASS = {
  code: "code",
  diff: "code",
  text: "text",
  markdown: "doc",
  pdf: "doc",
  csv: "data",
  relicindex: "data",
  archive: "archive",
  image: "image",
  excalidraw: "image",
  html: "web",
};

/** { cls, label } for the type badge: the r-t- class and a short extension-like label. */
export function typeBadge(relic) {
  const def = getFileTypeDefinition(relic.content_type);
  const cls = CATEGORY_CLASS[def.category] ?? "binary";
  const fromName = relic.name?.match(/\.([a-z][a-z0-9]{0,4})$/i)?.[1]?.toLowerCase();
  const known = def.category !== "unknown";
  const label = fromName || (known && (def.extensions?.[0] || def.syntax?.slice(0, 4))) || "bin";
  // The badge column is 34px: long extensions (gitignore, excalidraw) are cut to five letters.
  return { cls, label: label.slice(0, 5), name: def.label };
}

export const tagName = (t) => (typeof t === "string" ? t : t.name);

/** Middle-truncate long names so the end (often a version or extension) stays readable. */
export function middleTruncate(text, max = 64) {
  if (!text || text.length <= max) return text;
  const head = Math.ceil((max - 1) * 0.6);
  return `${text.slice(0, head)}…${text.slice(text.length - (max - 1 - head))}`;
}

/** { text: "expires 6 d", soon } for a row marker, or null when the relic never expires. */
export function expiryMarker(expiresAt, now = new Date()) {
  if (!expiresAt) return null;
  const ms = new Date(expiresAt) - now;
  const h = ms / 3600000;
  let text;
  if (ms <= 0) text = "expired";
  else if (h < 1) text = `expires ${Math.max(1, Math.round(ms / 60000))} min`;
  else if (h < 48) text = `expires ${Math.round(h)} h`;
  else text = `expires ${Math.round(h / 24)} d`;
  return { text, soon: h < 24 * 7 };
}

/**
 * How notable a counter is: "high" | "medium" | "low" | null. Same fixed thresholds as the
 * viewer's comment glyphs; views run naturally higher, so their scale is 10× wider.
 */
export function counterLevel(value, isViews = false) {
  if (!value || value <= 0) return null;
  const [low, medium, high] = isViews ? [10, 50, 100] : [2, 5, 10];
  if (value >= high) return "high";
  if (value >= medium) return "medium";
  if (value >= low) return "low";
  return null;
}

/** Short relative time, per the design system: "just now", "14 min ago", "6 h ago", "yesterday", "3 d ago"; "in 5 min" ahead. */
export function relativeTime(date, now = new Date()) {
  const ms = now - new Date(date);
  const future = ms < 0;
  const min = Math.round(Math.abs(ms) / 60000);
  let text;
  if (min < 1) return future ? "in under a minute" : "just now";
  if (min < 60) text = `${min} min`;
  else if (min < 48 * 60) {
    const h = Math.round(min / 60);
    if (!future && h >= 24) return "yesterday";
    text = `${h} h`;
  } else if (min < 60 * 24 * 60) text = `${Math.round(min / 1440)} d`;
  else return shortDate(date);
  return future ? `in ${text}` : `${text} ago`;
}
