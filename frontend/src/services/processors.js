/**
 * Frontend content processors for different file types
 * Processes raw content into formatted previews
 */

import hljs from 'highlight.js'
import { processMarkdown } from './markdownProcessor.js'
import { processPDF } from './pdfProcessor.js'
import { detectLanguageHint, isCodeType } from './typeUtils.js'

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
  const text = typeof content === 'string' ? content : new TextDecoder().decode(content)

  return {
    type: 'text',
    preview: text,
    metadata: {
      lineCount: text.split('\n').length,
      charCount: text.length,
      wordCount: text.split(/\s+/).length
    }
  }
}

/**
 * Process code content with syntax highlighting
 */
export function processCode(content, contentType, languageHint) {
  const text = typeof content === 'string' ? content : new TextDecoder().decode(content)
  const language = detectLanguage(text, contentType, languageHint)

  return {
    type: 'code',
    preview: text,
    highlighted: highlightCode(text, language),
    metadata: {
      language,
      lineCount: text.split('\n').length,
      charCount: text.length
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
  const text = typeof content === 'string' ? content : new TextDecoder().decode(content)

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
  const text = typeof content === 'string' ? content : new TextDecoder().decode(content)
  const lines = text.split('\n')
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
  const contentTypeLower = contentType.toLowerCase()

  // HTML
  if (
    contentTypeLower.includes('text/html') ||
    contentTypeLower.includes('application/xhtml+xml') ||
    contentTypeLower.includes('html')
  ) {
    return processHTML(content)
  }

  // Markdown
  if (
    contentTypeLower.includes('markdown') ||
    contentTypeLower.includes('text/markdown') ||
    languageHint === 'markdown' ||
    languageHint === 'md'
  ) {
    return processMarkdown(content)
  }

  // PDFs (check BEFORE code files to prevent Monaco display)
  if (contentTypeLower.includes('pdf') || contentTypeLower.includes('application/pdf')) {
    return processPDF(content)
  }

  // CSV
  if (contentTypeLower.includes('csv')) {
    return processCSV(content)
  }

  // Images
  if (contentTypeLower.includes('image')) {
    return processImage(content)
  }

  // Code files
  if (isCodeType(contentTypeLower)) {
    return processCode(content, contentType, languageHint)
  }

  // Text (fallback)
  if (contentTypeLower.includes('text')) {
    return processText(content)
  }

  // Unknown - return as text
  return processText(content)
}
