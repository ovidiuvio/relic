// Journals you pinned: they list first in the journal switcher and are the ones the sidebar shows
// (with none pinned, the sidebar shows them all). Kept in this browser, like pinned spaces.
const KEY = "relic.pinnedJournals.v1";

function read() {
  try {
    const list = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(list) ? list.filter((j) => j && typeof j.id === "string") : [];
  } catch {
    return [];
  }
}

class PinnedJournals {
  list = $state(read());

  has(id) {
    return this.list.some((j) => j.id === id);
  }

  /** Pin a journal, or unpin it when it already is. */
  toggle(journal) {
    this.list = this.has(journal.id) ? this.list.filter((j) => j.id !== journal.id) : [...this.list, { id: journal.id, name: journal.name ?? "" }];
    try {
      localStorage.setItem(KEY, JSON.stringify(this.list));
    } catch {
      // Storage can be unavailable (private windows); pins then last for the page.
    }
  }

  /** A list of journals with the pinned ones first, each in its own order. */
  sorted(journals) {
    return [...journals.filter((j) => this.has(j.id)), ...journals.filter((j) => !this.has(j.id))];
  }
}

export const pinnedJournals = new PinnedJournals();
