/**
 * Frontend content processors for different file types
 * Processes raw content into formatted previews
 */

import hljs from 'highlight.js'
import { processMarkdown } from './markdownProcessor.js'
import { processPDF } from './pdfProcessor.js'
import { detectLanguageHint, isCodeType, getFileTypeDefinition } from './typeUtils.js'

/**
 * Helper to decode content to string
 */
function decodeContent(content) {
  return typeof content === 'string' ? content : new TextDecoder().decode(content)
}

/**
 * Helper to get common text metadata
 */
function getTextMetadata(text) {
  return {
    lineCount: text.split(/\r?\n/).length,
    charCount: text.length
  }
}

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
 * Process text content
 */
export function processText(content) {
  const text = decodeContent(content)
  const metadata = getTextMetadata(text)

  return {
    type: 'text',
    preview: text,
    metadata: {
      ...metadata,
      wordCount: text.split(/\s+/).length
    }
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

/**
 * Process image content
 */
export function processImage(content) {
  const blob = new Blob([content], { type: 'image/*' })
  const url = URL.createObjectURL(blob)

  return {
    type: 'image',
    url,
    metadata: {
      // Additional metadata would need canvas inspection
    }
  }
}

/**
 * Process markdown content
 */
export { processMarkdown }

/**
 * Process HTML content
 */
export function processHTML(content) {
  const text = decodeContent(content)

  return {
    type: 'html',
    html: text,
    metadata: {
      charCount: text.length,
      // Basic HTML structure validation
      hasDoctype: text.toLowerCase().includes('<!doctype'),
      hasHtmlTag: text.toLowerCase().includes('<html'),
      hasBodyTag: text.toLowerCase().includes('<body')
    }
  }
}

/**
 * Process CSV content
 */
export function processCSV(content) {
  const text = decodeContent(content)
  const lines = text.split(/\r?\n/)
  const headers = lines[0]?.split(',').map(h => h.trim()) || []
  const rows = lines.slice(1, 11).map(line => {
    const cells = line.split(',')
    const row = {}
    headers.forEach((header, idx) => {
      row[header] = cells[idx]?.trim() || ''
    })
    return row
  })

  return {
    type: 'csv',
    rows,
    metadata: {
      columnCount: headers.length,
      rowCount: lines.length - 1,
      columns: headers
    }
  }
}

/**
 * Main processor function that delegates to type-specific processors
 */
export async function processContent(content, contentType, languageHint) {
  // Check language hint first for specific overrides
  if (languageHint === 'markdown' || languageHint === 'md') {
    return processMarkdown(content)
  }

  const typeDef = getFileTypeDefinition(contentType)

  switch (typeDef.category) {
    case 'html':
      return processHTML(content)
    case 'markdown':
      return processMarkdown(content)
    case 'pdf':
      return processPDF(content)
    case 'csv':
      return processCSV(content)
    case 'image':
      return processImage(content)
    case 'code':
      return processCode(content, contentType, languageHint)
    case 'text':
      return processText(content)
    default:
      // Fallback for unknown types that might still be code
      if (isCodeType(contentType)) {
        return processCode(content, contentType, languageHint)
      }
      return processText(content)
  }
}
