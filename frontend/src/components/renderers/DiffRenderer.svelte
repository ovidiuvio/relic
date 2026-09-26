<script>
  import { createEventDispatcher } from 'svelte';
  import CodeRenderer from './CodeRenderer.svelte';
  import Icon from '../../lib/ui/Icon.svelte';

  export let processed;
  export let relicId;
  export let showSource = false;
  export let showSyntaxHighlighting;
  export let showLineNumbers;
  export let showComments = true;
  export let fontSize = 13;
  export let comments = [];
  export let isAdmin = false;
  export let darkMode = true;
  export let diffViewMode = 'unified'; // 'unified' or 'split'

  const dispatch = createEventDispatcher();

  $: files = processed.files || [];

  // Lines added and removed, per file and in all.
  function stats(file) {
    let add = 0, del = 0;
    for (const hunk of file.hunks || []) for (const line of hunk.lines) {
      if (line.type === 'add') add++;
      else if (line.type === 'delete') del++;
    }
    return { add, del };
  }
  $: fileStats = files.map(stats);
  $: totals = fileStats.reduce((t, f) => ({ add: t.add + f.add, del: t.del + f.del }), { add: 0, del: 0 });

  function getSign(type) {
    if (type === 'add') return '+';
    if (type === 'delete') return '-';
    return ' ';
  }

  // Aligns lines for split view by grouping consecutive deletions and additions
  function getAlignedHunkLines(hunkLines) {
    const alignedRows = [];
    let i = 0;
    
    while (i < hunkLines.length) {
      const line = hunkLines[i];
      
      if (line.type === 'context' || line.type === 'meta') {
        alignedRows.push({
          left: line,
          right: line,
          type: line.type
        });
        i++;
      } else if (line.type === 'delete') {
        // Look ahead for additions to align with
        const deletions = [];
        const additions = [];
        
        // Collect consecutive deletions
        while (i < hunkLines.length && hunkLines[i].type === 'delete') {
          deletions.push(hunkLines[i]);
          i++;
        }
        
        // Collect subsequent consecutive additions
        while (i < hunkLines.length && hunkLines[i].type === 'add') {
          additions.push(hunkLines[i]);
          i++;
        }
        
        // Pair them up
        const maxLen = Math.max(deletions.length, additions.length);
        for (let j = 0; j < maxLen; j++) {
          alignedRows.push({
            left: deletions[j] || null,
            right: additions[j] || null,
            type: 'change'
          });
        }
      } else if (line.type === 'add') {
        // Lone addition (not preceded by deletions)
        alignedRows.push({
          left: null,
          right: line,
          type: 'add'
        });
        i++;
      }
    }
    
    return alignedRows;
  }
</script>

