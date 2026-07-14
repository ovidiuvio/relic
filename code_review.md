# Code Review: `feat/job-admin` Branch + Local Changes (v2 — Double-Checked)

**Branch:** `feat/job-admin` (1 commit + 4 unstaged files)  
**Scope:** Background job management & monitoring dashboard for admin panel  
**Files reviewed:** `backend/scheduler.py`, `backend/routes/admin.py`, `backend/tasks.py`, `frontend/src/components/AdminPanel.svelte`, `frontend/src/services/api/admin.js`, `tests/test_admin.py`

> [!NOTE]
> v2: Corrected two false positives from the initial review and added one newly discovered bug.
>
> **Retracted:**  
> - ~~Thread-safety of `scheduler_listener`~~ — `AsyncIOScheduler` listeners run on the **event loop thread**, not a separate thread. No cross-thread mutation.  
> - ~~`func_ref` shows wrapper name~~ — `@wraps(func)` preserves the original `__qualname__`, so `job.func_ref` correctly displays the original function.

---

## Overall Assessment

The feature is well-structured — the split into "Scheduled Tasks" and "Execution History & Logs" sub-tabs is clean, the concurrency guard (`asyncio.Lock` per-job), the structured `serialize_trigger()`, the synchronous entry creation before background execution, and the frontend polling are all solid improvements over the initial commit. The docstrings in `scheduler.py` are notably thorough.

---

## 🔴 Critical Issues

### 1. Manual runs double-wrap through `wrap_job`, causing double-finalization and cross-attribution risk

> [!CAUTION]
> This is an actual logic bug, not just a theoretical concern.

**The flow:**

