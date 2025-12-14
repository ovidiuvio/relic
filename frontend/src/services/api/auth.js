// Client key management and auth logic

const CLIENT_KEY_STORAGE_KEY = 'relic_client_key'

export function getClientKey() {
    if (typeof localStorage === 'undefined') return null
    return localStorage.getItem(CLIENT_KEY_STORAGE_KEY)
}

export function setClientKey(key) {
    if (typeof localStorage === 'undefined') return
    localStorage.setItem(CLIENT_KEY_STORAGE_KEY, key)
}

export function generateClientKey() {
    // Generate 32-character hex string (same as backend)
    const array = new Uint8Array(16)
    crypto.getRandomValues(array)
    return Array.from(array, b => b.toString(16).padStart(2, '0')).join('')
}

// Internal register function using fetch to avoid circular dependency with core api instance
async function registerClientInternal(clientKey) {
    try {
        const response = await fetch('/api/v1/client/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Client-Key': clientKey
            }
        })

        if (!response.ok) {
            throw new Error(`Registration failed: ${response.statusText}`)
        }

        const data = await response.json()
        console.log('[API] Client registered successfully:', data)
        return data
    } catch (error) {
        console.error('[API] Client registration failed:', error)
        // Don't throw for background registration
    }
}

export function getOrCreateClientKey() {
    let clientKey = getClientKey()
    if (!clientKey) {
        clientKey = generateClientKey()
        setClientKey(clientKey)
        // Register with server
        registerClientInternal(clientKey)
    }
    return clientKey
}
