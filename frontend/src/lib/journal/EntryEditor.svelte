<script>
  // The document pane of the journal: a slim toolbar, then one page that scrolls: the title, a
  // meta line, and the text in one of three views.
  //   Write   a live editor: what you type looks like the page (headings, bullets, checkboxes,
  //           [[links]], ![[embeds]]); the Markdown syntax shows only on the line you are on
  //   Source  the plain Markdown, coloured, for when you want every character
  //   Read    the rendered page; tasks can still be ticked
  import { untrack, tick } from "svelte";
  import Icon from "../ui/Icon.svelte";
  import LiveEditor from "./live/LiveEditor.svelte";
  import { highlight, toggleTask, countWords } from "./text";
  import { longDate } from "./dates";
  import { processMarkdown } from "../../services/processors/markdownProcessor";
  import { buildEmbedCard } from "./embeds";
  import { prepareLinks } from "./links";
  import { navigate } from "../../utils/navigation";
  import { createRelic } from "../../services/api";
  import { showToast } from "../../stores/toastStore";

  let {
    entry = null, // { id, title, body, entry_date, tags, ... } or null
    mode = "write", // "write" | "source" | "read"
    readonly = false,
    onchange, // ({ title, body }) after every edit
    oncreate, // the empty state's button
    resolved = {}, // what the [[links]] point at: { target(lowercase): { kind, ... } }
    onopenentry, // (entryId) a [[link]] to another entry was clicked
  } = $props();

  let title = $state("");
  let body = $state("");
  let loaded = null;
  let live = $state(); // the LiveEditor
  let ta = $state();
  let pre = $state();
  let scroller = $state();
  let html = $state("");
  let readEl = $state(); // the rendered page, for dressing up [[links]] and ![[embeds]]
  let slash = $state(null); // { items, i, top } while the "/" menu is open in Source

  const FENCE = "```";
  const BLOCKS = [
    { name: "Heading 2", hint: "Section", glyph: "##", text: "## " },
    { name: "Heading 3", hint: "Subsection", glyph: "###", text: "### " },
    { name: "Task list", hint: "Checkboxes", glyph: "[ ]", text: "- [ ] " },
    { name: "Bullet list", hint: "Plain list", glyph: "-", text: "- " },
    { name: "Quote", hint: "Set apart a passage", glyph: ">", text: "> " },
    { name: "Code block", hint: "Fenced", glyph: "```", text: `${FENCE}\n\n${FENCE}`, caret: 4 },
    { name: "Table", hint: "Columns and rows", glyph: "|", text: "| Column | Column |\n| --- | --- |\n|  |  |" },
    { name: "Divider", hint: "Rule", glyph: "---", text: "---" },
  ];

  const editing = $derived(mode === "write");
  const sourcing = $derived(mode === "source");
  const reading = $derived(mode === "read");
  const words = $derived(countWords(body));
  const tags = $derived([...new Set([...body.matchAll(/(?:^|\s)#([a-z][\w-]*)/gi)].map((m) => m[1].toLowerCase()))]);
  const marked = $derived(sourcing ? highlight(body) : "");

  // Load another entry into the editor. Edits to the same entry never come back through here.
  $effect(() => {
    const id = entry?.id ?? null;
    untrack(() => {
      if (id === loaded) return;
      loaded = id;
      title = entry?.title ?? "";
      body = entry?.body ?? "";
      slash = null;
      live?.load(body);
      scroller?.scrollTo({ top: 0 });
      tick().then(fit);
    });
  });

  // Source: keep the textarea as tall as its text; the page scrolls, not the textarea.
  function fit() {
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.max(ta.scrollHeight, 320)}px`;
  }
  $effect(() => {
    body;
    mode;
    tick().then(fit);
  });

  // The rendered page, a moment after typing stops.
  $effect(() => {
    if (!reading) return;
    const text = body;
    const timer = setTimeout(async () => {
      const result = await processMarkdown(prepareLinks(text));
      let n = -1;
      // Task checkboxes come out disabled; number them so a click can flip the right one.
      html = readonly ? result.html : result.html.replace(/<input type="checkbox"([^>]*)>/g, (_m, rest) => `<input type="checkbox" data-ti="${++n}"${/checked/.test(rest) ? " checked" : ""}>`);
    }, 120);
    return () => clearTimeout(timer);
  });

  function emit() {
    onchange?.({ title, body });
  }

  // ---- Write (live) ----
  function onlive(text) {
    body = text;
    emit();
  }
  function onlink({ kind, id }) {
    if (kind === "entry") onopenentry?.(id);
    else navigate(`/${id}`);
  }

  // A pasted screenshot or a dropped file becomes a private relic, embedded where the cursor is.
  async function onfiles(files) {
    if (readonly) return;
    const stamp = new Date().toISOString().slice(0, 16).replace("T", " ").replace(":", "-");
    showToast(files.length === 1 ? "Uploading…" : `Uploading ${files.length} files…`);
    const embeds = [];
    for (const file of files) {
      try {
        const generic = !file.name || /^image\.\w+$/i.test(file.name);
        const name = generic ? `Pasted ${stamp}.${(file.type.split("/")[1] || "bin").replace("jpeg", "jpg")}` : file.name;
        const { data } = await createRelic({ file, name, access_level: "private" });
        embeds.push(`![[${data.id}]]`);
      } catch (error) {
        showToast(error?.response?.data?.detail || `Couldn’t upload ${file.name || "the file"}`, "error");
      }
    }
    if (embeds.length) {
      live?.insertBlock(embeds.join("\n\n"), true); // the cursor lands below, so the card shows
      showToast(embeds.length === 1 ? "Added as a private relic" : `Added ${embeds.length} private relics`, "success");
    }
  }

  // ---- Source (textarea) ----
  function oninput() {
    body = ta.value;
    fit();
    emit();
    checkSlash();
  }
  function wrap(before, after, placeholder) {
    const s = ta.selectionStart;
    const e = ta.selectionEnd;
    const picked = ta.value.slice(s, e) || placeholder;
    ta.setRangeText(before + picked + after, s, e, "end");
    ta.setSelectionRange(s + before.length, s + before.length + picked.length);
  }
  function lineRange() {
    const v = ta.value;
    const p = ta.selectionStart;
    const start = v.lastIndexOf("\n", p - 1) + 1;
    const end = v.indexOf("\n", p);
    return [start, end < 0 ? v.length : end];
  }
  function prefix(mark) {
    const [s, e] = lineRange();
    const line = ta.value.slice(s, e);
    const bare = line.replace(/^(#{1,3}\s|>\s|- \[[ x]\]\s|-\s)/, "");
    ta.setRangeText(line.startsWith(mark) ? line.slice(mark.length) : mark + bare, s, e, "end");
  }
  function heading() {
    const [s, e] = lineRange();
    const line = ta.value.slice(s, e);
    const m = line.match(/^(#{1,3})\s/);
    const next = !m ? "## " : m[1].length === 2 ? "### " : "";
    ta.setRangeText(next + line.replace(/^#{1,3}\s/, ""), s, e, "end");
  }
  const insert = (text) => ta.setRangeText(text, ta.selectionStart, ta.selectionEnd, "end");
  const ACTIONS = {
    heading,
    bold: () => wrap("**", "**", "bold"),
    italic: () => wrap("*", "*", "italic"),
    code: () => wrap("`", "`", "code"),
    quote: () => prefix("> "),
    list: () => prefix("- "),
    task: () => prefix("- [ ] "),
    link: () => wrap("[", "](https://)", "text"),
    table: () => insert("\n| Column | Column |\n| --- | --- |\n|  |  |\n"),
    rule: () => insert("\n---\n"),
  };

  const TOOLS = [
    { id: "heading", label: "Heading", text: "H" },
    { id: "bold", label: "Bold (Ctrl+B)", text: "B", bold: true },
    { id: "italic", label: "Italic (Ctrl+I)", text: "I", italic: true },
    { id: "code", label: "Code", icon: "code" },
    null,
    { id: "quote", label: "Quote", icon: "quote" },
    { id: "list", label: "Bullet list", icon: "list" },
    { id: "task", label: "Task list", icon: "task" },
    null,
    { id: "link", label: "Link (Ctrl+K)", icon: "link" },
    { id: "table", label: "Table", icon: "table" },
    { id: "rule", label: "Divider", icon: "rule" },
  ];

  function act(id) {
    if (readonly) return;
    if (editing) {
      live?.format(id);
      return;
    }
    if (!ta) return;
    ta.focus();
    ACTIONS[id]();
    body = ta.value;
    fit();
    emit();
  }

  function checkSlash() {
    const v = ta.value;
    const p = ta.selectionStart;
    const start = v.lastIndexOf("\n", p - 1) + 1;
    const m = v.slice(start, p).match(/^\s*\/(\w*)$/);
    if (!m) {
      slash = null;
      return;
    }
    const items = BLOCKS.filter((b) => b.name.toLowerCase().includes(m[1].toLowerCase()));
    if (!items.length) {
      slash = null;
      return;
    }
    const line = pre?.children[v.slice(0, p).split("\n").length - 1];
    slash = { items, i: 0, start, top: line ? line.offsetTop + line.offsetHeight + 4 : 40 };
  }
  function pickBlock(i) {
    const block = slash.items[i];
    const v = ta.value;
    let end = v.indexOf("\n", slash.start);
    end = end < 0 ? v.length : end;
    ta.setRangeText(block.text, slash.start, end, "end");
    const caret = slash.start + (block.caret ?? block.text.length);
    ta.setSelectionRange(caret, caret);
    slash = null;
    body = ta.value;
    fit();
    emit();
    ta.focus();
  }
  function onkeydown(event) {
    if (slash) {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        const n = slash.items.length;
        slash.i = (slash.i + (event.key === "ArrowDown" ? 1 : n - 1)) % n;
        return;
      }
      if (event.key === "Enter" || event.key === "Tab") {
        event.preventDefault();
        pickBlock(slash.i);
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        slash = null;
        return;
      }
    }
    if ((event.ctrlKey || event.metaKey) && !event.shiftKey && !event.altKey) {
      if (event.key === "b") {
        event.preventDefault();
        act("bold");
      } else if (event.key === "i") {
        event.preventDefault();
        act("italic");
      }
    }
  }

  // ---- Read: [[links]] and ![[embeds]] in the rendered page ----
  function decorate() {
    if (!readEl) return;
    readEl.querySelectorAll(".emb-card").forEach((n) => n.remove());
    for (const a of readEl.querySelectorAll('a[href^="#jl/"], a[href^="#je/"], a[data-t]')) {
      const embed = a.dataset.e === "1" || a.getAttribute("href")?.startsWith("#je/");
      if (!a.dataset.t) {
        a.dataset.t = decodeURIComponent(a.getAttribute("href").slice(4));
        a.dataset.e = embed ? "1" : "0";
      }
      const target = a.dataset.t;
      const info = resolved[target.toLowerCase()];
      a.classList.remove("wl", "miss", "is-relic");
      if (a.dataset.e === "1") {
        const block = a.parentElement;
        if (block?.tagName === "P" && block.textContent.trim() === a.textContent.trim()) {
          block.before(buildEmbedCard(target, info));
          block.style.display = "none";
          continue;
        }
      }
      a.classList.add("wl");
      if (info?.kind === "entry") {
        a.dataset.entry = info.id;
        a.setAttribute("href", "#");
        a.title = "Open this entry";
      } else if (info?.kind === "relic") {
        delete a.dataset.entry;
        a.setAttribute("href", `/${info.id}`);
        a.classList.add("is-relic");
        a.title = info.name || "Open this relic";
      } else {
        delete a.dataset.entry;
        a.setAttribute("href", "#");
        a.classList.add("miss");
        a.title = info ? "Nothing with this name" : "Looking…";
      }
    }
  }
  $effect(() => {
    html;
    resolved;
    tick().then(decorate);
  });

  // Ticking a task in the rendered page changes the source; a [[link]] to an entry opens it.
  function onreadclick(event) {
    const link = event.target.closest?.("a.wl, .emb-card a[data-entry]");
    if (link) {
      if (link.dataset.entry) {
        event.preventDefault();
        onopenentry?.(link.dataset.entry);
      } else if (link.getAttribute("href") === "#") {
        event.preventDefault();
      }
      return;
    }
    const box = event.target.closest?.("input[data-ti]");
    if (!box || readonly) return;
    body = toggleTask(body, Number(box.dataset.ti));
    emit();
  }

  export function focusTitle() {
    tick().then(() => {
      const input = scroller?.querySelector(".ed-title");
      input?.focus();
      input?.select();
    });
  }
  export function focusBody() {
    if (editing) live?.focus(true);
    else ta?.focus();
  }

  /** Scroll to a heading of the outline: `h` has its source line, `index` its place among the headings. */
  export function goto(h, index) {
    if (editing) live?.scrollToLine(h.line);
    else if (sourcing) pre?.children[h.line]?.scrollIntoView({ block: "start", behavior: "smooth" });
    else readEl?.querySelectorAll("h1, h2, h3")[index]?.scrollIntoView({ block: "start", behavior: "smooth" });
  }
</script>

{#if !entry}
  <div class="ed ed-empty">
    <Icon name="book" size={26} />
    <p>Select an entry, or start a new one.</p>
    {#if oncreate}<button class="r-btn r-btn-primary r-btn-md" onclick={oncreate}><Icon name="plus" />New entry</button>{/if}
  </div>
{:else}
  <div class="ed">
    {#if !reading && !readonly}
      <div class="ed-tools" role="toolbar" aria-label="Formatting">
        {#each TOOLS as tool}
          {#if tool}
            <button
              class="ed-tool"
              class:is-text={tool.text}
              class:is-bold={tool.bold}
              class:is-italic={tool.italic}
              title={tool.label}
              aria-label={tool.label}
              onmousedown={(e) => {
                e.preventDefault();
                act(tool.id);
              }}
            >{#if tool.text}{tool.text}{:else}<Icon name={tool.icon} />{/if}</button>
          {:else}
            <span class="ed-sep"></span>
          {/if}
        {/each}
      </div>
    {/if}

    <div class="ed-scroll" bind:this={scroller}>
      <div class="ed-col">
        <input
          class="ed-title"
          placeholder="Untitled"
          aria-label="Entry title"
          {readonly}
          bind:value={title}
          oninput={emit}
          onkeydown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              focusBody();
            }
          }}
        />
        <div class="ed-meta">
          <span><Icon name="calendar" size={13} />{longDate(entry.entry_date)}</span>
          <span>{words.toLocaleString("en-US")} {words === 1 ? "word" : "words"} · {Math.max(1, Math.round(words / 220))} min</span>
          {#if tags.length}<span>{#each tags as tag}<span class="ed-tag">#{tag}</span>{/each}</span>{/if}
          <span><Icon name="lock" size={13} />{readonly ? "Read-only" : "Only you"}</span>
        </div>

        {#if editing}
          <div class="ed-live">
            <LiveEditor bind:this={live} doc={body} {readonly} {resolved} onchange={onlive} {onlink} {onfiles} />
          </div>
        {:else if sourcing}
          <div class="ed-srcin">
            <pre bind:this={pre} aria-hidden="true">{@html marked}</pre>
            <textarea
              bind:this={ta}
              value={body}
              {readonly}
              spellcheck="false"
              aria-label="Entry body"
              {oninput}
              {onkeydown}
              onclick={checkSlash}
              onblur={() => setTimeout(() => (slash = null), 120)}
            ></textarea>
            {#if slash}
              <div class="ed-slash" style="top:{slash.top}px" role="listbox" aria-label="Blocks">
                {#each slash.items as item, i}
                  <div class="ed-slash-item" class:is-on={i === slash.i} role="option" aria-selected={i === slash.i} tabindex="-1" onmousedown={(e) => { e.preventDefault(); pickBlock(i); }}>
                    <code>{item.glyph}</code><span>{item.name}</span><small>{item.hint}</small>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {:else}
          <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
          <div class="ed-read" bind:this={readEl} onclick={onreadclick}>{@html html}</div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .ed {
    flex: 1;
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    background: var(--surface);
  }
  .ed-empty {
    align-items: center;
    justify-content: center;
    gap: var(--space-3);
    color: var(--ink-3);
  }
  .ed-empty p {
    margin: 0;
  }
  .ed-tools {
    flex: none;
    display: flex;
    align-items: center;
    gap: 2px;
    height: 36px;
    padding: 0 var(--space-3);
    border-bottom: 1px solid var(--line);
    overflow: hidden;
  }
  .ed-tool {
    flex: none;
    display: grid;
    place-items: center;
    min-width: 28px;
    height: 28px;
    padding: 0;
    border: 0;
    border-radius: var(--radius-sm);
    background: none;
    color: var(--ink-2);
    cursor: pointer;
  }
  .ed-tool:hover {
    background: var(--chip);
    color: var(--ink);
  }
  .ed-tool.is-text {
    padding: 0 8px;
    font: 700 13px var(--font-sans);
  }
  .ed-tool.is-italic {
    font: italic 400 15px serif;
  }
  .ed-sep {
    flex: none;
    width: 1px;
    height: 16px;
    margin: 0 6px;
    background: var(--line);
  }

  /* One scrolling page: the title, the meta line and the text move together. */
  .ed-scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    scroll-padding-top: 16px;
  }
  .ed-col {
    width: 100%;
    max-width: 780px;
    margin-inline: auto;
    padding-inline: 48px;
  }
  .ed-title {
    width: 100%;
    padding: 30px 0 6px;
    border: 0;
    outline: 0;
    background: none;
    color: var(--ink);
    font: 700 32px/1.2 var(--font-sans);
    letter-spacing: -0.02em;
  }
  .ed-title::placeholder {
    color: var(--ink-4);
  }
  .ed-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 16px;
    padding-bottom: 12px;
    color: var(--ink-3);
    font-size: 12px;
  }
  .ed-meta > span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .ed-tag {
    margin-right: 6px;
    color: var(--accent);
    font-weight: 500;
  }

  /* Source: a colour layer (pre) under a transparent textarea, identical metrics. */
  .ed-srcin {
    position: relative;
    padding: 6px 0 200px;
  }
  .ed-srcin pre,
  .ed-srcin textarea {
    width: 100%;
    margin: 0;
    padding: 0;
    border: 0;
    font: 14.5px/26px var(--font-mono);
    letter-spacing: 0;
    tab-size: 2;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    word-break: normal;
  }
  .ed-srcin pre {
    position: absolute;
    inset: 6px 0 auto;
    color: var(--ink);
    pointer-events: none;
  }
  .ed-srcin textarea {
    position: relative;
    display: block;
    min-height: 320px;
    resize: none;
    overflow: hidden;
    outline: 0;
    background: transparent;
    color: transparent;
    caret-color: var(--accent);
  }
  .ed-srcin textarea:focus,
  .ed-srcin textarea:focus-visible {
    outline: 0;
    box-shadow: none;
  }
  .ed-srcin textarea::selection {
    background: color-mix(in srgb, var(--accent) 22%, transparent);
  }
  .ed-srcin :global(.ln) {
    display: block;
  }
  .ed-srcin :global(.ln.h) {
    color: var(--accent);
    font-weight: 700;
  }
  .ed-srcin :global(.ln.q) {
    color: var(--ink-2);
  }
  .ed-srcin :global(.ln.dn) {
    color: var(--ink-3);
  }
  .ed-srcin :global(.mk) {
    color: var(--ink-4);
  }
  .ed-srcin :global(.ln.h .mk) {
    color: var(--accent);
    opacity: 0.45;
  }
  .ed-srcin :global(.hc),
  .ed-srcin :global(.hf) {
    color: var(--type-code);
  }
  .ed-srcin :global(.hf) {
    opacity: 0.6;
  }
  .ed-srcin :global(.ic) {
    border-radius: 3px;
    background: var(--chip);
    color: var(--type-code);
  }
  .ed-srcin :global(.bd) {
    font-weight: 700;
  }
  .ed-srcin :global(.it) {
    font-style: italic;
  }
  .ed-srcin :global(.wk) {
    border-radius: 3px;
    background: var(--info-soft);
    color: var(--type-doc);
  }
  .ed-srcin :global(.lk) {
    color: var(--info-ink);
  }
  .ed-srcin :global(.tg) {
    color: var(--accent);
  }
  .ed-slash {
    position: absolute;
    left: 0;
    z-index: 6;
    width: 272px;
    padding: 4px;
    border: 1px solid var(--line-2);
    border-radius: var(--radius-md);
    background: var(--surface);
    box-shadow: var(--shadow-popover);
    font: 13px var(--font-sans);
  }
  .ed-slash-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 8px;
    border-radius: var(--radius-sm);
    cursor: pointer;
  }
  .ed-slash-item.is-on {
    background: var(--checked);
  }
  .ed-slash-item code {
    width: 34px;
    color: var(--accent);
    font: 12px var(--font-mono);
  }
  .ed-slash-item small {
    margin-left: auto;
    color: var(--ink-3);
    font-size: 11px;
  }

  /* Read: the same typography as the live editor, so writing and reading are one page. */
  .ed-read {
    padding: 6px 0 200px;
    color: var(--ink);
    font-size: 16px;
    line-height: 1.75;
    overflow-wrap: anywhere;
  }
  .ed-read > :global(*:first-child) {
    margin-top: 0;
  }
  .ed-read :global(h1),
  .ed-read :global(h2),
  .ed-read :global(h3),
  .ed-read :global(h4),
  .ed-read :global(h5),
  .ed-read :global(h6) {
    margin: 1.3em 0 0.35em;
    padding: 0;
    border: 0;
    color: var(--ink);
    font-weight: 700;
    letter-spacing: -0.01em;
    line-height: 1.3;
  }
  .ed-read :global(h1) {
    font-size: 1.75em;
    margin-top: 1.5em;
  }
  .ed-read :global(h2) {
    font-size: 1.4em;
  }
  .ed-read :global(h3) {
    font-size: 1.15em;
  }
  .ed-read :global(h4),
  .ed-read :global(h5),
  .ed-read :global(h6) {
    font-size: 1em;
  }
  .ed-read :global(p) {
    margin: 0 0 0.85em;
  }
  .ed-read :global(a) {
    color: var(--info-ink);
    font-weight: 400;
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  .ed-read :global(a.wl) {
    color: var(--type-doc);
    text-decoration: none;
    border-bottom: 1px solid color-mix(in srgb, var(--type-doc) 35%, transparent);
  }
  .ed-read :global(a.wl.is-relic) {
    color: var(--accent);
    border-bottom-color: color-mix(in srgb, var(--accent) 35%, transparent);
  }
  .ed-read :global(a.wl.miss) {
    color: var(--ink-3);
    border-bottom-style: dashed;
  }
  .ed-read :global(ul),
  .ed-read :global(ol) {
    margin: 0 0 0.85em;
    padding-left: 1.6em;
  }
  .ed-read :global(ul) {
    list-style: disc;
  }
  .ed-read :global(ol) {
    list-style: decimal;
  }
  .ed-read :global(li) {
    margin: 0.15em 0;
    padding-left: 0.2em;
  }
  .ed-read :global(li::marker) {
    color: var(--ink-3);
  }
  .ed-read :global(li > ul),
  .ed-read :global(li > ol) {
    margin: 0.15em 0 0;
  }
  .ed-read :global(li > p) {
    margin: 0;
  }
  .ed-read :global(ul.contains-task-list) {
    padding-left: 0;
    list-style: none;
  }
  .ed-read :global(li.task-list-item) {
    list-style: none;
    padding-left: 0;
  }
  .ed-read :global(li.task-list-item > ul),
  .ed-read :global(li.task-list-item > ol) {
    padding-left: 1.6em;
  }
  .ed-read :global(input[type="checkbox"]) {
    width: 15px;
    height: 15px;
    margin: 0 0.6em 0 0;
    vertical-align: -2px;
    accent-color: var(--accent);
    color: var(--accent);
  }
  .ed-read :global(code)::before,
  .ed-read :global(code)::after {
    content: none;
  }
  .ed-read :global(code) {
    padding: 1px 4px;
    border-radius: 4px;
    background: var(--chip);
    color: var(--type-code);
    font: 0.9em var(--font-mono);
  }
  .ed-read :global(pre) {
    margin: 0 0 0.85em;
    padding: 10px 14px;
    overflow-x: auto;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    background: var(--subtle);
    font: 0.875em/1.6 var(--font-mono);
  }
  .ed-read :global(pre code) {
    padding: 0;
    background: none;
    color: var(--code-ink);
    font: inherit;
  }
  .ed-read :global(blockquote) {
    margin: 0 0 0.85em;
    padding-left: 16px;
    border-left: 3px solid var(--line-2);
    color: var(--ink-2);
  }
  .ed-read :global(blockquote > p:last-child) {
    margin-bottom: 0;
  }
  .ed-read :global(hr) {
    margin: 1.1em 0;
    border: 0;
    border-top: 1px solid var(--line-2);
  }
  .ed-read :global(.table-scroll) {
    margin: 0 0 0.85em;
    overflow-x: auto;
  }
  .ed-read :global(table) {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
    line-height: 1.5;
  }
  .ed-read :global(th),
  .ed-read :global(td) {
    padding: 7px 12px;
    border: 1px solid var(--line);
    text-align: left;
  }
  .ed-read :global(th) {
    background: var(--subtle);
    font-weight: 500;
  }
  .ed-read :global(img) {
    max-width: 100%;
    border-radius: var(--radius-sm);
  }
  .ed-read :global(mark) {
    background: var(--mark);
    color: inherit;
  }
  .ed-read :global(.emb-card) {
    margin: 12px 0;
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    background: var(--surface);
    font-size: 14px;
    line-height: 1.5;
  }
  .ed-read :global(.emb-card.is-missing) {
    border-style: dashed;
    color: var(--ink-3);
  }
  .ed-read :global(.emb-head) {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 12px;
    background: var(--subtle);
  }
  .ed-read :global(.emb-head b) {
    font-weight: 500;
  }
  .ed-read :global(.emb-head em) {
    color: var(--ink-3);
    font: 12px var(--font-mono);
    font-style: normal;
  }
  .ed-read :global(.emb-head a) {
    margin-left: auto;
    color: var(--accent);
    font-size: 12px;
    font-weight: 500;
    text-decoration: none;
  }
  .ed-read :global(.emb-card pre) {
    margin: 0;
    padding: 10px 14px;
    border: 0;
    border-top: 1px solid var(--line);
    border-radius: 0;
    background: var(--surface);
    color: var(--ink);
    font: 13px/1.55 var(--font-mono);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .ed-read :global(.emb-card img) {
    display: block;
    max-width: 100%;
    max-height: 420px;
    margin: 0 auto;
  }
  @media (max-width: 767px) {
    .ed-col {
      padding-inline: 16px;
    }
    .ed-title {
      font-size: 24px;
      padding-top: 18px;
    }
  }
</style>
