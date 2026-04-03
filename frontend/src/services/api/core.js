import axios from 'axios'

const API_BASE_URL = '/api/v1'

// Gate: all requests wait until auth init (SW or fallback) is complete.
// Safety net: auto-resolve after 10s so the app never hangs permanently
// if initClientKey() fails to call markSwReady().
let _swReadyResolve
const _swReady = new Promise(resolve => { _swReadyResolve = resolve })
let _swReadyTimeout = setTimeout(() => {
    console.warn('[Auth] Auth init did not complete within 10s — unblocking requests')
    _swReadyResolve()
}, 10000)

// Set by auth.js after init — true = SW intercepts fetch, false = we inject header here.
let _fallbackMode = false
let _getClientKey = null

export function markSwReady() {
    clearTimeout(_swReadyTimeout)
    _swReadyResolve()
}

export function waitForAuth() {
    return _swReady
}

export function enableFallbackAuth(getKeyFn) {
    _fallbackMode = true
    _getClientKey = getKeyFn
}

// Use the fetch adapter so the Service Worker can intercept requests.
// In fallback mode (no SW), the interceptor below adds the header instead.
const api = axios.create({
    baseURL: API_BASE_URL,
    adapter: axios.getAdapter('fetch'),
    headers: {
        'Content-Type': 'application/json'
    }
})

// Hold every request until auth init is complete, then inject the header
// ourselves when running in localStorage-fallback mode.
api.interceptors.request.use(async (config) => {
    await _swReady
    if (_fallbackMode && _getClientKey) {
        const key = _getClientKey()
        if (key) config.headers['X-Client-Key'] = key
    }
    return config
})

export async function getVersion() {
    return api.get('/version')
}

export default api
