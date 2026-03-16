## 2024-05-20 - Chromium Headless Meta Key Issue
**Friction:** Writing Playwright tests for `Cmd+K` keyboard shortcuts in `chromium` fails silently because Chromium headless often misinterprets or drops `Meta` key presses.
**Insight:** Svelte's `on:keydown` correctly captures the event, but the simulated input from Playwright Chromium headless doesn't reliably trigger it.
**Action:** Always use `p.firefox.launch()` instead of `p.chromium.launch()` when verifying macOS `Meta` (Cmd) key shortcuts in headless Playwright scripts.
