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

  const dispatch = createEventDispatcher()
  const forwardEvent = createEventForwarder(dispatch)
</script>

<div class="border-t border-gray-200">
  {#if !showSource}
    <!-- HTML Preview Frame -->
    <div style="height: calc(100vh - 300px);">
      <iframe
        srcdoc={processed.html}
        class="w-full h-full border-0"
        sandbox="allow-same-origin allow-scripts allow-forms"
        title="HTML Content Preview"
      ></iframe>
    </div>
  {:else}
    <!-- HTML Source Editor -->
    <MonacoEditor
      value={processed.html || ''}
      language="html"
      readOnly={true}
      height="calc(100vh - 300px)"
      relicId={relicId}
      noWrapper={true}
      {showSyntaxHighlighting}
      {showLineNumbers}
      {showComments}
      {fontSize}
      {comments}
      {isAdmin}
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
