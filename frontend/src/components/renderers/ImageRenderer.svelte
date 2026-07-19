<script>
  import { publicSettings } from '../../stores/settingsStore'

  export let processed
  export let relicName
  export let contentType = ''

  $: isSvg = (contentType || '').split(';')[0].trim().toLowerCase() === 'image/svg+xml'
  $: blocked = isSvg && !$publicSettings.render_svg_inline
</script>

<div class="border-t border-gray-200 p-6">
  {#if blocked}
    <div class="p-6 text-center text-gray-500 bg-gray-50 border border-gray-200 rounded">
      <i class="fas fa-shield-alt text-2xl mb-2 text-gray-400"></i>
      <p class="text-sm">SVG display is disabled on this instance.</p>
      <a href={processed.url} download={relicName} class="text-sm text-blue-600 hover:underline mt-2 inline-block">
        Download the file instead
      </a>
    </div>
  {:else}
    <img src={processed.url} alt={relicName} class="max-w-full h-auto rounded" />
  {/if}
</div>
