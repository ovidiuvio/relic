/**
 * PDF processor using PDF.js
 * Handles PDF document loading, metadata extraction, and page rendering
 */

import * as pdfjsLib from 'pdfjs-dist'

// Configure worker path for PDF.js
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.mjs',
  import.meta.url
).toString()

/**
 * Process PDF content
 * @param {Uint8Array} content - Raw PDF bytes
 * @param {string|null} password - Optional password for protected PDFs
 * @returns {Promise<Object>} Processed PDF object with metadata
 */
export async function processPDF(content, password = null) {
  try {
    // Load PDF document
    const loadingTask = pdfjsLib.getDocument({
      data: content,
      password: password
    })

    const pdf = await loadingTask.promise

    // Extract metadata
    const metadata = await pdf.getMetadata().catch(() => ({ info: {}, metadata: null }))
    const outline = await pdf.getOutline().catch(() => null)

    return {
      type: 'pdf',
      pdfDocument: pdf, // Keep reference for rendering
      metadata: {
        numPages: pdf.numPages,
        title: metadata.info?.Title || null,
        author: metadata.info?.Author || null,
        subject: metadata.info?.Subject || null,
        keywords: metadata.info?.Keywords || null,
        creator: metadata.info?.Creator || null,
        producer: metadata.info?.Producer || null,
        creationDate: metadata.info?.CreationDate || null,
        modificationDate: metadata.info?.ModDate || null,
        hasOutline: outline !== null && outline.length > 0,
        pdfVersion: metadata.info?.PDFFormatVersion || null
      },
      passwordRequired: false
    }
  } catch (error) {
    console.error('PDF processing error:', error)

    // Check if password is required
    if (error.name === 'PasswordException') {
      return {
        type: 'pdf',
        pdfDocument: null,
        metadata: null,
        passwordRequired: true,
        passwordError: password ? 'Incorrect password' : null
      }
    }

    throw new Error(`Failed to load PDF: ${error.message}`)
  }
}

/**
 * Render a specific page to canvas
 * @param {PDFDocumentProxy} pdfDocument - PDF.js document object
 * @param {number} pageNumber - Page number (1-indexed)
 * @param {HTMLCanvasElement} canvas - Canvas element to render to
 * @param {number} scale - Rendering scale (default: 1.5 for good quality)
 * @returns {Promise<Object>} Rendered dimensions { width, height }
 */
export async function renderPDFPage(pdfDocument, pageNumber, canvas, scale = 1.5) {
  try {
    const page = await pdfDocument.getPage(pageNumber)

    // Account for device pixel ratio for sharp rendering on high-DPI displays
    const dpr = window.devicePixelRatio || 1
    const viewport = page.getViewport({ scale: scale * dpr })

    const context = canvas.getContext('2d')

    // Set canvas actual size (accounting for DPR)
    canvas.height = viewport.height
    canvas.width = viewport.width

    // Set canvas display size (CSS pixels)
    canvas.style.width = `${viewport.width / dpr}px`
    canvas.style.height = `${viewport.height / dpr}px`

    const renderContext = {
      canvasContext: context,
      viewport: viewport
    }

    await page.render(renderContext).promise

    return {
      width: viewport.width / dpr,
      height: viewport.height / dpr
    }
  } catch (error) {
    console.error(`Error rendering page ${pageNumber}:`, error)
    throw error
  }
}

/**
 * Get supported languages for code highlighting (placeholder for future use)
 */
export function isPDFSupported() {
  return typeof pdfjsLib !== 'undefined'
}

export default {
  processPDF,
  renderPDFPage,
  isPDFSupported
}
