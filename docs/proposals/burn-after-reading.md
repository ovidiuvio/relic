# ✨ Spark: "Burn After Reading" (Single-View Relics)

## 📖 User Story
As a security-conscious user sharing sensitive information (e.g., API keys, temporary passwords, or private configurations) with a colleague, I want to create a Relic that automatically deletes itself after being viewed exactly once, so that I have absolute certainty the data cannot be accessed again if the link is intercepted or leaked later.

## 🎯 The Problem
Currently, users can set time-based expiration (e.g., 1 hour, 1 day) for a Relic. While useful for general temporary sharing, it falls short for highly sensitive secrets. If a link with a 1-hour expiration is shared over an insecure channel or falls into the wrong hands within that hour, an unauthorized party can still access the data. There is no built-in way to guarantee single-use access for maximum security.

## 🛠️ The Proposed Solution
Introduce a "Burn After Reading" (or Single-View) expiration option. When a Relic is configured this way, the backend will immediately delete it from storage and the database after it has been successfully retrieved by a user for the first time.

## ✅ Acceptance Criteria

### Frontend (Svelte)
- [ ] Add a "Burn after reading" (or "Single-use") option to the expiration dropdown in the `RelicForm` component.
- [ ] When a single-use Relic is viewed, display a clear, dismissible warning banner to the viewer (e.g., "⚠️ This is a single-use Relic. Once you close or refresh this page, the content will be permanently gone. Please copy it now if needed.").

### Backend (FastAPI)
- [ ] Update the `expires_in` schema to accept a new value (e.g., `"burn"` or `"once"`).
- [ ] Modify the Relic creation logic to mark the Relic appropriately (potentially reusing the `expires_in` string or adding a simple flag/state, though sticking to the existing expiration pattern is likely simpler to implement).
- [ ] Modify the retrieval endpoints (e.g., `/{relic_id}` and `/{relic_id}/raw`). If the Relic is marked as single-use, schedule its immediate deletion right after returning the content to the client (e.g., using FastAPI's `BackgroundTask`).

### CLI (Go)
- [ ] Update the CLI `upload` (or equivalent creation) command to accept `--expires burn` or a dedicated `--burn` flag.
- [ ] Ensure the CLI correctly passes the new expiration parameter to the API.

## 📊 Expected Impact
- **Security:** Provides a highly requested, zero-trust sharing option for secrets, directly competing with specialized tools like "privnote" or "1password send".
- **Usage:** Encourages developers and IT professionals to use Relic for a wider variety of daily tasks, increasing overall engagement.
- **Simplicity:** Piggybacks on the existing expiration and storage mechanisms without requiring massive architectural changes or new infrastructure.
