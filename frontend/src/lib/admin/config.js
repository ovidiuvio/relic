// Server configuration as the admin API reports it: { section: { KEY: value } }.

export const CONFIG_SECTIONS = { app: "App", database: "Database", storage: "Storage", upload: "Uploads", backup: "Backups", cors: "CORS" };

/** One row per setting: { key, section, sectionLabel, value }. The admin list has its own view. */
export function configRows(config) {
  if (!config) return [];
  return Object.entries(config)
    .filter(([section]) => section !== "admin")
    .flatMap(([section, values]) =>
      Object.entries(values).map(([key, value]) => ({ key, section, sectionLabel: CONFIG_SECTIONS[section] || section, value }))
    );
}

/** A value as text: lists comma-separated, booleans on/off, blanks said so. */
export function settingValue(value) {
  if (typeof value === "boolean") return value ? "on" : "off";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "(empty)";
  if (value === "" || value == null) return "(not set)";
  return String(value);
}
