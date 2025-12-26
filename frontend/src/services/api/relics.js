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

export async function listRelics(limit = 1000, tag = null) {
    const params = { limit }
    if (tag) {
        params.tag = tag
    }
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

// Note: getRelicRaw often needs specific responseType, so it's a bit special.
// We import axios directly usually to avoid default interceptors modifying it? 
// No, raw content should be fine with interceptors, but we need responseType: 'blob'.
// However, in original code it used `axios.get` not `api.get`.
// This might be intentional to bypass base URL or interceptors?
// Base URL is `/api/v1` in `api`. Raw endpoint is `/{relic_id}/raw` (root level, usually).
// If `getRelicRaw` calls `/{relicId}/raw`, and base URL is `/api/v1`, `api.get` would be `/api/v1/{relicId}/raw`?
// Let's check `api.js` original. `axios.get('/' + relicId + '/raw')`.
// So it uses global axios to hit root path.
import axios from 'axios'

export async function getRelicRaw(relicId) {
    return axios.get(`/${relicId}/raw`, {
        responseType: 'blob'
    })
}
