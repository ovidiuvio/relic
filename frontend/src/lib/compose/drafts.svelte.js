// Autosaved drafts of the New relic editor, kept in this browser (up to 20, newest first).
// Same storage key and shape as the old form, so existing drafts carry over.
const KEY = "relic_drafts";
const LIMIT = 20;

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

function write(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch {
    // Drafts need storage; without it the editor still works.
  }
}

export class Drafts {
  list = $state(read());
  currentId = $state(null);
  savedAt = $state(null);

  /** Save the editor's state as the current draft (creating it on first save). */
  save({ title, content, syntax, tags }) {
    if (!content.trim()) return;
    const id = this.currentId ?? Math.random().toString(36).slice(2, 11);
    const draft = { id, title: title || "Untitled draft", content, syntax, tags, updatedAt: new Date().toISOString() };
    const others = read().filter((d) => d.id !== id);
    this.list = [draft, ...others].slice(0, LIMIT);
    write(this.list);
    this.currentId = id;
    this.savedAt = new Date();
  }

  remove(id) {
    this.list = read().filter((d) => d.id !== id);
    write(this.list);
    if (this.currentId === id) {
      this.currentId = null;
      this.savedAt = null;
    }
  }

  /** Put a removed draft back (Undo). */
  restoreRemoved(draft) {
    this.list = [draft, ...read()].slice(0, LIMIT);
    write(this.list);
  }

  open(draft) {
    this.currentId = draft.id;
    this.savedAt = new Date(draft.updatedAt);
  }

  /** Start fresh: the next save makes a new draft. */
  detach() {
    this.currentId = null;
    this.savedAt = null;
  }
}
