# Spec: Archive Explorer — In-Archive Search
Date: 2026-03-23
Author: Meridian

## Current State
The Archive Explorer allows users to view the file structure of a zip, tar, or tar.gz file via a sidebar tree. However, for large archives with hundreds or thousands of files, finding a specific file requires manual visual scanning and expanding folders, as there is no search or filtering functionality.

## Problem Statement
A user who wants to find a specific file inside a large archive currently has to manually expand directories and visually scan for the file, which is extremely slow and frustrating because there is no way to filter the file list.

## Inspiration
- **VSCode Explorer**: Filters the file tree dynamically based on text input, highlighting matches and auto-expanding paths to matched files while hiding non-matching branches.
- **GitHub File Finder** (`t` shortcut): Flattens the view into a simple list of matching file paths when searching, making it incredibly fast to navigate regardless of directory depth.

We will borrow the hybrid approach: keeping the file tree UI but filtering the `flatTree` to only show nodes that match the search query, and automatically expanding the parents of matched nodes so they are visible.

## Proposed Solution

### Overview
Add a search input field to the top of the Archive Contents sidebar in `ArchiveRenderer.svelte`. When text is entered, the file tree will dynamically filter to show only files and directories whose names or paths contain the search string (case-insensitive). When searching, we will also automatically expand directories that contain matching children so the matches are immediately visible to the user.

### User-Facing Changes
- A new search input box with a magnifying glass icon at the top of the "Archive Contents" sidebar.
- Typing in the search box instantly filters the file tree below.
- Directories that contain matching files will remain visible and automatically expand.
- If no files match the search query, an empty state message "No files found matching '[query]'" is shown.
- A clear button ('x' icon) appears inside the search input when text is entered, allowing quick reset.

### Frontend Changes
**`frontend/src/components/renderers/ArchiveRenderer.svelte`**:
- Add state variables: `let searchQuery = ''`.
- Add a sticky search input component just below the "Archive Contents" header.
- Update the `flattenTree` and `flatTree` logic to apply filtering.
  - Create a reactive statement `$: filteredTree = filterTree(processed.fileTree, searchQuery)`
  - The `filterTree` function will recursively traverse the tree. A node is included if its `name` matches `searchQuery` (case-insensitive), or if any of its descendants match.
  - If a directory is included because a descendant matches, the directory is automatically added to a temporary set of expanded directories, or we just force it to be expanded during render.
- Pass `filteredTree` instead of `processed.fileTree` to `flattenTree`.
- Ensure styling of the search input matches the Relic design system (standard border, focus ring, gray text).
- Add an empty state block when `flatTree.length === 0` and `searchQuery` is not empty.

### Backend Changes
None. Search happens entirely client-side using the already-extracted file tree metadata.

### Data Model Changes
None.

### CLI Changes
N/A.

### Constraints Respected
- Relic immutability: Maintained (only viewing/filtering data, not modifying).
- New npm dependencies: None.
- Backward compatible: Yes.

### Out of Scope
- Full-text search *inside* the contents of the files in the archive (this iteration is just filename/path search).
- Regex search.

### Acceptance Criteria
- [ ] A search input is visible at the top of the Archive Contents sidebar.
- [ ] Entering text filters the file tree to only show files/directories matching the text (case-insensitive).
- [ ] Parent directories of matching files are automatically shown and expanded.
- [ ] An empty state is shown if no files match the search query.
- [ ] Clearing the search query restores the full file tree to its previous state.
