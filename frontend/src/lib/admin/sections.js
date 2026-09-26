// The admin area's sections, in side-navigation order. Each is a page at /admin/<key>.
export const ADMIN_SECTIONS = [
  { key: "overview", label: "Overview", icon: "gauge" },
  { key: "relics", label: "Relics", icon: "file" },
  { key: "users", label: "Users", icon: "users" },
  { key: "reports", label: "Reports", icon: "flag" },
  { key: "backups", label: "Backups", icon: "database" },
  { key: "jobs", label: "Jobs", icon: "play" },
  { key: "config", label: "Config", icon: "sliders" },
];

export const adminPath = (key) => (key === "overview" ? "/admin" : `/admin/${key}`);
