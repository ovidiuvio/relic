<script>
  // The Relic mark: a page with three lines, drawn in currentColor.
  let { size = 20 } = $props();
</script>

<svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">
  <rect x="4" y="2.5" width="16" height="19" rx="3.5" fill="currentColor" opacity=".22" />
  <path d="M8.5 8h7M8.5 12h7M8.5 16h4" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none" />
</svg>
