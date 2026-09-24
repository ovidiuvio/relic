// Svelte action that makes an element behave as an accessible modal dialog:
// dialog semantics, initial focus, Tab trapping, Escape to close, and focus
// restore on teardown. Apply it to the dialog panel, not the backdrop:
//
//   <div class="panel" use:modal={{ onClose: close }}>
//
// Options:
//   onClose  - called on Escape; omit to make Escape a no-op (e.g. forced dialogs)
//   label    - accessible name when the dialog has no heading to point at

const FOCUSABLE = [
  "a[href]",
  "area[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type=hidden])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "iframe",
  "[contenteditable=true]",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

// Only the top-most open dialog reacts to keys.
const stack = [];
let idCounter = 0;

function focusables(node) {
  return [...node.querySelectorAll(FOCUSABLE)].filter(
    (el) => el.offsetParent !== null || el === document.activeElement,
  );
}

export function modal(node, options = {}) {
  let opts = options;
  const previouslyFocused = document.activeElement;

  node.setAttribute("role", node.getAttribute("role") === "alertdialog" ? "alertdialog" : "dialog");
  node.setAttribute("aria-modal", "true");
  if (!node.hasAttribute("tabindex")) node.setAttribute("tabindex", "-1");

  function applyLabel() {
    if (opts.label) {
      node.setAttribute("aria-label", opts.label);
      return;
    }
    if (node.hasAttribute("aria-labelledby") || node.hasAttribute("aria-label")) return;
    const heading = node.querySelector("h1, h2, h3, h4");
    if (heading) {
      if (!heading.id) heading.id = `modal-title-${++idCounter}`;
      node.setAttribute("aria-labelledby", heading.id);
    }
  }
  applyLabel();

  stack.push(node);

  // Defer so content rendered in the same tick (and `autofocus` fields) exists.
  queueMicrotask(() => {
    if (!node.isConnected || node.contains(document.activeElement)) return;
    const preferred = node.querySelector("[autofocus], [data-autofocus]");
    (preferred || focusables(node)[0] || node).focus();
  });

  function onKeydown(event) {
    if (stack[stack.length - 1] !== node) return;
    // Code editors own Tab (indent) and Escape (dismiss widgets).
    if (event.target.closest?.(".monaco-editor")) return;

    if (event.key === "Escape" && opts.onClose) {
      event.stopPropagation();
      event.preventDefault();
      opts.onClose();
      return;
    }

    if (event.key !== "Tab") return;
    const items = focusables(node);
    if (items.length === 0) {
      event.preventDefault();
      node.focus();
      return;
    }
    const first = items[0];
    const last = items[items.length - 1];
    const active = document.activeElement;
    if (event.shiftKey && (active === first || !node.contains(active))) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && (active === last || !node.contains(active))) {
      event.preventDefault();
      first.focus();
    }
  }

  // Capture phase so Escape wins over page-level shortcut handlers.
  document.addEventListener("keydown", onKeydown, true);

  return {
    update(newOptions = {}) {
      opts = newOptions;
      applyLabel();
    },
    destroy() {
      document.removeEventListener("keydown", onKeydown, true);
      const index = stack.lastIndexOf(node);
      if (index !== -1) stack.splice(index, 1);
      if (previouslyFocused && typeof previouslyFocused.focus === "function" && previouslyFocused.isConnected) {
        previouslyFocused.focus();
      }
    },
  };
}
