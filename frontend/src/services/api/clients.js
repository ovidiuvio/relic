import api from './core'

export async function getClientRelics(tag = null) {
    const params = {}
    if (tag) {
        params.tag = tag
    }
    return api.get('/client/relics', { params })
}

export async function updateClientName(name) {
    return api.put('/client/name', { name })
}

export async function registerClient(clientKey) {
    try {
        const response = await api.post(`/client/register`, {}, {
            headers: { 'X-Client-Key': clientKey }
        })
        console.log('[API] Client registered successfully:', response.data)
        return response.data
    } catch (error) {
        console.error('[API] Client registration failed:', error)
        throw error
    }
}
