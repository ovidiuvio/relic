import api from './core'

// A journal is a relic whose content is a folder of Markdown entries (see backend/routes/journal.py).

export async function createJournal(name, accessLevel = 'restricted') {
    const response = await api.post('/journals', { name, access_level: accessLevel })
    return response.data
}

export async function listMyJournals() {
    const response = await api.get('/journals')
    return response.data
}

export async function getJournal(journalId) {
    const response = await api.get(`/journals/${journalId}`)
    return response.data
}

export async function listJournalEntries(journalId, params = {}) {
    return api.get(`/journals/${journalId}/entries`, { params })
}

export async function getJournalDays(journalId, params = {}) {
    const response = await api.get(`/journals/${journalId}/days`, { params })
    return response.data
}

export async function getJournalEntry(journalId, entryId) {
    const response = await api.get(`/journals/${journalId}/entries/${entryId}`)
    return response.data
}

export async function createJournalEntry(journalId, entry) {
    const response = await api.post(`/journals/${journalId}/entries`, entry)
    return response.data
}

export async function updateJournalEntry(journalId, entryId, changes) {
    const response = await api.patch(`/journals/${journalId}/entries/${entryId}`, changes)
    return response.data
}

export async function deleteJournalEntry(journalId, entryId) {
    return api.delete(`/journals/${journalId}/entries/${entryId}`)
}

// The daily entry for a date (YYYY-MM-DD, the caller's local date), created if missing.
export async function openDailyEntry(journalId, entryDate) {
    const response = await api.post(`/journals/${journalId}/daily`, { entry_date: entryDate })
    return response.data
}

// Quick capture: add a line to the day's Log. `time` is the caller's local HH:MM.
export async function appendToJournal(journalId, { text, entryDate, time, heading }) {
    const response = await api.post(`/journals/${journalId}/append`, {
        text,
        entry_date: entryDate,
        time,
        heading,
    })
    return response.data
}

// The whole journal as a .zip (a Blob): every entry as a Markdown file with front matter.
export async function exportJournal(journalId) {
    const response = await api.get(`/journals/${journalId}/export`, { responseType: 'blob' })
    const name = /filename="([^"]+)"/.exec(response.headers?.['content-disposition'] ?? '')?.[1]
    return { blob: response.data, filename: name || 'journal.zip' }
}

// What [[links]] and ![[embeds]] point at: { "target": { kind: "entry" | "relic" | "missing", ... } },
// keyed by the lowercased target.
export async function resolveJournalLinks(journalId, targets) {
    const response = await api.post(`/journals/${journalId}/resolve`, { targets })
    return response.data
}

// The other entries of the journal that link to this one.
export async function getEntryBacklinks(journalId, entryId) {
    const response = await api.get(`/journals/${journalId}/entries/${entryId}/backlinks`)
    return response.data.entries
}

// Entries in your journals that mention a relic (private to you).
export async function getJournalMentions(relicId) {
    const response = await api.get(`/journals/mentions/${relicId}`)
    return response.data.entries
}

export async function listEntryRevisions(journalId, entryId) {
    const response = await api.get(`/journals/${journalId}/entries/${entryId}/revisions`)
    return response.data.revisions
}

export async function keepEntryVersion(journalId, entryId) {
    const response = await api.post(`/journals/${journalId}/entries/${entryId}/revisions`)
    return response.data
}

export async function restoreEntryRevision(journalId, entryId, revisionId) {
    const response = await api.post(`/journals/${journalId}/entries/${entryId}/revisions/${revisionId}/restore`)
    return response.data
}

// Add Markdown files (or zips of them) to a journal: { imported, entries, skipped: [{ name, reason }] }.
export async function importJournalEntries(journalId, files) {
    const form = new FormData()
    for (const file of files) form.append('files', file, file.name)
    const response = await api.post(`/journals/${journalId}/import`, form, { headers: { 'Content-Type': undefined } })
    return response.data
}