{#if showSource}
  <CodeRenderer
    {processed}
    {relicId}
    {showSyntaxHighlighting}
    {showLineNumbers}
    {showComments}
    {fontSize}
    {comments}
    {isAdmin}
    {darkMode}
    on:line-clicked
    on:line-range-selected
    on:multi-line-selected
    on:line-copied
    on:createComment
    on:updateComment
    on:deleteComment
    on:toggle-comments
  />
{:else}
  <div class="diff" class:is-dark={darkMode} style="--diff-font: {fontSize}px">
    {#if files.length === 0}
      <div class="diff-empty"><Icon name="split" size={22} /><p>No changes in this diff.</p></div>
    {:else}
      <div class="diff-summary">
        <b>{files.length} {files.length === 1 ? 'file' : 'files'} changed</b>
        <span class="diff-add">+{totals.add.toLocaleString('en-US')}</span>
        <span class="diff-del">−{totals.del.toLocaleString('en-US')}</span>
      </div>

      {#each files as file, fi}
        <section class="diff-file">
          <header class="diff-file-head">
            <Icon name="file" size={14} />
            <span class="diff-file-name" title={file.name}>{file.name}</span>
            <span class="diff-add">+{fileStats[fi].add}</span>
            <span class="diff-del">−{fileStats[fi].del}</span>
          </header>

          {#if diffViewMode === 'split'}
            <table class="diff-table is-split">
              <colgroup><col class="c-num" /><col /><col class="c-num" /><col /></colgroup>
              <tbody>
                {#each file.hunks as hunk}
                  <tr class="hunk"><td colspan="4">{hunk.header}</td></tr>
                  {#each getAlignedHunkLines(hunk.lines) as row}
                    <tr>
                      <td class="num" class:is-del={row.left?.type === 'delete'}>{row.left?.oldLine || ''}</td>
                      <td class="code" class:is-del={row.left?.type === 'delete'} class:is-none={!row.left}>{#if row.left}<span class="sign">{getSign(row.left.type)}</span>{row.left.content.substring(1)}{/if}</td>
                      <td class="num" class:is-add={row.right?.type === 'add'}>{row.right?.newLine || ''}</td>
                      <td class="code" class:is-add={row.right?.type === 'add'} class:is-none={!row.right}>{#if row.right}<span class="sign">{getSign(row.right.type)}</span>{row.right.content.substring(1)}{/if}</td>
                    </tr>
                  {/each}
                {/each}
              </tbody>
            </table>
          {:else}
            <table class="diff-table">
              <colgroup><col class="c-num" /><col class="c-num" /><col /></colgroup>
              <tbody>
                {#each file.hunks as hunk}
                  <tr class="hunk"><td colspan="3">{hunk.header}</td></tr>
                  {#each hunk.lines as line}
                    <tr class:is-add={line.type === 'add'} class:is-del={line.type === 'delete'}>
                      <td class="num">{line.oldLine || ''}</td>
                      <td class="num">{line.newLine || ''}</td>
                      <td class="code"><span class="sign">{getSign(line.type)}</span>{line.content.substring(1)}</td>
                    </tr>
                  {/each}
                {/each}
              </tbody>
            </table>
          {/if}
        </section>
      {/each}
    {/if}
  </div>
{/if}

<style>
  .diff {
    --d-bg: var(--surface);
    --d-panel: var(--subtle);
    --d-line: var(--line);
    --d-ink: var(--ink);
    --d-muted: var(--ink-3);
    --d-add: var(--success-soft);
    --d-add-num: color-mix(in srgb, var(--success) 16%, var(--surface));
    --d-add-ink: var(--success-ink);
    --d-del: var(--danger-soft);
    --d-del-num: color-mix(in srgb, var(--danger) 13%, var(--surface));
    --d-del-ink: var(--danger);
    --d-hunk: var(--info-soft);
    --d-hunk-ink: var(--info-ink);
    flex: 1;
    min-height: 0;
    overflow: auto;
    background: var(--d-bg);
    color: var(--d-ink);
    font: 13px/1.45 var(--font-sans);
  }
  /* Matches the editor's dark theme. */
  .diff.is-dark {
    --d-bg: #1e1e1e;
    --d-panel: #252526;
    --d-line: #333;
    --d-ink: #d4d4d4;
    --d-muted: #858585;
    --d-add: rgba(46, 160, 90, 0.16);
    --d-add-num: rgba(46, 160, 90, 0.28);
    --d-add-ink: var(--night-green);
    --d-del: rgba(229, 83, 75, 0.16);
    --d-del-num: rgba(229, 83, 75, 0.28);
    --d-del-ink: #f08c85;
    --d-hunk: rgba(209, 151, 183, 0.08);
    --d-hunk-ink: var(--night-accent);
  }
  .diff-summary {
    position: sticky;
    top: 0;
    z-index: 3;
    display: flex;
    align-items: center;
    gap: var(--space-2);
    height: 40px;
    padding: 0 var(--space-4);
    border-bottom: 1px solid var(--d-line);
    background: var(--d-bg);
  }
  .diff-summary b {
    font-weight: 600;
  }
  .diff-add,
  .diff-del {
    font: 12.5px var(--font-mono);
  }
  .diff-add {
    color: var(--d-add-ink);
  }
  .diff-del {
    color: var(--d-del-ink);
  }
  /* clip, not hidden: hidden would make the card the sticky header's scroll container. */
  .diff-file {
    margin: var(--space-3) var(--space-4);
    border: 1px solid var(--d-line);
    border-radius: var(--radius-md);
    overflow: clip;
  }
  .diff-file-head {
    position: sticky;
    top: 40px;
    z-index: 2;
    display: flex;
    align-items: center;
    gap: var(--space-2);
    height: 34px;
    padding: 0 var(--space-3);
    border-bottom: 1px solid var(--d-line);
    background: var(--d-panel);
    color: var(--d-muted);
  }
  .diff-file-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    color: var(--d-ink);
    font: 600 12.5px var(--font-mono);
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .diff-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    font: var(--diff-font) / 1.55 var(--font-mono);
  }
  .c-num {
    width: 52px;
  }
  .num {
    padding: 0 8px;
    border-right: 1px solid var(--d-line);
    color: var(--d-muted);
    font-size: 0.9em;
    text-align: right;
    vertical-align: top;
    user-select: none;
  }
  .code {
    padding: 0 12px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .sign {
    display: inline-block;
    width: 1.3em;
    color: var(--d-muted);
    user-select: none;
  }
  tr.is-add .code,
  .code.is-add {
    background: var(--d-add);
  }
  tr.is-add .num,
  .num.is-add {
    background: var(--d-add-num);
  }
  tr.is-del .code,
  .code.is-del {
    background: var(--d-del);
  }
  tr.is-del .num,
  .num.is-del {
    background: var(--d-del-num);
  }
  tr.is-add .sign,
  .is-add .sign {
    color: var(--d-add-ink);
  }
  tr.is-del .sign,
  .is-del .sign {
    color: var(--d-del-ink);
  }
  .code.is-none {
    background: var(--d-panel);
  }
  .is-split .code:nth-child(2) {
    border-right: 1px solid var(--d-line);
  }
  .hunk td {
    padding: 3px 12px;
    background: var(--d-hunk);
    color: var(--d-hunk-ink);
    font-size: 0.9em;
  }
  .diff-empty {
    display: grid;
    justify-items: center;
    gap: var(--space-2);
    padding: var(--space-5);
    color: var(--d-muted);
  }
  .diff-empty p {
    margin: 0;
  }
</style>
