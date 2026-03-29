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
  import { getFilesFromDrop } from "../services/utils/fileProcessing";
  import MonacoEditor from "./MonacoEditor.svelte";
  import { createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();

  export let spaceId = null;

  const syntaxOptions = getAvailableSyntaxOptions();

  let activeTab = "editor"; // editor, upload, cli, curl, api
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

  // Editor preferences
  let isFullWidth = (() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("relic_form_fullwidth");
      return saved === "true";
    }
    return false;
  })();

  let showSyntaxHighlighting = (() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("relic_form_syntax_highlighting");
      return saved === "false" ? false : true;
    }
    return true;
  })();

  let showLineNumbers = (() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("relic_form_line_numbers");
      return saved === "false" ? false : true;
    }
    return true;
  })();

  let fontSize = (() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("relic_form_font_size");
      return saved ? parseInt(saved, 10) : 13;
    }
    return 13;
  })();

  // Save editor preferences
  $: if (typeof window !== "undefined") {
    localStorage.setItem("relic_form_fullwidth", isFullWidth.toString());
  }
  $: if (typeof window !== "undefined") {
    localStorage.setItem("relic_form_syntax_highlighting", showSyntaxHighlighting.toString());
  }
  $: if (typeof window !== "undefined") {
    localStorage.setItem("relic_form_line_numbers", showLineNumbers.toString());
  }
  $: if (typeof window !== "undefined") {
    localStorage.setItem("relic_form_font_size", fontSize.toString());
  }

  // Sync fullWidth to parent
  $: dispatch("fullwidth-toggle", { isFullWidth });

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
    activeTab = "upload"; // Auto-switch to files tab when files are added

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


  async function handleSubmit(e) {
    e.preventDefault();

    if (!content.trim() && uploadedFiles.length === 0) {
      showToast("Please enter some content or upload a file", "warning");
      return;
    }

    // Check batch limit if not zipping
    const MAX_BATCH_SIZE = 100;
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
            space_id: spaceId || undefined,
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
              space_id: spaceId || undefined,
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
                space_id: spaceId || undefined,
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

    const droppedFiles = await getFilesFromDrop(e.dataTransfer);
    if (droppedFiles.length > 0) {
      processFiles(droppedFiles, "dropped_recursive");
    }
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
      showToast("Link copied to clipboard", "success");
    });
  }
</script>

