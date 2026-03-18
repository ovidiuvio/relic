# Spec: Fork Lineage — Fork Tree Visualization
Date: 2024-03-24  |  Author: meridian-1
Board Plan: pending  |  Board Claim: pending

## Current State
The `fork_of` lineage is stored in the database but there is no way for the user to visualize the tree of forks. The `RelicStatusBar` only shows a simple link to the immediate parent. Users cannot see what other relics have been forked from the current one.

## Problem Statement
A user who wants to understand the evolution of a relic currently has to manually follow links one by one. It is impossible to discover other branches of a relic's history or see its descendants. This makes collaboration and discovery of related modifications difficult.

## Inspiration
- **GitHub Network Graph / Forks page**: Shows an interactive or list-based tree of all forks of a repository, making it easy to see active branches and lineage.
- **Gist Revisions / Forks**: Shows the fork history clearly.

## Proposed Solution

### Overview
Add a "Lineage" tab or section to the Relic Viewer (e.g. via a modal) that visualizes the full fork tree for the current relic. It will recursively fetch and display the parent chain and all children (forks) of the current relic, forming a tree.

### User-Facing Changes
- In `RelicStatusBar.svelte` (or `RelicHeader.svelte`), add a "View Lineage" button next to the `fork_of` badge.
- Clicking this opens a `LineageModal.svelte` that displays a tree-like list or graph of the relic's ancestry and descendants.
- The tree will highlight the current relic and allow clicking on other nodes to navigate to them.

### Frontend Changes
- Create `LineageModal.svelte` to render the tree.
- Add an API function `getRelicLineage(relicId)` in `services/api/relics.js`.
- Update `RelicStatusBar.svelte` to open the modal.

### Backend Changes
- Add a new endpoint `GET /api/v1/relics/{relic_id}/lineage` in `backend/routes/relics.py`.
- This endpoint will perform a query to find the root ancestor (following `fork_of` upwards) and then recursively find all descendants downwards, building a tree structure. Or it could just find all relics that share the same root.
- Add a new schema `RelicNode` in `backend/schemas.py`.

### Data Model Changes
- No migrations needed. `fork_of` is already indexed and sufficient for queries.

### CLI Changes
- Add a command `relic lineage <ID>` to print a tree view in the terminal.

### Constraints Respected
- Relic immutability: Maintained. We are just querying existing data.
- No new npm dependencies: True. We will use plain HTML/CSS to render a simple indented list or tree diagram.
- Backward compatible: yes

### Out of Scope
- Diffing between forks in the tree view (can be a future enhancement).

### Acceptance Criteria
- [ ] Backend endpoint `/api/v1/relics/{relic_id}/lineage` returns the full tree of related relics.
- [ ] Frontend can display the tree in a modal, highlighting the current relic.
- [ ] CLI command `relic lineage` outputs the tree structure.
