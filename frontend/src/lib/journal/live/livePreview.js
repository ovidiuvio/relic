// Live preview: the Markdown you write is shown as the page it makes. Headings are big, **bold** is
// bold, lists have bullets, tasks have checkboxes, [[links]] are links and ![[embeds]] are cards.
// The characters that make the formatting (##, **, [ ]( ), > …) are hidden on every line except
// the one you are on, so you can still see and edit them where you are typing.
//
// The decorations come from the Markdown syntax tree plus a few line patterns the parser doesn't
// know (wiki links, embeds, #tags), and are kept in a state field: block widgets (embeds, rules)
// can't be made by view plugins.
import { StateEffect, StateField } from "@codemirror/state";
import { Decoration, EditorView } from "@codemirror/view";
import { ensureSyntaxTree, syntaxTree } from "@codemirror/language";
import { BulletWidget, CheckboxWidget, EmbedWidget, ImageWidget, NumberWidget, RuleWidget, TableWidget } from "./widgets";

/** What the [[links]] point at, from the server: { target(lowercase): { kind, ... } }. */
export const setResolved = StateEffect.define();
const setFocused = StateEffect.define();
export const setReadonly = StateEffect.define();

const WIKI = /(!?)\[\[([^\]\n|]+)(?:\|([^\]\n]+))?\]\]/g;
const EMBED_LINE = /^\s*!\[\[([^\]\n|]+)(?:\|[^\]\n]+)?\]\]\s*$/;
const TAG = /(^|\s)(#[a-z][\w-]*)/gi;
const KBD = /<kbd>[^<\n]+<\/kbd>/g;

function build(state, resolved, focused, readonly) {
  const doc = state.doc;
  const items = [];
  const atomic = [];

  // Lines the cursor or selection touches keep their syntax visible.
  const active = new Set();
  if (focused) {
    for (const r of state.selection.ranges) {
      for (let n = doc.lineAt(r.from).number, last = doc.lineAt(r.to).number; n <= last; n++) active.add(n);
    }
  }
  const isActive = (from, to) => {
    for (let n = doc.lineAt(from).number, last = doc.lineAt(Math.min(to, doc.length)).number; n <= last; n++) if (active.has(n)) return true;
    return false;
  };

  const hide = (from, to) => {
    if (to <= from) return;
    const d = Decoration.replace({});
    items.push(d.range(from, to));
    atomic.push(d.range(from, to));
  };
  const widget = (from, to, w, block = false) => {
    const d = Decoration.replace({ widget: w, block });
    items.push(d.range(from, to));
    atomic.push(d.range(from, to));
  };
  const line = (pos, cls, style) => items.push(Decoration.line({ attributes: { class: cls, ...(style ? { style } : {}) } }).range(doc.lineAt(pos).from));
  const mark = (from, to, cls, attributes) => {
    if (to > from) items.push(Decoration.mark({ class: cls, attributes }).range(from, to));
  };
  const dim = (from, to) => mark(from, to, "cm-syntax");

  const codeLines = new Set();
  const codeRanges = [];
  const handled = new Set(); // lines drawn by a block widget

  const tree = ensureSyntaxTree(state, doc.length, 200) ?? syntaxTree(state);
  tree.iterate({
    enter: (ref) => {
      const { name, from, to } = ref;
      let m;
      if ((m = /^ATXHeading([1-6])$/.exec(name))) {
        line(from, `cm-h cm-h${m[1]}`);
        const hm = ref.node.getChild("HeaderMark");
        if (hm) {
          if (isActive(from, to)) dim(hm.from, hm.to);
          else hide(hm.from, Math.min(hm.to + 1, to));
        }
        return;
      }
      switch (name) {
        case "StrongEmphasis":
        case "Emphasis":
        case "Strikethrough": {
          mark(from, to, name === "StrongEmphasis" ? "cm-strong" : name === "Emphasis" ? "cm-em" : "cm-strike");
          const on = isActive(from, to);
          for (const child of ref.node.getChildren(name === "Strikethrough" ? "StrikethroughMark" : "EmphasisMark")) (on ? dim : hide)(child.from, child.to);
          return;
        }
        case "InlineCode": {
          codeRanges.push([from, to]);
          const marks = ref.node.getChildren("CodeMark");
          const on = isActive(from, to);
          if (marks.length >= 2) mark(marks[0].to, marks[marks.length - 1].from, "cm-code-inline");
          for (const child of marks) (on ? dim : hide)(child.from, child.to);
          return false;
        }
        case "Link": {
          const marks = ref.node.getChildren("LinkMark");
          const url = ref.node.getChild("URL");
          // [text] with no (url) is not a link here: it is text, or the inside of a [[wiki link]]
          if (marks.length >= 2 && url) {
            const href = url ? state.sliceDoc(url.from, url.to) : "";
            mark(marks[0].to, marks[1].from, "cm-link", href ? { "data-href": href, title: `${href} (Ctrl+click to open)` } : undefined);
            if (isActive(from, to)) {
              dim(marks[0].from, marks[0].to);
              dim(marks[1].from, to);
            } else {
              hide(marks[0].from, marks[0].to);
              hide(marks[1].from, to);
            }
          }
          return false;
        }
        case "Image": {
          const m = /^!\[([^\]]*)\]\(\s*([^)\s]+)/.exec(state.sliceDoc(from, to));
          if (m && /^(https?:\/\/|\/)/.test(m[2]) && !isActive(from, to)) widget(from, to, new ImageWidget(m[2], m[1]));
          return false;
        }
        case "URL":
          mark(from, to, "cm-link", { "data-href": state.sliceDoc(from, to) });
          return;
        case "FencedCode":
        case "CodeBlock": {
          const first = doc.lineAt(from).number;
          const last = doc.lineAt(to).number;
          for (let n = first; n <= last; n++) {
            const l = doc.line(n);
            codeLines.add(n);
            const fence = name === "FencedCode" && (n === first || (n === last && /^\s*(```|~~~)/.test(l.text)));
            line(l.from, `cm-code-line${n === first ? " cm-code-first" : ""}${n === last ? " cm-code-last" : ""}${fence ? " cm-code-fence" : ""}`);
          }
          return false;
        }
        case "Blockquote": {
          for (let n = doc.lineAt(from).number, last = doc.lineAt(to).number; n <= last; n++) line(doc.line(n).from, "cm-quote");
          return;
        }
        case "QuoteMark":
          if (isActive(from, to)) dim(from, to);
          else hide(from, Math.min(to + (doc.sliceString(to, to + 1) === " " ? 1 : 0), doc.length));
          return;
        case "HorizontalRule":
          if (isActive(from, to)) line(from, "cm-rule-source");
          else {
            widget(from, to, new RuleWidget(), true);
            handled.add(doc.lineAt(from).number);
          }
          return false;
        case "ListItem": {
          let depth = -1;
          for (let p = ref.node.parent; p; p = p.parent) if (p.name === "BulletList" || p.name === "OrderedList") depth++;
          const l = doc.lineAt(from);
          const lm = ref.node.getChild("ListMark");
          if (!lm) return;
          const ordered = ref.node.parent?.name === "OrderedList";
          const task = ref.node.getChild("Task");
          const tm = task?.getChild("TaskMarker");
          line(from, `cm-li${tm ? " cm-li-task" : ""}`, `--depth:${Math.max(0, depth)}`);
          if (lm.from > l.from) hide(l.from, lm.from); // the indent is drawn by the line's padding
          const after = doc.sliceString(lm.to, lm.to + 1) === " " ? 1 : 0;
          if (tm) {
            const checked = /\[(x|X)\]/.test(state.sliceDoc(tm.from, tm.to));
            widget(lm.from, Math.min(tm.to + (doc.sliceString(tm.to, tm.to + 1) === " " ? 1 : 0), l.to), new CheckboxWidget(checked, readonly));
            if (checked) mark(Math.min(tm.to + 1, l.to), l.to, "cm-task-done");
          } else if (isActive(from, l.to)) {
            dim(lm.from, lm.to);
          } else {
            widget(lm.from, Math.min(lm.to + after, l.to), ordered ? new NumberWidget(state.sliceDoc(lm.from, lm.to)) : new BulletWidget());
          }
          return;
        }
        case "Table": {
          const first = doc.lineAt(from).number;
          const last = doc.lineAt(to).number;
          for (let n = first; n <= last; n++) codeLines.add(n);
          if (!isActive(from, to) && last - first >= 1) {
            // Not being edited: draw it as a table.
            widget(from, to, new TableWidget(state.sliceDoc(from, to)), true);
            for (let n = first; n <= last; n++) handled.add(n);
            return false;
          }
          for (let n = first; n <= last; n++) line(doc.line(n).from, `cm-table-line${n === first ? " cm-table-head" : ""}`);
          return;
        }
        case "TableDelimiter":
          dim(from, to);
          return;
        default:
      }
    },
  });

  // Patterns the Markdown parser doesn't know, on lines that aren't code.
  const inCode = (pos) => codeRanges.some(([a, b]) => pos >= a && pos < b);
  for (let n = 1; n <= doc.lines; n++) {
    const l = doc.line(n);
    if (handled.has(n)) continue;
    if (l.length === 0) {
      line(l.from, "cm-blank");
      continue;
    }
    if (codeLines.has(n)) continue;
    const lineActive = active.has(n);

    const embed = EMBED_LINE.exec(l.text);
    if (embed && !lineActive) {
      const target = embed[1].trim();
      widget(l.from, l.to, new EmbedWidget(target, resolved[target.toLowerCase()]), true);
      continue;
    }

    WIKI.lastIndex = 0;
    for (let w = WIKI.exec(l.text); w; w = WIKI.exec(l.text)) {
      const start = l.from + w.index;
      if (inCode(start)) continue;
      const end = start + w[0].length;
      const target = w[2].trim();
      const info = resolved[target.toLowerCase()];
      const kind = info?.kind ?? "loading";
      const attrs = { "data-wiki": target, ...(info?.kind === "entry" ? { "data-entry": info.id } : {}), ...(info?.kind === "relic" ? { "data-relic": info.id } : {}) };
      const open = start + w[1].length + 2; // after [[ or ![[
      const bodyStart = w[3] ? open + w[2].length + 1 : open; // after "target|" when there is an alias
      mark(bodyStart, end - 2, `cm-wiki cm-wiki-${kind}`, attrs);
      if (lineActive) {
        dim(start, bodyStart);
        dim(end - 2, end);
      } else {
        hide(start, bodyStart);
        hide(end - 2, end);
      }
    }

    // <kbd>Ctrl</kbd> keys, as the reading view shows them
    KBD.lastIndex = 0;
    for (let k = KBD.exec(l.text); k; k = KBD.exec(l.text)) {
      const start = l.from + k.index;
      if (inCode(start)) continue;
      const innerFrom = start + 5;
      const innerTo = start + k[0].length - 6;
      mark(innerFrom, innerTo, "cm-kbd");
      if (lineActive) {
        dim(start, innerFrom);
        dim(innerTo, start + k[0].length);
      } else {
        hide(start, innerFrom);
        hide(innerTo, start + k[0].length);
      }
    }

    TAG.lastIndex = 0;
    for (let t = TAG.exec(l.text); t; t = TAG.exec(l.text)) {
      const at = l.from + t.index + t[1].length;
      if (!inCode(at)) mark(at, at + t[2].length, "cm-tag");
    }
  }

  return { deco: Decoration.set(items, true), atomic: Decoration.set(atomic, true) };
}

export const livePreviewField = StateField.define({
  create(state) {
    const value = { resolved: {}, focused: false, readonly: false };
    return { ...value, ...build(state, value.resolved, value.focused, value.readonly) };
  },
  update(value, tr) {
    let { resolved, focused, readonly } = value;
    let changed = tr.docChanged || !!tr.selection;
    for (const e of tr.effects) {
      if (e.is(setResolved)) [resolved, changed] = [e.value, true];
      else if (e.is(setFocused)) [focused, changed] = [e.value, true];
      else if (e.is(setReadonly)) [readonly, changed] = [e.value, true];
    }
    if (!changed) return value;
    return { resolved, focused, readonly, ...build(tr.state, resolved, focused, readonly) };
  },
  provide: (field) => [
    EditorView.decorations.from(field, (v) => v.deco),
    EditorView.atomicRanges.of((view) => view.state.field(field).atomic),
  ],
});

/** Tells the field whether the editor has focus (syntax shows only while it does). */
export const focusTracker = EditorView.focusChangeEffect.of((_state, focusing) => setFocused.of(focusing));
