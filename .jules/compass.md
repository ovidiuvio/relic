
## 2024-03-18 — Missed Syncs for Bookmarks, Editing, and Excalidraw Types
**Finding:** The backend `RelicResponse` added `bookmark_count` and `can_edit` fields which were consumed in JS (e.g., `frontend/src/components/RelicTable.svelte` uses `bookmark_count`, and `frontend/src/components/RelicHeader.svelte` uses `can_edit`), but these were entirely missed in the Go CLI client `cli/client/pkg/relic/types.go` struct.
The MIME registry also drifted: `frontend/src/services/data/fileTypes.js` included an entry for 'excalidraw' (`application/vnd.excalidraw+json`) while `cli/client/internal/upload/mime.go` did not.
**Action:** When auditing `RelicResponse`, make sure new feature indicators like `can_edit` and interaction counts like `bookmark_count` are propagated to Go. Always verify complex drawing tools or app-specific formats added in frontend file types also have an equivalent mapped in the Go `mime.go`.
