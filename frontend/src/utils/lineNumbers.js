/**
 * Utilities for parsing and handling line numbers in URL fragments
 * Supports formats like:
 * - L1 (single line)
 * - L1-5 (range)
 * - L1,3,5-7 (multiple lines and ranges)
 * - L15-20,L25 (multiple ranges)
 */

/**
 * Parse line numbers from URL fragment
 * @param {string} fragment - URL fragment (e.g., "L1", "L1-5", "L1,3,5-7")
 * @returns {Object} - Parsed line information
 */
export function parseLineNumberFragment(fragment) {
  if (!fragment || !fragment.startsWith('L')) {
    return { lines: [], ranges: [], hasLines: false }
  }

  // Remove the 'L' prefix
  const lineSpec = fragment.substring(1)
  const lines = new Set()
  const ranges = []

  try {
    // Split by comma for multiple specifications
    const parts = lineSpec.split(',')

    for (const part of parts) {
      if (part.includes('-')) {
        // Handle range (e.g., "1-5")
        const [start, end] = part.split('-').map(n => parseInt(n, 10))
        if (!isNaN(start) && !isNaN(end) && start >= 1 && end >= start) {
          ranges.push({ start, end })
          // Add all lines in the range
          for (let i = start; i <= end; i++) {
            lines.add(i)
          }
        }
      } else {
        // Handle single line (e.g., "1")
        const lineNum = parseInt(part, 10)
        if (!isNaN(lineNum) && lineNum >= 1) {
          lines.add(lineNum)
          ranges.push({ start: lineNum, end: lineNum })
        }
      }
    }
  } catch (error) {
    console.warn('Invalid line number fragment:', fragment, error)
    return { lines: [], ranges: [], hasLines: false }
  }

  return {
    lines: Array.from(lines).sort((a, b) => a - b),
    ranges: ranges.sort((a, b) => a.start - b.start),
    hasLines: lines.size > 0
  }
}

/**
 * Create a line number fragment from lines array
 * @param {number[]} lines - Array of line numbers
 * @returns {string} - Fragment string (e.g., "L1,3,5-7")
 */
export function createLineNumberFragment(lines) {
  if (!lines || lines.length === 0) {
    return ''
  }

  const sortedLines = [...lines].sort((a, b) => a - b)
  const ranges = []
  let start = sortedLines[0]
  let end = start

  for (let i = 1; i < sortedLines.length; i++) {
    const current = sortedLines[i]
    if (current === end + 1) {
      // Continue the range
      end = current
    } else {
      // End current range and start new one
      if (start === end) {
        ranges.push(`${start}`)
      } else {
        ranges.push(`${start}-${end}`)
      }
      start = end = current
    }
  }

  // Add the final range
  if (start === end) {
    ranges.push(`${start}`)
  } else {
    ranges.push(`${start}-${end}`)
  }

  return `L${ranges.join(',')}`
}

/**
 * Get line number fragment from current URL
 * @returns {string|null} - Line number fragment or null
 */
export function getCurrentLineNumberFragment() {
  const hash = window.location.hash
  if (!hash) return null

  // Remove the # and check if it starts with L
  const fragment = hash.substring(1)
  return fragment.startsWith('L') ? fragment : null
}

/**
 * Update URL with line number fragment
 * @param {string} relicId - The relic ID
 * @param {string|number[]|null} lines - Line specification
 */
export function updateUrlWithLineNumbers(relicId, lines) {
  let fragment = ''

  if (typeof lines === 'string') {
    fragment = lines.startsWith('L') ? lines : ''
  } else if (Array.isArray(lines)) {
    fragment = createLineNumberFragment(lines)
  }

  // Use current pathname to preserve archive file paths
  const pathname = window.location.pathname
  const newUrl = `${pathname}${fragment ? `#${fragment}` : ''}`
  window.history.pushState({}, '', newUrl)
}

/**
 * Check if a line number is highlighted
 * @param {number} lineNumber - Line number to check
 * @param {Object} parsedLines - Result from parseLineNumberFragment
 * @returns {boolean} - Whether the line should be highlighted
 */
export function isLineHighlighted(lineNumber, parsedLines) {
  return parsedLines.lines.includes(lineNumber)
}
