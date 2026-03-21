# ADR-002: Extract Frontend Routing

**Date:** 2026-03-21
**Status:** Accepted

## Context

All URL parsing currently lives in `updateRouting()` inline in `frontend/src/App.svelte`. Furthermore, the actual rendering of the matching component is done with a massive `if/else` block based on manually set string states like `currentSection`.

This has made `App.svelte` a God Component. Every time a new agent adds a view to the application, they must modify `App.svelte`, increasing merge conflicts, logical complexity, and coupling. It represents a convergence point for unrelated concerns.

## Decision Drivers

- Maintainability: Every new view shouldn't require changing the main application shell.
- Scalability: The single `if/else` rendering block will grow unmanageably as the application gains new domains.
- Separation of Concerns: Svelte application components shouldn't implement URL string parsing directly inside component setup.

## Options Considered

### Option A: Extract to a `routes.js` module
Create a map of path patterns to component definitions in a dedicated `frontend/src/routes.js` file, exposing a `matchRoute` function. Refactor `App.svelte` to use this routing module and render the active route using `<svelte:component>`.
**Pros:** Lightweight, respects the existing Svelte configuration, removes routing logic from `App.svelte` entirely. Keeps Svelte standalone and unopinionated.
**Cons:** We still have to write our own simple regex router instead of using an established library.

### Option B: Introduce SvelteKit or `svelte-routing`
Adopt a third-party framework for routing.
**Pros:** Feature-rich.
**Cons:** Introduces a large dependency, might necessitate significant rewrites across the codebase, overkill for our specific problem.

## Decision

We will proceed with **Option A**. It aligns perfectly with the requirement to perform an architectural change without unnecessarily adding external dependencies, maintaining the simplicity constraint of the codebase.

## Consequences

**Positive:**
- `App.svelte` focuses solely on application layout, navigation shell, and initializing global states.
- Routing is strictly isolated and can be unit tested independent of the DOM.
- Adding a new view only requires modifying `routes.js`.

**Negative / Trade-offs:**
- Requires creating our own dynamic route matching using regex.

## Constraints Respected
- Relic immutability: preserved
- Three-layer separation: preserved (frontend logic refactor)
- New dependencies: none
- Migration required: no
