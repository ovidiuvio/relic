/**
 * Process image content
 */
export function processImage(content, contentType) {
    // Use the specific content type for proper MIME type handling
    const mimeType = contentType || 'image/*'
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)

    return {
        type: 'image',
        url,
        metadata: {
            mimeType,
            // Additional metadata would need canvas inspection for raster images
        }
    }
}