1. [admin_run_job](file:///home/ovidiu/Workspaces/relic/backend/routes/admin.py#L725) does `func = job.func` — but `job.func` is already the `wrap_job(original_func, job_id)` wrapper
2. [run_manual_job_wrapper](file:///home/ovidiu/Workspaces/relic/backend/scheduler.py#L272-L297) sets `current_run_id = run_id` (the manual entry's ID), then calls `func(...)` — which is the `wrap_job` wrapper
3. Inside `wrap_job`'s [async_wrapper](file:///home/ovidiu/Workspaces/relic/backend/scheduler.py#L164-L177): calls `_bind_run_id_for_scheduled_job(job_id)` which scans `job_history` in reverse for **any** `status=="running"` entry matching `job_id`

**Consequences:**

- **Double finalization:** Both `wrap_job` and `run_manual_job_wrapper` call `_finish_history(run_id, ...)` on the same entry. Idempotent for success, but on failure, `wrap_job` re-raises → `run_manual_job_wrapper` catches and calls `_finish_history` again. Harmless but wasteful.

- **Cross-attribution (real bug):** If a **scheduled** cron run fires while a **manual** run of the same `job_id` is still in-progress, `_bind_run_id_for_scheduled_job` will match the **manual** entry (status=running, job_id matches) instead of the SUBMITTED scheduled entry. The scheduled run's logs and status get written to the manual entry, and the SUBMITTED entry stays orphaned at status=running forever.

- **ContextVar token nesting:** `wrap_job` does `token = current_run_id.set(run_id)` which overwrites the token from `run_manual_job_wrapper`. Then `wrap_job`'s `finally` resets, then `run_manual_job_wrapper`'s `finally` resets. Due to ContextVar's token chain this **happens to work** — but it's fragile and unintentional.

**Fix:** In the admin route, unwrap to get the original function:

```python
func = job.func
# Unwrap to avoid double-wrapping with run_manual_job_wrapper's own
# current_run_id binding and _finish_history call.
while hasattr(func, '__wrapped__'):
    func = func.__wrapped__
```

Or add a `trigger_type` check in `_bind_run_id_for_scheduled_job` to only match `"scheduled"` entries.

---

### 2. `run_manual_job_wrapper` re-raises exceptions needlessly

[scheduler.py:287-295](file:///home/ovidiu/Workspaces/relic/backend/scheduler.py#L287-L295)

```python
except Exception as exc:
    _finish_history(...)
    raise  # ← propagates into FastAPI BackgroundTasks
```

FastAPI's `BackgroundTasks` runs **after** the response is sent. Unhandled exceptions:
- Have no effect on the HTTP response (already sent)
- Are logged to stderr by Uvicorn as unhandled exceptions
- May prevent subsequent queued BackgroundTasks from running

The error is already properly recorded in `_finish_history`. The `raise` only adds noise.

**Fix:** Replace `raise` with `logger.exception(f"Manual job {job_id} failed")` or just remove the raise.

> [!IMPORTANT]
> Note: the `raise` in `wrap_job` (line 174, 190) is **correct and intentional** — APScheduler needs the exception to propagate for its `EVENT_JOB_ERROR` mechanism. Only the `run_manual_job_wrapper` raise is problematic because it runs outside APScheduler.

---

## 🟡 Medium Issues

### 3. `manual_run_locked()` is a TOCTOU race

[admin.py:718-727](file:///home/ovidiu/Workspaces/relic/backend/routes/admin.py#L718-L727)

```python
if manual_run_locked(job_id):          # check
    raise HTTPException(status_code=409, ...)
run_id = create_manual_run_entry(job_id)  # act
background_tasks.add_task(...)
```

Between the `manual_run_locked()` check and `run_manual_job_wrapper` acquiring the lock, a second request can pass the same check. Two entries get created; the second blocks on the lock until the first finishes, then executes — but the admin sees duplicate history entries and no 409.

**Practical risk:** Low (requires near-simultaneous requests), but the 409 contract the frontend relies on becomes unreliable.

**Fix:** Use `lock.locked()` check + non-blocking acquire atomically, or move the lock acquisition into the route itself.

### 4. History entries serialized as mutable dict references

[admin.py:686](file:///home/ovidiu/Workspaces/relic/backend/routes/admin.py#L686)

```python
"history": list(job_history),
```

`list(job_history)` creates a list of references to the **same** mutable dicts that background tasks mutate via `_finish_history`. Since `AsyncIOScheduler` and all jobs run on the same event loop, and FastAPI serializes the response in the same event loop tick, this is **safe in practice** — but only because `json.dumps()` happens synchronously before yielding to the event loop.

Still, a defensive shallow copy costs nothing:

```python
"history": [dict(e) for e in job_history],
```

### 5. Polling has no cancellation on component unmount

[AdminPanel.svelte:479-498](file:///home/ovidiu/Workspaces/relic/frontend/src/components/AdminPanel.svelte#L479-L498)

`pollJobRun()` schedules recursive `setTimeout` calls for up to 30 seconds. If the user navigates away from the admin panel (component is destroyed), the polling continues — calling `loadJobs()` and `showToast()` on a destroyed component.

**Fix:**
```js
import { onDestroy } from "svelte";
let pollTimeouts = [];
onDestroy(() => pollTimeouts.forEach(clearTimeout));
// In pollJobRun, track: pollTimeouts.push(setTimeout(tick, 1500));
```

### 6. `paused_job_ids` not persisted — state lost on restart

[scheduler.py:62](file:///home/ovidiu/Workspaces/relic/backend/scheduler.py#L62)

`paused_job_ids` is an in-memory `set()`. Both APScheduler's state (using `MemoryJobStore`) and the admin tracking set are ephemeral. Acceptable, but worth a note in the UI.

### 7. `formatTriggerStr()` is ~90 lines of dead fallback code

[AdminPanel.svelte:222-314](file:///home/ovidiu/Workspaces/relic/frontend/src/components/AdminPanel.svelte#L222-L314)

Only reachable if `trigger_info` is missing from the API response, which the current backend always includes. Good as defensive code, but untested and adds maintenance burden. Mark as `@deprecated` or extract.

---

## 🟢 Low / Nits

### 8. No pagination for execution history

The history sub-tab renders **all** entries (up to 500) via `filteredHistory.slice().reverse()`. With expandable log/traceback panels, 500 rows could get sluggish. Add client-side pagination like other tabs.

### 9. No status filter on history tab

The "Filter Task" dropdown filters by job_id but there's no way to filter by status (failed only, running only). Useful for incident investigation.

### 10. No auto-refresh on the Jobs tab

Unlike the post-trigger polling, there's no periodic auto-refresh when the Jobs tab is active. Scheduled runs that fire while viewing the tab won't appear without clicking "Refresh Scheduler".

### 11. Missing test: concurrent manual run returns 409

Tests cover run, pause, resume, not-found, and forbidden — but no test verifies the 409 conflict. Since the frontend explicitly handles 409 (`error.response?.status === 409`), this contract should be tested.

### 12. `datetime.utcnow()` in tasks.py

[tasks.py](file:///home/ovidiu/Workspaces/relic/backend/tasks.py) uses deprecated `datetime.utcnow()` (deprecated since Python 3.12). The new `scheduler.py` code correctly uses `datetime.now(timezone.utc)`. Migrate for consistency.

### 13. Run button not disabled when a job is paused

The UI allows triggering a manual run on a paused job (APScheduler allows this). This may confuse admins who expect "paused" to mean "no execution whatsoever."

### 14. No confirmation dialog before manual job trigger

Other destructive admin actions (delete client, restore DB) show confirmation modals. Manual job triggers fire immediately.

### 15. No copy button on log/traceback panels

The execution history log viewer and traceback panels have no quick-copy button (unlike the restore modal which has copy/download/save-as-relic).

---

## Summary of Actions

### Must-fix before merge:

| # | Issue | Effort |
|---|-------|--------|
| **1** | Unwrap `job.func` in admin route to avoid double-wrapping through `wrap_job` | Small — 3 lines in `admin.py` |
| **2** | Remove `raise` in `run_manual_job_wrapper` | One-liner |
| **5** | Cancel poll timeouts on component unmount | Small — 5 lines |

### Should-fix:

| # | Issue | Effort |
|---|-------|--------|
| **3** | TOCTOU on `manual_run_locked` — decide if acceptable or fix | Small |
| **4** | Shallow-copy history entries before serialization | One-liner |

### Nice-to-have:

| # | Issue |
|---|-------|
| **8** | Pagination on history tab |
| **9** | Status filter on history tab |
| **11** | Test for 409 conflict |
| **13** | Disable run button when paused |
| **15** | Copy button on log panels |
