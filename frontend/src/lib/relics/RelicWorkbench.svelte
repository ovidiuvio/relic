<script>
  // A relic list page: the Workbench frame with the relic list and the relic inspector.
  // Used by Recent, My relics, Bookmarks and a space. It owns the selection:
  //   ≥1280px the inspector follows the selection · 768–1279px selecting opens it as a drawer
  //   · phones open the relic · e edits (your relics) · y copies the selected link
  // `aside` swaps the inspector's contents for a page panel (a space's details) while set.
  import Workbench from "../shell/Workbench.svelte";
  import RelicList from "./RelicList.svelte";
  import RelicInspector from "./inspector/RelicInspector.svelte";
  import { InspectorPanel } from "../shell/inspectorPanel.svelte.js";
  import { layout } from "../shell/layout";
  import { navigate } from "../../utils/navigation";
  import { copyToClipboard } from "../../services/relicActions";
  import { refreshSidebar } from "../shell/sidebarData";

  let {
    feed,
    panel = new InspectorPanel(), // pass one to open the inspector from the page (e.g. for `aside`)
    grouped = true,
    dateField = "created_at",
    dateLabel = null,
    showPublic = false,
    showOwner = true,
    highlight = "",
    actions = [], // [{ icon, title, run(relic) }] or { icon, title, request: "edit" | "delete" }
    emptyText,
    emptyAction = null,
    sort = null, // { key, dir }, shown and changed by the list's column headers
    onsort,
    ontag,
    pagebar, // snippet({ inspectorOpen, toggleInspector })
    status, // snippet for the status bar
    aside = null, // snippet({ close }) shown in the inspector instead of the selected relic
    editable = false, // your own relics: Edit, Access and Delete in the inspector
    onbookmark, // (relic, bookmarked) after the inspector's bookmark toggle
    onselect, // (relic) after a row is selected, e.g. to leave `aside`
    ondropfiles = null,
    dropLabel,
  } = $props();

  let selectedId = $state(null);
  let focus = $state(null);

  const selected = $derived(feed.items.find((r) => r.id === selectedId) ?? null);

  // Keep a docked inspector filled: select the first row when nothing (or a row that's gone) is selected.
  $effect(() => {
    if ($layout.dock && feed.items.length && !feed.items.some((r) => r.id === selectedId)) {
      selectedId = feed.items[0].id;
    }
  });

  function select(relic) {
    if ($layout.phone) return open(relic);
    focus = null;
    selectedId = relic.id;
    if (!$layout.dock) panel.show(false);
    onselect?.(relic);
  }

  // A counter or row action: select its row, make sure the inspector shows, open that section.
  function showSection(relic, section) {
    if ($layout.phone) return navigate(`/${relic.id}`);
    selectedId = relic.id;
    panel.show($layout.dock);
    focus = { id: section, n: (focus?.n ?? 0) + 1 };
    onselect?.(relic);
  }

  const rowActions = $derived(
    actions.map((a) => (a.request ? { ...a, run: (relic) => showSection(relic, a.request) } : a))
  );

  // After a delete, select the row that took its place (or the one above, at the end).
  function onDeleted(relic) {
    const i = feed.items.findIndex((r) => r.id === relic.id);
    feed.remove(relic.id);
    selectedId = feed.items[Math.min(i, feed.items.length - 1)]?.id ?? null;
    refreshSidebar();
  }

  function open(relic) {
    navigate(`/${relic.id}`);
  }

  function onKeydown(event) {
    if (event.key === "e" && editable && selected) {
      event.preventDefault();
      showSection(selected, "edit");
    } else if (event.key === "y" && selected) {
      copyToClipboard(`${location.origin}/${selected.id}`, "Link copied");
    }
  }
</script>

<Workbench {panel} hasSelection={!!selected || !!aside} label="Relics" {pagebar} {status} onkeydown={onKeydown} {ondropfiles} {dropLabel}>
  <RelicList
    relics={feed.items}
    loading={feed.loading}
    hasMore={feed.hasMore}
    {grouped}
    {dateField}
    {dateLabel}
    {showPublic}
    {showOwner}
    {highlight}
    actions={rowActions}
    {emptyText}
    {emptyAction}
    selectedId={aside ? null : selectedId}
    onselect={select}
    onopen={open}
    oncounter={showSection}
    {ontag}
    {sort}
    {onsort}
    onloadmore={() => feed.more()}
  />

  {#snippet inspector({ close })}
    {#if aside}
      {@render aside({ close })}
    {:else}
      <RelicInspector
        relic={selected}
        {focus}
        {editable}
        {ontag}
        {onbookmark}
        onupdated={(relic) => feed.update(relic)}
        ondeleted={onDeleted}
        onclose={close}
      />
    {/if}
  {/snippet}
</Workbench>
