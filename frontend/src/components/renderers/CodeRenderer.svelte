<script>
  import MonacoEditor from '../MonacoEditor.svelte'
  import { createEventDispatcher } from 'svelte'

  export let processed
  export let relicId
  export let showSyntaxHighlighting
  export let showLineNumbers
  export let fontSize = 13

  const dispatch = createEventDispatcher()

  function forwardEvent(event) {
    dispatch(event.type, event.detail)
  }

  $: language = processed.type === 'code' ? (processed.metadata?.language || 'plaintext') : 'plaintext'
</script>

<div class="border-t border-gray-200">
  <MonacoEditor
    value={processed.preview || ''}
    {language}
    readOnly={true}
    height="calc(100vh - 300px)"
    relicId={relicId}
    noWrapper={true}
    {showSyntaxHighlighting}
    {showLineNumbers}
    {fontSize}
    on:line-clicked={forwardEvent}
    on:line-range-selected={forwardEvent}
    on:multi-line-selected={forwardEvent}
    on:line-copied={forwardEvent}
  />
</div>
{#if processed.truncated}
  <div class="bg-blue-50 border-t border-gray-200 px-6 py-4 text-center text-sm text-blue-700 rounded-b-lg">
    Content truncated. <a href="/{relicId}/raw" class="font-semibold hover:underline">Download full file</a>
  </div>
{/if}
