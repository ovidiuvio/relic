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
