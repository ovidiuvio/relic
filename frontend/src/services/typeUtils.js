// Centralized file type definitions
const FILE_TYPES = [
  {
    syntax: 'javascript',
    label: 'JavaScript',
    icon: 'fa-brands fa-js',
    mime: 'application/javascript',
    extensions: ['js', 'jsx', 'mjs', 'cjs'],
    category: 'code'
  },
  {
    syntax: 'typescript',
    label: 'TypeScript',
    icon: 'fa-brands fa-js', // FontAwesome doesn't have TS specific icon yet, usually JS icon or custom
    mime: 'application/x-typescript',
    extensions: ['ts', 'tsx'],
    category: 'code'
  },
  {
    syntax: 'python',
    label: 'Python',
    icon: 'fa-brands fa-python',
    mime: 'text/x-python',
    extensions: ['py', 'pyx', 'pyi'],
    category: 'code'
  },
  {
    syntax: 'html',
    label: 'HTML',
    icon: 'fa-brands fa-html5',
    mime: 'text/html',
    extensions: ['html', 'htm'],
    category: 'html'
  },
  {
    syntax: 'css',
    label: 'CSS',
    icon: 'fa-brands fa-css3-alt',
    mime: 'text/css',
    extensions: ['css', 'scss', 'sass', 'less'],
    category: 'code'
  },
  {
    syntax: 'json',
    label: 'JSON',
    icon: 'fa-code',
    mime: 'application/json',
    extensions: ['json', 'jsonc'],
    category: 'code'
  },
  {
    syntax: 'markdown',
    label: 'Markdown',
    icon: 'fa-file-lines',
    mime: 'text/markdown',
    extensions: ['md', 'markdown'],
    category: 'markdown'
  },
  {
    syntax: 'xml',
    label: 'XML',
    icon: 'fa-code',
    mime: 'application/xml',
    extensions: ['xml', 'xsl', 'xslt'],
    category: 'code'
  },
  {
    syntax: 'yaml',
    label: 'YAML',
    icon: 'fa-code',
    mime: 'application/x-yaml',
    extensions: ['yaml', 'yml'],
    category: 'code'
  },
  {
    syntax: 'bash',
    label: 'Bash',
    icon: 'fa-terminal',
    mime: 'text/x-shellscript',
    extensions: ['sh', 'bash', 'zsh', 'fish'],
    category: 'code'
  },
  {
    syntax: 'sql',
    label: 'SQL',
    icon: 'fa-database',
    mime: 'application/sql',
    extensions: ['sql'],
    category: 'code'
  },
  {
    syntax: 'java',
    label: 'Java',
    icon: 'fa-brands fa-java',
    mime: 'text/x-java-source',
    extensions: ['java', 'class'],
    category: 'code'
  },
  {
    syntax: 'php',
    label: 'PHP',
    icon: 'fa-brands fa-php',
    mime: 'application/x-php',
    extensions: ['php'],
    category: 'code'
  },
  {
    syntax: 'ruby',
    label: 'Ruby',
    icon: 'fa-gem',
    mime: 'application/x-ruby',
    extensions: ['rb'],
    category: 'code'
  },
  {
    syntax: 'go',
    label: 'Go',
    icon: 'fa-brands fa-golang',
    mime: 'text/x-go',
    extensions: ['go'],
    category: 'code'
  },
  {
    syntax: 'rust',
    label: 'Rust',
    icon: 'fa-brands fa-rust',
    mime: 'text/x-rust',
    extensions: ['rs'],
    category: 'code'
  },
  {
    syntax: 'c',
    label: 'C',
    icon: 'fa-code',
    mime: 'text/x-c',
    extensions: ['c', 'h'],
    category: 'code'
  },
  {
    syntax: 'cpp',
    label: 'C++',
    icon: 'fa-code',
    mime: 'text/x-c++',
    extensions: ['cpp', 'cc', 'cxx', 'hpp'],
    category: 'code'
  },
  {
    syntax: 'dockerfile',
    label: 'Dockerfile',
    icon: 'fa-brands fa-docker',
    mime: 'text/x-dockerfile',
    extensions: ['dockerfile'],
    category: 'code'
  },
  {
    syntax: 'makefile',
    label: 'Makefile',
    icon: 'fa-file-code',
    mime: 'text/x-makefile',
    extensions: ['makefile'],
    category: 'code'
  },
  {
    syntax: 'pdf',
    label: 'PDF',
    icon: 'fa-file-pdf',
    mime: 'application/pdf',
    extensions: ['pdf'],
    category: 'pdf'
  },
  {
    syntax: 'csv',
    label: 'CSV',
    icon: 'fa-file-csv',
    mime: 'text/csv',
    extensions: ['csv'],
    category: 'csv'
  },
  {
    syntax: 'svg',
    label: 'SVG',
    icon: 'fa-image',
    mime: 'image/svg+xml',
    extensions: ['svg'],
    category: 'image'
  },
  {
    syntax: 'image',
    label: 'Image',
    icon: 'fa-image',
    mime: 'image/',
    extensions: ['jpg', 'jpeg', 'png', 'gif', 'webp'],
    category: 'image'
  },
  {
    syntax: 'archive',
    label: 'Archive',
    icon: 'fa-file-zipper',
    mime: 'application/zip',
    extensions: ['zip', 'tar', 'gz', '7z', 'rar'],
    category: 'archive'
  },
  {
    syntax: 'text',
    label: 'Text',
    icon: 'fa-file-lines',
    mime: 'text/plain',
    extensions: ['txt', 'text', 'conf', 'log', 'ini'],
    category: 'text'
  }
]

