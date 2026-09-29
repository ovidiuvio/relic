// How the live editor looks: the same typography as the reading view, so writing and reading are
// the same page. All colours come from the design tokens.
import { EditorView } from "@codemirror/view";

export const liveTheme = EditorView.theme({
  "&": {
    color: "var(--ink)",
    backgroundColor: "transparent",
    fontSize: "16px",
    minHeight: "340px",
  },
  "&.cm-focused": { outline: "none" },
  ".cm-scroller": { fontFamily: "var(--font-sans)", lineHeight: "1.75", overflow: "visible" },
  ".cm-content": { padding: "10px 0 220px", caretColor: "var(--accent)" },
  ".cm-line": { padding: "0" },
  ".cm-cursor, .cm-dropCursor": { borderLeftColor: "var(--accent)", borderLeftWidth: "2px" },
  "&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection": { backgroundColor: "color-mix(in srgb, var(--accent) 20%, transparent)" },
  ".cm-placeholder": { color: "var(--ink-4)" },

  // headings
  ".cm-h": { fontWeight: "700", letterSpacing: "-0.01em", lineHeight: "1.3" },
  ".cm-h1": { fontSize: "1.75em", paddingTop: "0.7em" },
  ".cm-h2": { fontSize: "1.4em", paddingTop: "0.65em" },
  ".cm-h3": { fontSize: "1.15em", paddingTop: "0.5em" },
  ".cm-h4, .cm-h5, .cm-h6": { fontSize: "1em", paddingTop: "0.4em" },

  // inline
  ".cm-strong": { fontWeight: "700" },
  ".cm-em": { fontStyle: "italic" },
  ".cm-strike": { textDecoration: "line-through", color: "var(--ink-3)" },
  ".cm-code-inline": { fontFamily: "var(--font-mono)", fontSize: "0.9em", backgroundColor: "var(--chip)", color: "var(--type-code)", borderRadius: "4px", padding: "1px 4px" },
  ".cm-link": { color: "var(--info-ink)", textDecoration: "underline", textUnderlineOffset: "2px" },
  ".cm-kbd": { fontFamily: "var(--font-mono)", fontSize: "0.85em", padding: "1px 6px", border: "1px solid var(--line-2)", borderBottomWidth: "2px", borderRadius: "5px", backgroundColor: "var(--surface)", color: "var(--ink-2)" },
  ".cm-tag": { color: "var(--accent)", fontWeight: "500" },
  ".cm-syntax": { color: "var(--ink-4)" },
  ".cm-wiki": { borderBottom: "1px solid color-mix(in srgb, var(--type-doc) 35%, transparent)", color: "var(--type-doc)", cursor: "pointer" },
  ".cm-wiki-relic": { color: "var(--accent)", borderBottomColor: "color-mix(in srgb, var(--accent) 35%, transparent)" },
  ".cm-wiki-missing, .cm-wiki-loading": { color: "var(--ink-3)", borderBottomStyle: "dashed" },

  // blocks
  ".cm-quote": { borderLeft: "3px solid var(--line-2)", paddingLeft: "16px", color: "var(--ink-2)" },
  ".cm-blank": { lineHeight: "0.85" },
  ".cm-code-line": { fontFamily: "var(--font-mono)", fontSize: "0.875em", lineHeight: "1.6", backgroundColor: "var(--subtle)", padding: "0 14px", borderLeft: "1px solid var(--line)", borderRight: "1px solid var(--line)", color: "var(--code-ink)" },
  ".cm-code-first": { borderTop: "1px solid var(--line)", borderTopLeftRadius: "8px", borderTopRightRadius: "8px", paddingTop: "6px" },
  ".cm-code-last": { borderBottom: "1px solid var(--line)", borderBottomLeftRadius: "8px", borderBottomRightRadius: "8px", paddingBottom: "6px" },
  ".cm-code-fence": { color: "var(--ink-3)", fontSize: "0.75em" },
  ".cm-table-line": { fontFamily: "var(--font-mono)", fontSize: "0.86em", lineHeight: "1.7", backgroundColor: "var(--subtle)", padding: "0 12px", borderLeft: "1px solid var(--line)", borderRight: "1px solid var(--line)" },
  ".cm-table-head": { fontWeight: "700", borderTop: "1px solid var(--line)", borderTopLeftRadius: "8px", borderTopRightRadius: "8px" },
  ".cm-table": { margin: "6px 0 10px", overflowX: "auto", cursor: "text" },
  ".cm-table table": { width: "100%", borderCollapse: "collapse", fontSize: "14px", lineHeight: "1.5" },
  ".cm-table th, .cm-table td": { padding: "7px 12px", border: "1px solid var(--line)", textAlign: "left" },
  ".cm-table th": { backgroundColor: "var(--subtle)", fontWeight: "500" },
  ".cm-table code": { fontFamily: "var(--font-mono)", fontSize: "0.9em", backgroundColor: "var(--chip)", color: "var(--type-code)", borderRadius: "4px", padding: "1px 4px" },
  ".cm-image": { display: "block", maxWidth: "100%", maxHeight: "480px", margin: "6px 0", borderRadius: "6px" },
  ".cm-rule": { height: "1px", margin: "0.9em 0", backgroundColor: "var(--line-2)" },
  ".cm-rule-source": { color: "var(--ink-4)" },

  // lists: the marker hangs in the margin, wrapped lines line up with the text
  ".cm-li": { paddingLeft: "calc(var(--depth, 0) * 1.6em + 1.6em)", textIndent: "-1.6em" },
  ".cm-bullet": { display: "inline-block", width: "1.6em", textIndent: "0", color: "var(--ink-3)", textAlign: "left", fontVariantNumeric: "tabular-nums" },
  ".cm-check input": { width: "15px", height: "15px", margin: "0", verticalAlign: "-2px", accentColor: "var(--accent)", color: "var(--accent)", cursor: "pointer" },
  ".cm-task-done": { color: "var(--ink-3)", textDecoration: "line-through" },

  // ![[embed]] cards
  ".cm-embed": { margin: "10px 0" },
  ".emb-card": { overflow: "hidden", border: "1px solid var(--line)", borderRadius: "8px", backgroundColor: "var(--surface)", fontSize: "14px", lineHeight: "1.5", textIndent: "0" },
  ".emb-card.is-missing": { borderStyle: "dashed", color: "var(--ink-3)" },
  ".emb-head": { display: "flex", alignItems: "center", gap: "10px", padding: "7px 12px", backgroundColor: "var(--subtle)" },
  ".emb-head b": { fontWeight: "500" },
  ".emb-head em": { color: "var(--ink-3)", font: "12px var(--font-mono)", fontStyle: "normal" },
  ".emb-head a": { marginLeft: "auto", color: "var(--accent)", fontSize: "12px", fontWeight: "500", textDecoration: "none" },
  ".emb-card pre": { margin: "0", padding: "10px 14px", borderTop: "1px solid var(--line)", font: "13px/1.55 var(--font-mono)", whiteSpace: "pre-wrap", overflowWrap: "anywhere", color: "var(--ink)" },
  ".emb-card img": { display: "block", maxWidth: "100%", maxHeight: "420px", margin: "0 auto" },
});
