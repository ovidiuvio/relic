<script>
  import { createEventDispatcher } from "svelte";
  import { createRelic } from "../services/api";
  import { showToast } from "../stores/toastStore";
  import JSZip from "jszip";
  import {
    getContentType,
    getSyntaxFromExtension,
    getFileTypeDefinition,
  } from "../services/typeUtils";
  import { formatBytes } from "../services/utils/formatting";

  const dispatch = createEventDispatcher();

  export let files = []; // [{ file, id, path }]
  export let spaceId = null;
  export let spaceName = "";

  let title = "";
  let visibility = "public";
  let tags = "";
  let expiry = "never";
  let zipMultiple = true;
  let isLoading = false;
  let uploadTotal = files.length;
  let uploadCurrent = 0;

  async function handleUpload() {
    if (files.length === 0) {
      showToast("No files to upload", "warning");
      return;
    }

    isLoading = true;
    uploadCurrent = 0;
    uploadTotal = zipMultiple && files.length > 1 ? 1 : files.length;

    let createdRelics = [];
    let errors = [];

    try {
      if (files.length > 1 && zipMultiple) {
        // Zip logic
        const zip = new JSZip();
        files.forEach(({ file, path }) => {
          const zipPath = path || file.name;
          zip.file(zipPath, file);
        });

        const zipBlob = await zip.generateAsync({
          type: "blob",
          compression: "DEFLATE",
        });
        
        const zipName = title 
          ? (title.toLowerCase().endsWith('.zip') ? title : `${title}.zip`)
          : (files.length > 0 ? `${files[0].file.name.split('.')[0]}_archive.zip` : "archive.zip");
          
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
        uploadCurrent = 1;
      } else {
        // Individual file upload
        for (let i = 0; i < files.length; i++) {
          const { file } = files[i];
          
          try {
            const ext = file.name.split(".").pop()?.toLowerCase();
            let fileSyntax = "auto";
            let fileContentType = file.type;

            if (ext) {
              const detected = getSyntaxFromExtension(ext);
              if (detected) {
                fileSyntax = detected;
                const canonicalMime = getContentType(detected);
                const typeDef = getFileTypeDefinition(canonicalMime);

                if (["code", "text", "markdown", "html", "csv", "json", "xml"].includes(typeDef.category)) {
                  fileContentType = canonicalMime;
                } else if (!fileContentType) {
                  fileContentType = canonicalMime;
                }
              }
            }

            const fileName = files.length === 1 && title ? title : file.name;

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
            uploadCurrent = i + 1;
          } catch (err) {
            console.error(`Error uploading ${file.name}:`, err);
            errors.push(file.name);
          }
        }
      }

      if (createdRelics.length > 0) {
        if (errors.length > 0) {
          showToast(`Uploaded ${createdRelics.length} relics, but ${errors.length} failed.`, "warning");
        } else {
          showToast(`Successfully uploaded ${createdRelics.length} relic(s) to ${spaceName || 'space'}!`, "success");
        }
        dispatch("success", { relics: createdRelics });
      } else if (errors.length > 0) {
        showToast(`Failed to upload any relics: ${errors.join(", ")}`, "error");
      }
    } catch (error) {
      console.error("Upload error:", error);
      showToast(error.message || "Failed to upload relics", "error");
    } finally {
      isLoading = false;
    }
  }

  function removeFile(index) {
    files = files.filter((_, i) => i !== index);
    if (files.length === 0) dispatch("close");
  }

  // Pre-fill title if single file
  $: if (files.length === 1 && !title) {
    title = files[0].file.name.replace(/\.[^/.]+$/, "");
  }
</script>

<div 
  class="fixed inset-0 bg-black/60 backdrop-blur-sm z-[200] flex items-center justify-center p-4 animate-in fade-in duration-200" 
  on:click={() => !isLoading && dispatch('close')}
  on:keydown={(e) => !isLoading && (e.key === 'Escape' || e.key === 'Enter') && dispatch('close')}
  role="button"
  tabindex="0"
  aria-label="Close modal"
