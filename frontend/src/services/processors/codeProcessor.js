import { detectLanguageHint } from '../typeUtils.js'
import { decodeContent, getTextMetadata } from './utils/contentUtils'
import { parseAnsiCodes, containsAnsiCodes } from './utils/ansiUtils'

let hljs = null;

async function ensureHljs() {
  if (!hljs) {
    hljs = (await import('highlight.js')).default;
  }
  return hljs;
}

/**
 * Detect programming language from content
 */
export async function detectLanguage(content, contentType, languageHint) {
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
        const h = await ensureHljs();
        const result = h.highlightAuto(content.slice(0, 1000))
        return result.language || 'plaintext'
    } catch (e) {
        return 'plaintext'
    }
}

/**
 * Highlight code with syntax highlighting
 */
export async function highlightCode(content, language) {
    try {
        const h = await ensureHljs();
        const highlighted = h.highlight(content, { language, ignoreIllegals: true })
        return highlighted.value
    } catch (e) {
        const h = await ensureHljs();
        return h.highlight(content, { language: 'plaintext' }).value
    }
}

/**
 * Process code content with syntax highlighting
 */
export async function processCode(content, contentType, languageHint) {
    const text = decodeContent(content)
    const language = await detectLanguage(text, contentType, languageHint)
    const metadata = getTextMetadata(text)

    // Check for ANSI codes even in code files
    if (containsAnsiCodes(text)) {
        const { text: cleanText, decorations } = parseAnsiCodes(text)
        return {
            type: 'code',
            preview: cleanText,
            highlighted: await highlightCode(cleanText, language),
            ansiDecorations: decorations,
            hasAnsiCodes: true,
            metadata: {
                ...metadata,
                language,
                hasAnsiCodes: true
            }
        }
    }

    return {
        type: 'code',
        preview: text,
        highlighted: await highlightCode(text, language),
        hasAnsiCodes: false,
        metadata: {
            ...metadata,
            language
        }
    }
}
