import { decodeContent, getTextMetadata } from './utils/contentUtils'
import { parseAnsiCodes, containsAnsiCodes } from './utils/ansiUtils'

/**
 * Determine if ANSI processing should be enabled by default for this file
 */
export function shouldEnableAnsiByDefault(metadata, contentType, language) {
    const ct = (contentType || '').toLowerCase()
    const lang = (language || '').toLowerCase()

    // Enable for log files
    if (ct.includes('log') || lang === 'log') return true
    if (metadata && (metadata.language === 'log' || metadata.language === 'text')) {
        // Check if filename suggests it's a log
        return true
    }

    // Disable for code files and structured data
    const codeExtensions = [
        'javascript', 'typescript', 'python', 'java', 'go', 'rust', 'c', 'cpp',
        'csharp', 'ruby', 'php', 'swift', 'kotlin', 'scala', 'groovy', 'gradle',
        'html', 'xml', 'json', 'yaml', 'css', 'scss', 'less', 'sql', 'dockerfile',
        'makefile', 'bash', 'sh', 'zsh', 'ps1', 'ps2'
    ]

    if (codeExtensions.includes(lang)) return false

    // Default to OFF unless explicitly detected as log
    return false
}

/**
 * Process text content
 */
export function processText(content, contentType = null, languageHint = null) {
    const text = decodeContent(content)
    const metadata = getTextMetadata(text)

    // Check for ANSI codes and parse them for Monaco decorations
    if (containsAnsiCodes(text)) {
        const { text: cleanText, decorations } = parseAnsiCodes(text)

        // Determine if ANSI should be enabled by default
        const ansiEnabled = shouldEnableAnsiByDefault(metadata, contentType, languageHint)

        return {
            type: 'text',
            preview: cleanText,
            ansiDecorations: decorations,
            ansiEnabled: ansiEnabled,
            hasAnsiCodes: true,
            metadata: {
                ...metadata,
                hasAnsiCodes: true,
                wordCount: cleanText.split(/\s+/).length
            }
        }
    }

    return {
        type: 'text',
        preview: text,
        ansiEnabled: false,
        hasAnsiCodes: false,
        metadata: {
            ...metadata,
            wordCount: text.split(/\s+/).length
        }
    }
}
