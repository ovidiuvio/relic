export function getTypeLabel(contentType) {
  if (!contentType) return 'Text'
  if (contentType.includes('javascript')) return 'JavaScript'
  if (contentType.includes('python')) return 'Python'
  if (contentType.includes('html')) return 'HTML'
  if (contentType.includes('css')) return 'CSS'
  if (contentType.includes('json')) return 'JSON'
  if (contentType.includes('markdown')) return 'Markdown'
  if (contentType.includes('xml')) return 'XML'
  if (contentType.includes('bash') || contentType.includes('shell')) return 'Bash'
  if (contentType.includes('sql')) return 'SQL'
  if (contentType.includes('java')) return 'Java'
  return 'Text'
}

export function formatBytes(bytes, decimals = 2) {
  if (!+bytes) return '0 Bytes'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
}

// Map type selections to MIME types
export function getContentType(syntax) {
  const mimeTypes = {
    'text': 'text/plain',
    'markdown': 'text/markdown',
    'html': 'text/html',
    'json': 'application/json',
    'xml': 'application/xml',
    'javascript': 'application/javascript',
    'python': 'text/x-python',
    'bash': 'text/x-shellscript',
    'sql': 'application/sql',
    'css': 'text/css',
    'java': 'text/x-java-source'
  }
  return mimeTypes[syntax] || 'text/plain'
}

// Map language selection to file extensions
export function getFileExtension(syntax) {
  const extensions = {
    'text': 'txt',
    'markdown': 'md',
    'html': 'html',
    'json': 'json',
    'xml': 'xml',
    'javascript': 'js',
    'python': 'py',
    'bash': 'sh',
    'sql': 'sql',
    'css': 'css',
    'java': 'java'
  }
  return extensions[syntax] || 'txt'
}

// Auto-detect language hint from content type
export function detectLanguageHint(contentType) {
  const typeToLanguage = {
    'text/markdown': 'markdown',
    'text/html': 'html',
    'application/json': 'json',
    'application/xml': 'xml',
    'application/javascript': 'javascript',
    'text/x-python': 'python',
    'text/x-shellscript': 'bash',
    'application/sql': 'sql',
    'text/css': 'css',
    'text/x-java-source': 'java'
  }
  return typeToLanguage[contentType] || 'auto'
}
