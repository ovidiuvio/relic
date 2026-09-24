# UI Polish Plan

Living plan for making the Relic web UI feel professional, polished and fast —
without a radical redesign. Update the status markers and the changelog at the
bottom as work lands.

**Status legend:** `[ ]` todo · `[~]` in progress · `[x]` done · `[-]` dropped

**Guiding constraints**

- Evolve, don't replace: keep the light theme, Ubuntu type, and the aubergine brand
  colour (`#772953`). No all-monospace UI, sepia palette or hard offset shadows.
- Borrow selectively from the Console mockup
  (`relic-exp-mockups/concept-c-console.html`): metadata strip, labeled actions
  with shortcuts, options bar under the editor, dense list, keyboard layer.
- Every change must work at 390px width and with keyboard only.

---

## 1. Baseline audit (2026-09-25)

Captured against the dev stack at 1440×900 and 390×844 (Recent, New, Spaces, and
code / markdown / CSV / diff / archive viewers).

### Root causes of the "unpolished" feel

1. **No design tokens.** 109 distinct hex colours, 12 Tailwind colour families, 8
   arbitrary font sizes (37 uses of 8–9px). Three different primary button colours
   (green Create/New Space, blue key modal, aubergine pagination); links `#0066cc`;
   focus Ubuntu orange; viewer icons each hover in a different hue.
2. **Timid hierarchy.** Viewer title is 15px (`RelicHeader.svelte:121`); metadata
   row is 11px `text-gray-400` + `opacity-60` (~1.8:1 contrast).
3. **Icon soup.** 11 same-grey icon-only buttons in the viewer header plus a second
   6–9 icon toolbar; list rows have 4 actions ghosted to ~30% opacity.
4. **Full page reloads.** List titles are plain `<a href="/{id}">`
   (`RelicTable.svelte:247`) and nothing intercepts them, so each click re-runs
   key init, version fetch, admin check and chunk loading.
5. **Template chrome.** Dotted background, shadowed white card, heavy aubergine
   header with pill nav and orange underline.

### Screen-specific findings

- **New relic:** Create button is below the fold at 1440×900; visibility is a tiny
  "PUBLIC" pill beside the Content label; Type dropdown competes with auto-detect.
- **Viewer:** code forced to dark theme inside a light app; comments render as
  monospace text inside the editor; expiry and fork source not visible in header.
- **Diff:** file-path header is dark text on dark background (`DiffRenderer`).
- **Lists:** 10 rows per page by default, generous padding, empty "ACTIONS" header,
  every title link-blue.
- **Branding:** "RELIC Bin" wordmark vs "RelicBin Service" tab title vs "Relic" docs.

### Mobile

- Navigation disappears under 768px (`App.svelte:251` `hidden md:flex`, no menu).
- Viewer title collapses to zero width.
- Pagination footer wraps badly.

### Accessibility

- `document.title` never changes; no `<h1>` on any page.
- 16 modal overlays, only 5 have `aria-modal`; `KeyRevealModal` has no dialog role,
  so the background stays interactive. No focus trap / restore found.
- Sortable headers are `<th on:click>` — not keyboard reachable, no `aria-sort`.
- Icon buttons rely on `title` (188 uses) more than `aria-label` (67).
- Hover-only controls (`opacity-0 group-hover`) invisible to touch/keyboard.
- 43 outline removals vs 4 `focus-visible` usages.
- Contrast failures: metadata text, ghosted row actions, 8–10px text.
- No `prefers-reduced-motion`; `alert()` in `ArchiveRenderer.svelte:180`;
  `prompt()` for font size in `RelicForm.svelte:912`.

### Productivity gaps

- No global keyboard shortcuts (only Ctrl+Enter in `CommentEditor`).
- No ⌘/Ctrl+Enter to create; URL not copied after create.
- No search-from-anywhere, no type facets, per-page size not remembered.

---

## 2. Plan

### Phase 1 — Foundation

