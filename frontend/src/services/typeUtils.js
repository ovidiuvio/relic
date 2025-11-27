export function getTypeLabel(contentType) {
  if (!contentType) return 'Text'
  if (contentType.includes('javascript')) return 'JavaScript'
  if (contentType.includes('python')) return 'Python'
  if (contentType.includes('html')) return 'HTML'
  if (contentType.includes('css')) return 'CSS'
  if (contentType.includes('json')) return 'JSON'
  if (contentType.includes('markdown')) return 'Markdown'
  if (contentType.includes('xml')) return 'XML'
  if (contentType.includes('bash') || contentType.includes('shell')) return 'Bash'
  if (contentType.includes('sql')) return 'SQL'
  if (contentType.includes('java')) return 'Java'
  if (contentType.includes('pdf')) return 'PDF'
  if (contentType.includes('image')) return 'Image'
  if (contentType.includes('csv')) return 'CSV'
  if (contentType.includes('zip') || contentType.includes('archive') || contentType.includes('tar') || contentType.includes('gzip')) return 'Archive'
  if (contentType.includes('text')) return 'Text'
  return 'Unknown'
}

export function getTypeIcon(contentType) {
  if (!contentType) return 'fa-file'
  if (contentType.includes('javascript')) return 'fa-brands fa-js'
  if (contentType.includes('python')) return 'fa-brands fa-python'
  if (contentType.includes('html')) return 'fa-brands fa-html5'
  if (contentType.includes('css')) return 'fa-brands fa-css3-alt'
  if (contentType.includes('json')) return 'fa-code'
  if (contentType.includes('markdown')) return 'fa-file-lines'
  if (contentType.includes('xml')) return 'fa-code'
  if (contentType.includes('bash') || contentType.includes('shell')) return 'fa-terminal'
  if (contentType.includes('sql')) return 'fa-database'
  if (contentType.includes('java')) return 'fa-brands fa-java'
  if (contentType.includes('pdf')) return 'fa-file-pdf'
  if (contentType.includes('image')) return 'fa-image'
  if (contentType.includes('csv')) return 'fa-file-csv'
  if (contentType.includes('zip') || contentType.includes('archive') || contentType.includes('tar') || contentType.includes('gzip')) return 'fa-file-zipper'
  if (contentType.includes('text')) return 'fa-file-lines'
  return 'fa-file'
}

export function getTypeIconColor(contentType) {
  return 'text-gray-500'
}

export function formatBytes(bytes, decimals = 2) {
  if (!+bytes) return '0 Bytes'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
}

// Map type selections to MIME types
export function getContentType(syntax) {
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

// Map language selection to file extensions
export function getFileExtension(syntax) {
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

// Auto-detect language hint from content type
export function detectLanguageHint(contentType) {
  const typeToLanguage = {
    'text/markdown': 'markdown',
    'text/html': 'html',
    'application/json': 'json',
    'application/xml': 'xml',
    'application/javascript': 'javascript',
    'text/x-python': 'python',
    'text/x-shellscript': 'bash',
    'application/sql': 'sql',
    'text/css': 'css',
    'text/x-java-source': 'java'
  }
  return typeToLanguage[contentType] || 'auto'
}

// Format time ago string
export function formatTimeAgo(dateString) {
  const now = new Date()
  const date = new Date(dateString)
  const diffInSeconds = Math.floor((now - date) / 1000)

  if (diffInSeconds < 60) return 'just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
  return `${Math.floor(diffInSeconds / 86400)}d ago`
}

// Copy relic ID to clipboard
export function copyRelicId(relicId) {
  navigator.clipboard.writeText(relicId).then(() => {
    // Could add toast notification here if desired
  })
}

// Get default items per page based on screen size
export function getDefaultItemsPerPage() {
  if (typeof window === 'undefined') return 20
  const width = window.innerWidth
  if (width < 768) return 10      // Mobile
  return 20                        // Tablet & Desktop
}
