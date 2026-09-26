<script>
  // Forking a relic: a page, not a dialog. The content is editable (text in the editor,
  // Excalidraw drawings in Excalidraw; binary files are kept as they are and previewed), and the
  // fork's options, starting from the original's, are in the inspector. Ctrl+Enter creates.
  import { onDestroy, untrack } from "svelte";
  import Icon from "../lib/ui/Icon.svelte";
  import PageBar from "../lib/shell/PageBar.svelte";
  import Workbench from "../lib/shell/Workbench.svelte";
  import ComposeInspector from "../lib/compose/ComposeInspector.svelte";
  import ForkEditor from "../components/ForkEditor.svelte";
  import { InspectorPanel } from "../lib/shell/inspectorPanel.svelte.js";
  import { refreshSidebar } from "../lib/shell/sidebarData";
  import { getRelic, getRelicRaw, forkRelic } from "../services/api";
  import { getContentType, getFileExtension, detectLanguageHint, isBinaryType } from "../services/typeUtils";
  import { tagName } from "../lib/relics/format";
  import { showToast } from "../stores/toastStore";
  import { pageTitle } from "../stores/pageTitle";
  import { navigate } from "../utils/navigation";

  let { relicId } = $props();

  const panel = new InspectorPanel();

  let relic = $state.raw(null);
  let error = $state(null);
  let binary = $state(false);
  let binaryBlob = $state.raw(null);
  let previewUrl = $state(null);
  let editorContent = $state("");
  let form = $state({ title: "", syntax: "auto", visibility: "public", expiry: "never", tags: [], spaceId: null });
  let busy = $state(false);

  async function load(id) {
    error = null;
    relic = null;
    try {
      const source = (await getRelic(id)).data;
      const raw = await (await getRelicRaw(id)).data.arrayBuffer();
      binary = isBinaryType(source.content_type);
      if (binary) {
        binaryBlob = new Blob([raw], { type: source.content_type });
        if (source.content_type?.startsWith("image/") || source.content_type === "application/pdf") {
          previewUrl = URL.createObjectURL(binaryBlob);
        }
      } else {
        editorContent = new TextDecoder().decode(raw);
      }
      form = {
        title: source.name || "",
        syntax: source.language_hint || detectLanguageHint(source.content_type) || "auto",
        visibility: source.access_level || "public",
        expiry: "never",
        tags: (source.tags ?? []).map(tagName),
        spaceId: null,
      };
      relic = source;
    } catch (e) {
      error = e.response?.status ?? "unknown";
    }
  }

  $effect(() => {
    const id = relicId;
    untrack(() => load(id));
  });

  $effect(() => {
    if (relic) pageTitle.set(`Fork of ${relic.name || "Untitled relic"}`);
  });

  onDestroy(() => previewUrl && URL.revokeObjectURL(previewUrl));

  async function createFork() {
    if (busy || !relic) return;
    let file;
    if (binary) {
      file = new File([binaryBlob], form.title || relic.name || `fork-of-${relicId}`, { type: relic.content_type });
    } else {
      if (!editorContent.trim()) return showToast("The fork needs some content", "warning");
      const contentType = form.syntax !== "auto" ? getContentType(form.syntax) : "text/plain";
      const extension = form.syntax !== "auto" ? getFileExtension(form.syntax) : "txt";
      file = new File([editorContent], form.title || `fork-of-${relicId}.${extension}`, { type: contentType });
    }
    busy = true;
    try {
      const { data } = await forkRelic(relicId, file, form.title, form.visibility, form.expiry, form.tags);
      showToast("Forked", "success");
      refreshSidebar();
      navigate(`/${data.id}`);
    } catch (e) {
      showToast(e.response?.data?.detail || "Couldn’t create the fork", "error");
    } finally {
      busy = false;
    }
  }

  function onWindowKeydown(event) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !busy) {
      event.preventDefault();
      event.stopPropagation();
      createFork();
    }
  }
</script>

<svelte:window onkeydowncapture={onWindowKeydown} />

{#if error}
  <div class="fork-state">
    <Icon name={error === 403 ? "lock" : "file"} size={28} />
    <h1>{error === 403 ? "You can’t fork this relic" : error === 404 ? "This relic doesn’t exist" : error === 410 ? "This relic has expired" : "Couldn’t load this relic"}</h1>
    <p>{error === 403 ? "You don’t have access to it." : error === 404 ? "It may have been deleted, or the link is wrong." : "Check your connection and try again."}</p>
    <a class="r-btn r-btn-secondary r-btn-md" href="/recent">Recent relics</a>
  </div>
{:else if !relic}
  <div class="fork-state" role="status"><p>Loading the relic to fork…</p></div>
{:else}
  <Workbench {panel} phoneDrawer label="Fork">
    {#snippet pagebar({ inspectorOpen, toggleInspector })}
      <PageBar title="Fork" {inspectorOpen} ontoggleinspector={toggleInspector}>
        {#snippet filters()}
          <span class="fork-of">of <a href="/{relic.id}">{relic.name || "Untitled"}</a></span>
        {/snippet}
      </PageBar>
    {/snippet}

    <div class="fork-editor">
      <!-- ForkEditor reports edits (text and Excalidraw) with a change event; it doesn't update its prop. -->
      <ForkEditor
        isBinary={binary}
        {binaryBlob}
        {previewUrl}
        {relic}
        {editorContent}
        forkLanguage={form.syntax}
        darkMode={false}
        on:change={(e) => (editorContent = e.detail)}
      />
    </div>

    {#snippet inspector({ close })}
      <ComposeInspector
        title="Fork"
        subtitle="Starts from the original’s options"
        bind:form
        showType={!binary}
        showSpace={false}
        {busy}
        submitLabel="Create fork"
        onsubmit={createFork}
        onclose={close}
      />
    {/snippet}
  </Workbench>
{/if}

<style>
  .fork-of {
    overflow: hidden;
    color: var(--ink-3);
    text-overflow: ellipsis;
  }
  .fork-of a {
    color: var(--accent);
    font-weight: 500;
    text-decoration: none;
  }
  .fork-of a:hover {
    text-decoration: underline;
  }
  .fork-editor {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .fork-state {
    display: grid;
    justify-items: center;
    align-content: center;
    gap: var(--space-2);
    flex: 1;
    padding: var(--space-5);
    color: var(--ink-3);
    text-align: center;
  }
  .fork-state h1 {
    margin: var(--space-2) 0 0;
    color: var(--ink);
    font-size: 17px;
    font-weight: 500;
  }
  .fork-state p {
    margin: 0;
  }
</style>
