<script>
  import MonacoEditor from '../MonacoEditor.svelte'
  import { createEventDispatcher } from 'svelte'
  import { createEventForwarder } from '../../services/utils/eventUtils'

  export let processed
  export let relicId
  export let showSyntaxHighlighting
  export let showLineNumbers
  export let showComments = true
  export let showSource = false
  export let fontSize = 13
  export let comments = []
  export let isAdmin = false
  export let darkMode = true

  const dispatch = createEventDispatcher()
  const forwardEvent = createEventForwarder(dispatch)

  let monacoHeight = 0
</script>

<div class="border-t border-gray-200 flex flex-col flex-1 min-h-0">
  {#if !showSource}
    <!-- Rendered Markdown - natural height -->
    <div class="p-6 prose prose-sm max-w-none">
      {@html processed.html}
    </div>
  {:else}
    <!-- Markdown Source Editor - fixed height for editor -->
    <div class="flex-1 min-h-0" bind:clientHeight={monacoHeight}>
    {#if monacoHeight > 0}
    <MonacoEditor
      value={processed.preview || ''}
      language="markdown"
      readOnly={true}
      height="{monacoHeight}px"
      relicId={relicId}
      noWrapper={true}
      {showSyntaxHighlighting}
      {showLineNumbers}
      {showComments}
      {fontSize}
      {comments}
      {isAdmin}
      {darkMode}
      on:line-clicked={forwardEvent}
      on:line-range-selected={forwardEvent}
      on:multi-line-selected={forwardEvent}
      on:line-copied={forwardEvent}
      on:createComment={forwardEvent}
      on:updateComment={forwardEvent}
      on:deleteComment={forwardEvent}
      on:toggle-comments={forwardEvent}
    />
    {/if}
    </div>
  {/if}
</div>
