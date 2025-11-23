import { getPasteRaw } from './api'
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

export function sharePaste(pasteId) {
  const shareUrl = `${window.location.origin}/${pasteId}`
  copyToClipboard(shareUrl, 'Link copied to clipboard!')
}

export async function copyPasteContent(pasteId) {
  try {
    const response = await getPasteRaw(pasteId)
    const content = await response.data.text()
    copyToClipboard(content, 'Content copied to clipboard!')
  } catch (error) {
    console.error('Failed to copy paste content:', error)
    showToast('Failed to copy paste content', 'error')
  }
}

export async function downloadPaste(pasteId, pasteName, contentType) {
  try {
    const response = await getPasteRaw(pasteId)
    const blob = new Blob([response.data], { type: contentType || 'text/plain' })
    const url = window.URL.createObjectURL(blob)

    // Generate appropriate file extension based on content type
    const extension = getFileExtension(contentType)

    // Generate filename from paste name with correct extension, or use default
    const cleanName = pasteName ? pasteName.replace(/[^a-zA-Z0-9-_]/g, '_') : pasteId
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
    console.error('Failed to download paste:', error)
    showToast('Failed to download paste', 'error')
  }
}

export function viewRaw(pasteId) {
  window.open(`/${pasteId}/raw`, '_blank')
}