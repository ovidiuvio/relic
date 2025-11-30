import { getRelicRaw, forkRelic } from './api'
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
  // Get current URL (preserves full path including archive file paths)
  const hash = window.location.hash
  const pathname = window.location.pathname
  const shareUrl = `${window.location.origin}${pathname}${hash}`
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

export async function fastForkRelic(relic) {
  try {
    // Get raw content of the relic
    const response = await getRelicRaw(relic.id)
    const blob = await response.data
    const file = new File([blob], relic.name || `${relic.id}.txt`, { type: relic.content_type || 'text/plain' })

    // Create fork with default settings (public, never expires, same name)
    const forkResponse = await forkRelic(
      relic.id,
      file,
      relic.name || null, // Keep the same name, let API handle null case
      'public',
      'never'
    )

    const forkedRelic = forkResponse.data
    showToast('Relic forked successfully!', 'success')

    // Navigate to the new forked relic
    window.location.href = `/${forkedRelic.id}`

  } catch (error) {
    console.error('Failed to fork relic:', error)
    showToast(error.message || 'Failed to fork relic', 'error')
  }
}

export function viewRaw(relicId) {
  window.open(`/${relicId}/raw`, '_blank')
}

// ===== Archive File Actions =====

export function downloadArchiveFile(fileContent, fileName, contentType) {
  try {
    const blob = new Blob([fileContent], { type: contentType || 'text/plain' })
    const url = window.URL.createObjectURL(blob)

    // Use the actual file name
    const link = document.createElement('a')
    link.href = url
    link.download = fileName
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    window.URL.revokeObjectURL(url)

    showToast(`Downloading ${fileName}...`, 'success')
  } catch (error) {
    console.error('Failed to download archive file:', error)
    showToast('Failed to download file', 'error')
  }
}

export async function copyArchiveFileContent(fileContent) {
  try {
    let text
    if (typeof fileContent === 'string') {
      text = fileContent
    } else {
      // Convert Uint8Array to string
      text = new TextDecoder().decode(fileContent)
    }
    copyToClipboard(text, 'Content copied to clipboard!')
  } catch (error) {
    console.error('Failed to copy archive file content:', error)
    showToast('Failed to copy content', 'error')
  }
}

export async function fastForkArchiveFile(fileContent, fileName, contentType) {
  try {
    // Create a File object from the extracted content
    const file = new File([fileContent], fileName, { type: contentType || 'text/plain' })

    // Create a new relic (not a fork, since the archive file is not a relic itself)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('name', fileName)
    formData.append('access_level', 'public')
    formData.append('expires_in', 'never')

    // Use the createRelic API (we'll need to import this or use fetch directly)
    const response = await fetch('/api/v1/relics', {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      throw new Error('Failed to create relic from archive file')
    }

    const newRelic = await response.json()
    showToast('File saved as new relic!', 'success')

    // Navigate to the new relic
    window.location.href = `/${newRelic.id}`

  } catch (error) {
    console.error('Failed to create relic from archive file:', error)
    showToast(error.message || 'Failed to create relic from file', 'error')
  }
}

export function viewArchiveFileRaw(fileContent, fileName, contentType) {
  try {
    const blob = new Blob([fileContent], { type: contentType || 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    window.open(url, '_blank')

    // Clean up after a delay
    setTimeout(() => window.URL.revokeObjectURL(url), 10000)
  } catch (error) {
    console.error('Failed to view raw content:', error)
    showToast('Failed to view raw content', 'error')
  }
}