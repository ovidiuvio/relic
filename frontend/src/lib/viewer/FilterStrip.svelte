<script>
  // The filter strip over the code and tree views: a search field with the match count and a
  // clear button, and optionally a case-sensitive toggle and regex help. The help is a popover
  // under the field (no dialog): clicking a pattern puts it in the field. `dark` matches the
  // editor's dark background.
  import Icon from "../ui/Icon.svelte";

  let {
    value = $bindable(""),
    placeholder = "Filter",
    label = placeholder,
    dark = false,
    count = null, // { matched, total } while filtering
    error = false, // the pattern doesn't parse
    caseSensitive = $bindable(null), // null hides the toggle
    patterns = null, // [[pattern, meaning]] for the regex help; null hides it
    oninput, // () after the value changed by typing or a pattern
    children, // more controls after the field (e.g. rows per page, Export)
  } = $props();

  let input = $state();
  let helpOpen = $state(false);
  let helpEl = $state();

  function clear() {
    value = "";
    oninput?.();
    input?.focus();
  }

  function use(pattern) {
    value = pattern;
    helpOpen = false;
    oninput?.();
    input?.focus();
  }

  function onKeydown(event) {
    if (event.key === "Escape") {
      if (helpOpen) helpOpen = false;
      else if (value) clear();
      else input?.blur();
      event.stopPropagation();
    }
  }

  function onWindowClick(event) {
    if (helpOpen && !helpEl?.contains(event.target)) helpOpen = false;
  }
</script>

<svelte:window onclick={onWindowClick} />

