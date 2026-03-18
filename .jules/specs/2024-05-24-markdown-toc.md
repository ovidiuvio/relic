# Spec: Markdown Renderer — Table of Contents
Date: 2024-05-24  |  Author: meridian-1
Board Plan: pending  |  Board Claim: pending

## Current State
The Markdown Renderer renders Markdown documents accurately using GitHub-flavored markdown and syntax highlighting. However, for long documents, it is difficult to navigate as there is no Table of Contents to jump to specific sections.

## Problem Statement
A user who wants to read a large Markdown document currently has to scroll manually to find sections, which is slow because there is no quick navigation overview or jump links.

## Inspiration
- GitHub: Adds automatically generated anchors to all Markdown headings, and often provides a jump-to menu.
- Notion/Confluence: Explicit "Table of Contents" block that gives a tree-view of the document structure.
- We will generate IDs for headings and extract a TOC that can be rendered in a sidebar or inline to allow quick navigation.

## Proposed Solution

### Overview
We will implement a Table of Contents (TOC) feature for the Markdown renderer. A custom rehype plugin will traverse the HTML AST, add unique `id` attributes to all heading elements (`h1` through `h6`), and extract their text and levels to form a TOC structure. The Svelte component will display this TOC alongside the rendered markdown.

### User-Facing Changes
- When viewing a Markdown file, a "Table of Contents" sidebar (or inline list, if appropriate) will be visible.
- Users can click on links in the TOC to scroll smoothly to the corresponding heading.

### Frontend Changes
- `markdownProcessor.js`:
  - Add a custom unified plugin (`rehypeSlugAndToc`) that assigns `id` properties to headings and stores TOC data in `file.data.toc`.
  - Update `rehype-sanitize` configuration to allow `id` attributes on heading elements.
  - Return the TOC array in the metadata of the `processMarkdown` result.
- `MarkdownRenderer.svelte`:
  - Add a sidebar layout to display the TOC if the `processed.metadata.toc` exists and is not empty.
  - Add smooth scrolling behavior for the TOC links.

### Backend Changes
- None.

### Data Model Changes
- None.

### CLI Changes
- None.

### Constraints Respected
- Relic immutability: preserved (we only change the view rendering).
- No new npm dependencies: true. We use a custom AST traversal inside the existing `unified` pipeline.
- Backward compatible: yes.

### Out of Scope
- Persisting TOC collapsed/expanded state.
- Nested collapsible TOC sections (we will just render a simple indented list).

### Acceptance Criteria
- [ ] Heading elements (`h1`-`h6`) in rendered Markdown possess `id` attributes.
- [ ] A Table of Contents is displayed when viewing a Markdown file.
- [ ] Clicking a TOC link navigates the view to the respective heading.
- [ ] The feature works without any new NPM packages.
