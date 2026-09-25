<script>
  // The list page frame: page bar and list on the left, the inspector beside them (docked from
  // 1280px, a drawer below that, hidden on phones), a status bar, and an optional drop zone.
  // Pages fill it with snippets; `panel` (InspectorPanel) says whether the inspector shows.
  //   ] toggles the inspector · Esc closes the drawer
  import Icon from "../ui/Icon.svelte";
  import { layout } from "./layout";

  let {
    panel,
    hasSelection = true, // a drawer only opens when there's something to inspect
    phoneDrawer = false, // let phones open the inspector as a drawer (the viewer does; lists open rows instead)
    label = "List",
    pagebar, // snippet({ inspectorOpen, toggleInspector })
    children, // the list
    inspector, // snippet({ close }) — close is set for drawers
    status, // snippet for the status bar
    onkeydown, // (event) for page keys; called when not typing and no modifier is held
    ondropfiles = null, // (dataTransfer) => void; enables dropping files onto the page
    dropLabel = "Drop files to upload",
  } = $props();

  const open = $derived((phoneDrawer || !$layout.phone) && panel.isOpen($layout.dock, hasSelection));
  const toggleInspector = () => panel.toggle($layout.dock);

  function typing(target) {
    return target.closest?.("input, textarea, select, [contenteditable=''], [contenteditable='true'], .monaco-editor");
  }

  function onWindowKeydown(event) {
    if (event.metaKey || event.ctrlKey || event.altKey || typing(event.target)) return;
    if (event.key === "]") {
      event.preventDefault();
      toggleInspector();
    } else if (event.key === "Escape" && panel.drawer) {
      panel.hide();
    } else {
      onkeydown?.(event);
    }
  }

  // Drag and drop upload.
  let dragging = $state(false);
  let dragDepth = 0;
  const hasFiles = (event) => event.dataTransfer?.types?.includes("Files");
  function onDragEnter(event) {
    if (!ondropfiles || !hasFiles(event)) return;
    dragDepth++;
    dragging = true;
  }
  function onDragLeave() {
    if (!ondropfiles) return;
    dragDepth = Math.max(0, dragDepth - 1);
    if (!dragDepth) dragging = false;
  }
  function onDragOver(event) {
    if (ondropfiles && hasFiles(event)) event.preventDefault();
  }
  function onDrop(event) {
    if (!ondropfiles) return;
    event.preventDefault();
    dragDepth = 0;
    dragging = false;
    ondropfiles(event.dataTransfer);
  }
</script>

<svelte:window onkeydown={onWindowKeydown} />

<div class="wb" role="region" aria-label={label} ondragenter={onDragEnter} ondragleave={onDragLeave} ondragover={onDragOver} ondrop={onDrop}>
  <div class="wb-row">
    <div class="wb-main">
      {@render pagebar?.({ inspectorOpen: $layout.phone && !phoneDrawer ? null : open, toggleInspector })}
      {@render children()}
    </div>

    {#if open && inspector}
      <div class="wb-inspector" class:is-drawer={!$layout.dock}>
        {@render inspector({ close: $layout.dock ? null : () => panel.hide() })}
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
  .wb-status :global(.status-error) {
    color: var(--danger);
  }
  .wb-status :global(.status-error button) {
    padding: 0;
    border: 0;
    background: none;
    cursor: pointer;
  }
  @media (max-width: 767px) {
    .wb-status {
      display: none;
    }
    .wb-inspector.is-drawer {
      left: 0;
    }
    .wb-inspector.is-drawer :global(.r-inspector) {
      width: 100%;
    }
  }
</style>
