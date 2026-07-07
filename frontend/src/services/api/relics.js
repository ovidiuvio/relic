import api, { waitForAuth } from './core'
import { usingSw, getClientKey } from './auth'

export async function createRelic(formData) {
    // Raw-body upload: the file streams straight from disk to the server
    // (no multipart encoding, no server-side spooling — fast path for large files)
    const file = formData.file
    const params = {
        name: formData.name || file.name,
        access_level: formData.access_level || 'public'
    }
    if (formData.content_type) params.content_type = formData.content_type
    if (formData.language_hint) params.language_hint = formData.language_hint
    if (formData.expires_in) params.expires_in = formData.expires_in
    if (formData.space_id) params.space_id = formData.space_id
    if (formData.tags) {
        params.tags = Array.isArray(formData.tags) ? formData.tags.join(',') : formData.tags
    }

    return api.post('/relics/raw', file, {
        params,
        headers: {
            'Content-Type': formData.content_type || file.type || 'application/octet-stream'
        }
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
    // Wait for auth init so the SW (or fallback) is ready to inject the key.
    await waitForAuth()
    // In fallback mode (no SW), inject the header manually.
    // In SW mode, the service worker intercepts /{id}/raw and injects it;
    // if the SW was restarted it re-reads the key from IDB before responding.
    const headers = {}
    if (!usingSw) {
        const key = getClientKey()
        if (!key) throw new Error('No client key available')
        headers['X-Client-Key'] = key
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
