<script>
  import { createPaste } from '../services/api'
  import { showToast } from '../stores/toastStore'

  let title = ''
  let syntax = 'auto'
  let content = ''
  let expiry = 'never'
  let visibility = 'public'
  let password = ''
  let isLoading = false
  let fileInput

  // Map type selections to MIME types
  function getContentType(syntax) {
    const mimeTypes = {
      'text': 'text/plain',
      'markdown': 'text/markdown',
      'html': 'text/html',
      'json': 'application/json',
      'xml': 'application/xml',
      'javascript': 'application/javascript',
      'python': 'text/x-python',
      'bash': 'text/x-shellscript',
      'sql': 'application/sql',
      'css': 'text/css',
      'java': 'text/x-java-source'
    }
    return mimeTypes[syntax] || 'text/plain'
  }

  function getFileExtension(syntax) {
    const extensions = {
      'text': 'txt',
      'markdown': 'md',
      'html': 'html',
      'json': 'json',
      'xml': 'xml',
      'javascript': 'js',
      'python': 'py',
      'bash': 'sh',
      'sql': 'sql',
      'css': 'css',
      'java': 'java'
    }
    return extensions[syntax] || 'txt'
  }

  async function handleSubmit(e) {
    e.preventDefault()

    if (!content.trim()) {
      showToast('Please enter some content', 'warning')
      return
    }

    isLoading = true

    try {
      // Determine content type based on type selection
      const contentType = syntax !== 'auto' ? getContentType(syntax) : 'text/plain'
      const fileExtension = syntax !== 'auto' ? getFileExtension(syntax) : 'txt'

      // Create a File object from the content with proper MIME type
      const blob = new Blob([content], { type: contentType })
      const fileName = title || `paste.${fileExtension}`
      const file = new File([blob], fileName, { type: contentType })

      // Create FormData and append the file
      const formData = new FormData()
      formData.append('file', file)
      formData.append('name', title || 'Untitled')
      formData.append('content_type', contentType)
      if (syntax !== 'auto') {
        formData.append('language_hint', syntax)
      }
      formData.append('access_level', visibility)
      if (expiry !== 'never') {
        formData.append('expires_in', expiry)
      }

      // Use axios directly for FormData
      const response = await fetch('/api/v1/pastes', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create paste')
      }

      const data = await response.json()
      const pasteUrl = `${window.location.origin}/${data.id}`
      showToast('Paste created successfully!', 'success')

      // Copy to clipboard
      navigator.clipboard.writeText(pasteUrl).then(() => {
        showToast('URL copied to clipboard!', 'info')
      })

      // Reset form
      title = ''
      syntax = 'auto'
      content = ''
      expiry = 'never'
      visibility = 'public'
      password = ''
    } catch (error) {
      showToast(error.message || 'Failed to create paste', 'error')
      console.error('Error creating paste:', error)
    } finally {
      isLoading = false
    }
  }

  function handleFileUpload(e) {
    const files = Array.from(e.target.files)
    if (files.length === 0) return

    const file = files[0]
    const reader = new FileReader()

    reader.onload = (event) => {
      content = event.target.result
      // Set title based on filename (without extension)
      const nameWithoutExt = file.name.replace(/\.[^/.]+$/, "")
      if (!title) title = nameWithoutExt

      // Try to detect type based on file extension
      const ext = file.name.split('.').pop()?.toLowerCase()
      if (ext && syntax === 'auto') {
        // Map extensions to syntax options
        const extToSyntax = {
          'js': 'javascript', 'ts': 'javascript', 'jsx': 'javascript', 'tsx': 'javascript',
          'py': 'python', 'pyx': 'python', 'pyi': 'python',
          'html': 'html', 'htm': 'html',
          'css': 'css', 'scss': 'css', 'sass': 'css', 'less': 'css',
          'json': 'json', 'jsonc': 'json',
          'md': 'markdown', 'markdown': 'markdown',
          'xml': 'xml', 'xsl': 'xml', 'xslt': 'xml',
          'sh': 'bash', 'bash': 'bash', 'zsh': 'bash', 'fish': 'bash',
          'sql': 'sql',
          'java': 'java', 'class': 'java'
        }
        if (extToSyntax[ext]) {
          syntax = extToSyntax[ext]
        }
      }

      showToast(`File "${file.name}" loaded successfully`, 'success')
    }

    // Read as text to preserve content
    reader.readAsText(file)
  }

  function handleDragOver(e) {
    e.preventDefault()
    e.currentTarget.classList.add('border-blue-500', 'bg-blue-50')
  }

  function handleDragLeave(e) {
    e.preventDefault()
    e.currentTarget.classList.remove('border-blue-500', 'bg-blue-50')
  }

  function handleDrop(e) {
    e.preventDefault()
    e.currentTarget.classList.remove('border-blue-500', 'bg-blue-50')

    const files = Array.from(e.dataTransfer.files)
    if (files.length === 0) return

    const file = files[0]
    const reader = new FileReader()

    reader.onload = (event) => {
      content = event.target.result
      // Set title based on filename (without extension)
      const nameWithoutExt = file.name.replace(/\.[^/.]+$/, "")
      if (!title) title = nameWithoutExt

      // Try to detect type based on file extension
      const ext = file.name.split('.').pop()?.toLowerCase()
      if (ext && syntax === 'auto') {
        // Map extensions to syntax options
        const extToSyntax = {
          'js': 'javascript', 'ts': 'javascript', 'jsx': 'javascript', 'tsx': 'javascript',
          'py': 'python', 'pyx': 'python', 'pyi': 'python',
          'html': 'html', 'htm': 'html',
          'css': 'css', 'scss': 'css', 'sass': 'css', 'less': 'css',
          'json': 'json', 'jsonc': 'json',
          'md': 'markdown', 'markdown': 'markdown',
          'xml': 'xml', 'xsl': 'xml', 'xslt': 'xml',
          'sh': 'bash', 'bash': 'bash', 'zsh': 'bash', 'fish': 'bash',
          'sql': 'sql',
          'java': 'java', 'class': 'java'
        }
        if (extToSyntax[ext]) {
          syntax = extToSyntax[ext]
        }
      }

      showToast(`File "${file.name}" dropped and loaded`, 'success')
    }

    // Read as text to preserve content
    reader.readAsText(file)
  }
