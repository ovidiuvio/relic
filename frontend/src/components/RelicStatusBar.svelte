<script>
  import { createEventDispatcher } from 'svelte'

  export let relic
  export let processed
  export let isFullWidth
  export let showSyntaxHighlighting
  export let showLineNumbers
  export let showComments = true
  export let showSource = false
  export let pdfState = null
  export let fontSize = 13

  const dispatch = createEventDispatcher()
</script>

<div class="px-6 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between flex-wrap gap-3">
  <!-- Status Badges -->
  <div class="flex flex-wrap gap-1.5">
    {#if relic.access_level === 'private'}
      <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium leading-none" style="background-color: #fce3eb; color: #76306c;" title="Private - accessible only via URL">
        <i class="fas fa-lock text-[10px]"></i>
        <span>Private</span>
      </span>
    {:else if relic.access_level === 'public'}
      <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium leading-none" style="background-color: #e2f2fd; color: #217db1;" title="Public - discoverable">
        <i class="fas fa-globe text-[10px]"></i>
        <span>Public</span>
      </span>
    {/if}
    {#if relic.fork_of}
      <a href="/{relic.fork_of}" class="inline-flex items-center gap-1.5 px-2 py-1 bg-teal-100 text-teal-700 rounded text-xs font-medium leading-none hover:bg-teal-200 transition-colors" title="Fork of {relic.fork_of}">
        <i class="fas fa-code-branch text-[10px]"></i>
        <span class="font-mono">{relic.fork_of.substring(0, 8)}</span>
      </a>
    {/if}
    {#if relic.password_hash}
      <span class="inline-flex items-center gap-1.5 px-2 py-1 bg-amber-100 text-amber-700 rounded text-xs font-medium leading-none" title="Password protected">
        <i class="fas fa-key text-[10px]"></i>
      </span>
    {/if}
    {#if relic.expires_at}
      <span class="inline-flex items-center gap-1.5 px-2 py-1 bg-orange-100 text-orange-700 rounded text-xs font-medium leading-none" title="Expires {new Date(relic.expires_at).toLocaleDateString()}">
        <i class="fas fa-clock text-[10px]"></i>
        <span class="text-[11px]">{new Date(relic.expires_at).toLocaleDateString()}</span>
      </span>
    {/if}
    {#if relic.tags && relic.tags.length > 0}
      {#each relic.tags as tag}
        <div class="inline-flex items-center bg-gray-200 text-gray-700 rounded text-xs font-medium leading-none overflow-hidden hover:bg-gray-300 transition-colors">
          <button
            on:click={() => dispatch('tag-click', tag.name)}
            class="flex items-center gap-1.5 px-2 py-1 h-full cursor-pointer focus:outline-none"
            title="Filter by tag: {tag.name}"
          >
            <i class="fas fa-tag text-[10px]"></i>
            <span>{tag.name}</span>
          </button>
          
          {#if relic.can_edit}
            <button
              on:click|stopPropagation={() => dispatch('remove-tag', tag.name)}
              class="px-1.5 h-full border-l border-gray-400/30 hover:bg-red-100 hover:text-red-600 transition-colors focus:outline-none"
              title="Remove tag"
            >
              <i class="fas fa-times text-[10px]"></i>
            </button>
          {/if}
        </div>
      {/each}
    {/if}
  </div>

  <!-- View Controls -->
  <div class="flex items-center gap-2">
    <!-- Full-Width Toggle -->
    <button
      on:click={() => dispatch('toggle-fullwidth')}
      class="px-2 py-1 rounded text-xs font-medium transition-colors {isFullWidth ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
      title={isFullWidth ? 'Normal width' : 'Full width'}
    >
      <i class="fas {isFullWidth ? 'fa-compress' : 'fa-expand'}"></i>
    </button>

    <!-- Editor Controls (for code, text, markdown/html source) -->
    {#if processed && (processed.type === 'code' || processed.type === 'text' || (processed.type === 'markdown' && showSource) || (processed.type === 'html' && showSource))}
      <div class="flex items-center gap-1 border-l border-gray-300 pl-2 ml-2">
        <button
          on:click={() => dispatch('toggle-syntax')}
          class="px-2 py-1 rounded text-xs font-medium transition-colors {showSyntaxHighlighting ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
          title="Toggle syntax highlighting"
        >
          <i class="fas fa-palette text-xs"></i>
        </button>
        <button
          on:click={() => dispatch('toggle-linenumbers')}
          class="px-2 py-1 rounded text-xs font-medium transition-colors {showLineNumbers ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
          title="Toggle line numbers"
        >
          <i class="fas fa-list-ol text-xs"></i>
        </button>
        <button
          on:click={() => dispatch('toggle-comments')}
          class="px-2 py-1 rounded text-xs font-medium transition-colors {showComments ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
          title="Toggle comments"
        >
          <i class="fas fa-comment-alt text-[10px]"></i>
        </button>

        <!-- Font Size Combo Box -->
        <div class="flex items-center gap-2 border-l border-gray-300 pl-2 ml-2">
          <i class="fas fa-text-height text-xs text-gray-600"></i>
          <select
            value={fontSize.toString()}
            on:change={(e) => {
              const val = e.target.value
              if (val === 'custom') {
                const custom = prompt('Enter font size (8-72):', fontSize.toString())
                if (custom && !isNaN(parseInt(custom, 10))) {
                  const num = parseInt(custom, 10)
                  if (num >= 8 && num <= 72) {
                    dispatch('update-font-size', num)
                  }
                }
              } else {
                dispatch('update-font-size', parseInt(val, 10))
              }
            }}
            class="pl-1.5 pr-0.5 py-1 rounded text-xs bg-white border border-gray-300 text-gray-700 cursor-pointer hover:border-gray-400"
            style="min-width: fit-content; width: auto;"
            title="Font size"
          >
            <option value="12">12</option>
            <option value="13">13</option>
            <option value="14">14</option>
            <option value="15">15</option>
            <option value="16">16</option>
            <option value="18">18</option>
            <option value="20">20</option>
            <option value="custom">Custom...</option>
          </select>
        </div>
      </div>
    {/if}

    <!-- PDF Controls -->
    {#if processed?.type === 'pdf'}
      <div class="flex items-center gap-1 border-l border-gray-300 pl-2 ml-2">
        <button
          on:click={() => dispatch('pdf-zoom-out')}
          class="px-2 py-1 rounded text-xs font-medium transition-colors text-gray-600 hover:text-gray-900 hover:bg-gray-100"
          title="Zoom out (-)"
        >
          <i class="fas fa-search-minus"></i>
        </button>
        <span class="text-xs text-gray-700 font-mono min-w-[3rem] text-center">
          {Math.round((pdfState?.scale || 1.5) * 100)}%
        </span>
        <button
          on:click={() => dispatch('pdf-zoom-in')}
          class="px-2 py-1 rounded text-xs font-medium transition-colors text-gray-600 hover:text-gray-900 hover:bg-gray-100"
          title="Zoom in (+)"
        >
          <i class="fas fa-search-plus"></i>
        </button>
        <button
          on:click={() => dispatch('pdf-reset-zoom')}
          class="px-2 py-1 rounded text-xs font-medium transition-colors text-gray-600 hover:text-gray-900 hover:bg-gray-100"
          title="Reset zoom (0)"
        >
          <i class="fas fa-undo text-[10px]"></i>
        </button>
      </div>
    {/if}

    <!-- Preview/Source Tabs (for Markdown and HTML) -->
    {#if processed?.type === 'markdown' || processed?.type === 'html'}
      <div class="flex items-center gap-1">
        <button
          on:click={() => dispatch('toggle-source', true)}
          class="px-2 py-1 rounded text-xs font-medium transition-colors {showSource ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
          title="Show source"
        >
          <i class="fas fa-file-code"></i>
        </button>
        <button
          on:click={() => dispatch('toggle-source', false)}
          class="px-2 py-1 rounded text-xs font-medium transition-colors {!showSource ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
          title="Show preview"
        >
          <i class="fas fa-eye"></i>
        </button>
      </div>
    {/if}
  </div>
</div>
