// Markdown helpers for journal entries: the editor's syntax colouring, the outline, and the
// tag and task rules (the same ones backend/journal.py applies when an entry is saved).

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// Code, bold, italic, [[wiki]] and ![[embed]], [links](url), #tags.
const INLINE = /(`[^`\n]+`)|(\*\*[^*\n]+\*\*)|(\*[^*\n]+\*)|(!?\[\[[^\]\n]+\]\])|(\[[^\]\n]+\]\([^)\n]+\))|((?:^|\s)#[a-z][\w-]*)/gi;

function highlightInline(text) {
  let out = "";
  let last = 0;
  INLINE.lastIndex = 0;
  for (let m = INLINE.exec(text); m; m = INLINE.exec(text)) {
    out += esc(text.slice(last, m.index));
    const raw = esc(m[0]);
    if (m[1]) out += `<span class="ic">${raw}</span>`;
    else if (m[2]) out += `<span class="bd">${raw}</span>`;
    else if (m[3]) out += `<span class="it">${raw}</span>`;
    else if (m[4]) out += `<span class="wk">${raw}</span>`;
    else if (m[5]) out += `<span class="lk">${raw}</span>`;
    else {
      const space = m[6].match(/^\s*/)[0];
      out += `${space}<span class="tg">${esc(m[6].slice(space.length))}</span>`;
    }
    last = m.index + m[0].length;
  }
  return out + esc(text.slice(last));
}

/**
 * The editor's colouring layer: one block per line, colour and weight only, so the text keeps
 * the exact metrics of the textarea above it (the font is monospace).
 */
export function highlight(source) {
  let fenced = false;
  return source
    .split("\n")
    .map((line) => {
      if (/^```/.test(line)) {
        fenced = !fenced;
        return `<span class="ln"><span class="hf">${esc(line)}</span></span>`;
      }
      if (fenced) return `<span class="ln"><span class="hc">${esc(line) || "​"}</span></span>`;
      let cls = /^#{1,3}\s/.test(line) ? "h" : /^>/.test(line) ? "q" : "";
      const html = highlightInline(line).replace(/^(\s*)(- \[[ x]\]|[-*]|\d+\.|&gt;|#{1,3})(\s)/, '$1<span class="mk">$2</span>$3');
      if (/^\s*- \[x\]/.test(line)) cls += " dn";
      return `<span class="ln ${cls}">${html || "​"}</span>`;
    })
    .join("");
}

/** Headings (levels 1 to 3) with the line they start on. Fenced code is skipped. */
export function outline(body) {
  const out = [];
  let fenced = false;
  body.split("\n").forEach((line, i) => {
    if (/^```/.test(line)) {
      fenced = !fenced;
      return;
    }
    const m = !fenced && line.match(/^(#{1,3})\s+(.*)$/);
    if (m) out.push({ level: m[1].length, text: m[2], line: i });
  });
  return out;
}

const TASK = /^\s*(?:[-*]|\d+\.)\s+\[( |x)\]\s/;

/** Flip the nth task checkbox of a body (in reading order); returns the new body. */
export function toggleTask(body, index) {
  let n = -1;
  return body
    .split("\n")
    .map((line) => {
      const m = line.match(TASK);
      if (!m || ++n !== index) return line;
      return line.replace(/\[( |x)\]/, m[1] === "x" ? "[ ]" : "[x]");
    })
    .join("\n");
}

/** Words as the server counts them: tokens holding a letter or digit, task markers excluded. */
export function countWords(body) {
  return (body.replace(/^\s*(?:[-*]|\d+\.)\s+\[[ x]\]\s/gm, "").match(/\S*\w\S*/g) || []).length;
}
