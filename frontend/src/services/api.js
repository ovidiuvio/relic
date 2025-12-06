import axios from 'axios'

const API_BASE_URL = '/api/v1'

// Client key management
const CLIENT_KEY_STORAGE_KEY = 'relic_client_key'

function getClientKey() {
  return localStorage.getItem(CLIENT_KEY_STORAGE_KEY)
}

function setClientKey(key) {
  localStorage.setItem(CLIENT_KEY_STORAGE_KEY, key)
}

function generateClientKey() {
  // Generate 32-character hex string (same as backend)
  const array = new Uint8Array(16)
  crypto.getRandomValues(array)
  return Array.from(array, b => b.toString(16).padStart(2, '0')).join('')
}

function getOrCreateClientKey() {
  let clientKey = getClientKey()
  if (!clientKey) {
    clientKey = generateClientKey()
    setClientKey(clientKey)
    // Register with server
    registerClient(clientKey)
  }
  return clientKey
}

async function registerClient(clientKey) {
  try {
    const response = await axios.post(`${API_BASE_URL}/client/register`, {}, {
      headers: { 'X-Client-Key': clientKey }
    })
    console.log('[API] Client registered successfully:', response.data)
  } catch (error) {
    console.error('[API] Client registration failed:', error)
    // Don't remove the client key from localStorage on registration failure
    // The user might still be able to use it if the server is temporarily unavailable
  }
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add client key to requests that need it
api.interceptors.request.use((config) => {
  console.log('[API] Intercepted request:', config.method?.toUpperCase(), config.url)

  // Only add client key to protected endpoints
  const needsAuth = (url, method) => {
    const protectedPatterns = [
      { endpoint: '/relics', methods: ['POST', 'DELETE'] },
      { endpoint: '/edit', methods: ['POST'] },
      { endpoint: 'client/relics', methods: ['GET'] },
      { endpoint: '/bookmarks', methods: ['GET', 'POST', 'DELETE'] },
      { endpoint: '/admin/', methods: ['GET', 'POST', 'DELETE'] }
    ]

    const needs = protectedPatterns.some(({ endpoint, methods }) =>
      url?.includes(endpoint) && methods.includes(method?.toUpperCase())
    )

    console.log('[API] Auth check:', { url, method, needs })
    return needs
  }

  if (needsAuth(config.url, config.method)) {
    const clientKey = getOrCreateClientKey()
    console.log('[API] Adding client key to', config.method, config.url, ':', clientKey)
    if (clientKey) {
      config.headers['X-Client-Key'] = clientKey
      console.log('[API] Final headers:', config.headers)
    }
  } else {
    console.log('[API] No auth needed for', config.method, config.url)
  }
  return config
})

export async function createRelic(formData) {
  const data = new FormData()
  if (formData.file) {
    data.append('file', formData.file)
  }
  if (formData.name) data.append('name', formData.name)
  if (formData.content_type) data.append('content_type', formData.content_type)
  if (formData.language_hint) data.append('language_hint', formData.language_hint)
  data.append('access_level', formData.access_level || 'public')
  if (formData.expires_in) data.append('expires_in', formData.expires_in)
  if (formData.tags) data.append('tags', JSON.stringify(formData.tags))

  // Use axios with FormData - let browser set Content-Type automatically
  return api.post('/relics', data, {
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    // Don't let axios override the Content-Type for FormData
    transformRequest: [(data, headers) => {
      // Remove the Content-Type header to let browser set it automatically for FormData
      delete headers['Content-Type']
      return data
    }]
  })
}

export async function getRelic(relicId) {
  return api.get(`/relics/${relicId}`)
}

export async function listRelics(limit = 1000) {
  return api.get('/relics', { params: { limit } })
}


export async function forkRelic(relicId, file, name, accessLevel, expiresIn) {
  const data = new FormData()
  if (file) data.append('file', file)
  if (name) data.append('name', name)
  // Always send access_level and expires_in, even if they're defaults
  data.append('access_level', accessLevel || 'public')
  data.append('expires_in', expiresIn || 'never')

  return api.post(`/relics/${relicId}/fork`, data, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export async function deleteRelic(relicId) {
  return api.delete(`/relics/${relicId}`)
}


export async function getRelicRaw(relicId) {
  return axios.get(`/${relicId}/raw`, {
    responseType: 'blob'
  })
}

// Bookmark endpoints
export async function addBookmark(relicId) {
  return api.post('/bookmarks', null, {
    params: { relic_id: relicId }
  })
}

export async function removeBookmark(relicId) {
  return api.delete(`/bookmarks/${relicId}`)
}

export async function checkBookmark(relicId) {
  return api.get(`/bookmarks/check/${relicId}`)
}

export async function getClientBookmarks() {
  return api.get('/bookmarks')
}

// Client-specific endpoints
export async function getClientRelics() {
  return api.get('/client/relics')
}

// Admin endpoints
export async function checkAdminStatus() {
  return api.get('/admin/check')
}

export async function getAdminStats() {
  return api.get('/admin/stats')
}

export async function getAdminRelics(limit = 100, offset = 0, accessLevel = null, clientId = null) {
  const params = { limit, offset }
  if (accessLevel) params.access_level = accessLevel
  if (clientId) params.client_id = clientId
  return api.get('/admin/relics', { params })
}

export async function getAdminClients(limit = 100, offset = 0) {
  return api.get('/admin/clients', { params: { limit, offset } })
}

export async function deleteClient(clientId, deleteRelics = false) {
  return api.delete(`/admin/clients/${clientId}`, {
    params: { delete_relics: deleteRelics }
  })
}

export async function getAdminConfig() {
  return api.get('/admin/config')
}

export async function getAdminBackups(limit = 25, offset = 0) {
  return api.get('/admin/backups', { params: { limit, offset } })
}

export async function createAdminBackup() {
  return api.post('/admin/backups')
}

export async function downloadAdminBackup(filename) {
  const response = await api.get(`/admin/backups/${filename}/download`, {
    responseType: 'blob'
  })

  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

// Report endpoints
export async function submitReport(relicId, reason) {
  return api.post('/reports', { relic_id: relicId, reason })
}

export async function getAdminReports(limit = 100, offset = 0) {
  return api.get('/admin/reports', { params: { limit, offset } })
}

export async function deleteReport(reportId) {
  return api.delete(`/admin/reports/${reportId}`)
}

// Export client key functions for components that need them
export { getClientKey, getOrCreateClientKey }

export default api