>
  <section 
    class="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200" 
    on:click|stopPropagation
    on:keydown|stopPropagation
    role="document"
    tabindex="-1"
  >
    <!-- Header -->
    <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600">
          <i class="fas fa-cloud-upload-alt text-xl"></i>
        </div>
        <div>
          <h2 class="text-lg font-bold text-gray-800 leading-tight">
            {spaceName ? 'Upload to Space' : 'Add to Collection'}
          </h2>
          <p class="text-[10px] text-gray-500 font-bold uppercase tracking-widest mt-0.5">
            {spaceName ? `Target: ${spaceName}` : 'Uploading as global relics'}
          </p>
        </div>
      </div>
      <button 
        on:click={() => dispatch("close")} 
        class="w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all focus:outline-none"
        disabled={isLoading}
      >
        <i class="fas fa-times"></i>
      </button>
    </div>

    <!-- Content -->
    <div class="p-6 flex-1 overflow-y-auto space-y-6">
      <!-- File List -->
      <div class="space-y-3">
        <div class="flex items-center justify-between px-1">
          <h3 class="text-[11px] font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
            <i class="fas fa-file-invoice text-blue-400"></i>
            Files to Sync ({files.length})
          </h3>
          {#if files.length > 1}
            <label class="flex items-center space-x-2 text-[11px] text-gray-500 cursor-pointer select-none px-2 py-1 bg-gray-50 rounded border border-gray-200 hover:border-blue-300 transition-colors">
              <input
                type="checkbox"
                bind:checked={zipMultiple}
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500 w-3 h-3"
              />
              <span class="font-bold uppercase tracking-tighter">Zip all files</span>
            </label>
          {/if}
        </div>
        
        <div class="bg-gray-50/50 rounded-xl border border-gray-100 divide-y divide-gray-100 max-h-64 overflow-y-auto shadow-inner">
          {#each files as { file, path }, i}
            <div class="flex items-center justify-between p-3 text-sm hover:bg-white transition-colors group">
              <div class="flex items-center min-w-0 pr-4">
                <div class="w-8 h-8 rounded bg-white border border-gray-100 flex items-center justify-center text-gray-400 mr-3 flex-shrink-0 group-hover:border-blue-200 group-hover:text-blue-500 transition-colors shadow-sm">
                  <i class="fas fa-file-code text-[10px]"></i>
                </div>
                <div class="min-w-0">
                  <div class="font-bold text-gray-700 truncate text-[13px]">{path || file.name}</div>
                  <div class="flex items-center gap-2 mt-0.5">
                    <span class="text-[9px] text-gray-400 font-bold px-1.5 py-0.5 bg-white rounded border border-gray-100 uppercase tracking-tighter shadow-sm">{formatBytes(file.size)}</span>
                  </div>
                </div>
              </div>
              <button
                type="button"
                on:click={() => removeFile(i)}
                class="text-gray-300 hover:text-red-500 p-1.5 rounded-lg hover:bg-red-50 transition-all opacity-0 group-hover:opacity-100 sm:opacity-100 sm:text-gray-200"
                title="Remove from batch"
                disabled={isLoading}
              >
                <i class="fas fa-trash-alt text-[10px]"></i>
              </button>
            </div>
          {/each}
        </div>
      </div>

      <!-- Options -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
        <div class="space-y-5">
          <div>
            <label for="drop-title" class="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5 ml-1">Archive Title (Optional)</label>
            <input
              type="text"
              id="drop-title"
              bind:value={title}
              placeholder={zipMultiple && files.length > 1 ? "e.g. Project Archive" : "e.g. My Document"}
              class="maas-input w-full bg-white shadow-sm"
              disabled={isLoading}
            />
          </div>
          <div>
            <label for="drop-tags" class="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5 ml-1">Tags (Comma separated)</label>
            <input
              type="text"
              id="drop-tags"
              bind:value={tags}
              placeholder="e.g. logs, production, project-x"
              class="maas-input w-full bg-white shadow-sm"
              disabled={isLoading}
            />
          </div>
        </div>

        <div class="space-y-5">
          <div>
            <label for="drop-visibility" class="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5 ml-1">Visibility</label>
            <div class="grid grid-cols-2 gap-2">
              <label class="flex items-center p-2.5 border rounded-lg cursor-pointer transition-all shadow-sm {visibility === 'public' ? 'border-green-500 bg-green-50/50 ring-1 ring-green-500' : 'border-gray-200 bg-white hover:bg-gray-50'}">
                <input type="radio" bind:group={visibility} value="public" class="hidden" disabled={isLoading}>
                <i class="fas fa-globe text-green-600 text-[10px] mr-2"></i>
                <span class="text-[11px] font-bold text-gray-700 uppercase tracking-tight">Public</span>
              </label>
              <label class="flex items-center p-2.5 border rounded-lg cursor-pointer transition-all shadow-sm {visibility === 'private' ? 'border-blue-500 bg-blue-50/50 ring-1 ring-blue-500' : 'border-gray-200 bg-white hover:bg-gray-50'}">
                <input type="radio" bind:group={visibility} value="private" class="hidden" disabled={isLoading}>
                <i class="fas fa-lock text-gray-600 text-[10px] mr-2"></i>
                <span class="text-[11px] font-bold text-gray-700 uppercase tracking-tight">Private</span>
              </label>
            </div>
          </div>
          <div>
            <label for="drop-expiry" class="block text-[11px] font-bold text-gray-500 uppercase tracking-widest mb-1.5 ml-1">Auto-Expire</label>
            <select
              id="drop-expiry"
              bind:value={expiry}
              class="maas-input w-full bg-white cursor-pointer shadow-sm"
              disabled={isLoading}
            >
              <option value="never">Never</option>
              <option value="1h">1 Hour</option>
              <option value="24h">24 Hours</option>
              <option value="7d">7 Days</option>
              <option value="30d">30 Days</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="px-6 py-4 bg-gray-50/80 border-t border-gray-100 flex flex-col gap-4">
      {#if isLoading}
        <div class="w-full">
          <div class="flex justify-between items-center mb-1.5 px-0.5">
            <span class="text-[10px] font-bold text-blue-600 uppercase tracking-widest animate-pulse">
                {uploadCurrent < uploadTotal ? 'Streaming Data...' : 'Finalizing Relic...'}
            </span>
            <span class="text-[10px] font-mono font-bold text-blue-600">
              {Math.round((uploadCurrent / uploadTotal) * 100)}%
            </span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden shadow-inner">
            <div 
              class="bg-blue-600 h-full transition-all duration-300 ease-out shadow-sm"
              style="width: {(uploadCurrent / uploadTotal) * 100}%"
            ></div>
          </div>
        </div>
      {/if}

      <div class="flex justify-end gap-3">
        <button
          on:click={() => dispatch("close")}
          class="maas-btn-secondary px-6 text-xs font-bold uppercase tracking-widest hover:bg-white transition-colors"
          disabled={isLoading}
        >
          Cancel
        </button>
        <button
          on:click={handleUpload}
          class="maas-btn-primary px-10 text-xs font-bold uppercase tracking-widest shadow-md shadow-green-200/50 group overflow-hidden relative active:scale-95 transition-all"
          disabled={isLoading || files.length === 0}
        >
          {#if isLoading}
            <i class="fas fa-circle-notch fa-spin mr-2"></i>
            Syncing...
          {:else}
            <i class="fas fa-upload mr-2 group-hover:-translate-y-0.5 transition-transform"></i>
            {spaceName ? 'Sync to Space' : 'Add to Relics'}
          {/if}
        </button>
      </div>
    </div>
  </section>
</div>