<div class="fs" class:is-dark={dark}>
  <label class="fs-field" class:is-error={error}>
    <Icon name="search" />
    <input bind:this={input} bind:value {placeholder} aria-label={label} spellcheck="false" autocomplete="off" oninput={() => oninput?.()} onkeydown={onKeydown} />
    {#if count}<span class="fs-count" aria-live="polite">{count.matched.toLocaleString("en-US")} / {count.total.toLocaleString("en-US")}</span>{/if}
    {#if error}<span class="fs-error">invalid pattern</span>{/if}
    {#if value}
      <button type="button" class="fs-btn" onclick={clear} title="Clear (Esc)" aria-label="Clear filter"><Icon name="x" /></button>
    {/if}
  </label>
  {@render children?.()}
  {#if caseSensitive !== null}
    <button type="button" class="fs-btn fs-toggle" aria-pressed={caseSensitive} onclick={() => (caseSensitive = !caseSensitive)} title="Case sensitive">Aa</button>
  {/if}
  {#if patterns}
    <div class="fs-help-anchor" bind:this={helpEl}>
      <button type="button" class="fs-btn fs-toggle" aria-expanded={helpOpen} aria-controls="fs-help" onclick={() => (helpOpen = !helpOpen)} title="Regex help">?</button>
      {#if helpOpen}
        <div class="fs-help" id="fs-help" role="dialog" aria-label="Regex help">
          <p class="fs-help-head">Regular expressions <span>click one to use it</span></p>
          {#each patterns as [pattern, meaning] (pattern)}
            <button type="button" class="fs-pattern" onclick={() => use(pattern)}><code>{pattern}</code><span>{meaning}</span></button>
          {/each}
          {#if caseSensitive !== null}<p class="fs-help-foot"><b>Aa</b> makes matching case sensitive.</p>{/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .fs {
    --fs-bg: var(--surface);
    --fs-field: var(--surface);
    --fs-line: var(--line);
    --fs-line-2: var(--line-2);
    --fs-ink: var(--ink);
    --fs-muted: var(--ink-3);
    --fs-hover: var(--hover);
    --fs-accent: var(--accent);
    flex: none;
    display: flex;
    align-items: center;
    gap: var(--space-1);
    height: var(--strip-height, 40px);
    padding: 0 var(--space-3);
    border-bottom: 1px solid var(--fs-line);
    background: var(--fs-bg);
    font: 12.5px var(--font-sans);
  }
  /* The editor's dark theme (#1e1e1e), with the design system's night accents. */
  .fs.is-dark {
    --fs-bg: #1e1e1e;
    --fs-field: #262626;
    --fs-line: #333;
    --fs-line-2: #444;
    --fs-ink: #d4d4d4;
    --fs-muted: #8a8a8a;
    --fs-hover: #2f2f2f;
    --fs-accent: var(--night-accent);
  }
  .fs-field {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 6px;
    height: var(--control-md);
    padding: 0 4px 0 8px;
    border: 1px solid var(--fs-line-2);
    border-radius: var(--radius-sm);
    background: var(--fs-field);
    color: var(--fs-muted);
  }
  .fs-field:focus-within {
    border-color: var(--fs-accent);
  }
  .fs-field.is-error {
    border-color: var(--danger);
  }
  .fs-field > :global(.r-icon) {
    flex: none;
    width: 13px;
    height: 13px;
  }
  .fs-field input {
    flex: 1;
    min-width: 0;
    padding: 0;
    border: 0;
    background: none;
    color: var(--fs-ink);
    font: 12.5px var(--font-mono);
    outline: 0;
    box-shadow: none;
  }
  .fs-field input::placeholder {
    color: var(--fs-muted);
    font-family: var(--font-sans);
  }
  .fs-count {
    color: var(--fs-muted);
    font: 11.5px var(--font-mono);
    white-space: nowrap;
  }
  .fs-error {
    color: var(--danger);
    font-size: 11.5px;
    white-space: nowrap;
  }
  .fs-btn {
    display: grid;
    place-items: center;
    flex: none;
    min-width: 24px;
    height: 24px;
    padding: 0 4px;
    border: 0;
    border-radius: var(--radius-xs);
    background: none;
    color: var(--fs-muted);
    cursor: pointer;
  }
  .fs-btn :global(.r-icon) {
    width: 13px;
    height: 13px;
  }
  .fs-btn:hover {
    background: var(--fs-hover);
    color: var(--fs-ink);
  }
  .fs-toggle {
    font: 600 11.5px var(--font-mono);
  }
  .fs-toggle[aria-pressed="true"],
  .fs-toggle[aria-expanded="true"] {
    background: color-mix(in srgb, var(--fs-accent) 18%, transparent);
    color: var(--fs-accent);
  }
  .fs-help-anchor {
    position: relative;
  }
  .fs-help {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    z-index: 30;
    display: grid;
    width: 320px;
    padding: var(--space-1\.5) 0;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    background: var(--surface);
    color: var(--ink);
    box-shadow: var(--shadow-popover);
  }
  .fs-help-head {
    display: flex;
    justify-content: space-between;
    margin: 0;
    padding: var(--space-1) var(--space-3) var(--space-1\.5);
    font-weight: 600;
  }
  .fs-help-head span {
    color: var(--ink-3);
    font-weight: 400;
    font-size: 11.5px;
  }
  .fs-pattern {
    display: grid;
    grid-template-columns: 116px 1fr;
    align-items: center;
    gap: var(--space-2);
    padding: 5px var(--space-3);
    border: 0;
    background: none;
    color: var(--ink-2);
    font: 12px var(--font-sans);
    text-align: left;
    cursor: pointer;
  }
  .fs-pattern:hover,
  .fs-pattern:focus-visible {
    background: var(--hover);
  }
  .fs-pattern code {
    color: var(--accent);
    font: 12px var(--font-mono);
  }
  .fs-help-foot {
    margin: var(--space-1) 0 0;
    padding: var(--space-1\.5) var(--space-3) 0;
    border-top: 1px solid var(--line);
    color: var(--ink-3);
    font-size: 11.5px;
  }
  .fs-help-foot b {
    font-family: var(--font-mono);
  }
</style>