- [x] Design tokens in `tailwind.config.js`: `brand` scale (600 = `#772953`), `link`,
      `public` / `private` visibility colours, `font-sans` / `font-mono`, `text-2xs`
      (11px minimum). Brand/link/visibility hex values replaced with tokens.
- [x] One primary button style: `.btn-primary` / `.btn-secondary` / `.btn-danger` in
      `app.css`. All `maas-btn-*` usages migrated; green Create Relic / New Space and
      blue modal buttons now use the brand primary. `ConfirmModal` picks danger for
      delete/remove confirmations.
- [x] Unified link colour (`text-link`) and a global brand `:focus-visible` ring that
      also overrides `focus:outline-none` on interactive controls.
- [x] `IconButton` component (`components/IconButton.svelte`): required `label`
      (aria-label + tooltip on hover and keyboard focus), optional `shortcut`
      (tooltip + `aria-keyshortcuts`), `pressed`, `loading`, `tone`, neutral hover.
      Adopted in the viewer header toolbar; other icon rows migrate in later phases.
- [x] Client-side navigation: `utils/navigation.js` (`navigate()`,
      `internalLinkTarget()`); App intercepts same-origin link clicks (skips
      modifier keys, `target`, `download`, `/raw`, `/api`, `/docs`, same-page
      hashes). Post-create / post-fork / tree redirects no longer reload the page.
      `RelicViewer` ignores stale responses when switching relic → relic.
- [x] Per-route `document.title` (`<name> · Relic`) via `stores/pageTitle.js`; relic
      and space viewers set their real names. One `<h1>` per page (list title,
      relic name, space name, form title). Focus moves to `<main>` on page change.
- [x] Mobile nav menu for < md (toggle in header, closes on navigate / Escape).
- [x] Accessible modals via the `use:modal` action (`utils/modal.js`) rather than a
      wrapper component, so each dialog kept its markup: dialog role, `aria-modal`,
      auto-labelled from the first heading, initial focus, Tab trap, Escape (topmost
      dialog only; Monaco keeps Tab/Escape), focus restore. Applied to all 19
      overlays; `KeyRevealModal` deliberately has no Escape.
- [x] Header keeps the aubergine bar, "RELIC Bin" wordmark and dotted background;
      nav items are real links (`aria-current`) with an underline for the active
      page instead of the pill overlay.
- [x] Tab titles use "<page> · Relic".
- [x] Dark editor no longer flashes white while Monaco loads.
- [x] Editor scrollbar no longer resizes repeatedly on load (pre-existing bug):
      comment markdown is rendered before comment zones are built, zones are built
      once, and zones Monaco hides off-screen keep their height. Editor scrollbars
      are `auto` instead of always visible.
- [x] No stray native scrollbar beside the editor in Chrome: renderer wrappers that
      size Monaco/iframes via `bind:clientHeight` now clip (`overflow-hidden`), so
      sub-pixel rounding at some zoom levels can't make the viewer container scroll.
- [x] Overflow sweep (21 pages × 6 zoom levels + 390px): markdown tables are
      wrapped in their own scroll container (whole document no longer scrolls
      sideways on phones); Excalidraw error text wraps.
- [x] `prefers-reduced-motion` guard.
- [x] Extras: skip-to-content link; profile menu gets `aria-expanded`, labelled
      inputs, keyboard-reachable key import, Enter to save name.

**Carried over from Phase 1** (picked up in the phase that owns each screen):

- [ ] 139 uses of `text-[10px]` remain (8–9px text is gone; 8–9px icons remain).
- [ ] ~100 raw hex colours remain in component styles (Monaco, CSV, diff, admin).
- [ ] 61 Svelte a11y compiler warnings remain (was 67).
- [ ] `alert()` in `ArchiveRenderer`, `prompt()` in `RelicForm` (Phase 2 / 3).
- [x] Excalidraw relics failed to load in the dev server (pre-existing): the
      `process.env` define left `NODE_ENV` undefined, so the package's webpack
      development bundle loaded and threw. `vite.config.mjs` now aliases it to the
      production bundle, which production builds already used.
