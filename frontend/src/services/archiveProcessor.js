/**
 * Archive processor for ZIP, TAR, and TAR.GZ files
 * Handles file listing extraction and individual file extraction
 */

import JSZip from 'jszip'
import untar from 'js-untar'
import { gunzipSync } from 'fflate'
import { detectLanguageHint } from './typeUtils.js'

/**
 * Detect archive type from content type
 */
function detectArchiveType(contentType) {
  const type = contentType.toLowerCase()

  // Check gzip BEFORE zip (since "gzip" contains "zip")
  if (type.includes('gzip') || type.includes('x-gzip')) return 'tar.gz'
  if (type.includes('x-tar') || type.includes('/tar')) return 'tar'
  if (type.includes('zip') && !type.includes('gzip')) return 'zip'

  return 'unknown'
}

/**
 * Format file size for display
 */
function formatSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

/**
 * Build file tree structure from flat file list
 */
function buildFileTree(files) {
  const tree = {
    name: '/',
    path: '',
    type: 'directory',
    children: [],
    size: 0
  }

  files.forEach(file => {
    const parts = file.path.split('/').filter(p => p)
    let current = tree

    parts.forEach((part, index) => {
      const isLast = index === parts.length - 1
      const isDirectory = file.type === 'directory' || !isLast

      let child = current.children.find(c => c.name === part)

      if (!child) {
        child = {
          name: part,
          path: parts.slice(0, index + 1).join('/'),
          type: isDirectory ? 'directory' : 'file',
          children: isDirectory ? [] : undefined,
          size: isLast ? file.size : 0,
          contentType: isLast ? file.contentType : undefined,
          languageHint: isLast ? file.languageHint : undefined
        }
        current.children.push(child)
      }

      if (isDirectory) {
        current = child
      }
    })
  })

  // Sort: directories first, then files, both alphabetically
  function sortTree(node) {
    if (node.children) {
      node.children.sort((a, b) => {
        if (a.type !== b.type) {
          return a.type === 'directory' ? -1 : 1
        }
        return a.name.localeCompare(b.name)
      })
      node.children.forEach(sortTree)
    }
  }
  sortTree(tree)

  return tree
}

/**
 * Get content type from file extension
 */
function getContentTypeFromPath(path) {
  const ext = path.split('.').pop()?.toLowerCase()

  const mimeTypes = {
    'txt': 'text/plain',
    'md': 'text/markdown',
    'json': 'application/json',
    'js': 'application/javascript',
    'ts': 'application/typescript',
    'html': 'text/html',
    'css': 'text/css',
    'py': 'text/x-python',
    'java': 'text/x-java',
    'cpp': 'text/x-c++',
    'c': 'text/x-c',
    'go': 'text/x-go',
    'rs': 'text/x-rust',
    'sh': 'application/x-sh',
    'yaml': 'text/yaml',
    'yml': 'text/yaml',
    'xml': 'application/xml',
    'svg': 'image/svg+xml',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'webp': 'image/webp',
    'pdf': 'application/pdf',
    'csv': 'text/csv',
    'zip': 'application/zip',
    'tar': 'application/x-tar',
    'gz': 'application/gzip'
  }

  return mimeTypes[ext] || 'application/octet-stream'
}

/**
 * Process ZIP archive
 */
async function processZip(content) {
  const zip = await JSZip.loadAsync(content)
  const files = []

  // Extract file metadata
  zip.forEach((relativePath, zipEntry) => {
    const contentType = getContentTypeFromPath(relativePath)
    const languageHint = detectLanguageHint(contentType)

    files.push({
      path: relativePath,
      name: relativePath.split('/').pop() || relativePath,
      size: zipEntry._data?.uncompressedSize || 0,
      type: zipEntry.dir ? 'directory' : 'file',
      contentType,
      languageHint,
      // Store reference for later extraction
      _zipEntry: zipEntry
    })
  })

  return {
    type: 'zip',
    files,
    fileTree: buildFileTree(files),
    // Function to extract a specific file
    extractFile: async (path) => {
      const file = zip.file(path)
      if (!file) throw new Error('File not found in archive')

      const contentType = getContentTypeFromPath(path)
      const isText = contentType.startsWith('text/') ||
                     contentType.includes('json') ||
                     contentType.includes('javascript') ||
                     contentType.includes('typescript') ||
                     contentType.includes('xml')

      if (isText) {
        return await file.async('string')
      } else {
        return await file.async('uint8array')
      }
    }
  }
}

/**
 * Process TAR or TAR.GZ archive
 */
async function processTar(content, isGzipped = false) {
  try {
    let data = content

    // Decompress gzip if needed
    if (isGzipped) {
      console.log('[Archive] Decompressing gzipped tar...')
      const uint8Array = content instanceof Uint8Array ? content : new Uint8Array(content)
      data = gunzipSync(uint8Array)
      console.log('[Archive] Decompression complete, size:', data.length)
    }

    // js-untar expects an ArrayBuffer
    const arrayBuffer = data instanceof ArrayBuffer
      ? data
      : data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength)

    const tarFiles = await untar(arrayBuffer)
    const files = []

    tarFiles.forEach(tarFile => {
      const contentType = getContentTypeFromPath(tarFile.name)
      const languageHint = detectLanguageHint(contentType)

      files.push({
        path: tarFile.name,
        name: tarFile.name.split('/').pop() || tarFile.name,
        size: tarFile.size || 0,
        type: tarFile.type === '5' || tarFile.name.endsWith('/') ? 'directory' : 'file',
        contentType,
        languageHint,
        // Store buffer for later extraction
        _buffer: tarFile.buffer
      })
    })

    return {
      type: 'tar',
      files,
      fileTree: buildFileTree(files),
      // Function to extract a specific file
      extractFile: async (path) => {
        const file = files.find(f => f.path === path)
        if (!file || file.type === 'directory') {
          throw new Error('File not found in archive')
        }

        const contentType = file.contentType
        const isText = contentType.startsWith('text/') ||
                       contentType.includes('json') ||
                       contentType.includes('javascript') ||
                       contentType.includes('typescript') ||
                       contentType.includes('xml')

        if (isText) {
          return new TextDecoder().decode(file._buffer)
        } else {
          return new Uint8Array(file._buffer)
        }
      }
    }
  } catch (error) {
    console.error('Error processing TAR archive:', error)
    throw new Error('Failed to process TAR archive: ' + error.message)
  }
}

/**
 * Main archive processor
 */
export async function processArchive(content, contentType) {
  const archiveType = detectArchiveType(contentType)

  try {
    let result

    if (archiveType === 'zip') {
      result = await processZip(content)
    } else if (archiveType === 'tar' || archiveType === 'tar.gz') {
      const isGzipped = archiveType === 'tar.gz'
      result = await processTar(content, isGzipped)
    } else {
      throw new Error(`Unsupported archive type: ${archiveType}`)
    }

    // Calculate statistics
    const stats = {
      totalFiles: result.files.filter(f => f.type === 'file').length,
      totalDirectories: result.files.filter(f => f.type === 'directory').length,
      totalSize: result.files.reduce((sum, f) => sum + (f.size || 0), 0),
      archiveType
    }

    return {
      type: 'archive',
      archiveType: result.type,
      files: result.files,
      fileTree: result.fileTree,
      extractFile: result.extractFile,
      metadata: {
        ...stats,
        totalSizeFormatted: formatSize(stats.totalSize)
      }
    }
  } catch (error) {
    console.error('Archive processing error:', error)
    throw error
  }
}