<div class="mb-8 {isFullWidth ? 'max-w-none' : ''}">
  <div class="bg-white shadow-sm border border-gray-200 overflow-hidden {isFullWidth ? 'rounded-none border-x-0' : 'rounded-lg'}">
    <div
      class="px-6 h-14 border-b border-gray-200 flex items-center justify-between"
    >
      <div class="flex items-center h-full">
        <h2 class="text-lg font-semibold text-gray-900 flex items-center mr-8">
          {#if creationResult}
            <i class="fas fa-check-circle text-green-600 mr-2 text-base"></i>
            Relics Created Successfully
          {:else}
            <i class="fas fa-plus text-blue-600 mr-2 text-base"></i>
            Create New Relic
          {/if}
        </h2>
 
        {#if !creationResult}
          <!-- Tab Navigation -->
          <nav class="flex -mb-px space-x-2 h-full">
            <button
              on:click={() => (activeTab = "editor")}
              class="px-3 h-full text-sm font-medium border-b-2 transition-colors {activeTab ===
              'editor'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            >
              <i class="fas fa-edit mr-1.5 opacity-70"></i>
              Editor
            </button>
            <button
              on:click={() => (activeTab = "upload")}
              class="px-3 h-full text-sm font-medium border-b-2 transition-colors {activeTab ===
              'upload'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            >
              <i class="fas fa-upload mr-1.5 opacity-70"></i>
              Files
            </button>
            <button
              on:click={() => (activeTab = "cli")}
              class="px-3 h-full text-sm font-medium border-b-2 transition-colors {activeTab ===
              'cli'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            >
              <i class="fas fa-terminal mr-1.5 opacity-70"></i>
              CLI
            </button>
            <button
              on:click={() => (activeTab = "curl")}
              class="px-3 h-full text-sm font-medium border-b-2 transition-colors {activeTab ===
              'curl'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
            >
              <i class="fas fa-code mr-1.5 opacity-70"></i>
              Curl
            </button>
          </nav>
        {/if}
      </div>

      {#if !creationResult}
        <div class="flex items-center gap-4">
          <div class="text-[10px] uppercase tracking-wider font-semibold text-gray-400">
            {#if activeTab === "upload" && uploadedFiles.length > 0}
              {uploadedFiles.length} file(s) attached
            {:else if activeTab === "editor"}
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
      {:else if activeTab === "upload" || activeTab === "editor"}
        <form on:submit={handleSubmit} class="space-y-6">
          <div class={activeTab === 'editor' ? "grid grid-cols-1 md:grid-cols-2 gap-6" : "w-full"}>
            <div>
              <label for="title" class="block text-sm font-medium text-gray-700 mb-1">Title</label>
              <input
                type="text"
                id="title"
                bind:value={title}
                placeholder={activeTab === 'editor' ? "e.g. Nginx Configuration" : "Archive name (optional)"}
                class="w-full px-3 py-2 text-sm maas-input"
              />
              <p class="text-xs text-gray-500 mt-1">
                {#if activeTab === 'editor'}A descriptive name for this relic{:else}Optional title for your archive{/if}
              </p>
            </div>

            {#if activeTab === 'editor'}
              <div>
                <label for="syntax" class="block text-sm font-medium text-gray-700 mb-1">Type</label>
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
                <p class="text-xs text-gray-500 mt-1">Syntax highlighting for the editor</p>
              </div>
            {/if}
          </div>

          {#if activeTab === 'editor'}
            <div>
              <div class="flex items-center justify-between mb-1">
                <label for="content" class="block text-sm font-medium text-gray-700">Content</label>
                
                <div class="flex items-center gap-2">
                  <!-- Full-width Toggle -->
                  <button
                    type="button"
                    on:click={() => isFullWidth = !isFullWidth}
                    class="px-2 py-1 rounded text-xs font-medium transition-colors {isFullWidth ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
                    title={isFullWidth ? "Normal width" : "Full width"}
                  >
                    <i class="fas {isFullWidth ? 'fa-compress' : 'fa-expand'}"></i>
                  </button>

                  <!-- Editor Controls -->
                  <div class="flex items-center gap-1 border-l border-gray-300 pl-2">
                    <button
                      type="button"
                      on:click={() => showSyntaxHighlighting = !showSyntaxHighlighting}
                      class="px-2 py-1 rounded text-xs font-medium transition-colors {showSyntaxHighlighting ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
                      title="Toggle syntax highlighting"
                    >
                      <i class="fas fa-palette text-xs"></i>
                    </button>
                    <button
                      type="button"
                      on:click={() => showLineNumbers = !showLineNumbers}
                      class="px-2 py-1 rounded text-xs font-medium transition-colors {showLineNumbers ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}"
                      title="Toggle line numbers"
                    >
                      <i class="fas fa-list-ol text-xs"></i>
                    </button>

                    <!-- Font Size Combo Box -->
                    <div class="flex items-center gap-2 border-l border-gray-300 pl-2 ml-1">
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
                                fontSize = num
                              }
                            }
                          } else {
                            fontSize = parseInt(val, 10)
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
                </div>
              </div>

              <div 
                class="relative border border-[#dfdcd9] overflow-hidden group transition-colors resize-y h-[600px] min-h-[200px]"
                on:dragover={handleDragOver}
                on:dragleave={handleDragLeave}
                on:drop={handleDrop}
                role="region"
                aria-label="Code editor"
              >
                <MonacoEditor
                  value={content}
                  language={syntax === 'auto' ? 'plaintext' : syntax}
                  readOnly={false}
                  height="100%"
                  showSyntaxHighlighting={showSyntaxHighlighting}
                  showLineNumbers={showLineNumbers}
                  fontSize={fontSize}
                  darkMode={false}
                  showComments={false}
                  on:change={(e) => content = e.detail}
                  noWrapper={true}
                />
              </div>
            </div>
          {:else}
            <!-- Files Tab Content -->
            <div 
              class="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center transition-colors hover:border-blue-400 hover:bg-blue-50/30 cursor-pointer"
              on:dragover={handleDragOver}
              on:dragleave={handleDragLeave}
              on:drop={handleDrop}
              on:click={() => fileInput?.click()}
              on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && fileInput?.click()}
              role="button"
              tabindex="0"
            >
              <input type="file" bind:this={fileInput} on:change={handleFileUpload} class="hidden" multiple />
              <div class="mb-4">
                <i class="fas fa-cloud-upload-alt text-4xl text-gray-400"></i>
              </div>
              <p class="text-lg font-medium text-gray-700">Click or drag files here to upload</p>
              <p class="text-sm text-gray-500 mt-1">Add scripts, configs, logs, or any other files</p>
            </div>

            <!-- Uploaded Files List -->
            {#if uploadedFiles.length > 0}
              <div class="mt-6 space-y-3">
                <div class="flex items-center justify-between">
                  <h3 class="text-sm font-semibold text-gray-900">
                    Selected Files ({uploadedFiles.length})
                  </h3>
                  {#if uploadedFiles.length > 1}
                    <label class="flex items-center space-x-2 text-sm text-gray-600 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        bind:checked={zipMultiple}
                        class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                      />
                      <span>Zip multiple files</span>
                    </label>
                  {/if}
                </div>
                <div class="bg-gray-50 rounded-lg border border-gray-200 divide-y divide-gray-200 max-h-64 overflow-y-auto shadow-inner">
                  {#each uploadedFiles as { file, id }}
                    <div class="flex items-center justify-between p-3 text-sm hover:bg-white transition-colors">
                      <div class="flex items-center truncate">
                        <i class="fas {file.type.includes('image') ? 'fa-file-image' : 'fa-file-alt'} text-gray-400 mr-3"></i>
                        <span class="font-medium text-gray-700 truncate max-w-sm">{file.name}</span>
                        <span class="text-gray-500 ml-2 text-xs">({formatBytes(file.size)})</span>
                      </div>
                      <button
                        type="button"
                        on:click|stopPropagation={() => removeFile(id)}
                        class="text-gray-400 hover:text-red-500 p-1.5 rounded-full hover:bg-red-50 transition-all"
                        title="Remove file"
                      >
                        <i class="fas fa-times"></i>
                      </button>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
          {/if}

          <!-- Common Tags Field -->
          <div class="mt-6">
            <label for="tags" class="block text-sm font-medium text-gray-700 mb-1">Tags</label>
            <input
              type="text"
              id="tags"
              bind:value={tags}
              placeholder="e.g. config, nginx, production (comma separated)"
              class="w-full px-3 py-2 text-sm maas-input"
            />
            <p class="text-xs text-gray-500 mt-1">Optional tags to categorize this relic</p>
          </div>

          <!-- Actions Area -->
          <div class="flex items-center justify-between mt-8 pt-6 border-t border-gray-200">
            <div class="flex items-center gap-2">
              <div class="flex p-[3px] bg-gray-100 border border-gray-200 rounded gap-0.5">
                <button 
                  type="button"
                  on:click={() => visibility = 'public'}
                  class="flex items-center gap-1.5 px-3 py-1 rounded-sm text-[10px] font-bold transition-all {visibility === 'public' ? 'shadow-sm opacity-100 ring-1 ring-black/5' : 'text-gray-500 hover:text-gray-700 opacity-60 hover:opacity-100'}"
                  style={visibility === 'public' ? 'background-color: #e2f2fd; color: #217db1;' : ''}
                  title="Anyone can view"
                >
                  <i class="fas fa-globe text-[10px]"></i>
                  <span>PUBLIC</span>
                </button>
                <button 
                  type="button"
                  on:click={() => visibility = 'private'}
                  class="flex items-center gap-1.5 px-3 py-1 rounded-sm text-[10px] font-bold transition-all {visibility === 'private' ? 'shadow-sm opacity-100 ring-1 ring-black/5' : 'text-gray-500 hover:text-gray-700 opacity-60 hover:opacity-100'}"
                  style={visibility === 'private' ? 'background-color: #fce3eb; color: #76306c;' : ''}
                  title="Direct URL only"
                >
                  <i class="fas fa-lock text-[10px]"></i>
                  <span>PRIVATE</span>
                </button>
                <button 
                  type="button"
                  on:click={() => visibility = 'restricted'}
                  class="flex items-center gap-1.5 px-3 py-1 rounded-sm text-[10px] font-bold transition-all {visibility === 'restricted' ? 'shadow-sm opacity-100 ring-1 ring-black/5' : 'text-gray-500 hover:text-gray-700 opacity-60 hover:opacity-100'}"
                  style={visibility === 'restricted' ? 'background-color: #fef3c7; color: #b45309;' : ''}
                  title="Restricted access"
                >
                  <i class="fas fa-user-lock text-[10px]"></i>
                  <span>RESTRICTED</span>
                </button>
              </div>
            </div>

            <div class="flex items-center gap-3">
              {#if activeTab === 'upload' && uploadedFiles.length > 0}
                <button
                  type="button"
                  on:click={resetForm}
                  class="text-[11px] font-bold text-gray-400 hover:text-red-500 transition-colors px-3 py-2 uppercase tracking-tight"
                >
                  Clear All
                </button>
              {/if}
              
              <div class="flex items-center bg-[#0e8420] rounded shadow-sm hover:shadow-md transition-all overflow-hidden border border-[#0a6b19] h-10">
                <button
                  type="submit"
                  disabled={isLoading}
                  class="h-full px-5 text-white text-sm font-bold flex items-center justify-center gap-2 hover:bg-[#0a6b19] transition-colors active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                >
                  {#if isLoading}
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>Creating...</span>
                  {:else}
                    <i class="fas fa-plus text-[10px]"></i>
                    <span class="tracking-tight">
                      {#if activeTab === 'editor'}Create Relic{:else if uploadedFiles.length > 1 && zipMultiple}Create Archive{:else}Create Relic{/if}
                    </span>
                  {/if}
                </button>
                
                <div class="w-[1px] h-6 bg-white/20"></div>

                <div class="relative h-full group flex items-center">
                  <select
                    bind:value={expiry}
                    class="h-full font-bold border-none focus:outline-none focus:ring-0 transition-colors appearance-none cursor-pointer outline-none flex items-center [&::-webkit-outer-spin-button]:hidden [&::-webkit-calendar-picker-indicator]:hidden"
                    style="background-image: none;"
                    class:bg-[#0e8420]={expiry === 'never'}
                    class:text-transparent={expiry === 'never'}
                    class:hover:bg-[#0a6b19]={expiry === 'never'}
                    class:text-[10px]={expiry === 'never'}
                    class:px-1.5={expiry === 'never'}
                    class:bg-orange-100={expiry !== 'never'}
                    class:text-orange-700={expiry !== 'never'}
                    class:hover:bg-orange-200={expiry !== 'never'}
                    class:text-[11px]={expiry !== 'never'}
                    class:px-3={expiry !== 'never'}
                    class:pr-7={expiry !== 'never'}
                    title="Set expiration"
                  >
                    <option value="never" class="text-gray-900">Never</option>
                    <option value="10m" class="text-gray-900">10m</option>
                    <option value="1h" class="text-gray-900">1h</option>
                    <option value="12h" class="text-gray-900">12h</option>
                    <option value="24h" class="text-gray-900">24h</option>
                    <option value="3d" class="text-gray-900">3d</option>
                    <option value="7d" class="text-gray-900">1w</option>
                    <option value="30d" class="text-gray-900">1mo</option>
                    <option value="1y" class="text-gray-900">1y</option>
                  </select>
                  <div class={`absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center pointer-events-none transition-colors ${expiry !== 'never' ? 'text-orange-700 group-hover:text-orange-800' : 'text-white/70 group-hover:text-white'}`}>
                    <i class="fas fa-clock text-[10px]"></i>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </form>
      {:else if activeTab === "cli"}
        <!-- CLI Tab -->
        <div class="space-y-6">
          <div>
            <h3 class="text-base font-semibold text-gray-900 mb-2">
              CLI Installation
            </h3>
            <p class="text-sm text-gray-600 mb-3">
              Install the Relic CLI with a single command:
            </p>
            <div
              class="bg-gray-100 border-l-3 border-gray-400 rounded p-3 text-gray-900 text-xs font-mono overflow-x-auto"
            >
              <pre>curl -sSL {serverUrl}/install.sh | bash</pre>
            </div>
          </div>

          <div>
            <h3 class="text-base font-semibold text-gray-900 mb-2">
              Quick Start
            </h3>
            <div
              class="bg-gray-100 border-l-3 border-gray-400 rounded p-3 text-gray-900 text-xs font-mono overflow-x-auto"
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
            <h3 class="text-base font-semibold text-gray-900 mb-2">
              Configuration
            </h3>
            <p class="text-sm text-gray-600 mb-2">
              The CLI automatically configures itself to use <code
                class="bg-gray-200 px-2 py-0.5 rounded text-xs font-mono"
                >{serverUrl}</code
              > as the server.
            </p>
            <p class="text-sm text-gray-600 mb-3">
              Configuration file: <code
                class="bg-gray-200 px-2 py-0.5 rounded text-xs font-mono"
                >~/.relic/config</code
              >
            </p>
            <div
              class="bg-gray-100 border-l-3 border-gray-400 rounded p-3 text-gray-900 text-xs font-mono overflow-x-auto"
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
            <h3 class="text-base font-semibold text-gray-900 mb-2">
              Upload from stdin
            </h3>
            <div
              class="bg-gray-100 border-l-3 border-gray-400 rounded p-3 text-gray-900 text-xs font-mono overflow-x-auto"
            >
              <pre>echo "Hello World" | curl -X POST {serverUrl}/api/v1/relics \
  -F "file=@-" \
  -F "name=greeting"</pre>
            </div>
          </div>

          <div>
            <h3 class="text-base font-semibold text-gray-900 mb-2">
              Upload a file
            </h3>
            <div
              class="bg-gray-100 border-l-3 border-gray-400 rounded p-3 text-gray-900 text-xs font-mono overflow-x-auto"
            >
              <pre>curl -X POST {serverUrl}/api/v1/relics \
  -F "file=@script.py" \
  -F "name=My Script" \
  -F "access_level=public" \
  -F "expires_in=24h"</pre>
            </div>
          </div>

          <div>
            <h3 class="text-base font-semibold text-gray-900 mb-2">
              Pipe command output
            </h3>
            <div
              class="bg-gray-100 border-l-3 border-gray-400 rounded p-3 text-gray-900 text-xs font-mono overflow-x-auto"
            >
              <pre>ps aux | curl -X POST {serverUrl}/api/v1/relics \
  -F "file=@-" \
  -F "name=processes.txt"</pre>
            </div>
          </div>

          <div class="p-3 bg-gray-50 border border-gray-300 rounded">
            <p class="text-sm text-gray-700">
              <strong>Tip:</strong> Use the <code
                class="bg-white px-2 py-0.5 rounded text-xs font-mono border border-gray-300"
                >X-Client-Key</code
              > header to authenticate and associate relics with your account.
            </p>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  /* Component-specific styles only - global svelte-select styles are in app.css */
</style>
