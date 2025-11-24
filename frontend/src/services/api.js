import axios from 'axios'

const API_BASE_URL = '/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
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

  return api.post('/relics', data, {
    headers: { 'Content-Type': 'multipart/form-data' }
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

export default api
