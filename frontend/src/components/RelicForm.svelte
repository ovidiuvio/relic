<script>
  import { createRelic } from "../services/api";
  import { showToast } from "../stores/toastStore";
  import Select from "svelte-select";
  import {
    getContentType,
    getFileExtension,
    getSyntaxFromExtension,
    getAvailableSyntaxOptions,
    getFileTypeDefinition,
  } from "../services/typeUtils";

  const syntaxOptions = getAvailableSyntaxOptions();

  let title = "";
  let syntax = "auto";
  let syntaxValue = { value: "auto", label: "Auto-detect" };
  let content = "";
  let expiry = "never";
  let visibility = "public";
  let isLoading = false;
  let fileInput;
  let uploadedFiles = []; // Array of { file, id }
  let creationResult = null; // { success: [], errors: [] }

  // Update syntax when syntaxValue changes
  $: syntax = syntaxValue?.value || "auto";

  // Helper function to find option by value
  function findOptionByValue(options, value) {
    return options.find((option) => option.value === value) || null;
  }

  // Format bytes to human readable string
  function formatBytes(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  }

  // Reset form to initial state
  function resetForm() {
    title = "";
    syntax = "auto";
    syntaxValue = { value: "auto", label: "Auto-detect" };
    content = "";
    expiry = "never";
    visibility = "public";
    uploadedFiles = [];
    creationResult = null;
  }

  // Process uploaded/dropped files
  function processFiles(files, source = "uploaded") {
    const newFiles = Array.from(files).map((file) => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
    }));

    uploadedFiles = [...uploadedFiles, ...newFiles];

    // If it's a single file and we don't have a title yet, suggest one
    if (uploadedFiles.length === 1 && !title) {
      title = uploadedFiles[0].file.name.replace(/\.[^/.]+$/, "");
    }

    const action = source === "dropped" ? "dropped" : "selected";
    showToast(`${newFiles.length} file(s) ${action}`, "success");
  }

  function removeFile(id) {
    uploadedFiles = uploadedFiles.filter((f) => f.id !== id);
    if (uploadedFiles.length === 0 && title) {
      // Optional: clear title if it was auto-set? keeping it is probably fine.
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();

    if (!content.trim() && uploadedFiles.length === 0) {
      showToast("Please enter some content or upload a file", "warning");
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
          });
          createdRelics.push(response.data);
        } catch (err) {
          console.error("Error creating text relic:", err);
          errors.push("Text content");
        }
      }

      // 2. Create relics from uploaded files
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
              // This fixes issues where browser detects .ts as video/mp2t or .js as text/plain
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
          // Let's stick to auto-detect for batch files unless it's a single file and user overrode it?
          // Simpler: Just use auto-detect for files, or the file's own type.

          const response = await createRelic({
            file: file,
            name: file.name, // Use filename as title for batch uploads
            content_type: fileContentType || undefined,
            language_hint: fileSyntax !== "auto" ? fileSyntax : undefined,
            access_level: visibility,
            expires_in: expiry !== "never" ? expiry : undefined,
          });
          createdRelics.push(response.data);
        } catch (err) {
          console.error(`Error creating relic for ${file.name}:`, err);
          errors.push(file.name);
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

  function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove("border-blue-500", "bg-blue-50");

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processFiles(files, "dropped");
    }
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
      showToast("Link copied to clipboard", "success");
    });
  }
</script>

