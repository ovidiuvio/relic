import api from './core'

export async function getUserRelics(params = {}) {
    return api.get('/user/relics', { params })
}

export async function updateUserName(name) {
    return api.put('/user/name', { name })
}

export async function registerUser() {
    try {
        const response = await api.post('/user/register', {})
        console.log('[API] User registered successfully:', response.data)
        return response.data
    } catch (error) {
        console.error('[API] User registration failed:', error)
        throw error
    }
}

// Pinned searches: { id, name, query, path, created_at }
export async function getSavedSearches() {
    return api.get('/user/searches')
}

export async function createSavedSearch({ query, path, name = null }) {
    return api.post('/user/searches', { query, path, name })
}

export async function renameSavedSearch(id, name) {
    return api.patch(`/user/searches/${id}`, { name })
}

export async function deleteSavedSearch(id) {
    return api.delete(`/user/searches/${id}`)
}
