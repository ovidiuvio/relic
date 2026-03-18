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
</script>

<div class="border-t border-gray-200 flex flex-col md:flex-row">
  {#if !showSource}
    <!-- TOC Sidebar -->
    {#if processed?.metadata?.toc && processed.metadata.toc.length > 0}
      <aside class="w-full md:w-64 flex-shrink-0 border-b md:border-b-0 md:border-r border-gray-200 p-6 bg-gray-50 dark:bg-gray-800/50 hidden md:block overflow-y-auto" style="max-height: calc(100vh - 200px);">
        <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-wider mb-4">Table of Contents</h3>
        <nav class="space-y-1">
          {#each processed.metadata.toc as item}
            <a
              href="#{item.id}"
              class="block text-sm text-gray-600 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 truncate"
              style="padding-left: {(item.level - 1) * 0.75}rem;"
              title={item.text}
            >
              {item.text}
            </a>
          {/each}
        </nav>
      </aside>
    {/if}

    <!-- Rendered Markdown - natural height -->
    <div class="p-6 prose prose-sm max-w-none flex-grow min-w-0">
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
