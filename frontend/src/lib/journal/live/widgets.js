// Widgets the live editor draws in place of Markdown syntax: list bullets and numbers,
// task checkboxes, horizontal rules and ![[embed]] cards.
import { WidgetType } from "@codemirror/view";
import { buildEmbedCard } from "../embeds";

export class BulletWidget extends WidgetType {
  eq() {
    return true;
  }
  toDOM() {
    const span = document.createElement("span");
    span.className = "cm-bullet";
    span.textContent = "•";
    return span;
  }
  ignoreEvent() {
    return false;
  }
}

export class NumberWidget extends WidgetType {
  constructor(text) {
    super();
    this.text = text;
  }
  eq(other) {
    return other.text === this.text;
  }
  toDOM() {
    const span = document.createElement("span");
    span.className = "cm-bullet cm-number";
    span.textContent = this.text;
    return span;
  }
  ignoreEvent() {
    return false;
  }
}

export class CheckboxWidget extends WidgetType {
  constructor(checked, readonly) {
    super();
    this.checked = checked;
    this.readonly = readonly;
  }
  eq(other) {
    return other.checked === this.checked && other.readonly === this.readonly;
  }
  toDOM(view) {
    const wrap = document.createElement("span");
    wrap.className = "cm-bullet cm-check";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = this.checked;
    box.setAttribute("aria-label", this.checked ? "Done" : "Not done");
    box.disabled = this.readonly;
    // Flip the [ ] / [x] this checkbox stands for.
    box.addEventListener("mousedown", (event) => {
      event.preventDefault();
      if (this.readonly) return;
      const pos = view.posAtDOM(wrap);
      const line = view.state.doc.lineAt(pos);
      const match = /\[( |x|X)\]/.exec(line.text);
      if (!match) return;
      const at = line.from + match.index + 1;
      view.dispatch({ changes: { from: at, to: at + 1, insert: match[1] === " " ? "x" : " " } });
    });
    wrap.append(box);
    return wrap;
  }
  ignoreEvent() {
    return true;
  }
}

/** ![alt](https://…) drawn as the picture (only web and same-site addresses). */
export class ImageWidget extends WidgetType {
  constructor(src, alt) {
    super();
    this.src = src;
    this.alt = alt;
  }
  eq(other) {
    return other.src === this.src && other.alt === this.alt;
  }
  toDOM() {
    const img = document.createElement("img");
    img.className = "cm-image";
    img.src = this.src;
    img.alt = this.alt;
    img.loading = "lazy";
    return img;
  }
  ignoreEvent() {
    return false;
  }
}

export class RuleWidget extends WidgetType {
  eq() {
    return true;
  }
  toDOM() {
    const hr = document.createElement("div");
    hr.className = "cm-rule";
    return hr;
  }
}

export class EmbedWidget extends WidgetType {
  constructor(target, info) {
    super();
    this.target = target;
    this.info = info;
    this.key = JSON.stringify(info ?? null);
  }
  eq(other) {
    return other.target === this.target && other.key === this.key;
  }
  toDOM() {
    const wrap = document.createElement("div");
    wrap.className = "cm-embed";
    wrap.append(buildEmbedCard(this.target, this.info));
    return wrap;
  }
  ignoreEvent(event) {
    return event.type !== "mousedown" ? true : false;
  }
}

const escapeHtml = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// A little inline formatting for table cells: `code`, **bold**, *italic*.
const inline = (t) =>
  escapeHtml(t)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");

const cells = (line) => line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());

/** A pipe table drawn as a table. Clicking it puts the cursor in the source, to edit. */
export class TableWidget extends WidgetType {
  constructor(text) {
    super();
    this.text = text;
  }
  eq(other) {
    return other.text === this.text;
  }
  toDOM(view) {
    const lines = this.text.split("\n");
    const head = cells(lines[0]);
    const align = cells(lines[1] ?? "").map((c) => (/^:-+:$/.test(c) ? "center" : /-+:$/.test(c) ? "right" : "left"));
    const wrap = document.createElement("div");
    wrap.className = "cm-table";
    const table = document.createElement("table");
    const row = (values, tag) => {
      const tr = document.createElement("tr");
      values.forEach((v, i) => {
        const td = document.createElement(tag);
        td.innerHTML = inline(v);
        td.style.textAlign = align[i] ?? "left";
        tr.append(td);
      });
      return tr;
    };
    const thead = document.createElement("thead");
    thead.append(row(head, "th"));
    const tbody = document.createElement("tbody");
    for (const line of lines.slice(2)) if (line.trim()) tbody.append(row(cells(line), "td"));
    table.append(thead, tbody);
    wrap.append(table);
    wrap.addEventListener("mousedown", (event) => {
      event.preventDefault();
      const pos = view.posAtDOM(wrap);
      view.dispatch({ selection: { anchor: pos } });
      view.focus();
    });
    return wrap;
  }
  ignoreEvent() {
    return true;
  }
}
