<script>
  // Scoped search in the navbar. `/` focuses it from anywhere; Enter shows the results
  // on the scope's list page (?search=), Esc puts the field back and leaves it.
  import Icon from "../ui/Icon.svelte";
  import { navigate } from "../../utils/navigation";
  import { searchScope } from "./searchScope";

  let { section, routeProps = {} } = $props();

  const scope = $derived(searchScope(section, routeProps));
  const active = $derived(routeProps?.search || "");

  let input = $state();
  let query = $state("");
  let focused = $state(false);

  // Keep the field in step with the page: it shows the search the list is filtered by.
  $effect(() => {
    query = active;
  });

  function submit() {
    const q = query.trim();
    navigate(q ? `${scope.path}?search=${encodeURIComponent(q)}` : scope.path);
    input.blur();
  }

  function onkeydown(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      submit();
    } else if (event.key === "Escape") {
      query = active;
      input.blur();
    }
  }

  function onWindowKeydown(event) {
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
    if (event.target.closest?.('input, textarea, select, [contenteditable="true"], .monaco-editor')) return;
    event.preventDefault();
    input.focus();
    input.select();
  }
</script>

<svelte:window onkeydown={onWindowKeydown} />

<label class="r-nav-search" role="search">
  <span class="r-nav-scope">{scope.label}</span>
  <Icon name="search" />
  <input
    bind:this={input}
    bind:value={query}
    placeholder={scope.placeholder}
    aria-label={scope.placeholder}
    autocomplete="off"
    spellcheck="false"
    {onkeydown}
    onfocus={() => (focused = true)}
    onblur={() => (focused = false)}
  />
  <kbd class="r-kbd">{focused ? "Esc" : "/"}</kbd>
</label>
