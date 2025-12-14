import { FILE_TYPES } from './data/fileTypes'
import { formatBytes, formatTimeAgo } from './utils/formatting'

// Re-export helpers
export { formatBytes, formatTimeAgo }

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
  if (lowerType.includes('notebook') || lowerType.includes('ipynb')) return FILE_TYPES.find(t => t.syntax === 'notebook')
  if (lowerType.includes('zip') || lowerType.includes('archive') || lowerType.includes('tar') || lowerType.includes('gzip')) return FILE_TYPES.find(t => t.syntax === 'archive')

  // Extension-based detection for files with custom formats (e.g., .excalidraw, .excalidraw.json)
  const extensionMatch = FILE_TYPES.find(t => {
    if (!t.extensions || t.extensions.length === 0) return false
    return t.extensions.some(ext => {
      // Check if contentType ends with the extension (handles compound extensions)
      return lowerType.endsWith(`.${ext}`) || lowerType.endsWith(`/${ext}`)
    })
  })
  if (extensionMatch) return extensionMatch

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
  // Can be enhanced if we move color logic here
  return 'text-gray-500'
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

// Get all available syntax options for forms (flat list, searchable by language name)
export function getAvailableSyntaxOptions() {
  // Popular languages that should appear at the top
  const popularLanguages = ['javascript', 'typescript', 'python', 'java', 'html', 'css', 'json', 'markdown', 'sql', 'bash']

  // Filter FILE_TYPES to only include code-related categories
  const codeTypes = FILE_TYPES.filter(t =>
    ['code', 'text', 'markdown', 'html'].includes(t.category)
  )

  // Get popular languages first
  const popularOptions = popularLanguages
    .map(lang => codeTypes.find(t => t.syntax === lang))
    .filter(Boolean)
    .map(t => ({ value: t.syntax, label: t.label }))

  // Get all other languages sorted alphabetically
  const otherOptions = codeTypes
    .filter(t => !popularLanguages.includes(t.syntax))
    .map(t => ({ value: t.syntax, label: t.label }))
    .sort((a, b) => a.label.localeCompare(b.label))

  // Return flat list: Auto-detect, then popular, then rest alphabetically
  return [
    { value: 'auto', label: 'Auto-detect' },
    ...popularOptions,
    ...otherOptions
  ]
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
