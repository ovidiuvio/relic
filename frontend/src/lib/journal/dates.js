// Dates for the journal. Entry dates are plain calendar days ("2026-09-29"), never converted
// between time zones; "today" is the reader's local day.
const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

const utc = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
};

/** The reader's local date as YYYY-MM-DD. */
export function todayLocal(now = new Date()) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** The reader's local time as HH:MM. */
export function timeLocal(now = new Date()) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

/** { day: 29, weekday: "Tue" } for the date block of a row. */
export function dayParts(iso) {
  const d = utc(iso);
  return { day: d.getUTCDate(), weekday: WEEKDAYS[d.getUTCDay()].slice(0, 3) };
}

/** "Tue 29 Sep 2026". */
export function longDate(iso) {
  const d = utc(iso);
  return `${WEEKDAYS[d.getUTCDay()].slice(0, 3)} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()].slice(0, 3)} ${d.getUTCFullYear()}`;
}

/** "September 2026". */
export function monthLabel(iso) {
  const d = utc(iso);
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/** Entries grouped for the list: pinned first, then by month, keeping their order. */
export function groupEntries(entries) {
  const groups = [];
  const pinned = entries.filter((e) => e.pinned);
  if (pinned.length) groups.push({ key: "pinned", label: "Pinned", entries: pinned });
  for (const e of entries) {
    if (e.pinned) continue;
    const key = e.entry_date.slice(0, 7);
    let g = groups[groups.length - 1];
    if (!g || g.key !== key) {
      g = { key, label: monthLabel(e.entry_date), entries: [] };
      groups.push(g);
    }
    g.entries.push(e);
  }
  return groups;
}

/** "Today · Tue 29 Sep 2026", "Yesterday · …", otherwise just the date. */
export function dayLabel(iso, today = todayLocal()) {
  const days = Math.round((utc(today) - utc(iso)) / 864e5);
  return (days === 0 ? "Today · " : days === 1 ? "Yesterday · " : "") + longDate(iso);
}

/** The date n days after (or before, when negative) another. */
export function addDays(iso, n) {
  const d = utc(iso);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** Whole days from one date to another (b minus a). */
export const daysBetween = (a, b) => Math.round((utc(b) - utc(a)) / 864e5);

/** The month a date is in as "2026-09". */
export const monthKey = (iso) => iso.slice(0, 7);

/** The first day of the month after (or before) a "2026-09" key. */
export function shiftMonth(key, n) {
  const [y, m] = key.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + n, 1));
  return d.toISOString().slice(0, 7);
}

/** "September 2026" for a "2026-09" key. */
export const monthTitle = (key) => monthLabel(`${key}-01`);

/** "Sep 2026" for a "2026-09" key. */
export const monthShort = (key) => `${MONTHS[Number(key.slice(5)) - 1].slice(0, 3)} ${key.slice(0, 4)}`;

/** The weeks of a month, Monday first: 5 or 6 rows of 7 { date, inMonth } cells. */
export function monthGrid(key) {
  const first = `${key}-01`;
  const lead = (utc(first).getUTCDay() + 6) % 7;
  const start = addDays(first, -lead);
  const days = new Date(Date.UTC(Number(key.slice(0, 4)), Number(key.slice(5)), 0)).getUTCDate();
  const rows = Math.ceil((lead + days) / 7);
  return Array.from({ length: rows }, (_, r) =>
    Array.from({ length: 7 }, (_, c) => {
      const date = addDays(start, r * 7 + c);
      return { date, inMonth: monthKey(date) === key };
    })
  );
}
