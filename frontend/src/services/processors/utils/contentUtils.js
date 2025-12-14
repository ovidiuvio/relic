/**
 * Helper to decode content to string
 */
export function decodeContent(content) {
    return typeof content === 'string' ? content : new TextDecoder().decode(content)
}

/**
 * Helper to get common text metadata
 */
export function getTextMetadata(text) {
    return {
        lineCount: text.split(/\r?\n/).length,
        charCount: text.length
    }
}
