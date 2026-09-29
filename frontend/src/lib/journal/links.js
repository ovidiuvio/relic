// [[Wiki links]] and ![[embeds]] in entry text: finding their targets, and turning them into
// ordinary Markdown links for the renderer, which are then dressed up from what the server
// resolved (an entry of this journal, a relic, or nothing). Fenced code and `inline code` are left alone.

const LINK = /(!?)\[\[([^\]\n]+)\]\]/g;
const CODE = /(`[^`\n]+`)/;

// Apply a change to the parts of a line that are not `inline code`.
const outsideCode = (line, change) => line.split(CODE).map((part, i) => (i % 2 ? part : change(part))).join("");

/** The distinct targets in a body, as written (the part before "|alias"). */
export function linkTargets(body) {
  const out = new Map();
  let fenced = false;
  for (const line of body.split("\n")) {
    if (/^```/.test(line)) {
      fenced = !fenced;
      continue;
    }
    if (fenced) continue;
    outsideCode(line, (text) => {
      for (const m of text.matchAll(LINK)) {
        const target = m[2].split("|", 1)[0].trim();
        if (target && !out.has(target.toLowerCase())) out.set(target.toLowerCase(), target);
      }
      return text;
    });
  }
  return [...out.values()];
}

/**
 * Links become #jl/… anchors and embeds #je/…, so the Markdown renderer (which sanitises hrefs)
 * passes them through; the editor rewrites them once it knows what they point at.
 */
export function prepareLinks(body) {
  let fenced = false;
  return body
    .split("\n")
    .map((line) => {
      if (/^```/.test(line)) {
        fenced = !fenced;
        return line;
      }
      if (fenced) return line;
      return outsideCode(line, (part) =>
        part.replace(LINK, (_m, bang, inner) => {
          const [target, alias] = inner.split("|");
          const text = (alias ?? target).trim().replace(/[[\]]/g, "");
          return `[${text}](#${bang ? "je" : "jl"}/${encodeURIComponent(target.trim())})`;
        })
      );
    })
    .join("\n");
}
