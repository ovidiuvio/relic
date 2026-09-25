// The viewer's display settings, remembered per browser. Keys are the ones the old viewer
// used, so existing preferences carry over.
const FIELDS = {
  syntax: ["relic_editor_syntax_highlighting", true],
  lineNumbers: ["relic_editor_line_numbers", true],
  comments: ["relic_editor_show_comments", true],
  fontSize: ["relic_editor_font_size", 13],
  darkMode: ["relic_editor_dark_mode", true],
  beautify: ["relic_editor_beautify", false],
  lineFilter: ["showLineFilter", false],
  diffView: ["relic_viewer_diff_view_mode", "unified"], // "unified" | "split"
  treeMode: ["relic_viewer_tree_mode", "code"], // "code" | "tree"
  treePageSize: ["relic_viewer_tree_page_size", 100],
};

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (raw == null) return fallback;
    if (typeof fallback === "boolean") return raw === "true";
    if (typeof fallback === "number") return Number.isFinite(Number(raw)) ? Number(raw) : fallback;
    return raw;
  } catch {
    return fallback;
  }
}

export class ViewerPrefs {
  syntax = $state(read(...FIELDS.syntax));
  lineNumbers = $state(read(...FIELDS.lineNumbers));
  comments = $state(read(...FIELDS.comments));
  fontSize = $state(read(...FIELDS.fontSize));
  darkMode = $state(read(...FIELDS.darkMode));
  beautify = $state(read(...FIELDS.beautify));
  lineFilter = $state(read(...FIELDS.lineFilter));
  diffView = $state(read(...FIELDS.diffView));
  treeMode = $state(read(...FIELDS.treeMode));
  treePageSize = $state(read(...FIELDS.treePageSize));

  /** Set a preference and remember it. */
  set(name, value) {
    this[name] = value;
    try {
      localStorage.setItem(FIELDS[name][0], String(value));
    } catch {
      // Not remembered without storage.
    }
  }

  toggle(name) {
    this.set(name, !this[name]);
  }
}
