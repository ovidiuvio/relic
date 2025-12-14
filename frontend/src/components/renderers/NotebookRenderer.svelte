<script>
    export let processed;
</script>

<div class="notebook-container bg-white p-4">
    {#each processed.cells as cell}
        <div class="cell mb-4">
            {#if cell.type === 'markdown'}
                <div class="markdown-cell prose max-w-none p-4 rounded-md">
                    {@html cell.content}
                </div>
            {:else if cell.type === 'code'}
                <div class="code-cell">
                    <div class="input-area bg-gray-50 border border-gray-200 rounded-md mb-2">
                        <div class="execution-count text-gray-500 text-xs p-1 border-b border-gray-200 bg-gray-100">
                            In [{cell.execution_count || ' '}]
                        </div>
                        <div class="code-content p-3 font-mono text-sm overflow-x-auto">
                            {@html cell.source}
                        </div>
                    </div>

                    {#if cell.outputs && cell.outputs.length > 0}
                        <div class="output-area pl-4">
                            {#each cell.outputs as output}
                                <div class="output mb-2">
                                    {#if output.type === 'text'}
                                        <pre class="whitespace-pre-wrap font-mono text-sm text-gray-800 bg-white p-2">{output.content}</pre>
                                    {:else if output.type === 'html'}
                                        <div class="html-output prose max-w-none">
                                            {@html output.content}
                                        </div>
                                    {:else if output.type === 'image'}
                                        <div class="image-output">
                                            <img src="data:image/{output.format};base64,{output.content}" alt="Output" class="max-w-full" />
                                        </div>
                                    {:else if output.type === 'error'}
                                        <div class="error-output bg-red-50 text-red-700 p-2 rounded font-mono text-sm whitespace-pre-wrap">
                                            <div class="font-bold">{output.ename}: {output.evalue}</div>
                                            {#each output.traceback as line}
                                                <div>{line}</div>
                                            {/each}
                                        </div>
                                    {/if}
                                </div>
                            {/each}
                        </div>
                    {/if}
                </div>
            {/if}
        </div>
    {/each}
</div>

<style>
    .notebook-container {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
    }

    /* Ensure code highlighting styles from global CSS are applied */
    :global(.code-content pre) {
        margin: 0;
        background: transparent !important;
    }
</style>
