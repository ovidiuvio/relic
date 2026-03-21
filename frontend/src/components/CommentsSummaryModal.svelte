<script>
  import { getCommentsPaginated } from '../services/api/comments';
  import { getRelic, getRelicRaw } from '../services/api/relics';
  import { showToast } from '../stores/toastStore';
  import MonacoEditor from './MonacoEditor.svelte';
  import { getSyntaxFromExtension } from '../services/typeUtils';
  import { processContent } from '../services/processors/index.js';

  export let open = false;
  export let relicId = "";
  export let relicName = "";

  let comments = [];
  let totalComments = 0;
  let relicMetadata = null;
  let processed = null;
  let rawContent = '';
  let lines = [];
  let isLoading = false;
  let loadingMore = false;
  let error = null;

  const PAGE_SIZE = 1000;

  async function fetchAllData() {
    if (!relicId) return;

    isLoading = true;
    error = null;
    try {
      const [commentsRes, relicRes, rawRes] = await Promise.all([
        getCommentsPaginated(relicId, { limit: PAGE_SIZE }),
        getRelic(relicId),
        getRelicRaw(relicId)
      ]);

      comments = commentsRes.comments;
      totalComments = commentsRes.total;
      relicMetadata = relicRes.data;
      
      const blob = rawRes.data;
      rawContent = await blob.text();
      
      // Process content to handle ANSI and other types
      processed = await processContent(rawContent, relicMetadata.type, relicMetadata.language_hint);
      
      const displayContent = processed.preview || processed.text || rawContent;
      lines = displayContent.split('\n');

    } catch (err) {
      console.error("[CommentsSummaryModal] Error fetching data:", err);
      error = "Failed to load discussion and code context.";
      showToast(error, "error");
    } finally {
      isLoading = false;
    }
  }

  async function loadMore() {
    if (loadingMore) return;
    loadingMore = true;
    try {
      const res = await getCommentsPaginated(relicId, { limit: PAGE_SIZE, offset: comments.length });
      comments = [...comments, ...res.comments];
    } catch (err) {
      showToast("Failed to load more comments", "error");
    } finally {
      loadingMore = false;
    }
  }

  $: if (open && relicId) {
    fetchAllData();
  }

  $: groupedComments = comments.reduce((acc, c) => {
    if (!acc[c.line_number]) acc[c.line_number] = [];
    acc[c.line_number].push(c);
    return acc;
  }, {});

  $: sortedLines = Object.keys(groupedComments).map(Number).sort((a, b) => a - b);

  function getSnippet(lineNum) {
    const startNum = Math.max(0, lineNum - 6);
    const endNum = Math.min(lines.length, lineNum + 5);
    
    const snippetContent = lines.slice(startNum, endNum).join('\n');
    
    // Handle ANSI decorations if present
    let snippetDecorations = [];
    if (processed && processed.hasAnsiCodes && processed.ansiDecorations) {
        const fullContent = processed.preview || processed.text || '';
        const fullLines = fullContent.split('\n');
        
        // Calculate char offset for the start of the snippet
        let startCharOffset = 0;
        for (let i = 0; i < startNum; i++) {
            startCharOffset += fullLines[i].length + 1; // +1 for \n
        }
        
        const endCharOffset = startCharOffset + snippetContent.length;
        
        // Filter and offset decorations
        snippetDecorations = processed.ansiDecorations
            .filter(d => d.range.end > startCharOffset && d.range.start < endCharOffset)
            .map(d => ({
                range: {
                    start: Math.max(0, d.range.start - startCharOffset),
                    end: Math.min(snippetContent.length, d.range.end - startCharOffset)
                },
                options: d.options
            }));
    }

    return {
      content: snippetContent,
      offset: startNum,
      lineCount: endNum - startNum,
      ansiDecorations: snippetDecorations
    };
  }

  function closeModal() {
    open = false;
  }

  function handleBackdropClick(e) {
    if (e.target === e.currentTarget) {
      closeModal();
    }
  }

  function handleKeydown(e) {
    if (e.key.toLowerCase() === 'escape' && open) {
      closeModal();
    }
  }

  $: language = relicMetadata ? (relicMetadata.language_hint || (relicMetadata.name ? getSyntaxFromExtension(relicMetadata.name.split('.').pop()) : 'plaintext')) : 'plaintext';
  
  function navigateToLine(lineNum) {
    window.open(`/${relicId}#L${lineNum}`, '_blank');
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
  <div
    class="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-4 transition-opacity backdrop-blur-sm"
    on:click={handleBackdropClick}
    role="dialog"
    aria-modal="true"
    aria-labelledby="comments-summary-title"
  >
    <div
      class="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col transform transition-all border border-gray-200"
      on:click|stopPropagation
    >
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white rounded-t-xl z-20">
        <h2 id="comments-summary-title" class="text-xl font-bold text-gray-900 flex items-center gap-3">
          <div class="p-2 bg-green-50 text-green-600 rounded-lg shadow-sm border border-green-100">
            <i class="fas fa-comment-alt"></i>
          </div>
          <div class="flex flex-col">
              <span>Discussion Context</span>
              <span class="text-xs font-normal text-gray-400 mt-0.5">
                  <a href="/{relicId}" target="_blank" class="hover:underline text-blue-500 font-medium">{relicName || relicId}</a>
              </span>
          </div>
        </h2>
        <div class="flex items-center gap-3">
            {#if totalComments > 0}
              <span class="text-xs text-gray-400 font-medium">{comments.length} of {totalComments}</span>
            {/if}
            <button
              on:click={closeModal}
              class="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-2 rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-green-500"
              title="Close (Esc)"
              aria-label="Close modal"
            >
              <i class="fas fa-times text-lg" aria-hidden="true"></i>
            </button>
        </div>
      </div>

      <!-- Content -->
      <div class="p-6 overflow-y-auto flex-1 custom-scrollbar bg-gray-50/20">
        {#if isLoading}
          <div class="flex flex-col items-center justify-center py-24 text-gray-500">
            <i class="fas fa-spinner fa-spin text-3xl mb-4 text-green-600"></i>
            <p>Syncing code context...</p>
          </div>
        {:else if error}
          <div class="text-center py-12">
            <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 text-red-500 mb-4">
              <i class="fas fa-exclamation-triangle text-2xl"></i>
            </div>
            <h3 class="text-lg font-medium text-gray-900 mb-2">Error Loading Discussion</h3>
            <p class="text-gray-500">{error}</p>
            <button
              class="mt-4 px-4 py-2 border border-gray-300 rounded-md text-sm font-medium hover:bg-gray-50 transition-colors focus:outline-none"
              on:click={fetchAllData}
            >
              Retry
            </button>
          </div>
        {:else if sortedLines.length > 0}
          <div class="space-y-8">
            {#each sortedLines as lineNum}
                {@const snippet = getSnippet(lineNum)}
                <div class="group/snippet border border-gray-200 rounded-xl overflow-hidden shadow-sm bg-white transition-all hover:border-gray-300">
                    <div class="bg-gray-50/50 px-6 py-2 border-b border-gray-100 flex items-center justify-between font-mono">
                        <div class="flex items-center gap-4">
                            <button
                                on:click={() => navigateToLine(lineNum)}
                                class="text-xs font-bold text-gray-500 hover:text-blue-600 bg-white px-2 py-0.5 rounded shadow-sm border border-gray-200 transition-all flex items-center gap-2 group-hover/snippet:border-blue-200"
                                title="Open in file at line {lineNum}"
                            >
                                <i class="fas fa-external-link-alt text-[9px] opacity-40"></i>
                                L{lineNum}
                            </button>
                            <span class="text-[10px] font-bold text-gray-300 uppercase tracking-widest">{groupedComments[lineNum].length} comments</span>
                        </div>
                    </div>
                    <div class="monaco-container">
                        <MonacoEditor
                            value={snippet.content}
                            {language}
                            readOnly={true}
                            height="{Math.max(120, (snippet.lineCount * 24) + 120)}px"
                            {relicId}
                            noWrapper={true}
                            showSyntaxHighlighting={true}
                            showLineNumbers={true}
                            showComments={true}
                            fontSize={13}
                            comments={groupedComments[lineNum].map(c => ({
                                ...c,
                                line_number: c.line_number - snippet.offset
                            }))}
                            isAdmin={false}
                            darkMode={false}
                            lineNumberOffset={snippet.offset}
                            ansiDecorations={snippet.ansiDecorations}
                        />
                    </div>
                </div>
            {/each}
            {#if comments.length < totalComments}
              <div class="flex justify-center pt-2">
                <button
                  on:click={loadMore}
                  disabled={loadingMore}
                  class="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 transition-colors focus:outline-none disabled:opacity-50"
                >
                  {#if loadingMore}
                    <i class="fas fa-spinner fa-spin mr-2"></i>Loading...
                  {:else}
                    Load more ({totalComments - comments.length} remaining)
                  {/if}
                </button>
              </div>
            {/if}
          </div>
        {:else}
          <div class="text-center py-24 text-gray-500">
            <div class="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-gray-100">
                <i class="far fa-comments text-2xl text-gray-300"></i>
            </div>
            <p>No discussion found for this relic.</p>
          </div>
        {/if}
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 border-t border-gray-100 bg-gray-50 rounded-b-xl flex justify-between items-center z-20">
        <div class="flex items-center gap-2">
            <div class="w-1.5 h-1.5 bg-green-500 rounded-full shadow-[0_0_5px_rgba(34,197,94,0.4)]"></div>
            <span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest leading-none">Contextual Summary</span>
        </div>
        <button
          type="button"
          on:click={closeModal}
          class="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 transition-colors focus:outline-none"
        >
          Dismiss
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .custom-scrollbar::-webkit-scrollbar {
    width: 8px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: #e2e8f0;
    border-radius: 4px;
    border: 2px solid transparent;
    background-clip: content-box;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #cbd5e1;
    background-clip: content-box;
  }

  :global(.monaco-container .monaco-editor) {
      padding: 0 !important;
  }
</style>
