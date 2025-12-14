import { decodeContent } from './utils/contentUtils'

/**
 * Process CSV content
 */
export function processCSV(content) {
    const text = decodeContent(content)
    const lines = text.split(/\r?\n/)
    const headers = lines[0]?.split(',').map(h => h.trim()) || []
    const rows = lines.slice(1).map(line => {
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
            columns: headers,
            fileSize: content.byteLength || text.length
        }
    }
}
