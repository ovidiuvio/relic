<script>
  let selectedEndpoint = "create";
</script>

<div class="px-4 sm:px-0">
  <div class="bg-white shadow-sm rounded-lg border border-gray-200 overflow-hidden">
    <div class="px-6 py-4 border-b border-gray-200">
      <h2 class="text-lg font-semibold text-gray-900 flex items-center">
        <i class="fas fa-code text-blue-600 mr-2"></i>
        API Documentation
      </h2>
    </div>
    <div class="p-6">
      <div class="space-y-6">
        <div>
          <h3 class="text-md font-semibold text-gray-900 mb-3">
            Command Line Usage
          </h3>
          <div
            class="bg-gray-900 rounded-lg p-4 text-green-400 text-sm font-mono overflow-x-auto"
          >
            <pre>{`# Basic usage
echo "Hello World" | curl -X POST http://localhost:8000/api/v1/relics \\
  -F "file=@-" \\
  -F "name=Example"

# Create with options
curl -X POST http://localhost:8000/api/v1/relics \\
  -F "file=@myfile.txt" \\
  -F "name=My File" \\
  -F "access_level=public" \\
  -F "expires_in=24h"`}</pre>
          </div>
        </div>

        <div>
          <h3 class="text-md font-semibold text-gray-900 mb-3">
            REST API Endpoints
          </h3>
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead>
                <tr class="text-[#666] uppercase text-[11px] font-semibold tracking-wider bg-gray-50 border-b-2 border-[#cdcdcd]">
                  <th class="px-6 py-2.5 text-left border-none">Method</th>
                  <th class="px-6 py-2.5 text-left border-none">Endpoint</th>
                  <th class="px-6 py-2.5 text-left border-none">Description</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >DELETE</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/admin/clients/{client_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Delete a client</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >DELETE</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/admin/reports/{report_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Delete a report</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >DELETE</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/bookmarks/{relic_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Remove bookmark</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >DELETE</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics/{relic_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Delete relic (hard delete)</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >DELETE</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics/{relic_id}/access/{public_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Remove relic access</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >DELETE</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics/{relic_id}/comments/{comment_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Delete comment</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >DELETE</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/spaces/{space_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Delete a space</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >DELETE</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/spaces/{space_id}/access/{access_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Remove space access</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >DELETE</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/spaces/{space_id}/relics/{relic_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Remove relic from space</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/{relic_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Get raw relic content</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/{relic_id}/raw</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Get raw relic content</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/admin/backups</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >List backups</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/admin/backups/{filename}/download</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Download backup</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/admin/check</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Admin check</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/admin/clients</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >List clients</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/admin/config</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Get admin config</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/admin/relics</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >List all relics (admin)</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/admin/reports</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >List reports</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/admin/stats</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Get system stats</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/bookmarks</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >List bookmarks</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/bookmarks/{relic_id}/bookmarkers</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >List bookmarkers</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/bookmarks/check/{relic_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Check if bookmarked</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/client/relics</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >List client relics</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >List recent relics</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics/{relic_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Get relic metadata</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics/{relic_id}/access</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Get relic access</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics/{relic_id}/comments</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >List comments</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics/{relic_id}/lineage</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Get relic lineage</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/spaces</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >List spaces</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/spaces/{space_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Get space details</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/spaces/{space_id}/access</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Get space access</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/spaces/{space_id}/relics</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >List space relics</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/version</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Get API version</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >GET</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/health</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Health check</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/admin/backups</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Create backup</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/admin/backups/{filename}/restore</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Restore backup</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/admin/backups/restore-upload</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Restore from upload</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/bookmarks</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Add bookmark</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/client/register</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Register client</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Create new relic</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics/reports</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Submit report</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics/{relic_id}/access</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Add relic access</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics/{relic_id}/comments</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Add comment</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics/{relic_id}/fork</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Fork relic (new lineage)</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/spaces</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Create space</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/spaces/{space_id}/access</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Add space access</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/spaces/{space_id}/relics</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Add relic to space</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >POST</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/spaces/{space_id}/transfer-ownership</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Transfer space ownership</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >PUT</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/client/name</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Update client name</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >PUT</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics/{relic_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Update relic metadata</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >PUT</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/relics/{relic_id}/comments/{comment_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Update comment</td
                  >
                </tr>
                <tr>
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900"
                    >PUT</td
                  >
                  <td
                    class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono"
                    >/api/v1/spaces/{space_id}</td
                  >
                  <td class="px-6 py-4 text-sm text-gray-500"
                    >Update space details</td
                  >
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
              <span
                ><strong>Immutable Relics:</strong> Each relic is permanent and cannot
                be modified after creation.</span
              >
            </li>
            <li class="flex items-start">
              <i class="fas fa-check text-green-600 mr-2 mt-1"></i>
              <span
                ><strong>Fork Support:</strong> Create independent copies of relics
                for modification.</span
              >
            </li>
            <li class="flex items-start">
              <i class="fas fa-check text-green-600 mr-2 mt-1"></i>
              <span
                ><strong>Universal Content:</strong> Support for text, code, images,
                PDFs, CSVs, archives, and more.</span
              >
            </li>
            <li class="flex items-start">
              <i class="fas fa-check text-green-600 mr-2 mt-1"></i>
              <span
                ><strong>Smart Processing:</strong> Automatic syntax highlighting,
                thumbnail generation, metadata extraction.</span
              >
            </li>
            <li class="flex items-start">
              <i class="fas fa-check text-green-600 mr-2 mt-1"></i>
              <span
                ><strong>Access Control:</strong> Public, unlisted, and private relics
                with optional password protection.</span
              >
            </li>
            <li class="flex items-start">
              <i class="fas fa-check text-green-600 mr-2 mt-1"></i>
              <span
                ><strong>Expiration:</strong> Set relics to expire after 1h, 24h,
                7d, 30d, or never.</span
              >
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</div>
