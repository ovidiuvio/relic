<script>
  // One collapsible inspector section. Whether you left it open is remembered per section
  // (Details opens by default); the body renders only while open, so sections can load lazily.
  import Icon from "../../ui/Icon.svelte";

  // focus: { id, n } — when its id matches, the section opens and scrolls into view
  // (a list counter was clicked). n changes on every request so repeats still work.
  let { id, title, aside = "", defaultOpen = false, focus = null, children } = $props();
  let el = $state();

  const KEY = "relic_inspector_sections";

  function remembered() {
    try {
      return JSON.parse(localStorage.getItem(KEY) || "{}")[id];
    } catch {
      return undefined;
    }
  }

  // Only the initial state comes from the props; after that the reader's choice wins.
  const initial = () => remembered() ?? defaultOpen;
  let open = $state(initial());

  $effect(() => {
    if (focus?.id !== id) return;
    focus.n;
    open = true;
    requestAnimationFrame(() => el?.scrollIntoView({ block: "nearest", behavior: "smooth" }));
  });

  function toggle(event) {
    open = event.currentTarget.open;
    try {
      const all = JSON.parse(localStorage.getItem(KEY) || "{}");
      all[id] = open;
      localStorage.setItem(KEY, JSON.stringify(all));
    } catch {
      // Storage can be unavailable (private windows); the section still works.
    }
  }
</script>

<details class="r-ins-sec" {open} ontoggle={toggle} bind:this={el}>
  <summary><Icon name="chevr" />{title}{#if aside}<span class="r-ins-sec-aside">{aside}</span>{/if}</summary>
  {#if open}{@render children()}{/if}
</details>