- [ ] On phones, list tables, the CSV grid and spaces scroll sideways inside their
      containers (Phase 4: compact card rows).

### Phase 2 — Relic viewer

- [ ] Title at page-heading size; ID with copy affordance always visible.
- [ ] Metadata strip: type · size · lines · visibility · expiry · views · owner ·
      age · fork of — readable contrast.
- [ ] Labeled primary actions (**Copy link**, **Fork**) + `⋯` overflow menu listing
      remaining actions with shortcut hints.
- [ ] Merge header toolbar and view toolbar into one row where possible.
- [ ] Light code theme by default matching the app; keep dark toggle (persisted).
- [ ] Comments as note cards anchored to lines (proportional font, avatar/name, time).
- [ ] Optional right sidebar: actions, lineage tree, tags/space.
- [ ] Fix diff file-header contrast.
- [ ] Mobile: title never collapses; actions collapse into overflow.
- [ ] Replace `alert()` / `prompt()` with toast / inline controls.

### Phase 3 — New relic

- [ ] Editor as hero; name field in the editor header with "detected · <type>" badge.
- [ ] Options bar under the editor: visibility · expires · password · tags · space ·
      **Create** (always visible, no scroll needed).
- [ ] ⌘/Ctrl+Enter to create; auto-copy URL + toast on success.
- [ ] Side panel (desktop): your last relics, CLI snippet, key hints.
- [ ] Paste-anywhere (on non-input focus) to start a new relic.

### Phase 4 — Lists (Recent / My Relics / Bookmarks / Space)

- [ ] Denser rows; default 25 per page; remember per-page choice.
- [ ] Type badge column; title in ink colour (not link-blue), ID secondary.
- [ ] Whole-row click target (still a real link for middle-click / new tab).
- [ ] Row actions visible on focus and on touch, not hover-only.
- [ ] Sortable headers as buttons with `aria-sort`.
- [ ] Day grouping for date-sorted views.
- [ ] Type facet filter with counts (needs backend aggregate).
- [ ] First-line preview column (needs backend field).
- [ ] Mobile: compact card rows, fixed pagination footer.

### Phase 5 — Keyboard layer

- [ ] Global: `/` search, `n` new, `g r` / `g m` / `g s` / `g b` go to, `?` cheat sheet.
- [ ] Lists: `j/k` move, `Enter` open, `y` copy link.
- [ ] Viewer: `y` link, `c` copy content, `r` raw, `d` download, `f` fork, `b` bookmark.
- [ ] Shortcuts ignored while typing in inputs / Monaco.
- [ ] Context hint bar (desktop only, dismissible).

### Later / needs backend

- [ ] Query-token search (`is:public tag: type: by: size:>1mb`).
- [ ] Full-text search.

---

## 3. Decisions

| Date | Decision |
|---|---|
| 2026-09-25 | Keep light theme, Ubuntu font, aubergine brand; Console mockup used as a source of ideas, not a target. |
| 2026-09-25 | Tried a white header; rejected — it looked worse. Keep the aubergine bar and original wordmark; only the active-tab style changed (underline, liked). Visual changes need sign-off before landing. |
| 2026-09-25 | Modal accessibility is a Svelte action (`use:modal`), not a wrapper component, to avoid rewriting 19 dialogs. |

## 4. Changelog

| Date | Change |
|---|---|
| 2026-09-25 | Plan created from baseline audit. |
| 2026-09-25 | Phase 1 (foundation) implemented on branch `ui-update`. |
| 2026-09-25 | Fixed Monaco load flicker (comment zone sizing) and always-on editor scrollbars. |
| 2026-09-25 | Fixed Chrome-only full-height scrollbar next to the editor (sub-pixel overflow). |
| 2026-09-25 | Overflow sweep; fixed markdown table and Excalidraw error overflow on mobile. |
| 2026-09-25 | Fixed Excalidraw failing to load in the dev server. |
