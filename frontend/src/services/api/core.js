import axios from 'axios'
import { getOrCreateClientKey } from './auth'

const API_BASE_URL = '/api/v1'

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json'
    }
})

// Add client key to requests that need it
api.interceptors.request.use((config) => {
    // console.log('[API] Intercepted request:', config.method?.toUpperCase(), config.url)

    // Only add client key to protected endpoints
    const needsAuth = (url, method) => {
        const protectedPatterns = [
            { endpoint: '/relics', methods: ['GET', 'POST', 'DELETE', 'PUT'] },
            { endpoint: '/edit', methods: ['POST'] },
            { endpoint: 'client/relics', methods: ['GET'] },
            { endpoint: '/client/name', methods: ['PUT'] },
            { endpoint: '/bookmarks', methods: ['GET', 'POST', 'DELETE'] },
            { endpoint: '/admin/', methods: ['GET', 'POST', 'DELETE'] }
        ]

        const needs = protectedPatterns.some(({ endpoint, methods }) =>
            url?.includes(endpoint) && methods.includes(method?.toUpperCase())
        )

        // console.log('[API] Auth check:', { url, method, needs })
        return needs
    }

    if (needsAuth(config.url, config.method)) {
        const clientKey = getOrCreateClientKey()
        // console.log('[API] Adding client key to', config.method, config.url, ':', clientKey)
        if (clientKey) {
            config.headers['X-Client-Key'] = clientKey
        }
    }

    return config
})

export async function getVersion() {
    return api.get('/version')
}

export default api
