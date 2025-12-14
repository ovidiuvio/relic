import { showToast } from '../../stores/toastStore'
import { getFileExtension as getSyntaxExtension, getFileTypeDefinition } from '../typeUtils'

/**
 * Determine best file extension for content type
 */
export function getFileExtension(contentType) {
    if (!contentType) return 'txt'

    // Use centralized type definitions
    const typeDef = getFileTypeDefinition(contentType)
    if (typeDef && typeDef.extensions && typeDef.extensions.length > 0) {
        return typeDef.extensions[0]
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

/**
 * Trigger a browser download for a blob or string content
 */
export function triggerDownload(content, filename, contentType = 'text/plain') {
    try {
        const blob = content instanceof Blob ? content : new Blob([content], { type: contentType })
        const url = window.URL.createObjectURL(blob)

        const link = document.createElement('a')
        link.href = url
        link.download = filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)

        window.URL.revokeObjectURL(url)

        showToast(`Downloading ${filename}...`, 'success')
        return true
    } catch (error) {
        console.error('Download failed:', error)
        showToast('Failed to download file', 'error')
        return false
    }
}
