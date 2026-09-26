// Search history for the search bar and the sidebar:
//   recent: searches you ran in this browser (the last 20, newest first)
//   pinned: searches you pinned, kept on the server so they follow your key to other devices
// An entry is { query, path, label }: the query as you typed it, the list URL it ran on
// (with its filters and sort) and the list's name. Running one again opens its path.
import { getSavedSearches, createSavedSearch, renameSavedSearch, deleteSavedSearch } from "../../services/api";

const KEY = "relic.searchHistory.v1";
const MAX_RECENT = 20;

const appPath = (p) => typeof p === "string" && p.startsWith("/") && !p.startsWith("//");

function readRecent() {
  try {
    const list = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(list) ? list.filter((e) => e && typeof e.query === "string" && appPath(e.path)) : [];
  } catch {
    return [];
  }
}

function writeRecent(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch {
    // Storage can be unavailable (private windows); history then lasts for the page.
  }
}

/** The list a path belongs to, for showing where an entry runs. */
export function pathLabel(path, spaces = []) {
  const p = path.split("?")[0];
  if (p === "/recent") return "Recent";
  if (p === "/my-relics") return "My relics";
  if (p === "/my-bookmarks") return "Bookmarks";
  if (p === "/spaces") return "Spaces";
  if (p === "/admin/relics") return "All relics";
  if (p === "/admin/users") return "Users";
  const space = /^\/spaces\/([^/]+)$/.exec(p);
  if (space) return spaces.find((s) => s.id === space[1])?.name || "A space";
  return "Search";
}

class SearchHistory {
  recent = $state(readRecent());
  pinned = $state(null); // null until loaded from the server
  #loading = null;

  /** Remember a search that ran. Running the same list URL again moves it to the top. */
  record({ query, path, label }) {
    if (!query?.trim() || !appPath(path)) return;
    const list = [{ query: query.trim(), path, label }, ...this.recent.filter((e) => e.path !== path)].slice(0, MAX_RECENT);
    this.recent = list;
    writeRecent(list);
  }

  forget(path) {
    this.recent = this.recent.filter((e) => e.path !== path);
    writeRecent(this.recent);
  }

  clear() {
    this.recent = [];
    writeRecent([]);
  }

  load() {
    if (this.pinned || this.#loading) return this.#loading;
    this.#loading = getSavedSearches()
      .then(({ data }) => (this.pinned = data.searches ?? []))
      .catch(() => (this.pinned = this.pinned ?? []))
      .finally(() => (this.#loading = null));
    return this.#loading;
  }

  pinnedFor(path) {
    return this.pinned?.find((p) => p.path === path) ?? null;
  }

  async pin({ query, path, name = null }) {
    const { data } = await createSavedSearch({ query, path, name });
    this.pinned = [...(this.pinned ?? []).filter((p) => p.id !== data.id), data];
    return data;
  }

  async unpin(id) {
    await deleteSavedSearch(id);
    this.pinned = (this.pinned ?? []).filter((p) => p.id !== id);
  }

  async rename(id, name) {
    const { data } = await renameSavedSearch(id, name);
    this.pinned = (this.pinned ?? []).map((p) => (p.id === id ? data : p));
  }
}

export const searchHistory = new SearchHistory();
