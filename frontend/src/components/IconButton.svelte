<script>
  // Icon-only button with a required accessible name. The label doubles as a
  // tooltip (shown on hover and keyboard focus) alongside an optional shortcut.

  export let label;               // accessible name + tooltip text (required)
  export let icon = "";           // Font Awesome classes, e.g. "fas fa-copy"
  export let shortcut = "";       // e.g. "y"; shown in the tooltip, exposed as aria-keyshortcuts
  export let pressed = undefined; // set for toggle buttons (true/false)
  export let disabled = false;
  export let loading = false;
  export let tone = "default";    // "default" | "danger"
  export let align = "center";    // tooltip alignment: "center" | "end"
</script>

<button
  type="button"
  class="icon-btn group relative inline-flex items-center justify-center w-8 h-8 rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed
    {pressed ? 'text-brand-700 bg-brand-50 hover:bg-brand-100' : tone === 'danger' ? 'text-gray-500 hover:text-red-700 hover:bg-red-50' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'}"
  aria-label={label}
  aria-pressed={pressed}
  aria-keyshortcuts={shortcut || undefined}
  disabled={disabled || loading}
  on:click
  {...$$restProps}
>
  <i class="{loading ? 'fas fa-spinner fa-spin' : icon} text-[13px] w-[14px] text-center" aria-hidden="true"></i>
  <span
    class="pointer-events-none absolute top-full mt-1.5 z-50 whitespace-nowrap rounded bg-gray-900 px-2 py-1 text-2xs font-medium text-white opacity-0 shadow transition-opacity delay-300
      group-hover:opacity-100 group-focus-visible:opacity-100 group-focus-visible:delay-0
      {align === 'end' ? 'right-0' : 'left-1/2 -translate-x-1/2'}"
    aria-hidden="true"
  >
    {label}{#if shortcut}<kbd class="ml-2 rounded border border-white/30 px-1 font-mono text-[10px] text-white/80">{shortcut}</kbd>{/if}
  </span>
</button>
