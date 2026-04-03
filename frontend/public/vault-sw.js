// Service Worker Key Vault
// Stores the client authentication key in SW-scoped IndexedDB.
// Intercepts all /api/ requests and injects the X-Client-Key header.
// The key is never accessible via localStorage after migration.

const DB_NAME = 'relic-vault'
const DB_VERSION = 1
const KEY_STORE = 'auth'
const KEY_RECORD = 'client_key'

// In-memory cache so fetch interception never hits IDB.
// Updated on SET_KEY / CLEAR_KEY; hydrated on activate.
let cachedKey = null

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => req.result.createObjectStore(KEY_STORE)
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function readKey() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const req = db.transaction(KEY_STORE, 'readonly').objectStore(KEY_STORE).get(KEY_RECORD)
    req.onsuccess = () => resolve(req.result ?? null)
    req.onerror = () => reject(req.error)
  })
}

async function writeKey(key) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const req = db.transaction(KEY_STORE, 'readwrite').objectStore(KEY_STORE).put(key, KEY_RECORD)
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
}

async function deleteKey() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const req = db.transaction(KEY_STORE, 'readwrite').objectStore(KEY_STORE).delete(KEY_RECORD)
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
}

async function hydrateCache() {
  try { cachedKey = await readKey() } catch { cachedKey = null }
}

// Intercept all /api/ requests and inject the auth header.
// cachedKey may be null after a SW restart (browser terminated it),
// so fall back to IDB when needed.
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)
  const path = url.pathname
  if (!path.startsWith('/api/') && !path.endsWith('/raw')) return

  event.respondWith(
    (async () => {
      const key = cachedKey ?? (cachedKey = await readKey())
      if (!key) return fetch(event.request)
      const headers = new Headers(event.request.headers)
      headers.set('X-Client-Key', key)
      return fetch(new Request(event.request, { headers }))
    })()
  )
})

// Handle messages from page via one-shot MessageChannel ports
self.addEventListener('message', (event) => {
  const port = event.ports[0]
  if (!port) return
  const { type, key } = event.data ?? {}

  ;(async () => {
    try {
      switch (type) {
        case 'HAS_KEY':
          port.postMessage({ hasKey: !!(await readKey()) })
          break

        case 'SET_KEY':
          if (!key || typeof key !== 'string' || !/^[a-f0-9]{32}$/i.test(key))
            throw new Error('Invalid key format')
          await writeKey(key)
          cachedKey = key
          port.postMessage({ ok: true })
          break

        case 'CLEAR_KEY':
          await deleteKey()
          cachedKey = null
          port.postMessage({ ok: true })
          break

        case 'CLAIM':
          await self.clients.claim()
          port.postMessage({ ok: true })
          break

        default:
          port.postMessage({ error: `Unknown message type: ${type}` })
      }
    } catch (err) {
      port.postMessage({ error: err.message })
    }
  })()
})

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', event =>
  event.waitUntil(hydrateCache().then(() => self.clients.claim()))
)
