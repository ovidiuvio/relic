<script>
  import { createRelic } from "../services/api";
  import { showToast } from "../stores/toastStore";
  import Select from "svelte-select";
  import JSZip from "jszip";
  import {
    getContentType,
    getFileExtension,
    getSyntaxFromExtension,
    getAvailableSyntaxOptions,
    getFileTypeDefinition,
  } from "../services/typeUtils";
  import { formatBytes } from "../services/utils/formatting";

  const syntaxOptions = getAvailableSyntaxOptions();

  let activeTab = "upload"; // upload, cli, curl, api
  let title = "";
  let syntax = "auto";
  let syntaxValue = { value: "auto", label: "Auto-detect" };
  let content = "";
  let expiry = "never";
  let visibility = "public";
  let tags = "";
  let isLoading = false;
  let fileInput;
  let uploadedFiles = []; // Array of { file, id }
  let creationResult = null; // { success: [], errors: [] }
  let zipMultiple = true; // Default to true for auto-zipping

  // Get current server URL
  const serverUrl = window.location.origin;

  // Configuration
  const MAX_BATCH_SIZE = 10;
  const IGNORED_NAMES = [
    ".git",
    "node_modules",
    ".DS_Store",
    "__pycache__",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "coverage",
    "venv",
    ".env",
  ];

  // Update syntax when syntaxValue changes
  $: syntax = syntaxValue?.value || "auto";

  // Reset form to initial state
  function resetForm() {
    title = "";
    syntax = "auto";
    syntaxValue = { value: "auto", label: "Auto-detect" };
    content = "";
    expiry = "never";
    visibility = "public";
    tags = "";
    uploadedFiles = [];
    creationResult = null;
    zipMultiple = true;
  }

  // Process uploaded/dropped files
  function processFiles(files, source = "uploaded") {
    // files can be a FileList (from input) or an array of objects { file, path } (from recursive drop)

    let newFiles = [];

    if (source === "dropped_recursive") {
      newFiles = files.map(({ file, path }) => ({
        file,
        id: Math.random().toString(36).substr(2, 9),
        path: path || "",
      }));
    } else {
      newFiles = Array.from(files).map((file) => ({
        file,
        id: Math.random().toString(36).substr(2, 9),
        path: "",
      }));
    }

    uploadedFiles = [...uploadedFiles, ...newFiles];

    // If it's a single file and we don't have a title yet, suggest one
    if (uploadedFiles.length === 1 && !title) {
      title = uploadedFiles[0].file.name.replace(/\.[^/.]+$/, "");
    }

    const action = source.includes("dropped") ? "dropped" : "selected";
    showToast(`${newFiles.length} file(s) ${action}`, "success");
  }

  function removeFile(id) {
    uploadedFiles = uploadedFiles.filter((f) => f.id !== id);
    if (uploadedFiles.length === 0 && title) {
      // Optional: clear title if it was auto-set? keeping it is probably fine.
    }
  }

  // Recursive function to traverse file system entries
  async function traverseFileTree(item, path = "") {
    if (IGNORED_NAMES.includes(item.name)) {
      return [];
    }

    if (item.isFile) {
      return new Promise((resolve) => {
        item.file((file) => {
          // Double check file name for ignore list (though item.name caught dirs)
          if (IGNORED_NAMES.includes(file.name)) {
            resolve([]);
          } else {
            resolve([{ file, path: path + file.name }]);
          }
        });
      });
    } else if (item.isDirectory) {
      const dirReader = item.createReader();
      const entries = await new Promise((resolve) => {
        dirReader.readEntries((entries) => resolve(entries));
      });

      let files = [];
      for (const entry of entries) {
        const children = await traverseFileTree(entry, path + item.name + "/");
        files = [...files, ...children];
      }
      return files;
    }
    return [];
  }

  async function handleSubmit(e) {
    e.preventDefault();

    if (!content.trim() && uploadedFiles.length === 0) {
      showToast("Please enter some content or upload a file", "warning");
      return;
    }

    // Check batch limit if not zipping
    if (uploadedFiles.length > MAX_BATCH_SIZE && !zipMultiple) {
      showToast(
        `Batch creation is limited to ${MAX_BATCH_SIZE} files. Please use the Zip option or reduce the number of files.`,
        "error",
      );
      return;
    }

    isLoading = true;
    let createdRelics = [];
    let errors = [];

    try {
      // 1. Create relic from text content if present
      if (content.trim()) {
        try {
          const contentType =
            syntax !== "auto" ? getContentType(syntax) : "text/plain";
          const fileExtension =
            syntax !== "auto" ? getFileExtension(syntax) : "txt";
          const blob = new Blob([content], { type: contentType });
          const fileName = title || `relic.${fileExtension}`;
          const file = new File([blob], fileName, { type: contentType });

          const response = await createRelic({
            file: file,
            name: title || undefined,
            content_type: contentType,
            language_hint: syntax !== "auto" ? syntax : undefined,
            access_level: visibility,
            expires_in: expiry !== "never" ? expiry : undefined,
            tags: tags.trim() ? tags.split(',').map(t => t.trim()).filter(Boolean) : undefined,
          });
          createdRelics.push(response.data);
        } catch (err) {
          console.error("Error creating text relic:", err);
          errors.push("Text content");
        }
      }

      // 2. Handle uploaded files
      if (uploadedFiles.length > 0) {
        if (uploadedFiles.length > 1 && zipMultiple) {
          // Auto-zip logic
          try {
            const zip = new JSZip();
            uploadedFiles.forEach(({ file, path }) => {
              // Use the preserved path if available, otherwise just filename
              const zipPath = path || file.name;
              zip.file(zipPath, file);
            });

            const zipBlob = await zip.generateAsync({
              type: "blob",
              compression: "DEFLATE",
            });
            const zipName = title
              ? `${title}.zip`
              : uploadedFiles.length > 0
                ? `${uploadedFiles[0].file.name.split(".")[0]}_archive.zip`
                : "archive.zip";
            const zipFile = new File([zipBlob], zipName, {
              type: "application/zip",
            });

            const response = await createRelic({
              file: zipFile,
              name: title || zipName,
              content_type: "application/zip",
              language_hint: "archive",
              access_level: visibility,
              expires_in: expiry !== "never" ? expiry : undefined,
              tags: tags.trim() ? tags.split(',').map(t => t.trim()).filter(Boolean) : undefined,
            });
            createdRelics.push(response.data);
          } catch (err) {
            console.error("Error creating zip relic:", err);
            errors.push("Zip Archive");
          }
        } else {
          // Batch creation logic (existing)
          for (let i = 0; i < uploadedFiles.length; i++) {
            const { file } = uploadedFiles[i];
            try {
              // Determine content type and syntax hint for this specific file
              const ext = file.name.split(".").pop()?.toLowerCase();
              let fileSyntax = "auto";
              let fileContentType = file.type;

              if (ext) {
                const detected = getSyntaxFromExtension(ext);
                if (detected) {
                  fileSyntax = detected;
                  const canonicalMime = getContentType(detected);
                  const typeDef = getFileTypeDefinition(canonicalMime);

                  // Always prefer our detected MIME type for code/text files
                  if (
                    [
                      "code",
                      "text",
                      "markdown",
                      "html",
                      "csv",
                      "json",
                      "xml",
                    ].includes(typeDef.category)
                  ) {
                    fileContentType = canonicalMime;
                  } else if (!fileContentType) {
                    fileContentType = canonicalMime;
                  }
                }
              }
              // If user manually selected a syntax and it's a single file, maybe apply it?
              // But for batch uploads, auto-detect per file is safer.
              // Let's stick to auto-detect for files, or the file's own type.

              // For single file uploads, use the title if provided, otherwise use filename
              const fileName = uploadedFiles.length === 1 && title ? title : file.name;

              const response = await createRelic({
                file: file,
                name: fileName,
                content_type: fileContentType || undefined,
                language_hint: fileSyntax !== "auto" ? fileSyntax : undefined,
                access_level: visibility,
                expires_in: expiry !== "never" ? expiry : undefined,
                tags: tags.trim() ? tags.split(',').map(t => t.trim()).filter(Boolean) : undefined,
              });
              createdRelics.push(response.data);
            } catch (err) {
              console.error(`Error creating relic for ${file.name}:`, err);
              errors.push(file.name);
            }
          }
        }
      }

      if (createdRelics.length > 0) {
        if (errors.length > 0) {
          showToast(
            `Created ${createdRelics.length} relics, but failed: ${errors.join(", ")}`,
            "warning",
          );
        } else {
          showToast(
            `Successfully created ${createdRelics.length} relic(s)!`,
            "success",
          );
        }

        // If only one relic was created, redirect to it directly (classic behavior)
        if (createdRelics.length === 1 && errors.length === 0) {
          window.location.href = `/${createdRelics[0].id}`;
        } else {
          // Show summary view
          creationResult = { success: createdRelics, errors };
          // Clear form data but keep creationResult
          title = "";
          content = "";
          tags = "";
          uploadedFiles = [];
        }
      } else if (errors.length > 0) {
        showToast(`Failed to create relics: ${errors.join(", ")}`, "error");
      }
    } catch (error) {
      showToast(error.message || "Failed to create relic", "error");
      console.error("Error creating relic:", error);
    } finally {
      isLoading = false;
    }
  }

  function handleFileUpload(e) {
    const files = e.target.files;
    if (files.length > 0) {
      processFiles(files, "uploaded");
    }
    // Reset input so same files can be selected again if needed (though we clear form on submit)
    e.target.value = "";
  }

  function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add("border-blue-500", "bg-blue-50");
  }

  function handleDragLeave(e) {
    e.preventDefault();
    e.currentTarget.classList.remove("border-blue-500", "bg-blue-50");
  }

  async function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove("border-blue-500", "bg-blue-50");

    const dt = e.dataTransfer;
    if (!dt) return;

    if (dt.items && dt.items.length > 0) {
      // Important: Collect all items/entries synchronously because dt.items
      // can be cleared once we start awaiting in the loop.
      const entriesToProcess = [];
      for (let i = 0; i < dt.items.length; i++) {
        const item = dt.items[i];
        if (item.webkitGetAsEntry) {
          const entry = item.webkitGetAsEntry();
          if (entry) entriesToProcess.push({ entry });
        } else if (item.kind === "file") {
          const file = item.getAsFile();
          if (file) entriesToProcess.push({ file });
        }
      }

      let allFiles = [];
      for (const { entry, file } of entriesToProcess) {
        if (entry) {
          const files = await traverseFileTree(entry);
          allFiles = [...allFiles, ...files];
        } else if (file) {
          allFiles.push({ file, path: file.name });
        }
      }

      if (allFiles.length > 0) {
        processFiles(allFiles, "dropped_recursive");
      }
    } else {
      // Fallback for older browsers
      const files = dt.files;
      if (files && files.length > 0) {
        processFiles(files, "dropped");
      }
    }
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
      showToast("Link copied to clipboard", "success");
    });
  }
