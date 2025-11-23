<script>
  let selectedEndpoint = 'create'
</script>

<div class="px-4 sm:px-0">
  <div class="bg-white shadow-sm rounded-lg border border-gray-200">
    <div class="px-6 py-4 border-b border-gray-200">
      <h2 class="text-lg font-semibold text-gray-900 flex items-center">
        <i class="fas fa-code text-blue-600 mr-2"></i>
        API Documentation
      </h2>
    </div>
    <div class="p-6">
      <div class="space-y-6">
        <div>
          <h3 class="text-md font-semibold text-gray-900 mb-3">Command Line Usage</h3>
          <div class="bg-gray-900 rounded-lg p-4 text-green-400 text-sm font-mono overflow-x-auto">
            <pre>{`# Basic usage
echo "Hello World" | curl -X POST http://localhost:8000/api/v1/pastes \\
  -F "file=@-" \\
  -F "name=Example"

# Create with options
curl -X POST http://localhost:8000/api/v1/pastes \\
  -F "file=@myfile.txt" \\
  -F "name=My File" \\
  -F "access_level=public" \\
  -F "expires_in=24h"`}</pre>
          </div>
        </div>

        <div>
          <h3 class="text-md font-semibold text-gray-900 mb-3">REST API Endpoints</h3>
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Method</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Endpoint</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr>
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">POST</td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">/api/v1/pastes</td>
                  <td class="px-6 py-4 text-sm text-gray-500">Create new paste</td>
                </tr>
                <tr>
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">GET</td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">/api/v1/pastes</td>
                  <td class="px-6 py-4 text-sm text-gray-500">List recent pastes</td>
                </tr>
                <tr>
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">GET</td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">/api/v1/pastes/:id</td>
                  <td class="px-6 py-4 text-sm text-gray-500">Get paste metadata</td>
                </tr>
                <tr>
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">GET</td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">/:id/raw</td>
                  <td class="px-6 py-4 text-sm text-gray-500">Get raw content</td>
                </tr>
                <tr>
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">POST</td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">/api/v1/pastes/:id/edit</td>
                  <td class="px-6 py-4 text-sm text-gray-500">Create new version</td>
                </tr>
                <tr>
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">POST</td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">/api/v1/pastes/:id/fork</td>
                  <td class="px-6 py-4 text-sm text-gray-500">Fork paste (new lineage)</td>
                </tr>
                <tr>
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">DELETE</td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">/api/v1/pastes/:id</td>
                  <td class="px-6 py-4 text-sm text-gray-500">Delete paste (soft delete)</td>
                </tr>
                <tr>
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">GET</td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">/api/v1/pastes/:id/history</td>
                  <td class="px-6 py-4 text-sm text-gray-500">Get version history</td>
                </tr>
                <tr>
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">GET</td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">/api/v1/diff</td>
                  <td class="px-6 py-4 text-sm text-gray-500">Compare two pastes</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <h3 class="text-md font-semibold text-gray-900 mb-3">Features</h3>
          <ul class="space-y-2 text-sm text-gray-600">
            <li class="flex items-start">
              <i class="fas fa-check text-green-600 mr-2 mt-1"></i>
              <span><strong>Immutable Pastes:</strong> Each paste is permanent. Edits create new versions with complete history.</span>
            </li>
            <li class="flex items-start">
              <i class="fas fa-check text-green-600 mr-2 mt-1"></i>
              <span><strong>Version Lineage:</strong> Track complete history through parent-child relationships and forks.</span>
            </li>
            <li class="flex items-start">
              <i class="fas fa-check text-green-600 mr-2 mt-1"></i>
              <span><strong>Universal Content:</strong> Support for text, code, images, PDFs, CSVs, archives, and more.</span>
            </li>
            <li class="flex items-start">
              <i class="fas fa-check text-green-600 mr-2 mt-1"></i>
              <span><strong>Smart Processing:</strong> Automatic syntax highlighting, thumbnail generation, metadata extraction.</span>
            </li>
            <li class="flex items-start">
              <i class="fas fa-check text-green-600 mr-2 mt-1"></i>
              <span><strong>Diff Support:</strong> Compare any two pastes with full diff output.</span>
            </li>
            <li class="flex items-start">
              <i class="fas fa-check text-green-600 mr-2 mt-1"></i>
              <span><strong>Access Control:</strong> Public, unlisted, and private pastes with optional password protection.</span>
            </li>
            <li class="flex items-start">
              <i class="fas fa-check text-green-600 mr-2 mt-1"></i>
              <span><strong>Expiration:</strong> Set pastes to expire after 1h, 24h, 7d, 30d, or never.</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</div>
