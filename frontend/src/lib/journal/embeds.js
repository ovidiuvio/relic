// The card an ![[embed]] shows: the relic's name and size with an Open link and, below, the first
// lines of a text relic or the image itself. Shared by the editor and the reading view. Plain DOM,
// so it works inside CodeMirror widgets and inside rendered HTML alike.
import { getRelicRawHead } from "../../services/api";
import { getFileTypeDefinition, isBinaryType } from "../../services/typeUtils";
import { compactBytes } from "../relics/format";

const peeks = new Map(); // relic id → its first lines, for the session
const PEEK_LINES = 14;

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
};

/** `info` is what the server resolved: { kind: "relic" | "entry" | "missing", ... } (or undefined while unknown). */
export function buildEmbedCard(target, info) {
  const card = el("div", "emb-card");
  const head = el("div", "emb-head");
  if (info?.kind === "relic") {
    head.append(el("b", "", info.name || info.id), el("em", "", compactBytes(info.size_bytes)));
    const open = el("a", "", "Open relic");
    open.href = `/${info.id}`;
    head.append(open);
    card.append(head);
    const def = getFileTypeDefinition(info.content_type);
    if (def.category === "image") {
      const img = el("img");
      img.src = `/${info.id}/raw`;
      img.alt = info.name || "";
      img.loading = "lazy";
      card.append(img);
    } else if (!isBinaryType(info.content_type)) {
      const pre = el("pre", "", peeks.get(info.id) ?? "Loading…");
      card.append(pre);
      if (!peeks.has(info.id)) {
        getRelicRawHead(info.id, 2048)
          .then(({ text, truncated }) => {
            const lines = text.replace(/\r\n?/g, "\n").split("\n");
            peeks.set(info.id, lines.slice(0, PEEK_LINES).join("\n") + (truncated || lines.length > PEEK_LINES ? "\n…" : ""));
          })
          .catch(() => peeks.set(info.id, "Couldn’t load a preview"))
          .finally(() => {
            pre.textContent = peeks.get(info.id);
          });
      }
    }
  } else if (info?.kind === "entry") {
    head.append(el("b", "", info.title));
    const open = el("a", "", "Open entry");
    open.href = "#";
    open.dataset.entry = info.id;
    head.append(open);
    card.append(head);
  } else {
    card.classList.add("is-missing");
    head.textContent = info ? `Nothing named “${target}”` : `Looking for “${target}”…`;
    card.append(head);
  }
  return card;
}
