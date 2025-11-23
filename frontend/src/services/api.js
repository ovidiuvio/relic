import axios from 'axios'

const API_BASE_URL = '/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

export async function createPaste(formData) {
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

  return api.post('/pastes', data, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export async function getPaste(pasteId) {
  return api.get(`/pastes/${pasteId}`)
}

export async function listPastes(limit = 50, offset = 0) {
  return api.get('/pastes', { params: { limit, offset } })
}

export async function editPaste(pasteId, file, name) {
  const data = new FormData()
  data.append('file', file)
  if (name) data.append('name', name)

  return api.post(`/pastes/${pasteId}/edit`, data, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export async function forkPaste(pasteId, file, name) {
  const data = new FormData()
  if (file) data.append('file', file)
  if (name) data.append('name', name)

  return api.post(`/pastes/${pasteId}/fork`, data, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export async function deletePaste(pasteId) {
  return api.delete(`/pastes/${pasteId}`)
}

export async function getPasteHistory(pasteId) {
  return api.get(`/pastes/${pasteId}/history`)
}

export async function getPasteParent(pasteId) {
  return api.get(`/pastes/${pasteId}/parent`)
}

export async function getPasteChildren(pasteId) {
  return api.get(`/pastes/${pasteId}/children`)
}

export async function diffPastes(fromId, toId) {
  return api.get('/diff', { params: { from: fromId, to: toId } })
}

export async function diffWithParent(pasteId) {
  return api.get(`/pastes/${pasteId}/diff`)
}

export async function getPasteRaw(pasteId) {
  return axios.get(`/${pasteId}/raw`, {
    responseType: 'blob'
  })
}

export default api
