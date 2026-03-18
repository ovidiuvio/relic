## 2024-05-24 - Secure Error Handling in FastAPI
**Vulnerability:** Leaking stack traces or internal errors to clients via `str(e)` in HTTP 500 responses.
**Learning:** Returning `str(e)` in `HTTPException` detail exposes internal system structure, database structure, and potentially sensitive information. It occurred in relic creation, fetching, and forking endpoints.
**Prevention:** Always log the actual exception internally using a logger (`logger.error(f"Operation failed: {e}")`) and return a generic, secure error message (`"An internal error occurred"`) to the client.
## 2026-03-18 - Secure Error Handling in Admin Routes
**Vulnerability:** Leaking internal errors or stack traces to clients via `str(e)` in admin route HTTP responses.
**Learning:** Returning `str(e)` in `HTTPException` detail or JSON responses in admin routes (like `admin_list_backups`, `admin_create_backup`, `admin_download_backup`) exposes internal system structures, S3 key patterns, and potentially sensitive information about backup/storage drivers.
**Prevention:** Log the actual exception internally using a logger (`logger.error(f"Error: {e}")`) and return a generic, secure error message (e.g. `"Backup operation failed"` or `"An internal error occurred"`) to the client.
