// Spaces you pinned to the sidebar. Kept in this browser (like recent searches), so the
// entry carries the name it had when pinned; the sidebar uses a fresher one when it knows it.
const KEY = "relic.pinnedSpaces.v1";

function read() {
  try {
    const list = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(list) ? list.filter((s) => s && typeof s.id === "string" && typeof s.name === "string") : [];
  } catch {
    return [];
  }
}

class PinnedSpaces {
  list = $state(read());

  has(id) {
    return this.list.some((s) => s.id === id);
  }

  /** Pin a space, or unpin it when it already is. */
  toggle(space) {
    this.list = this.has(space.id)
      ? this.list.filter((s) => s.id !== space.id)
      : [...this.list, { id: space.id, name: space.name, visibility: space.visibility }];
    try {
      localStorage.setItem(KEY, JSON.stringify(this.list));
    } catch {
      // Storage can be unavailable (private windows); pins then last for the page.
    }
  }
}

export const pinnedSpaces = new PinnedSpaces();
