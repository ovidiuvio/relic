<script>
  import { createRelic } from "../services/api";
  import { showToast } from "../stores/toastStore";
  import Select from "svelte-select";
  import {
    getContentType,
    getFileExtension,
    getSyntaxFromExtension,
    getAvailableSyntaxOptions,
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
  let uploadedFile = null;

  // Update syntax when syntaxValue changes
  $: syntax = syntaxValue?.value || "auto";

  // Helper function to find option by value
  function findOptionByValue(options, value) {
    return options.find((option) => option.value === value) || null;
  }

  // Check if a file is binary based on MIME type
  function isBinaryFile(file) {
    return (
      file.type.startsWith("image/") ||
      file.type === "application/pdf" ||
      file.type.startsWith("video/") ||
      file.type.startsWith("audio/") ||
      file.type.includes("zip") ||
      file.type.includes("archive") ||
      file.type === "application/octet-stream"
    );
  }

  // Format bytes to human readable string
  function formatBytes(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
  }

  // Reset form to initial state
  function resetForm() {
    title = "";
    syntax = "auto";
    syntaxValue = { value: "auto", label: "Auto-detect" };
    content = "";
    expiry = "never";
    visibility = "public";
    uploadedFile = null;
  }

  // Process uploaded/dropped file
  function processFile(file, source = "uploaded") {
    // Set title based on filename (without extension)
    const nameWithoutExt = file.name.replace(/\.[^/.]+$/, "");
    if (!title) title = nameWithoutExt;

    // Try to detect type based on file extension
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (ext && syntax === "auto") {
      const detectedSyntax = getSyntaxFromExtension(ext);
      if (detectedSyntax) {
        syntax = detectedSyntax;
        const matchingOption = findOptionByValue(syntaxOptions, detectedSyntax);
        if (matchingOption) {
          syntaxValue = matchingOption;
        }
      }
    }

    if (isBinaryFile(file)) {
      uploadedFile = file;
      content = `[Binary file: ${file.name} (${formatBytes(file.size)})]`;
      showToast(`Binary file "${file.name}" ready for upload`, "success");
    } else {
      uploadedFile = null;
      const reader = new FileReader();

      reader.onload = (event) => {
        content = event.target.result;
        const action = source === "dropped" ? "dropped and loaded" : "loaded successfully";
        showToast(`File "${file.name}" ${action}`, "success");
      };

      reader.onerror = () => {
        showToast("Failed to read file", "error");
      };

      reader.readAsText(file);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();

    if (!content.trim() && !uploadedFile) {
      showToast("Please enter some content or upload a file", "warning");
      return;
    }

    isLoading = true;

    try {
      let file;
      let contentType;

      if (uploadedFile) {
        file = uploadedFile;
        contentType = uploadedFile.type || getContentType(syntax);
      } else {
        contentType = syntax !== "auto" ? getContentType(syntax) : "text/plain";
        const fileExtension = syntax !== "auto" ? getFileExtension(syntax) : "txt";
        const blob = new Blob([content], { type: contentType });
        const fileName = title || `relic.${fileExtension}`;
        file = new File([blob], fileName, { type: contentType });
      }

      const response = await createRelic({
        file: file,
        name: title || undefined,
        content_type: contentType,
        language_hint: syntax !== "auto" ? syntax : undefined,
        access_level: visibility,
        expires_in: expiry !== "never" ? expiry : undefined,
      });

      const data = response.data;
      showToast("Relic created successfully!", "success");
      window.location.href = `/${data.id}`;
      resetForm();
    } catch (error) {
      showToast(error.message || "Failed to create relic", "error");
      console.error("Error creating relic:", error);
    } finally {
      isLoading = false;
    }
  }

  function handleFileUpload(e) {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      processFile(files[0], "uploaded");
    }
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

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      processFile(files[0], "dropped");
    }
  }
</script>

<div class="mb-8">
  <div class="bg-white shadow-sm rounded-lg border border-gray-200">
    <div
      class="px-6 py-4 border-b border-gray-200 flex items-center justify-between"
    >
      <h2 class="text-lg font-semibold text-gray-900 flex items-center">
        <i class="fas fa-plus text-blue-600 mr-2"></i>
        Create New Relic
      </h2>
      <div class="flex items-center gap-4">
        <div class="text-xs text-gray-500">
          {content.length} characters
        </div>
      </div>
    </div>

    <div class="p-6">
      <form on:submit={handleSubmit} class="space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label
              for="title"
              class="block text-sm font-medium text-gray-700 mb-1">Title</label
            >
            <input
              type="text"
              id="title"
              bind:value={title}
              placeholder="e.g. Nginx Configuration"
              class="w-full px-3 py-2 text-sm maas-input"
            />
            <p class="text-xs text-gray-500 mt-1">
              A descriptive name for this relic
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
            class="block text-sm font-medium text-gray-700 mb-1">Content</label
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
              placeholder="// Paste your code here..."
            ></textarea>
          </div>
          <div class="flex items-center gap-4 text-sm text-gray-500 mt-2">
            <div class="flex items-center gap-2">
              <button
                type="button"
                on:click={() => fileInput?.click()}
                class="maas-btn-secondary px-3 py-1 text-xs rounded font-medium"
              >
                <i class="fas fa-upload mr-1"></i>
                Upload File
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
              Creating Relic...
            {:else}
              <i class="fas fa-plus mr-1"></i>
              Create Relic
            {/if}
          </button>
        </div>
      </form>
    </div>
  </div>
</div>

<style>
  /* Component-specific styles only - global svelte-select styles are in app.css */
</style>
