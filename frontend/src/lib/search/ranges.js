// Date and size filters: after:, before: and size:, as the URL keeps them (what you typed:
// ?after=7d, ?size=>1mb) and as the API takes them (created_after/created_before as instants,
// min_size/max_size in bytes). Dates resolve when the list loads, in your timezone, so a pinned
// "after:7d" always means the last seven days.
//
//   after:today  after:yesterday  after:mon (since Monday)  after:7d  after:2w  after:3m  after:1y
//   after:2026-09-01  after:2026-09  after:2026           (before: takes the same)
//   size:>1mb  size:>=500kb  size:<10kb  size:1mb..5mb    (units: b, kb, mb, gb; 1 kb = 1024 b)

const WEEKDAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
const UNITS = { b: 1, k: 1024, kb: 1024, m: 1024 ** 2, mb: 1024 ** 2, g: 1024 ** 3, gb: 1024 ** 3, t: 1024 ** 4, tb: 1024 ** 4 };

const midnight = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

/** The instant a date value names (local time), or null if it isn't one. */
export function parseDate(value, now = new Date()) {
  const v = (value || "").trim().toLowerCase();
  if (!v) return null;
  if (v === "today") return midnight(now);
  if (v === "yesterday") return new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
  // A weekday, by at least its first three letters: the most recent one (today, if it's today).
  const day = v.length >= 3 ? WEEKDAYS.findIndex((d) => d.startsWith(v)) : -1;
  if (day >= 0) {
    const back = (now.getDay() - day + 7) % 7;
    return new Date(now.getFullYear(), now.getMonth(), now.getDate() - back);
  }
  const rel = /^(\d{1,4})(h|d|w|m|y)$/.exec(v);
  if (rel) {
    const n = Number(rel[1]);
    const d = new Date(now);
    if (rel[2] === "h") d.setHours(d.getHours() - n);
    if (rel[2] === "d") d.setDate(d.getDate() - n);
    if (rel[2] === "w") d.setDate(d.getDate() - 7 * n);
    if (rel[2] === "m") d.setMonth(d.getMonth() - n);
    if (rel[2] === "y") d.setFullYear(d.getFullYear() - n);
    return d;
  }
  const abs = /^(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?$/.exec(v);
  if (abs) {
    const [y, m = 1, dd = 1] = [Number(abs[1]), Number(abs[2] ?? 1), Number(abs[3] ?? 1)];
    const d = new Date(y, m - 1, dd);
    // Reject dates that rolled over (2026-02-30).
    if (d.getFullYear() !== y || d.getMonth() !== m - 1 || d.getDate() !== dd) return null;
    return d;
  }
  return null;
}

function bytes(text) {
  const m = /^(\d+(?:\.\d+)?)(b|kb?|mb?|gb?|tb?)?$/.exec(text);
  if (!m) return null;
  return Math.round(Number(m[1]) * UNITS[m[2] ?? "b"]);
}

/** { min, max } in bytes (inclusive, either may be missing) for a size value, or null. */
export function parseSize(value) {
  const v = (value || "").trim().toLowerCase().replace(/\s+/g, "");
  const range = /^(.+)\.\.(.+)$/.exec(v);
  if (range) {
    const [lo, hi] = [bytes(range[1]), bytes(range[2])];
    return lo != null && hi != null && lo <= hi ? { min: lo, max: hi } : null;
  }
  const m = /^(>=|<=|>|<)(.+)$/.exec(v);
  if (!m) return null;
  const n = bytes(m[2]);
  if (n == null) return null;
  if (m[1] === ">") return { min: n + 1 };
  if (m[1] === ">=") return { min: n };
  if (m[1] === "<") return { max: Math.max(0, n - 1) };
  return { max: n };
}

/** The API parameters for a list's after/before/size filters (URL values). */
export function rangeParams({ after, before, size } = {}, now = new Date()) {
  const out = {};
  const a = parseDate(after, now);
  const b = parseDate(before, now);
  const s = size ? parseSize(size) : null;
  if (a) out.created_after = a.toISOString();
  if (b) out.created_before = b.toISOString();
  if (s?.min != null) out.min_size = s.min;
  if (s?.max != null) out.max_size = s.max;
  return out;
}

/** A value as the URL keeps it: lowercase, no spaces. */
export const normalizeRange = (value) => (value || "").trim().toLowerCase().replace(/\s+/g, "");
