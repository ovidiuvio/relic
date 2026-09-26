import api, { waitForAuth } from './core'
import { usingSw, getUserKey } from './auth'

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
        const key = getUserKey()
        if (!key) throw new Error('No user key available')
        headers['X-User-Key'] = key
    }
    const response = await fetch(`/${relicId}/raw`, { headers })
    if (!response.ok) throw new Error(`Raw fetch failed: ${response.status}`)
    const blob = await response.blob()
    return { data: blob, headers: Object.fromEntries(response.headers.entries()) }
}

/**
 * The first `bytes` of a relic's content as text, for a quick preview: the download stops there,
 * so a large relic costs no more than a small one. Throws with `status` set on HTTP errors.
 */
export async function getRelicRawHead(relicId, bytes = 8192, signal = undefined) {
    await waitForAuth()
    const headers = {}
    if (!usingSw) {
        const key = getUserKey()
        if (key) headers['X-User-Key'] = key
    }
    const controller = new AbortController()
    signal?.addEventListener('abort', () => controller.abort())
    const response = await fetch(`/${relicId}/raw`, { headers, signal: controller.signal })
    if (!response.ok) throw Object.assign(new Error(`Raw fetch failed: ${response.status}`), { status: response.status })
    const reader = response.body.getReader()
    const chunks = []
    let size = 0
    while (size < bytes) {
        const { done, value } = await reader.read()
        if (done) break
        chunks.push(value)
        size += value.length
    }
    controller.abort()
    const all = new Uint8Array(Math.min(size, bytes))
    let at = 0
    for (const c of chunks) {
        const part = c.subarray(0, Math.min(c.length, all.length - at))
        all.set(part, at)
        at += part.length
        if (at >= all.length) break
    }
    return { text: new TextDecoder().decode(all), truncated: size >= bytes }
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
