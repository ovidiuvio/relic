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