</script>

<div class="maas-card mb-8">
  <div class="px-4 py-3 border-b border-[#ccc] bg-[#f5f5f5] flex items-center justify-between">
    <h2 class="text-sm font-bold text-gray-800 flex items-center uppercase tracking-wide">
      {#if creationResult}
        <i class="fas fa-check-circle text-green-600 mr-2"></i>
        Relics Created
      {:else}
        <i class="fas fa-plus-circle text-blue-600 mr-2"></i>
        Create Relic
      {/if}
    </h2>
    {#if !creationResult && activeTab === "upload"}
      <div class="flex items-center gap-4">
        <div class="text-xs text-gray-500 font-mono">
          {#if uploadedFiles.length > 0}
            {uploadedFiles.length} file(s) attached
          {:else}
            {content.length} characters
          {/if}
        </div>
      </div>
    {/if}
  </div>

    {#if !creationResult}
      <!-- Tab Navigation -->
      <div class="border-b border-[#ccc] bg-gray-50">
        <nav class="flex px-4">
          <button
            on:click={() => (activeTab = "upload")}
            class="px-4 py-2 text-sm font-medium border-b-2 transition-colors {activeTab ===
            'upload'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'}"
          >
            <i class="fas fa-upload mr-2"></i>
            Upload
          </button>
          <button
            on:click={() => (activeTab = "cli")}
            class="px-4 py-2 text-sm font-medium border-b-2 transition-colors {activeTab ===
            'cli'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'}"
          >
            <i class="fas fa-terminal mr-2"></i>
            CLI
          </button>
          <button
            on:click={() => (activeTab = "curl")}
            class="px-4 py-2 text-sm font-medium border-b-2 transition-colors {activeTab ===
            'curl'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'}"
          >
            <i class="fas fa-code mr-2"></i>
            Curl
          </button>
        </nav>
      </div>
    {/if}

    <div class="p-6">
      {#if creationResult}
        <div class="space-y-6">
          <div class="bg-green-50 border border-green-200 p-4 rounded-sm">
            <div class="flex">
              <div class="flex-shrink-0">
                <i class="fas fa-check-circle text-green-400"></i>
              </div>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-green-800">
                  Successfully created {creationResult.success.length} relic(s)
                </h3>
                {#if creationResult.errors.length > 0}
                  <div class="mt-2 text-sm text-red-700">
                    <p>Failed to create: {creationResult.errors.join(", ")}</p>
                  </div>
                {/if}
              </div>
            </div>
          </div>

          <div class="border border-[#ccc] divide-y divide-[#ccc]">
            {#each creationResult.success as relic}
              <div
                class="p-4 flex items-center justify-between hover:bg-gray-50 bg-white"
              >
                <div class="flex items-center space-x-3 truncate">
                  <i class="fas fa-file-code text-gray-400"></i>
                  <div class="truncate">
                    <a
                      href="/{relic.id}"
                      class="text-sm font-medium text-blue-600 hover:text-blue-800 hover:underline block truncate"
                    >
                      {relic.name || relic.id}
                    </a>
                    <div class="text-xs text-gray-500 flex items-center gap-2">
                      <span>{formatBytes(relic.size_bytes)}</span>
                      <span>&bull;</span>
                      <span class="font-mono">{relic.id}</span>
                    </div>
                  </div>
                </div>
                <div class="flex items-center gap-2 ml-4">
                  <button
                    on:click={() =>
                      copyToClipboard(`${window.location.origin}/${relic.id}`)}
                    class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-sm"
                    title="Copy Link"
                  >
                    <i class="fas fa-link"></i>
                  </button>
                  <a
                    href="/{relic.id}"
                    class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-sm"
                    title="View Relic"
                  >
                    <i class="fas fa-external-link-alt"></i>
                  </a>
                </div>
              </div>
            {/each}
          </div>

          <div class="flex justify-end pt-4">
            <button
              on:click={resetForm}
              class="maas-btn-primary px-6 py-2 text-sm shadow-sm"
            >
              <i class="fas fa-plus mr-1"></i>
              Create More
            </button>
          </div>
        </div>
      {:else if activeTab === "upload"}
        <form on:submit={handleSubmit} class="space-y-6">

        <fieldset class="border border-[#ccc] p-4 bg-white">
          <legend class="text-xs font-bold text-blue-600 uppercase px-1">General Properties</legend>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label
                for="title"
                class="block text-sm font-bold text-gray-700 mb-1"
                >Name</label
              >
              <input
                type="text"
                id="title"
                bind:value={title}
                placeholder="e.g. Nginx Configuration"
                class="w-full maas-input"
              />
              <p class="text-[11px] text-gray-500 mt-1">
                A descriptive name for this relic
              </p>
            </div>

            <div>
              <label
                for="syntax"
                class="block text-sm font-bold text-gray-700 mb-1">Content Type</label
              >
              <div class="w-full">
                <Select
                  items={syntaxOptions}
                  bind:value={syntaxValue}
                  placeholder="Auto-detect"
                  searchable={true}
                  clearable={false}
                  showChevron={true}
                  --border="1px solid #ccc"
                  --border-radius="0"
                  --border-focused="1px solid #2196f3"
                  --border-hover="1px solid #bbb"
                  --padding="0.2rem 0.5rem"
                  --font-size="0.85rem"
                  --height="30px"
                  --item-padding="0.25rem 0.5rem"
                  --item-height="auto"
                  --item-line-height="1.25"
                  --background="white"
                  --list-background="white"
                  --list-border="1px solid #ccc"
                  --list-border-radius="0"
                  --list-shadow="0 2px 4px rgba(0,0,0,0.1)"
                  --input-color="#333"
                  --item-color="#333"
                  --item-hover-bg="#e3f2fd"
                  --item-hover-color="#333"
                  --item-is-active-bg="#2196f3"
                  --item-is-active-color="white"
                  --internal-padding="0"
                  --chevron-height="16px"
                  --chevron-width="16px"
                  --chevron-color="#666"
                />
              </div>
              <p class="text-[11px] text-gray-500 mt-1">
                Applies to text content only.
              </p>
            </div>

             <div>
              <label
                for="tags"
                class="block text-sm font-bold text-gray-700 mb-1"
                >Tags</label
              >
              <input
                type="text"
                id="tags"
                bind:value={tags}
                placeholder="e.g. config, nginx (comma separated)"
                class="w-full maas-input"
              />
            </div>
          </div>
        </fieldset>

        <fieldset class="border border-[#ccc] p-4 bg-white">
          <legend class="text-xs font-bold text-blue-600 uppercase px-1">Access & Lifecycle</legend>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label
                for="visibility"
                class="block text-sm font-bold text-gray-700 mb-1"
                >Visibility</label
              >
              <select
                id="visibility"
                bind:value={visibility}
                class="w-full maas-input"
              >
                <option value="public">Public</option>
                <option value="private">Private</option>
              </select>
              <p class="text-[11px] text-gray-500 mt-1">
                {#if visibility === "public"}Visible in 'Recent Relics'
                {:else}Hidden from lists, accessible via direct link only
                {/if}
              </p>
            </div>

            <div>
              <label
                for="expiry"
                class="block text-sm font-bold text-gray-700 mb-1"
                >Expiration</label
              >
              <select
                id="expiry"
                bind:value={expiry}
                class="w-full maas-input"
              >
                <option value="never">Never</option>
                <option value="10m">10 Minutes</option>
                <option value="1h">1 Hour</option>
                <option value="12h">12 Hours</option>
                <option value="24h">24 Hours</option>
                <option value="3d">3 Days</option>
                <option value="7d">7 Days</option>
                <option value="30d">30 Days</option>
                <option value="1y">1 Year</option>
              </select>
            </div>
          </div>
        </fieldset>


          <div>
            <div class="flex justify-between items-center mb-1">
                 <label
                  for="content"
                  class="block text-sm font-bold text-gray-700"
                  >Content</label
                >
                <div class="flex items-center gap-2">
                    <button
                      type="button"
                      on:click={() => fileInput?.click()}
                      class="text-xs text-blue-600 hover:underline font-bold"
                    >
                      <i class="fas fa-upload mr-1"></i> Upload Files
                    </button>
                    <input
                      type="file"
                      bind:this={fileInput}
                      on:change={handleFileUpload}
                      class="hidden"
                      multiple
                    />
                </div>
            </div>

            <div class="relative">
              <textarea
                id="content"
                bind:value={content}
                on:dragover={handleDragOver}
                on:dragleave={handleDragLeave}
                on:drop={handleDrop}
                rows="16"
                class="w-full h-64 font-mono text-sm p-4 maas-input resize-y border border-[#ccc]"
                placeholder="// Paste code here or drag & drop files..."
              ></textarea>
            </div>

            <!-- Uploaded Files List -->
            {#if uploadedFiles.length > 0}
              <div class="mt-4 space-y-2">
                <div class="flex items-center justify-between">
                  <h3 class="text-sm font-bold text-gray-700 uppercase">
                    Attached Files ({uploadedFiles.length})
                  </h3>
                  {#if uploadedFiles.length > 1}
                    <label
                      class="flex items-center space-x-2 text-sm text-gray-600 cursor-pointer select-none"
                    >
                      <input
                        type="checkbox"
                        bind:checked={zipMultiple}
                        class="rounded-sm border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                      />
                      <span>Zip multiple files</span>
                    </label>
                  {/if}
                </div>
                <div
                  class="bg-gray-50 border border-[#ccc] divide-y divide-[#ccc] max-h-48 overflow-y-auto"
                >
                  {#each uploadedFiles as { file, id }}
                    <div class="flex items-center justify-between p-2 text-sm bg-white hover:bg-gray-50">
                      <div class="flex items-center truncate">
                        <i class="fas fa-file text-gray-400 mr-2"></i>
                        <span
                          class="font-medium text-gray-700 truncate max-w-xs"
                          >{file.name}</span
                        >
                        <span class="text-gray-500 ml-2 text-xs"
                          >({formatBytes(file.size)})</span
                        >
                      </div>
                      <button
                        type="button"
                        on:click={() => removeFile(id)}
                        class="text-red-500 hover:text-red-700 p-1 hover:bg-red-50 transition-colors"
                        title="Remove file"
                      >
                        <i class="fas fa-times"></i>
                      </button>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
          </div>


          <div class="flex justify-end pt-4 border-t border-[#ccc]">
            <button
              type="submit"
              disabled={isLoading}
              class="maas-btn-primary px-6 py-2 text-sm shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {#if isLoading}
                <i class="fas fa-spinner fa-spin mr-1"></i>
                {#if uploadedFiles.length > 1 && zipMultiple}
                  Creating Zip Archive...
                {:else}
                  Creating {uploadedFiles.length + (content.trim() ? 1 : 0)} Relic(s)...
                {/if}
              {:else}
                <i class="fas fa-plus mr-1"></i>
                {#if uploadedFiles.length > 1 && zipMultiple}
                  Create Zip Archive
                {:else}
                  Create Relic(s)
                {/if}
              {/if}
            </button>
          </div>
        </form>
      {:else if activeTab === "cli"}
        <!-- CLI Tab -->
        <div class="space-y-6">
          <div>
            <h3 class="text-sm font-bold text-gray-800 mb-2 uppercase border-b border-[#ccc] pb-1">
              CLI Installation
            </h3>
            <p class="text-sm text-gray-600 mb-3">
              Install the Relic CLI with a single command:
            </p>
            <div
              class="bg-[#f5f5f5] border border-[#ccc] p-3 text-gray-900 text-xs font-mono overflow-x-auto"
            >
              <pre>curl -sSL {serverUrl}/install.sh | bash</pre>
            </div>
          </div>

          <div>
            <h3 class="text-sm font-bold text-gray-800 mb-2 uppercase border-b border-[#ccc] pb-1">
              Quick Start
            </h3>
            <div
              class="bg-[#f5f5f5] border border-[#ccc] p-3 text-gray-900 text-xs font-mono overflow-x-auto"
            >
              <pre># Upload a file
relic script.py

# Upload from stdin
echo "Hello World" | relic

# Upload with options
relic file.txt --name "My File" --access-level public --expires-in 24h

# List your relics
relic list

# Download a relic
relic get &lt;relic-id&gt;</pre>
            </div>
          </div>

          <div>
            <h3 class="text-sm font-bold text-gray-800 mb-2 uppercase border-b border-[#ccc] pb-1">
              Configuration
            </h3>
            <p class="text-sm text-gray-600 mb-2">
              The CLI automatically configures itself to use <code
                class="bg-gray-200 px-2 py-0.5 rounded-sm text-xs font-mono"
                >{serverUrl}</code
              > as the server.
            </p>
            <p class="text-sm text-gray-600 mb-3">
              Configuration file: <code
                class="bg-gray-200 px-2 py-0.5 rounded-sm text-xs font-mono"
                >~/.relic/config</code
              >
            </p>
            <div
              class="bg-[#f5f5f5] border border-[#ccc] p-3 text-gray-900 text-xs font-mono overflow-x-auto"
            >
              <pre># View configuration
relic config --list

# Change server
relic config core.server {serverUrl}</pre>
            </div>
          </div>
        </div>
      {:else if activeTab === "curl"}
        <!-- Curl Tab -->
        <div class="space-y-6">
          <div>
            <h3 class="text-sm font-bold text-gray-800 mb-2 uppercase border-b border-[#ccc] pb-1">
              Upload from stdin
            </h3>
            <div
              class="bg-[#f5f5f5] border border-[#ccc] p-3 text-gray-900 text-xs font-mono overflow-x-auto"
            >
              <pre>echo "Hello World" | curl -X POST {serverUrl}/api/v1/relics \
  -F "file=@-" \
  -F "name=greeting"</pre>
            </div>
          </div>

          <div>
            <h3 class="text-sm font-bold text-gray-800 mb-2 uppercase border-b border-[#ccc] pb-1">
              Upload a file
            </h3>
            <div
              class="bg-[#f5f5f5] border border-[#ccc] p-3 text-gray-900 text-xs font-mono overflow-x-auto"
            >
              <pre>curl -X POST {serverUrl}/api/v1/relics \
  -F "file=@script.py" \
  -F "name=My Script" \
  -F "access_level=public" \
  -F "expires_in=24h"</pre>
            </div>
          </div>

          <div>
            <h3 class="text-sm font-bold text-gray-800 mb-2 uppercase border-b border-[#ccc] pb-1">
              Pipe command output
            </h3>
            <div
              class="bg-[#f5f5f5] border border-[#ccc] p-3 text-gray-900 text-xs font-mono overflow-x-auto"
            >
              <pre>ps aux | curl -X POST {serverUrl}/api/v1/relics \
  -F "file=@-" \
  -F "name=processes.txt"</pre>
            </div>
          </div>

          <div class="p-3 bg-blue-50 border border-blue-200 text-blue-800 text-sm">
            <p>
              <strong>Tip:</strong> Use the <code
                class="bg-white px-2 py-0.5 rounded-sm text-xs font-mono border border-blue-300"
                >X-Client-Key</code
              > header to authenticate and associate relics with your account.
            </p>
          </div>
        </div>
      {/if}
    </div>
  </div>

<style>
  /* Component-specific styles only - global svelte-select styles are in app.css */
</style>
