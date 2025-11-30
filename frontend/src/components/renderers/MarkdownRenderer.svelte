<script>
  import MonacoEditor from '../MonacoEditor.svelte'
  import { createEventDispatcher } from 'svelte'

  export let processed
  export let relicId
  export let showSyntaxHighlighting
  export let showLineNumbers
  export let showSource = false

  const dispatch = createEventDispatcher()

  function forwardEvent(event) {
    dispatch(event.type, event.detail)
  }
</script>

<div class="border-t border-gray-200">
  {#if !showSource}
    <!-- Rendered Markdown - natural height -->
    <div class="p-6 prose prose-sm max-w-none">
      {@html processed.html}
    </div>
  {:else}
    <!-- Markdown Source Editor - fixed height for editor -->
    <MonacoEditor
      value={processed.preview || ''}
      language="markdown"
      readOnly={true}
      height="calc(100vh - 300px)"
      relicId={relicId}
      noWrapper={true}
      {showSyntaxHighlighting}
      {showLineNumbers}
      on:line-clicked={forwardEvent}
      on:line-range-selected={forwardEvent}
      on:multi-line-selected={forwardEvent}
      on:line-copied={forwardEvent}
    />
  {/if}
</div>
