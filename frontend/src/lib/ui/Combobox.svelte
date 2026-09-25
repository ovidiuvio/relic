<script>
  // A searchable picker: type any part of an option's label (or value) to filter, ↑↓ to move,
  // Enter to choose, Esc to close. ARIA combobox with a listbox popup. Styled as an r-input.
  //   <Combobox options={[{ value, label }]} bind:value placeholder="Search languages" />
  import Icon from "./Icon.svelte";

  let { options = [], value = $bindable(), placeholder = "", id = undefined, maxShown = 200 } = $props();

  const uid = `cb-${Math.random().toString(36).slice(2, 8)}`;
  let query = $state("");
  let open = $state(false);
  let active = $state(0);
  let root = $state();
  let listEl = $state();

  const selected = $derived(options.find((o) => o.value === value));

  const matches = $derived.by(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options.slice(0, maxShown);
    const hits = options.filter((o) => o.label.toLowerCase().includes(q) || String(o.value).toLowerCase().includes(q));
    // Labels that start with the query come first; otherwise keep the given order.
    const starts = hits.filter((o) => o.label.toLowerCase().startsWith(q));
    const rest = hits.filter((o) => !o.label.toLowerCase().startsWith(q));
    return [...starts, ...rest].slice(0, maxShown);
  });

  function show() {
    if (open) return;
    open = true;
    query = "";
    active = Math.max(0, matches.findIndex((o) => o.value === value));
    requestAnimationFrame(scrollActive);
  }

  function choose(option) {
    value = option.value;
    open = false;
    query = "";
  }

  function scrollActive() {
    listEl?.querySelector(`[data-i="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }

  function onKeydown(event) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) return show();
      const step = event.key === "ArrowDown" ? 1 : -1;
      active = Math.min(matches.length - 1, Math.max(0, active + step));
      requestAnimationFrame(scrollActive);
    } else if (event.key === "Enter" && open) {
      event.preventDefault();
      if (matches[active]) choose(matches[active]);
    } else if (event.key === "Escape" && open) {
      event.preventDefault();
      event.stopPropagation();
      open = false;
      query = "";
    } else if (event.key === "Tab") {
      open = false;
      query = "";
    }
  }

  function onWindowPointer(event) {
    if (open && !root?.contains(event.target)) {
      open = false;
      query = "";
    }
  }
</script>

<svelte:window onpointerdown={onWindowPointer} />

<div class="combo" bind:this={root}>
  <span class="r-input combo-field">
    <input
      {id}
      role="combobox"
      aria-expanded={open}
      aria-controls="{uid}-list"
      aria-autocomplete="list"
      aria-activedescendant={open && matches[active] ? `${uid}-${active}` : undefined}
      autocomplete="off"
      spellcheck="false"
      value={open ? query : (selected?.label ?? "")}
      placeholder={open ? (selected?.label ?? placeholder) : placeholder}
      oninput={(e) => {
        query = e.currentTarget.value;
        active = 0;
        open = true;
      }}
      onfocus={show}
      onclick={show}
      onkeydown={onKeydown}
    />
    <Icon name="chev" />
  </span>

  {#if open}
    <ul class="combo-list" id="{uid}-list" role="listbox" bind:this={listEl}>
      {#each matches as option, i (option.value)}
        <li
          id="{uid}-{i}"
          data-i={i}
          role="option"
          aria-selected={option.value === value}
          class:is-active={i === active}
          onpointerdown={(e) => {
            e.preventDefault();
            choose(option);
          }}
          onpointermove={() => (active = i)}
        >
          {option.label}
          {#if option.value === value}<Icon name="check" size={13} />{/if}
        </li>
      {:else}
        <li class="combo-empty" role="presentation">No match for “{query}”</li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .combo {
    position: relative;
  }
  .combo-field {
    padding-right: 8px;
  }
  .combo-field input {
    cursor: pointer;
  }
  .combo-field input:focus {
    cursor: text;
  }
  .combo-field > :global(.r-icon) {
    flex: none;
    color: var(--ink-3);
  }
  .combo-list {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    z-index: 30;
    max-height: 260px;
    margin: 0;
    padding: var(--space-1) 0;
    overflow-y: auto;
    border: 1px solid var(--line-2);
    border-radius: var(--radius-md);
    background: var(--surface);
    box-shadow: var(--shadow-popover);
    list-style: none;
  }
  .combo-list li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 5px var(--space-3);
    font-size: 13px;
    cursor: pointer;
  }
  .combo-list li.is-active {
    background: var(--hover);
  }
  .combo-list li[aria-selected="true"] {
    color: var(--accent);
    font-weight: 500;
  }
  .combo-list .combo-empty {
    color: var(--ink-3);
    cursor: default;
  }
</style>
