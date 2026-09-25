<script>
  // The list page frame shared by Recent, My relics, Bookmarks and spaces: page bar, relic list,
  // inspector and status bar. It owns the selection and how the inspector appears:
  //   ≥1280px: docked beside the list, toggled with ] (remembered)
  //   768–1279px: opens over the list when you select a row
  //   phones: selecting a row opens the relic
  import RelicList from "./RelicList.svelte";
  import RelicInspector from "./inspector/RelicInspector.svelte";
  import Icon from "../ui/Icon.svelte";
  import { layout } from "../shell/layout";
  import { navigate } from "../../utils/navigation";
  import { copyToClipboard } from "../../services/relicActions";

  let {
    feed,
    grouped = true,
    dateField = "created_at",
    highlight = "",
    actions = [],
    emptyText,
    emptyAction = null,
    sort = null, // { key, dir }, shown and changed by the list's column headers
    onsort,
    ontag,
    pagebar, // snippet({ inspectorOpen, toggleInspector })
    status, // snippet for the status bar
    ondropfiles = null, // (files) => void; enables dropping files onto the list
    dropLabel = "Drop files to upload",
  } = $props();

  const OPEN_KEY = "relic_inspector_open";
  let docked = $state(readOpen());
  let drawer = $state(false);
  let selectedId = $state(null);
  let dragging = $state(false);
  let focus = $state(null);

  function readOpen() {
    try {
      return localStorage.getItem(OPEN_KEY) !== "false";
    } catch {
      return true;
    }
  }

  const selected = $derived(feed.relics.find((r) => r.id === selectedId) ?? null);
  const inspectorOpen = $derived($layout.dock ? docked : drawer && !!selected);

  // Keep a docked inspector filled: select the first row when nothing (or a row that's gone) is selected.
  $effect(() => {
    if ($layout.dock && feed.relics.length && !feed.relics.some((r) => r.id === selectedId)) {
      selectedId = feed.relics[0].id;
    }
  });

  function toggleInspector() {
    if ($layout.dock) {
      docked = !docked;
      try {
        localStorage.setItem(OPEN_KEY, String(docked));
      } catch {
        // Not remembered without storage; the toggle still works.
      }
    } else {
      drawer = !drawer;
    }
  }

  function select(relic) {
    if ($layout.phone) return open(relic);
    focus = null;
    selectedId = relic.id;
    if (!$layout.dock) drawer = true;
  }

  // A counter in the list: select its row, make sure the inspector shows, open that section.
  function showSection(relic, section) {
    if ($layout.phone) return navigate(`/${relic.id}`);
    selectedId = relic.id;
    if ($layout.dock) docked = true;
    else drawer = true;
    focus = { id: section, n: (focus?.n ?? 0) + 1 };
  }

  function open(relic) {
    navigate(`/${relic.id}`);
  }

  function typing(target) {
    return target.closest?.("input, textarea, select, [contenteditable=''], [contenteditable='true'], .monaco-editor");
  }

  function onKeydown(event) {
    if (event.metaKey || event.ctrlKey || event.altKey || typing(event.target)) return;
    if (event.key === "]") {
      event.preventDefault();
      toggleInspector();
    } else if (event.key === "y" && selected) {
      copyToClipboard(`${location.origin}/${selected.id}`, "Link copied");
    } else if (event.key === "Escape" && drawer) {
      drawer = false;
    }
  }

  // Drag and drop upload.
  let dragDepth = 0;
  function onDragEnter(event) {
    if (!ondropfiles || !event.dataTransfer?.types?.includes("Files")) return;
    dragDepth++;
    dragging = true;
  }
  function onDragLeave() {
    if (!ondropfiles) return;
    dragDepth = Math.max(0, dragDepth - 1);
    if (!dragDepth) dragging = false;
  }
  function onDragOver(event) {
    if (ondropfiles && event.dataTransfer?.types?.includes("Files")) event.preventDefault();
  }
  function onDrop(event) {
    if (!ondropfiles) return;
    event.preventDefault();
    dragDepth = 0;
    dragging = false;
    ondropfiles(event.dataTransfer);
  }
</script>

<svelte:window onkeydown={onKeydown} />

<div class="wb" role="region" aria-label="Relics" ondragenter={onDragEnter} ondragleave={onDragLeave} ondragover={onDragOver} ondrop={onDrop}>
  <div class="wb-row">
    <div class="wb-main">
      {@render pagebar({ inspectorOpen: $layout.phone ? null : inspectorOpen, toggleInspector })}
      <RelicList
        relics={feed.relics}
        loading={feed.loading}
        hasMore={feed.hasMore}
        {grouped}
        {dateField}
        {highlight}
        {actions}
        {emptyText}
        {emptyAction}
        {selectedId}
        onselect={select}
        onopen={open}
        oncounter={showSection}
        {ontag}
        {sort}
        {onsort}
        onloadmore={() => feed.more()}
      />
    </div>

    {#if inspectorOpen}
      <div class="wb-inspector" class:is-drawer={!$layout.dock}>
        <RelicInspector relic={selected} {focus} {ontag} onclose={$layout.dock ? null : () => (drawer = false)} />
      </div>
    {/if}

    {#if dragging}
      <div class="wb-drop" aria-hidden="true">
        <Icon name="upload" size={28} />
        <b>{dropLabel}</b>
      </div>
    {/if}
  </div>

  {#if status}
    <div class="r-statusbar wb-status">{@render status()}</div>
  {/if}
</div>

<style>
  .wb {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    background: var(--surface);
    color: var(--ink);
    font: 13px/1.45 var(--font-sans);
  }
  .wb-row {
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
  }
  .wb-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .wb-inspector {
    flex: none;
    display: flex;
    min-height: 0;
  }
  .wb-inspector.is-drawer {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 20;
    box-shadow: var(--shadow-popover);
  }
  .wb-drop {
    position: absolute;
    inset: 8px;
    z-index: 30;
    display: grid;
    place-content: center;
    justify-items: center;
    gap: var(--space-2);
    border: 2px dashed var(--accent);
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--accent-soft) 88%, transparent);
    color: var(--accent);
    font-size: 15px;
    pointer-events: none;
  }
  .wb-drop b {
    font-weight: 500;
  }
  .wb-status {
    flex: none;
  }
  @media (max-width: 767px) {
    .wb-status {
      display: none;
    }
  }
</style>
