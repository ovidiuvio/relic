import { getRelicRaw, forkRelic, createRelic } from './api' // Auto-resolves to api/index.js if api.js is gone, or we might need to be specific if keeping api.js
import { showToast } from '../stores/toastStore'
import { copyToClipboard } from './utils/clipboard'
import { triggerDownload, getExtensionFromMimeType } from './utils/download'
import { decodeContent } from './processors/utils/contentUtils'

export { copyToClipboard, getExtensionFromMimeType }

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

    // Generate appropriate file extension from MIME type
    const extension = getExtensionFromMimeType(contentType)

    // Generate filename from relic name with correct extension, or use default
    const cleanName = relicName ? relicName.replace(/[^a-zA-Z0-9-_]/g, '_') : relicId
    const filename = `${cleanName}.${extension}`

    triggerDownload(response.data, filename, contentType || 'text/plain')
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
      'never',
      relic.tags ? relic.tags.map(t => typeof t === 'string' ? t : t.name) : []
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
  triggerDownload(fileContent, fileName, contentType)
}

export async function copyArchiveFileContent(fileContent) {
  try {
    const text = decodeContent(fileContent)
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
    // We use createRelic from api service properly now
    // Note: formData construction is handled in createRelic service
    const relicData = {
      file,
      name: fileName,
      access_level: 'public',
      expires_in: 'never'
    }

    const response = await createRelic(relicData)
    const newRelic = response.data

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