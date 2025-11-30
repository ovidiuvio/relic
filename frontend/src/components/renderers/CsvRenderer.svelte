<script>
  export let processed
</script>

<div class="border-t border-gray-200 p-6">
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-gray-200">
          <th class="px-4 py-2 text-left font-semibold text-gray-900">Row</th>
          {#each processed.metadata.columns as col}
            <th class="px-4 py-2 text-left font-semibold text-gray-900">{col}</th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each processed.rows as row, idx}
          <tr class="border-b border-gray-100 hover:bg-gray-50">
            <td class="px-4 py-2 text-gray-600">{idx + 1}</td>
            {#each processed.metadata.columns as col}
              <td class="px-4 py-2 text-gray-900">{row[col] || ''}</td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>
