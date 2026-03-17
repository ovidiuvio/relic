## 2024-05-24 - Secure Error Handling in FastAPI
**Vulnerability:** Leaking stack traces or internal errors to clients via `str(e)` in HTTP 500 responses.
**Learning:** Returning `str(e)` in `HTTPException` detail exposes internal system structure, database structure, and potentially sensitive information. It occurred in relic creation, fetching, and forking endpoints.
**Prevention:** Always log the actual exception internally using a logger (`logger.error(f"Operation failed: {e}")`) and return a generic, secure error message (`"An internal error occurred"`) to the client.