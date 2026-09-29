// Formatting commands for the live editor: wrap the selection (bold, italic, code, link), toggle a
// prefix on the selected lines (quote, lists, tasks), cycle heading levels, and insert blocks.
import { EditorSelection } from "@codemirror/state";

const LINE_MARK = /^(\s*)(#{1,3}\s|>\s|- \[[ xX]\]\s|[-*+]\s|\d+\.\s)?/;

/** Wrap the selection in `before` / `after`, or unwrap it when it already is. */
export function wrapSelection(view, before, after, placeholder) {
  const { state } = view;
  const r = state.selection.main;
  const text = state.sliceDoc(r.from, r.to);
  const near = (a, b) => state.sliceDoc(Math.max(0, a), b);
  if (text && near(r.from - before.length, r.from) === before && state.sliceDoc(r.to, r.to + after.length) === after) {
    view.dispatch({
      changes: [
        { from: r.from - before.length, to: r.from, insert: "" },
        { from: r.to, to: r.to + after.length, insert: "" },
      ],
      selection: EditorSelection.range(r.from - before.length, r.to - before.length),
    });
  } else {
    const inner = text || placeholder;
    view.dispatch({
      changes: { from: r.from, to: r.to, insert: before + inner + after },
      selection: EditorSelection.range(r.from + before.length, r.from + before.length + inner.length),
    });
  }
  view.focus();
}

function selectedLines(state) {
  const r = state.selection.main;
  const out = [];
  for (let n = state.doc.lineAt(r.from).number, last = state.doc.lineAt(r.to).number; n <= last; n++) out.push(state.doc.line(n));
  return out;
}

/** Toggle a line prefix ("> ", "- ", "- [ ] ") on every selected line, replacing any other list or quote prefix. */
export function togglePrefix(view, prefix) {
  const lines = selectedLines(view.state).filter((l) => l.text.trim() || selectedLines(view.state).length === 1);
  const allHave = lines.every((l) => l.text.replace(/^\s*/, "").startsWith(prefix));
  const changes = lines.map((l) => {
    const m = LINE_MARK.exec(l.text);
    const indent = m[1] ?? "";
    const body = l.text.slice(m[0].length);
    return { from: l.from, to: l.to, insert: allHave ? indent + body : indent + prefix + body };
  });
  view.dispatch({ changes });
  view.focus();
}

/** Cycle the current line: text → ## → ### → text. */
export function cycleHeading(view) {
  const l = view.state.doc.lineAt(view.state.selection.main.head);
  const m = /^(#{1,3})\s/.exec(l.text);
  const next = !m ? "## " : m[1].length === 2 ? "### " : "";
  view.dispatch({ changes: { from: l.from, to: l.from + (m ? m[0].length : 0), insert: next } });
  view.focus();
}

/** Insert text on its own line(s) after the cursor's line, leaving a blank line before it when needed. */
export function insertBlock(view, text, caret = null, trailing = false) {
  const { state } = view;
  const l = state.doc.lineAt(state.selection.main.head);
  const lead = l.text.trim() ? "\n\n" : "";
  const from = l.text.trim() ? l.to : l.from;
  const tail = trailing ? "\n\n" : "";
  view.dispatch({
    changes: { from, to: l.to, insert: lead + text + tail },
    selection: EditorSelection.cursor(from + lead.length + (trailing ? text.length + tail.length : (caret ?? text.length))),
  });
  view.focus();
}

/** Replace the current line's text (used by the "/" menu, which owns its line). */
export function replaceLine(view, text, caret = null) {
  const l = view.state.doc.lineAt(view.state.selection.main.head);
  view.dispatch({
    changes: { from: l.from, to: l.to, insert: text },
    selection: EditorSelection.cursor(l.from + (caret ?? text.length)),
  });
  view.focus();
}

export const FORMATS = {
  heading: (v) => cycleHeading(v),
  bold: (v) => wrapSelection(v, "**", "**", "bold"),
  italic: (v) => wrapSelection(v, "*", "*", "italic"),
  code: (v) => wrapSelection(v, "`", "`", "code"),
  quote: (v) => togglePrefix(v, "> "),
  list: (v) => togglePrefix(v, "- "),
  task: (v) => togglePrefix(v, "- [ ] "),
  link: (v) => wrapSelection(v, "[", "](https://)", "text"),
  table: (v) => insertBlock(v, "| Column | Column |\n| --- | --- |\n|  |  |"),
  rule: (v) => insertBlock(v, "---"),
};
