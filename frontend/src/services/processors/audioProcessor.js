/**
 * Process audio content
 */
export function processAudio(content, contentType) {
    // Use the specific content type for proper MIME type handling
    const mimeType = contentType || 'audio/*'
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)

    return {
        type: 'audio',
        url,
        metadata: {
            mimeType,
        }
    }
}
