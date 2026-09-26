import axios from 'axios'

const API_BASE_URL = '/api/v1'

// Gate: all requests wait until auth init (SW or fallback) is complete.
// Safety net: auto-resolve after 10s so the app never hangs permanently
// if initUserKey() fails to call markSwReady().
let _swReadyResolve
const _swReady = new Promise(resolve => { _swReadyResolve = resolve })
let _swReadyTimeout = setTimeout(() => {
    console.warn('[Auth] Auth init did not complete within 10s — unblocking requests')
    _swReadyResolve()
}, 10000)

// Set by auth.js after init — true = SW intercepts fetch, false = we inject header here.
let _fallbackMode = false
let _getUserKey = null

export function markSwReady() {
    clearTimeout(_swReadyTimeout)
    _swReadyResolve()
}

export function waitForAuth() {
    return _swReady
}

export function enableFallbackAuth(getKeyFn) {
    _fallbackMode = true
    _getUserKey = getKeyFn
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
    if (_fallbackMode && _getUserKey) {
        const key = _getUserKey()
        if (key) config.headers['X-User-Key'] = key
    }
    return config
})

// The API sends most timestamps as UTC without saying so ("2026-09-26T08:44:12.07"), and
// JavaScript reads a zone-less date-time as local time, which puts every time off by the
// viewer's UTC offset. Mark them as UTC once, here, for every response; timestamps that
// already carry a zone ("...+00:00", "...Z") and plain dates are left as they are.
const NAIVE_UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$/

function markUtc(value) {
    if (typeof value === 'string') return NAIVE_UTC.test(value) ? `${value}Z` : value
    if (Array.isArray(value)) {
        for (let i = 0; i < value.length; i++) value[i] = markUtc(value[i])
        return value
    }
    if (value && typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype) {
        for (const key of Object.keys(value)) value[key] = markUtc(value[key])
    }
    return value
}

api.interceptors.response.use((response) => {
    // Only parsed JSON: raw content arrives as a Blob or ArrayBuffer and is never touched.
    if (response.data && typeof response.data === 'object') markUtc(response.data)
    return response
})

export async function getVersion() {
    return api.get('/version')
}

export default api
