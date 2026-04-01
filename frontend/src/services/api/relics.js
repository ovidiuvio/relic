import api from './core'

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
    if (formData.space_id) data.append('space_id', formData.space_id)

    // Handle tags: FastAPI expects List[str], which usually means repeating keys or comma separated
    // Sending as comma separated string works best with the backend implementation we added
    if (formData.tags) {
        if (Array.isArray(formData.tags)) {
            data.append('tags', formData.tags.join(','))
        } else {
            data.append('tags', formData.tags)
        }
    }

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

export async function listRelics(params = {}) {
    return api.get('/relics', { params })
}

export async function forkRelic(relicId, file, name, accessLevel, expiresIn, tags) {
    const data = new FormData()
    if (file) data.append('file', file)
    if (name) data.append('name', name)
    // Always send access_level and expires_in, even if they're defaults
    data.append('access_level', accessLevel || 'public')
    data.append('expires_in', expiresIn || 'never')

    // Handle tags: sending as comma separated string
    if (tags) {
        if (Array.isArray(tags)) {
            data.append('tags', tags.join(','))
        } else {
            data.append('tags', tags)
        }
    }

    return api.post(`/relics/${relicId}/fork`, data, {
        headers: { 'Content-Type': 'multipart/form-data' }
    })
}

export async function deleteRelic(relicId) {
    return api.delete(`/relics/${relicId}`)
}

export async function updateRelic(relicId, data) {
    return api.put(`/relics/${relicId}`, data)
}

export async function getRelicRaw(relicId) {
    // SW intercepts /{id}/raw and injects X-Client-Key automatically.
    // In fallback mode (no SW), we inject the header manually.
    const headers = {}
    const { usingSw, getClientKey } = await import('./auth')
    if (!usingSw) {
        const key = getClientKey()
        if (key) headers['X-Client-Key'] = key
    }
    const response = await fetch(`/${relicId}/raw`, { headers })
    if (!response.ok) throw new Error(`Raw fetch failed: ${response.status}`)
    const blob = await response.blob()
    return { data: blob, headers: Object.fromEntries(response.headers.entries()) }
}

export async function getRelicLineage(relicId, params = {}) {
    return api.get(`/relics/${relicId}/lineage`, { params });
}

export async function getRelicAccess(relicId, params = {}) {
    return api.get(`/relics/${relicId}/access`, { params })
}

export async function addRelicAccess(relicId, publicId) {
    return api.post(`/relics/${relicId}/access`, { public_id: publicId })
}

export async function removeRelicAccess(relicId, publicId) {
    return api.delete(`/relics/${relicId}/access/${publicId}`)
}
