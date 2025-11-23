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

  // Map syntax selections to MIME types
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
      // Determine content type based on syntax selection
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

      // Try to detect syntax based on file extension
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

      // Try to detect syntax based on file extension
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

<div class="px-4 sm:px-0 mb-8">
  <div class="bg-white shadow-sm rounded-lg border border-gray-200">
    <div class="px-6 py-4 border-b border-gray-200">
      <h2 class="text-lg font-semibold text-gray-900 flex items-center">
        <i class="fas fa-edit text-blue-600 mr-2"></i>
        Create New Paste
      </h2>
    </div>
    <div class="p-6">
      <form on:submit={handleSubmit} class="space-y-6">
        <div class="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <label for="title" class="block text-sm font-medium text-gray-700">Title (Optional)</label>
            <input
              type="text"
              id="title"
              bind:value={title}
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="Enter paste title..."
            />
          </div>
          <div>
            <label for="syntax" class="block text-sm font-medium text-gray-700">Syntax</label>
            <select
              id="syntax"
              bind:value={syntax}
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="auto">Auto-detect</option>
              <option value="text">Plain Text</option>
              <option value="markdown">Markdown</option>
              <option value="html">HTML</option>
              <option value="json">JSON</option>
              <option value="xml">XML</option>
              <option value="javascript">JavaScript</option>
              <option value="python">Python</option>
              <option value="bash">Bash</option>
              <option value="sql">SQL</option>
              <option value="css">CSS</option>
              <option value="java">Java</option>
            </select>
          </div>
        </div>

        <div>
          <label for="content" class="block text-sm font-medium text-gray-700">Content</label>
          <textarea
            id="content"
            bind:value={content}
            on:dragover={handleDragOver}
            on:dragleave={handleDragLeave}
            on:drop={handleDrop}
            rows="12"
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 font-mono text-sm border-2 border-dashed border-gray-300 transition-colors"
            placeholder="Paste your content here or drag & drop files..."
          ></textarea>
        </div>

        <div class="grid grid-cols-1 gap-6 sm:grid-cols-3">
          <div>
            <label for="expiry" class="block text-sm font-medium text-gray-700">Expires</label>
            <select
              id="expiry"
              bind:value={expiry}
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="never">Never</option>
              <option value="1h">1 Hour</option>
              <option value="24h">24 Hours</option>
              <option value="7d">7 Days</option>
              <option value="30d">30 Days</option>
            </select>
          </div>
          <div>
            <label for="visibility" class="block text-sm font-medium text-gray-700">Visibility</label>
            <select
              id="visibility"
              bind:value={visibility}
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="public">Public</option>
              <option value="unlisted">Unlisted</option>
              <option value="private">Private</option>
            </select>
          </div>
          <div>
            <label for="password" class="block text-sm font-medium text-gray-700">Password (Optional)</label>
            <input
              type="password"
              id="password"
              bind:value={password}
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="Password protect"
            />
          </div>
        </div>

        <div class="flex items-center justify-between pt-4">
          <div class="flex items-center space-x-4">
            <button
              type="button"
              on:click={() => fileInput?.click()}
              class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <i class="fas fa-upload mr-2"></i>
              Upload File
            </button>
            <input
              type="file"
              bind:this={fileInput}
              on:change={handleFileUpload}
              class="hidden"
              multiple
            />
            <span class="text-sm text-gray-500">or drag & drop files</span>
          </div>
          <button
            type="submit"
            disabled={isLoading}
            class="inline-flex items-center px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i class="fas fa-share mr-2"></i>
            {isLoading ? 'Creating...' : 'Create Paste'}
          </button>
        </div>
      </form>
    </div>
  </div>
</div>
