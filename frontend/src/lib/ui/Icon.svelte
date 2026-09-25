<script>
  // One icon from the Relic design system set (24px grid, 1.75 stroke, currentColor).
  import icons from "../../design-system/icons.json";

  let { name, size = 16, title = undefined, class: className = "" } = $props();

  const style = $derived(size === 16 ? undefined : `width:${size}px;height:${size}px`);
</script>

<svg
  class="r-icon {className}"
  {style}
  viewBox="0 0 24 24"
  role={title ? "img" : undefined}
  aria-hidden={title ? undefined : "true"}
  aria-label={title}
>{@html icons[name] ?? ""}</svg>
