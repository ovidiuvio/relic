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
      { endpoint: 'client/relics', methods: ['GET'] }
    ]

    const needs = protectedPatterns.some(({endpoint, methods}) =>
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

export async function listRelics(limit = 50, offset = 0) {
  return api.get('/relics', { params: { limit, offset } })
}

export async function editRelic(relicId, file, name) {
  const data = new FormData()
  data.append('file', file)
  if (name) data.append('name', name)

  return api.post(`/relics/${relicId}/edit`, data, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export async function forkRelic(relicId, file, name) {
  const data = new FormData()
  if (file) data.append('file', file)
  if (name) data.append('name', name)

  return api.post(`/relics/${relicId}/fork`, data, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export async function deleteRelic(relicId) {
  return api.delete(`/relics/${relicId}`)
}

export async function getRelicHistory(relicId) {
  return api.get(`/relics/${relicId}/history`)
}

export async function getRelicParent(relicId) {
  return api.get(`/relics/${relicId}/parent`)
}

export async function getRelicChildren(relicId) {
  return api.get(`/relics/${relicId}/children`)
}

export async function diffRelics(fromId, toId) {
  return api.get('/diff', { params: { from: fromId, to: toId } })
}

export async function diffWithParent(relicId) {
  return api.get(`/relics/${relicId}/diff`)
}

export async function getRelicRaw(relicId) {
  return axios.get(`/${relicId}/raw`, {
    responseType: 'blob'
  })
}

// Client-specific endpoints
export async function getClientRelics() {
  return api.get('/client/relics')
}

// Export client key functions for components that need them
export { getClientKey, getOrCreateClientKey }

export default api
