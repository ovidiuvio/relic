<script>
  // The journal's live editor (CodeMirror 6): Markdown that looks like the page it makes while you
  // write it. Headings are big, **bold** is bold, lists have bullets, tasks have checkboxes, [[links]]
  // and ![[embeds]] work, and the syntax shows only on the line you are on (see livePreview.js).
  // Type "/" on an empty line for a menu of blocks.
  import { onMount, tick } from "svelte";
  import { Compartment, EditorState, Prec } from "@codemirror/state";
  import { EditorView, drawSelection, keymap, placeholder as placeholderExt } from "@codemirror/view";
  import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
  import { markdown, markdownLanguage } from "@codemirror/lang-markdown";
  import { focusTracker, livePreviewField, setReadonly, setResolved } from "./livePreview";
  import { FORMATS, insertBlock as insertBlockAt, replaceLine } from "./commands";
  import { liveTheme } from "./theme";

  let {
    doc = "", // the text to start with (use load() to change it later)
    readonly = false,
    resolved = {}, // what the [[links]] point at
    placeholder = "Start writing. Type / for blocks.",
    onchange, // (text) after every edit
    onlink, // ({ kind: "entry" | "relic", id }) a rendered [[link]] was clicked
    onfiles, // (File[]) files were pasted or dropped
  } = $props();

  let host = $state();
  let view = $state.raw(null);
  let slash = $state(null); // { items, i, x, y } while the "/" menu is open
  let loading = false;

  const FENCE = "```";
  const BLOCKS = [
    { name: "Heading 2", hint: "Section", glyph: "##", text: "## " },
    { name: "Heading 3", hint: "Subsection", glyph: "###", text: "### " },
    { name: "Task list", hint: "Checkboxes", glyph: "[ ]", text: "- [ ] " },
    { name: "Bullet list", hint: "Plain list", glyph: "•", text: "- " },
    { name: "Quote", hint: "Set apart a passage", glyph: ">", text: "> " },
    { name: "Code block", hint: "Fenced", glyph: "```", text: `${FENCE}\n\n${FENCE}`, caret: 4 },
    { name: "Table", hint: "Columns and rows", glyph: "|", text: "| Column | Column |\n| --- | --- |\n|  |  |" },
    { name: "Divider", hint: "Rule", glyph: "—", text: "---" },
    { name: "Link to an entry", hint: "[[Entry title]]", glyph: "[[", text: "[[]]", caret: 2 },
    { name: "Embed a relic", hint: "![[relic name]]", glyph: "![[", text: "![[]]", caret: 3 },
  ];

  const readonlyCompartment = new Compartment();

  function checkSlash(v) {
    const { state } = v;
    const head = state.selection.main.head;
    const line = state.doc.lineAt(head);
    const m = /^\s*\/(\w*)$/.exec(state.sliceDoc(line.from, head));
    if (!m || !state.selection.main.empty) {
      slash = null;
      return;
    }
    const items = BLOCKS.filter((b) => b.name.toLowerCase().includes(m[1].toLowerCase()));
    if (!items.length) {
      slash = null;
      return;
    }
    const c = v.coordsAtPos(head);
    const box = host.getBoundingClientRect();
    slash = { items, i: 0, x: Math.max(0, (c?.left ?? box.left) - box.left), y: (c?.bottom ?? box.top) - box.top + 6 };
  }

  function pick(i) {
    const block = slash.items[i];
    slash = null;
    replaceLine(view, block.text, block.caret ?? block.text.length);
  }

  // While the menu is open it owns these keys.
  const slashKeys = Prec.highest(
    keymap.of([
      { key: "ArrowDown", run: () => !!slash && ((slash.i = (slash.i + 1) % slash.items.length), true) },
      { key: "ArrowUp", run: () => !!slash && ((slash.i = (slash.i + slash.items.length - 1) % slash.items.length), true) },
      { key: "Enter", run: () => !!slash && (pick(slash.i), true) },
      { key: "Tab", run: () => !!slash && (pick(slash.i), true) },
      { key: "Escape", run: () => !!slash && ((slash = null), true) },
    ])
  );

  const shortcuts = keymap.of([
    { key: "Mod-b", run: (v) => (FORMATS.bold(v), true) },
    { key: "Mod-i", run: (v) => (FORMATS.italic(v), true) },
    { key: "Mod-k", run: (v) => (FORMATS.link(v), true) },
  ]);

  // A click on a rendered [[link]] follows it, unless the cursor is already on that line (then it
  // just places the cursor, so you can edit the link). Ctrl/Cmd+click opens an external link.
  const clicks = EditorView.domEventHandlers({
    mousedown(event, v) {
      const target = event.target instanceof Element ? event.target : null;
      const link = target?.closest(".cm-link[data-href]");
      if (link && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        window.open(link.getAttribute("data-href"), "_blank", "noopener");
        return true;
      }
      const wiki = target?.closest(".cm-wiki");
      if (!wiki || event.button !== 0 || event.shiftKey) return false;
      const pos = v.posAtDOM(wiki);
      const line = v.state.doc.lineAt(pos).number;
      const onLine = v.state.selection.ranges.some((r) => v.state.doc.lineAt(r.from).number <= line && line <= v.state.doc.lineAt(r.to).number);
      if (onLine && v.hasFocus) return false;
      const entry = wiki.getAttribute("data-entry");
      const relic = wiki.getAttribute("data-relic");
      if (entry || relic) {
        event.preventDefault();
        onlink?.({ kind: entry ? "entry" : "relic", id: entry ?? relic });
        return true;
      }
      return false;
    },
  });

  // Pasted or dropped files go to the parent (which uploads them); text pastes normally.
  const files = EditorView.domEventHandlers({
    paste(event) {
      const list = Array.from(event.clipboardData?.files ?? []);
      if (!list.length || !onfiles || readonly) return false;
      event.preventDefault();
      onfiles(list);
      return true;
    },
    drop(event) {
      const list = Array.from(event.dataTransfer?.files ?? []);
      if (!list.length || !onfiles || readonly) return false;
      event.preventDefault();
      onfiles(list);
      return true;
    },
  });

  function extensions() {
    return [
      history(),
      drawSelection(),
      EditorView.lineWrapping,
      markdown({ base: markdownLanguage }),
      livePreviewField,
      focusTracker,
      liveTheme,
      placeholderExt(placeholder),
      readonlyCompartment.of(EditorState.readOnly.of(readonly)),
      slashKeys,
      shortcuts,
      keymap.of([indentWithTab, ...defaultKeymap, ...historyKeymap]),
      clicks,
      files,
      EditorView.contentAttributes.of({ "aria-label": "Entry text", spellcheck: "true" }),
      EditorView.updateListener.of((update) => {
        if (update.docChanged && !loading) onchange?.(update.state.doc.toString());
        if (update.docChanged || update.selectionSet) checkSlash(update.view);
        if (update.focusChanged && !update.view.hasFocus) slash = null;
      }),
    ];
  }

  const stateFor = (text) => EditorState.create({ doc: text, extensions: extensions() });

  onMount(() => {
    view = new EditorView({ state: stateFor(doc), parent: host });
    view.dispatch({ effects: [setResolved.of(resolved), setReadonly.of(readonly)] });
    return () => view.destroy();
  });

  // What the links point at changed (the server answered): redraw them.
  $effect(() => {
    const map = resolved;
    view?.dispatch({ effects: setResolved.of(map) });
  });
  $effect(() => {
    const ro = readonly;
    view?.dispatch({ effects: [readonlyCompartment.reconfigure(EditorState.readOnly.of(ro)), setReadonly.of(ro)] });
  });

  /** Replace the whole text (another entry): resets undo history and the selection. */
  export function load(text) {
    if (!view) return;
    loading = true;
    slash = null;
    view.setState(stateFor(text));
    view.dispatch({ effects: [setResolved.of(resolved), setReadonly.of(readonly)] });
    loading = false;
  }
  export function focus(end = false) {
    if (!view) return;
    if (end) view.dispatch({ selection: { anchor: view.state.doc.length } });
    view.focus();
  }
  export function format(kind) {
    if (view && !readonly && FORMATS[kind]) FORMATS[kind](view);
  }
  /** Put text on its own lines after the cursor's line. */
  export function insertBlock(text, trailing = false) {
    if (view && !readonly) insertBlockAt(view, text, null, trailing);
  }
  export function insert(text) {
    if (!view || readonly) return;
    const r = view.state.selection.main;
    view.dispatch({ changes: { from: r.from, to: r.to, insert: text }, selection: { anchor: r.from + text.length } });
    view.focus();
  }
  /** The scroll position of a line, for the outline. */
  export function coordsOfLine(line) {
    if (!view || line < 0 || line >= view.state.doc.lines) return null;
    return view.lineBlockAt(view.state.doc.line(line + 1).from);
  }
  export function scrollToLine(line) {
    if (!view || line < 0 || line >= view.state.doc.lines) return;
    view.dispatch({ effects: EditorView.scrollIntoView(view.state.doc.line(line + 1).from, { y: "start", yMargin: 24 }) });
  }
