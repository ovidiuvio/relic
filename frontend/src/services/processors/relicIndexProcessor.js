import { decodeContent } from './utils/contentUtils'
import { getFileTypeDefinition } from '../typeUtils'

/**
 * Process a relic index file (list of relic IDs)
 * Supports both simple list of IDs and structured YAML with metadata
 */
async function processRelicIndexInternal(content) {
    const text = decodeContent(content)
    const lines = text.split('\n')
    const relicIds = []
    let title = 'Relic Index'
    let description = ''

    // Simple check if it's structured YAML
    const isStructured = text.includes('relics:')

    if (isStructured) {
        // Basic YAML parsing for our specific format to avoid heavy dependency
        let inRelics = false
        let currentRelic = null

        for (const line of lines) {
            const trimmed = line.trim()

            if (trimmed.startsWith('title:')) {
                if (!inRelics) title = trimmed.substring(6).trim()
                else if (currentRelic) currentRelic.title = trimmed.substring(6).trim()
            } else if (trimmed.startsWith('description:')) {
                if (!inRelics) description = trimmed.substring(12).trim()
                else if (currentRelic) currentRelic.description = trimmed.substring(12).trim()
            } else if (trimmed.startsWith('relics:')) {
                inRelics = true
            } else if (inRelics && trimmed.startsWith('- id:')) {
                const id = trimmed.substring(5).trim()
                if (/^[a-f0-9]{32}$/i.test(id)) {
                    currentRelic = { id }
                    relicIds.push(currentRelic)
                }
            } else if (inRelics && trimmed.startsWith('tags:')) {
                // Simple tag parsing [tag1, tag2]
                if (currentRelic) {
                    const tagsContent = trimmed.substring(5).trim()
                    if (tagsContent.startsWith('[') && tagsContent.endsWith(']')) {
                        currentRelic.tags = tagsContent.slice(1, -1).split(',').map(t => t.trim())
                    }
                }
            }
        }
    } else {
        // Fallback to simple ID scanning
        const idPattern = /\b[a-f0-9]{32}\b/g
        let match
        while ((match = idPattern.exec(text)) !== null) {
            relicIds.push({ id: match[0] })
        }
    }

    return {
        type: 'relicindex',
        relics: relicIds,
        meta: {
            title,
            description,
            count: relicIds.length
        }
    }
}

// Rename to match export
export const processRelicIndex = processRelicIndexInternal

/**
 * Check if content looks like a relic index
 */
export function isRelicIndex(content, contentType) {
    // If explicitly identified as relic index by extension/mime
    if (contentType === 'application/x-relic-index') return true

    // Don't treat binary formats (archives, PDFs, images) as relic indexes
    const typeDef = getFileTypeDefinition(contentType)
    if (typeDef.category === 'archive' || typeDef.category === 'pdf' || typeDef.category === 'image') {
        return false
    }

    const text = decodeContent(content)

    // Check for structured format signature
    if (text.includes('relics:') && text.includes('- id:')) return true

    // Fallback heuristic for simple lists
    const lines = text.split(/\r?\n/).filter(l => l.trim())
    if (lines.length === 0) return false

    const idPattern = /^[a-f0-9]{32}$/
    const listItemPattern = /^-\s+[a-f0-9]{32}$/

    let matchCount = 0
    for (const line of lines) {
        const trimmed = line.trim()
        if (idPattern.test(trimmed) || listItemPattern.test(trimmed)) {
            matchCount++
        }
    }

    return matchCount > 0 && (matchCount / lines.length) > 0.5
}