// Fallback for unknown types
const UNKNOWN_TYPE = {
  syntax: 'auto',
  label: 'Unknown',
  icon: 'fa-file',
  mime: 'application/octet-stream',
  extensions: [],
  category: 'unknown'
}

export function getFileTypeDefinition(contentType) {
  if (!contentType) return FILE_TYPES.find(t => t.syntax === 'text')

  const lowerType = contentType.toLowerCase()

  // First, try exact MIME type match
  const exactMatch = FILE_TYPES.find(t => lowerType === t.mime.toLowerCase())
  if (exactMatch) return exactMatch

  // Then try partial MIME type match (for variations like text/html; charset=utf-8)
  const mimeMatch = FILE_TYPES.find(t => lowerType.startsWith(t.mime.toLowerCase()))
  if (mimeMatch) return mimeMatch

  // Special cases for generic matches
  if (lowerType.includes('pdf')) return FILE_TYPES.find(t => t.syntax === 'pdf')
  if (lowerType.includes('image')) return FILE_TYPES.find(t => t.syntax === 'image')
  if (lowerType.includes('csv')) return FILE_TYPES.find(t => t.syntax === 'csv')
  if (lowerType.includes('zip') || lowerType.includes('archive') || lowerType.includes('tar') || lowerType.includes('gzip')) return FILE_TYPES.find(t => t.syntax === 'archive')
  
  // Try syntax substring match (less reliable, but catches some edge cases)
  const syntaxMatch = FILE_TYPES.find(t => lowerType.includes(t.syntax) && t.syntax.length > 2)
  if (syntaxMatch) return syntaxMatch

  // Fallback to text if it includes text
  if (lowerType.includes('text')) return FILE_TYPES.find(t => t.syntax === 'text')

  return UNKNOWN_TYPE
}

export function getTypeLabel(contentType) {
  return getFileTypeDefinition(contentType).label
}

export function getTypeIcon(contentType) {
  return getFileTypeDefinition(contentType).icon
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
  const type = FILE_TYPES.find(t => t.syntax === syntax)
  return type ? type.mime : 'text/plain'
}

// Map language selection to file extensions
export function getFileExtension(syntax) {
  const type = FILE_TYPES.find(t => t.syntax === syntax)
  return type ? type.extensions[0] : 'txt'
}

// Auto-detect language hint from content type
export function detectLanguageHint(contentType) {
  if (!contentType) return 'auto'
  const type = getFileTypeDefinition(contentType)
  return type.syntax !== 'auto' ? type.syntax : 'auto'
}

// Get syntax from file extension
export function getSyntaxFromExtension(extension) {
  if (!extension) return null
  const ext = extension.toLowerCase()
  const type = FILE_TYPES.find(t => t.extensions.includes(ext))
  return type ? type.syntax : null
}

// Check if content type is a code type
export function isCodeType(contentType) {
  if (!contentType) return false
  const type = getFileTypeDefinition(contentType)
  
  if (type.category === 'code') return true
  
  // Fallback checks for other common code indicators
  const lowerType = contentType.toLowerCase()
  if (lowerType.includes('script') || lowerType.includes('source')) {
    return true
  }

  return false
}

// Get all available syntax options for forms
export function getAvailableSyntaxOptions() {
  const options = [
    { value: 'auto', label: 'Auto-detect' },
    ...FILE_TYPES
      .filter(t => ['code', 'text', 'markdown', 'html', 'pdf', 'csv'].includes(t.category))
      .map(t => ({ value: t.syntax, label: t.label }))
  ]
  return options
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

// Check if content type is binary/non-editable
export function isBinaryType(contentType) {
  const type = getFileTypeDefinition(contentType)
  return ['image', 'pdf', 'archive', 'unknown'].includes(type.category)
}