<div class="mb-8">
  <div class="bg-white shadow-sm rounded-lg border border-gray-200">
    <div
      class="px-6 py-4 border-b border-gray-200 flex items-center justify-between"
    >
      <h2 class="text-lg font-semibold text-gray-900 flex items-center">
        {#if creationResult}
          <i class="fas fa-check-circle text-green-600 mr-2"></i>
          Relics Created Successfully
        {:else}
          <i class="fas fa-plus text-blue-600 mr-2"></i>
          Create New Relic
        {/if}
      </h2>
      {#if !creationResult}
        <div class="flex items-center gap-4">
          <div class="text-xs text-gray-500">
            {#if uploadedFiles.length > 0}
              {uploadedFiles.length} file(s) attached
            {:else}
              {content.length} characters
            {/if}
          </div>
        </div>
      {/if}
    </div>

    <div class="p-6">
      {#if creationResult}
        <div class="space-y-6">
          <div class="bg-green-50 border border-green-200 rounded-md p-4">
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

          <div class="border rounded-md divide-y divide-gray-200">
            {#each creationResult.success as relic}
              <div
                class="p-4 flex items-center justify-between hover:bg-gray-50"
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
                    class="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
                    title="Copy Link"
                  >
                    <i class="fas fa-link"></i>
                  </button>
                  <a
                    href="/{relic.id}"
                    class="p-2 text-gray-400 hover:text-blue-600 rounded-full hover:bg-blue-50"
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
              class="maas-btn-primary px-6 py-2 text-sm rounded font-medium shadow-sm"
            >
              <i class="fas fa-plus mr-1"></i>
              Create More
            </button>
          </div>
        </div>
      {:else}
        <form on:submit={handleSubmit} class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label
                for="title"
                class="block text-sm font-medium text-gray-700 mb-1"
                >Title</label
              >
              <input
                type="text"
                id="title"
                bind:value={title}
                placeholder="e.g. Nginx Configuration"
                class="w-full px-3 py-2 text-sm maas-input"
              />
              <p class="text-xs text-gray-500 mt-1">
                A descriptive name for this relic (used for text content)
              </p>
            </div>

            <div>
              <label
                for="syntax"
                class="block text-sm font-medium text-gray-700 mb-1">Type</label
              >
              <div class="w-full">
                <Select
                  items={syntaxOptions}
                  bind:value={syntaxValue}
                  placeholder="Search or select language..."
                  searchable={true}
                  clearable={false}
                  showChevron={true}
                  --border="1px solid #AEA79F"
                  --border-radius="2px"
                  --border-focused="1px solid #E95420"
                  --border-hover="1px solid #AEA79F"
                  --padding="0.15rem 0.5rem"
                  --font-size="0.875rem"
                  --height="24px"
                  --item-padding="0.25rem 0.5rem"
                  --item-height="auto"
                  --item-line-height="1.25"
                  --background="white"
                  --list-background="#f3f4f5"
                  --list-border="1px solid #AEA79F"
                  --list-border-radius="6px"
                  --list-shadow="0 4px 6px -1px rgb(0 0 0 / 0.1)"
                  --input-color="rgb(17 24 39)"
                  --item-color="rgb(17 24 39)"
                  --item-hover-bg="#bcdff1"
                  --item-hover-color="rgb(17 24 39)"
                  --item-is-active-bg="#f3f4f5"
                  --item-is-active-color="rgb(17 24 39)"
                  --internal-padding="0"
                  --chevron-height="20px"
                  --chevron-width="20px"
                  --chevron-color="rgb(107, 114, 128)"
                />
              </div>
              <p class="text-xs text-gray-500 mt-1">
                Applies to text content only. Files are auto-detected.
              </p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label
                for="visibility"
                class="block text-sm font-medium text-gray-700 mb-1"
                >Visibility</label
              >
              <select
                id="visibility"
                bind:value={visibility}
                class="w-full px-3 py-2 text-sm maas-input bg-white"
              >
                <option value="public">Public</option>
                <option value="private">Private</option>
              </select>
              <p class="text-xs text-gray-500 mt-1">
                {#if visibility === "public"}Anyone can view this relic
                {:else}Private relic - only accessible via direct URL
                {/if}
              </p>
            </div>

            <div>
              <label
                for="expiry"
                class="block text-sm font-medium text-gray-700 mb-1"
                >Expires</label
              >
              <select
                id="expiry"
                bind:value={expiry}
                class="w-full px-3 py-2 text-sm maas-input bg-white"
              >
                <option value="never">Never</option>
                <option value="1h">1 Hour</option>
                <option value="24h">24 Hours</option>
                <option value="7d">7 Days</option>
                <option value="30d">30 Days</option>
              </select>
            </div>
          </div>

          <div>
            <label
              for="content"
              class="block text-sm font-medium text-gray-700 mb-1"
              >Content</label
            >
            <div class="relative">
              <textarea
                id="content"
                bind:value={content}
                on:dragover={handleDragOver}
                on:dragleave={handleDragLeave}
                on:drop={handleDrop}
                rows="16"
                class="w-full h-64 font-mono text-sm p-4 maas-input resize-y focus:shadow-none border border-[#dfdcd9] transition-colors"
                placeholder="// Paste your code here or drop files..."
              ></textarea>
            </div>

            <!-- Uploaded Files List -->
            {#if uploadedFiles.length > 0}
              <div class="mt-4 space-y-2">
                <h3 class="text-sm font-medium text-gray-700">
                  Attached Files ({uploadedFiles.length})
                </h3>
                <div
                  class="bg-gray-50 rounded border border-gray-200 divide-y divide-gray-200 max-h-48 overflow-y-auto"
                >
                  {#each uploadedFiles as { file, id }}
                    <div class="flex items-center justify-between p-2 text-sm">
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
                        class="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors"
                        title="Remove file"
                      >
                        <i class="fas fa-times"></i>
                      </button>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <div class="flex items-center gap-4 text-sm text-gray-500 mt-2">
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  on:click={() => fileInput?.click()}
                  class="maas-btn-secondary px-3 py-1 text-xs rounded font-medium"
                >
                  <i class="fas fa-upload mr-1"></i>
                  Add Files
                </button>
                <input
                  type="file"
                  bind:this={fileInput}
                  on:change={handleFileUpload}
                  class="hidden"
                  multiple
                />
              </div>
              <span class="text-xs">or drag & drop files</span>
            </div>
          </div>

          <div class="flex justify-end pt-4 border-t border-gray-200">
            <button
              type="submit"
              disabled={isLoading}
              class="maas-btn-primary px-6 py-2 text-sm rounded font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {#if isLoading}
                <i class="fas fa-spinner fa-spin mr-1"></i>
                Creating {uploadedFiles.length + (content.trim() ? 1 : 0)} Relic(s)...
              {:else}
                <i class="fas fa-plus mr-1"></i>
                Create Relic(s)
              {/if}
            </button>
          </div>
        </form>
      {/if}
    </div>
  </div>
</div>

<style>
  /* Component-specific styles only - global svelte-select styles are in app.css */
</style>
