/**
 * Frontend content processors for different file types
 * Processes raw content into formatted previews
 */

import { getFileTypeDefinition, isCodeType } from '../typeUtils.js'

// Import processors from their specific files
import { processText, shouldEnableAnsiByDefault } from './textProcessor.js'
import { processCode, detectLanguage, highlightCode } from './codeProcessor.js'
import { processImage } from './imageProcessor.js'
import { processHTML } from './htmlProcessor.js'
import { processCSV } from './csvProcessor.js'
import { processRelicIndex, isRelicIndex } from './relicIndexProcessor.js'
import { processMarkdown } from './markdownProcessor.js'
import { processPDF } from './pdfProcessor.js'
import { processArchive } from './archiveProcessor.js'
import { processExcalidraw } from './excalidrawProcessor.js'

// Re-export specific processors and helpers for direct usage
export {
  processText,
  shouldEnableAnsiByDefault,
  processCode,
  detectLanguage,
  highlightCode,
  processImage,
  processHTML,
  processCSV,
  processRelicIndex,
  isRelicIndex,
  processMarkdown, // Was already re-exported
  processPDF,
  processArchive,
  processExcalidraw
}

/**
 * Main processor function that delegates to type-specific processors
 */
export async function processContent(content, contentType, languageHint) {
  // Check language hint first for specific overrides
  if (languageHint === 'markdown' || languageHint === 'md') {
    return processMarkdown(content)
  }

  // Check for relicindex
  if (isRelicIndex(content, contentType)) {
    return processRelicIndex(content)
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
      return processImage(content, contentType)
    case 'archive':
      return processArchive(content, contentType)
    case 'excalidraw':
      return processExcalidraw(content, contentType)
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