</script>

<div class="live" bind:this={host}>
  {#if slash}
    <div class="live-slash" style="left:{slash.x}px; top:{slash.y}px" role="listbox" aria-label="Blocks">
      {#each slash.items as item, i}
        <div class="live-slash-item" class:is-on={i === slash.i} role="option" aria-selected={i === slash.i} tabindex="-1" onmousedown={(e) => { e.preventDefault(); pick(i); }}>
          <code>{item.glyph}</code><span>{item.name}</span><small>{item.hint}</small>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .live {
    position: relative;
  }
  .live-slash {
    position: absolute;
    z-index: 10;
    width: 280px;
    padding: 4px;
    border: 1px solid var(--line-2);
    border-radius: var(--radius-md);
    background: var(--surface);
    box-shadow: var(--shadow-popover);
    font: 13px/1.4 var(--font-sans);
  }
  .live-slash-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 8px;
    border-radius: var(--radius-sm);
    cursor: pointer;
  }
  .live-slash-item.is-on {
    background: var(--checked);
  }
  .live-slash-item code {
    width: 34px;
    color: var(--accent);
    font: 12px var(--font-mono);
  }
  .live-slash-item small {
    margin-left: auto;
    color: var(--ink-3);
    font: 11px var(--font-mono);
  }
</style>
