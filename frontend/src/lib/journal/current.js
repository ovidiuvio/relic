// Which journal a place that has no journal open (the navbar search) means: the one you used
// last, else your first.
import { listMyJournals } from "../../services/api";

export const KEY_JOURNAL = "relic_journal_id";

export async function currentJournalId() {
  let saved = null;
  try {
    saved = localStorage.getItem(KEY_JOURNAL);
  } catch {
    // Not remembered without storage.
  }
  const journals = await listMyJournals();
  return (journals.find((j) => j.id === saved) ?? journals[0])?.id ?? null;
}
