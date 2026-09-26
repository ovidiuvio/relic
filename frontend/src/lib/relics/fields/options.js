// Choices shared by the forms that set a relic's options (new relic, fork, edit details).

export const VISIBILITY = [
  { value: "public", icon: "globe", label: "Public", hint: "Listed in Recent and search" },
  { value: "private", icon: "lock", label: "Private", hint: "Anyone with the link" },
  { value: "restricted", icon: "users", label: "Restricted", hint: "Only people you add" },
];

// Expiry presets as the API's duration strings; "custom" lets you type a number and unit.
export const EXPIRY = [
  ["never", "Never"],
  ["10m", "10 min"],
  ["1h", "1 hour"],
  ["12h", "12 hours"],
  ["24h", "24 hours"],
  ["3d", "3 days"],
  ["7d", "7 days"],
  ["30d", "30 days"],
  ["1y", "1 year"],
];

export const EXPIRY_UNITS = [
  ["m", "minutes"],
  ["h", "hours"],
  ["d", "days"],
  ["w", "weeks"],
  ["y", "years"],
];
