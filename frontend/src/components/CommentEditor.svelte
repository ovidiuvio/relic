<script>
  import { createEventDispatcher } from 'svelte';
  import { processMarkdown } from '../services/markdownProcessor';
  
  export let initialValue = '';
  export let submitLabel = 'Comment';
  
  const dispatch = createEventDispatcher();
  
  let value = initialValue;
  let activeTab = 'write'; // 'write' | 'preview'
  let previewHtml = '';
  let textarea;
  
  async function togglePreview() {
    if (activeTab === 'write') {
      const result = await processMarkdown(value);
      previewHtml = result.html;
      activeTab = 'preview';
    } else {
      activeTab = 'write';
      // Focus textarea on next tick
      setTimeout(() => textarea?.focus(), 0);
    }
  }
  
  function insertText(before, after = '') {
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const selection = text.substring(start, end);
    
    const newText = text.substring(0, start) + before + selection + after + text.substring(end);
    value = newText;
    
    // Restore selection / cursor position
    setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(start + before.length, end + before.length);
    }, 0);
  }
  
  function handleKeydown(e) {
    if (e.ctrlKey && e.key === 'Enter') {
        handleSubmit();
    }
  }
  
  function handleSubmit() {
    if (!value.trim()) return;
    dispatch('submit', value);
  }
  
  function handleCancel() {
    dispatch('cancel');
  }
</script>

<div class="comment-editor">
  <div class="editor-header">
    <div class="tabs">
      <button class:active={activeTab === 'write'} on:click={() => activeTab = 'write'}>Write</button>
      <button class:active={activeTab === 'preview'} on:click={togglePreview}>Preview</button>
    </div>
    {#if activeTab === 'write'}
    <div class="toolbar">
      <button title="Bold" on:click={() => insertText('**', '**')}><i class="fas fa-bold"></i></button>
      <button title="Italic" on:click={() => insertText('*', '*')}><i class="fas fa-italic"></i></button>
      <button title="Link" on:click={() => insertText('[', '](url)')}><i class="fas fa-link"></i></button>
      <button title="Code" on:click={() => insertText('`', '`')}><i class="fas fa-code"></i></button>
      <button title="Quote" on:click={() => insertText('> ')}><i class="fas fa-quote-right"></i></button>
      <button title="List" on:click={() => insertText('- ')}><i class="fas fa-list-ul"></i></button>
    </div>
    {/if}
  </div>

  <div class="editor-content">
    {#if activeTab === 'write'}
      <textarea
        bind:this={textarea}
        bind:value
        placeholder="Leave a comment... (Markdown supported)"
        on:keydown={handleKeydown}
      ></textarea>
    {:else}
      <div class="preview markdown-body">
        {@html previewHtml}
      </div>
    {/if}
  </div>

  <div class="editor-actions">
    <span class="hint">Ctrl+Enter to submit</span>
    <div class="buttons">
      <button class="cancel-btn" on:click={handleCancel}>Cancel</button>
      <button class="submit-btn" on:click={handleSubmit} disabled={!value.trim()}>{submitLabel}</button>
    </div>
  </div>
</div>

<style>
  .comment-editor {
    background: transparent;
    border: 1px solid #e5e7eb;
    border-radius: 4px;
    display: block;
    box-shadow: none;
    width: 100%;
    transition: all 0.2s ease;
    min-height: 150px;
  }

  .comment-editor:focus-within {
    border-color: #9ca3af;
    box-shadow: none;
  }
  
  .editor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: transparent;
    border-bottom: 1px solid #e5e7eb;
    padding: 0 12px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
  }
  
  .tabs {
    display: flex;
    gap: 2px;
  }
  
  .tabs button {
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    color: #6b7280;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    transition: all 0.2s;
    margin-bottom: -1px;
  }
  
  .tabs button:hover {
    color: #374151;
  }

  .tabs button.active {
    color: #2563eb;
    border-bottom-color: #2563eb;
  }
  
  .toolbar {
    display: flex;
    gap: 4px;
    padding: 4px 0;
  }
  
  .toolbar button {
    padding: 6px;
    color: #6b7280;
    background: transparent;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
  }
  
  .toolbar button:hover {
    background: #e5e7eb;
    color: #111827;
  }
  
  .editor-content {
    position: relative;
    min-height: 200px;
    background: transparent;
    display: block;
  }
  
  textarea {
    width: 100%;
    min-height: 200px;
    padding: 12px;
    border: none;
    resize: vertical;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 13px;
    line-height: 1.6;
    outline: none;
    display: block;
    color: #374151;
    background: transparent;
    overflow: auto;
  }
  
  .preview {
    padding: 16px;
    min-height: 120px;
    overflow-y: auto;
    font-size: 14px;
    line-height: 1.6;
    color: #374151;
    resize: none;
    flex: 1;
  }
  
  .editor-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: transparent;
    border-top: 1px solid #e5e7eb;
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
  }
  
  .hint {
    font-size: 12px;
    color: #9ca3af;
  }
  
  .buttons {
    display: flex;
    gap: 10px;
  }
  
  .cancel-btn {
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    color: #6b7280;
    background: transparent;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .cancel-btn:hover {
    color: #374151;
    background: #f3f4f6;
  }
  
  .submit-btn {
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #2563eb;
    background: transparent;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: none;
  }
  
  .submit-btn:hover {
    background: #eff6ff;
    color: #1d4ed8;
  }
  
  .submit-btn:disabled {
    color: #9ca3af;
    background: transparent;
    cursor: not-allowed;
    box-shadow: none;
  }
  
  /* Markdown Styles for Preview */
  :global(.markdown-body p) { margin-bottom: 0.75em; }
  :global(.markdown-body pre) { background: #f3f4f6; padding: 12px; border-radius: 6px; overflow-x: auto; margin-bottom: 0.75em; }
  :global(.markdown-body code) { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.9em; }
  :global(.markdown-body :not(pre) > code) { background: #f3f4f6; padding: 2px 4px; border-radius: 4px; color: #ef4444; }
  :global(.markdown-body pre code) { background: transparent; padding: 0; border-radius: 0; color: inherit; }
  :global(.markdown-body blockquote) { border-left: 4px solid #e5e7eb; padding-left: 12px; color: #6b7280; margin-left: 0; margin-bottom: 0.75em; font-style: italic; }
  :global(.markdown-body ul, .markdown-body ol) { padding-left: 24px; margin-bottom: 0.75em; }
  :global(.markdown-body a) { color: #2563eb; text-decoration: none; }
  :global(.markdown-body a:hover) { text-decoration: underline; }
  :global(.markdown-body img) { max-width: 100%; border-radius: 4px; }
</style>