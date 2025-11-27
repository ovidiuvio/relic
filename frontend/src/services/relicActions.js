import { getRelicRaw } from './api'
import { showToast } from '../stores/toastStore'

export function getFileExtension(contentType) {
  if (!contentType) return 'txt'

  const extensionMap = {
    'text/plain': 'txt',
    'text/markdown': 'md',
    'text/html': 'html',
    'text/css': 'css',
    'text/javascript': 'js',
    'application/javascript': 'js',
    'text/x-javascript': 'js',
    'application/json': 'json',
    'text/xml': 'xml',
    'application/xml': 'xml',
    'text/x-python': 'py',
    'application/x-python': 'py',
    'text/x-shellscript': 'sh',
    'application/x-sh': 'sh',
    'application/sql': 'sql',
    'text/x-java-source': 'java',
    'text/x-java': 'java',
    'application/java': 'java',
    'text/csv': 'csv',
    'application/csv': 'csv',
    'text/yaml': 'yml',
    'application/x-yaml': 'yml',
    'text/x-yaml': 'yml',
    'application/xml+xslt': 'xsl',
    'text/x-less': 'less',
    'text/x-scss': 'scss',
    'text/x-typescript': 'ts',
    'application/typescript': 'ts',
    'application/tsx': 'tsx',
    'application/jsx': 'jsx',
    'text/php': 'php',
    'application/php': 'php',
    'text/x-c': 'c',
    'text/x-c++': 'cpp',
    'text/x-csharp': 'cs',
    'text/x-go': 'go',
    'text/x-ruby': 'rb',
    'text/x-rust': 'rs',
    'application/pdf': 'pdf',
    'application/zip': 'zip',
    'application/x-tar': 'tar',
    'application/x-gzip': 'gz',
    'application/gzip': 'gz',
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/gif': 'gif',
    'image/svg+xml': 'svg'
  }

  // Check for exact match first
  if (extensionMap[contentType]) {
    return extensionMap[contentType]
  }

  // Check for partial matches
  for (const [type, ext] of Object.entries(extensionMap)) {
    if (contentType.includes(type)) {
      return ext
    }
  }

  // Default fallback patterns
  if (contentType.includes('text/')) {
    if (contentType.includes('plain')) return 'txt'
    return 'txt'
  }
  if (contentType.includes('application/')) {
    return 'txt'
  }
  if (contentType.includes('image/')) {
    return 'img'
  }

  return 'txt'
}

export async function copyToClipboard(text, successMessage = 'Copied to clipboard!') {
  try {
    await navigator.clipboard.writeText(text)
    showToast(successMessage, 'success')
  } catch (error) {
    console.error('Failed to copy to clipboard:', error)
    showToast('Failed to copy to clipboard', 'error')
  }
}

export function shareRelic(relicId) {
  // Read current URL and include any line number parameters
  const currentUrl = window.location.href
  const urlParts = currentUrl.split('#')
  const baseUrl = urlParts[0] || `${window.location.origin}/${relicId}`
  const fragment = urlParts[1] || ''

  const shareUrl = fragment ? `${baseUrl}#${fragment}` : baseUrl
  copyToClipboard(shareUrl, 'Link copied to clipboard!')
}

export async function copyRelicContent(relicId) {
  try {
    const response = await getRelicRaw(relicId)
    const content = await response.data.text()
    copyToClipboard(content, 'Content copied to clipboard!')
  } catch (error) {
    console.error('Failed to copy relic content:', error)
    showToast('Failed to copy relic content', 'error')
  }
}

export async function downloadRelic(relicId, relicName, contentType) {
  try {
    const response = await getRelicRaw(relicId)
    const blob = new Blob([response.data], { type: contentType || 'text/plain' })
    const url = window.URL.createObjectURL(blob)

    // Generate appropriate file extension based on content type
    const extension = getFileExtension(contentType)

    // Generate filename from relic name with correct extension, or use default
    const cleanName = relicName ? relicName.replace(/[^a-zA-Z0-9-_]/g, '_') : relicId
    const filename = `${cleanName}.${extension}`

    // Create temporary link and trigger download
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    // Clean up object URL
    window.URL.revokeObjectURL(url)

    showToast(`Downloading ${filename}...`, 'success')
  } catch (error) {
    console.error('Failed to download relic:', error)
    showToast('Failed to download relic', 'error')
  }
}

export function viewRaw(relicId) {
  window.open(`/${relicId}/raw`, '_blank')
}