</script>

<div class="mb-8">
  <div class="bg-white shadow-sm rounded-lg border border-gray-200">
    <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
      <h2 class="text-lg font-semibold text-gray-900 flex items-center">
        <i class="fas fa-plus text-blue-600 mr-2"></i>
        Create New Paste
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
            <label for="title" class="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input
              type="text"
              id="title"
              bind:value={title}
              placeholder="e.g. Nginx Configuration"
              class="w-full px-3 py-2 text-sm maas-input"
            />
            <p class="text-xs text-gray-500 mt-1">A descriptive name for this paste</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Type</label>
            <select
              id="syntax"
              bind:value={syntax}
              class="w-full px-3 py-2 text-sm maas-input bg-white"
            >
              <option value="auto">Auto-detect</option>
              <option value="text">Plain Text</option>
              <option value="markdown">Markdown</option>
              <option value="html">HTML</option>
              <option value="css">CSS</option>
              <option value="json">JSON</option>
              <option value="xml">XML</option>
              <option value="javascript">JavaScript</option>
              <option value="python">Python</option>
              <option value="bash">Bash</option>
              <option value="sql">SQL</option>
              <option value="java">Java</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Visibility</label>
            <select
              id="visibility"
              bind:value={visibility}
              class="w-full px-3 py-2 text-sm maas-input bg-white"
            >
              <option value="public">Public</option>
              <option value="unlisted">Unlisted</option>
              <option value="private">Private</option>
            </select>
            <p class="text-xs text-gray-500 mt-1">
              {#if visibility === 'public'}Anyone can view this paste
              {:else if visibility === 'unlisted'}Only those with link can view
              {:else}Only you can view this paste
              {/if}
            </p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Expires</label>
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
          <label for="content" class="block text-sm font-medium text-gray-700 mb-1">Content</label>
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
              Creating...
            {:else}
              <i class="fas fa-plus mr-1"></i>
              Create Paste
            {/if}
          </button>
        </div>
      </form>
    </div>
  </div>
</div>