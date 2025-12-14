import hljs from 'highlight.js'
import { detectLanguageHint } from '../typeUtils.js'
import { decodeContent, getTextMetadata } from './utils/contentUtils'

/**
 * Detect programming language from content
 */
export function detectLanguage(content, contentType, languageHint) {
    if (languageHint && languageHint !== 'auto') {
        return languageHint
    }

    // Try to detect from content type using our unified logic
    const detected = detectLanguageHint(contentType)
    if (detected && detected !== 'auto' && detected !== 'text') {
        return detected
    }

    // Try to auto-detect based on content
    try {
        const result = hljs.highlightAuto(content.slice(0, 1000))
        return result.language || 'plaintext'
    } catch (e) {
        return 'plaintext'
    }
}

/**
 * Highlight code with syntax highlighting
 */
export function highlightCode(content, language) {
    try {
        const highlighted = hljs.highlight(content, { language, ignoreIllegals: true })
        return highlighted.value
    } catch (e) {
        // Fallback to plain text if highlighting fails
        return hljs.highlight(content, { language: 'plaintext' }).value
    }
}

/**
 * Process code content with syntax highlighting
 */
export function processCode(content, contentType, languageHint) {
    const text = decodeContent(content)
    const language = detectLanguage(text, contentType, languageHint)
    const metadata = getTextMetadata(text)

    return {
        type: 'code',
        preview: text,
        highlighted: highlightCode(text, language),
        metadata: {
            ...metadata,
            language
        }
    }
}
