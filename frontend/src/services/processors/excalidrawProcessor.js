/**
 * Excalidraw content processor
 * Processes .excalidraw and .excalidraw.json files
 */

/**
 * Helper to decode content to string
 */
function decodeContent(content) {
  return typeof content === 'string' ? content : new TextDecoder().decode(content)
}

/**
 * Process Excalidraw drawing content
 */
export function processExcalidraw(content, contentType) {
  const text = decodeContent(content)

  try {
    // Parse the JSON
    const excalidrawData = JSON.parse(text)

    // Validate that it's actually Excalidraw format
    // Excalidraw files have a specific structure with elements array and/or type field
    const isValid = excalidrawData && (
      Array.isArray(excalidrawData.elements) ||
      (excalidrawData.type === 'excalidraw')
    )

    if (!isValid) {
      throw new Error('Invalid Excalidraw format: missing elements array or type field')
    }

    return {
      type: 'excalidraw',
      data: excalidrawData,
      rawContent: text,
      metadata: {
        elementCount: excalidrawData.elements?.length || 0,
        hasAppState: !!excalidrawData.appState,
        version: excalidrawData.version || 'unknown',
        source: excalidrawData.source || 'unknown'
      }
    }
  } catch (error) {
    console.error('[ExcalidrawProcessor] Failed to parse Excalidraw data:', error)

    // Fallback to error state if parsing fails
    return {
      type: 'excalidraw',
      data: null,
      rawContent: text,
      error: error.message,
      metadata: {
        elementCount: 0,
        hasAppState: false,
        parseError: true
      }
    }
  }
}
