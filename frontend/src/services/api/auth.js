// User key management via Service Worker vault.
// Falls back to localStorage when SW is unavailable (Firefox private mode,
// disabled by policy, non-secure context other than localhost, etc.).

import { markSwReady, enableFallbackAuth } from './core'

const STORAGE_KEY = 'relic_user_key'
// Pre-rename key name. Only read as a one-time migration fallback for
// browsers that already had an identity stored under the old name.
const OLD_LEGACY_STORAGE_KEY = 'relic_client_key'

// True when the SW vault is active; false when using localStorage fallback.
export let usingSw = false

// ─── SW messaging (one-shot MessageChannel) ───────────────────────────────────

function swMessage(type, payload = {}, target) {
  return new Promise((resolve, reject) => {
    const sw = target ?? navigator.serviceWorker?.controller
    if (!sw) { reject(new Error('SW not controlling page')); return }
    const { port1, port2 } = new MessageChannel()
    const timeout = setTimeout(() => {
      port1.close()
      reject(new Error('SW communication timeout'))
    }, 5000)
    port1.onmessage = ({ data }) => {
      clearTimeout(timeout)
      port1.close()
      data.error ? reject(new Error(data.error)) : resolve(data)
    }
    sw.postMessage({ type, ...payload }, [port2])
  })
}

export async function swHasKey() {
  try { return (await swMessage('HAS_KEY')).hasKey } catch { return false }
}

export async function swSetKey(key) {
  if (!usingSw) {
    localStorage.setItem(STORAGE_KEY, key)
    return
  }
  await swMessage('SET_KEY', { key })
}
export async function swClearKey() {
  if (!usingSw) {
    localStorage.removeItem(STORAGE_KEY)
    return
  }
  await swMessage('CLEAR_KEY')
}

// ─── localStorage fallback ────────────────────────────────────────────────────

export function getUserKey() {
  if (typeof localStorage === 'undefined') return null
  return localStorage.getItem(STORAGE_KEY)
}

function initFallback() {
  console.warn('[Auth] Service Worker unavailable — using localStorage fallback')
  usingSw = false
  enableFallbackAuth(getUserKey)
  let key = localStorage.getItem(STORAGE_KEY)
  if (!key) {
    // One-time migration from the pre-rename key name, if present.
    const old = localStorage.getItem(OLD_LEGACY_STORAGE_KEY)
    if (old) {
      localStorage.setItem(STORAGE_KEY, old)
      localStorage.removeItem(OLD_LEGACY_STORAGE_KEY)
      markSwReady()
      return null         // existing key migrated — no reveal needed
    }
    key = _generateKey()
    localStorage.setItem(STORAGE_KEY, key)
    markSwReady()
    return key           // new key — caller should show it once
  }
  markSwReady()
  return null            // existing key — no reveal needed
}

// ─── Initialisation ───────────────────────────────────────────────────────────

export async function initUserKey() {
  // Bail out early if SW API is missing entirely
  if (!('serviceWorker' in navigator)) return initFallback()

  try {
    await navigator.serviceWorker.register('/vault-sw.js', { updateViaCache: 'none' })
    await navigator.serviceWorker.ready
  } catch (err) {
    console.warn('[Auth] SW registration failed:', err)
    return initFallback()
  }

  // Ensure SW is controlling this page. On first install, clients.claim()
  // fires during activate. On hard refresh (Shift+F5), the SW is active
  // but not controlling — ask it to re-claim.
  if (!navigator.serviceWorker.controller) {
    try {
      const reg = await navigator.serviceWorker.ready
      await swMessage('CLAIM', {}, reg.active)
      // Wait for the controller to actually be set on this page
      if (!navigator.serviceWorker.controller) {
        await new Promise(resolve =>
          navigator.serviceWorker.addEventListener('controllerchange', resolve, { once: true })
        )
      }
    } catch (err) {
      console.warn('[Auth] SW claim failed:', err)
      return initFallback()
    }
  }

  try {
    // Migrate key from localStorage → SW vault (current or pre-rename key name)
    // Note: usingSw is still false here, so call swMessage directly
    // to talk to the SW without going through the usingSw guard.
    const legacy = localStorage.getItem(STORAGE_KEY) || localStorage.getItem(OLD_LEGACY_STORAGE_KEY)
    if (legacy) {
      console.log('[Auth] Migrating user key to SW vault')
      await swMessage('SET_KEY', { key: legacy })
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem(OLD_LEGACY_STORAGE_KEY)
      usingSw = true
      markSwReady()
      return legacy
    }

    // Key already in vault — we can't retrieve it (by design)
    const { hasKey } = await swMessage('HAS_KEY')
    if (hasKey) {
      usingSw = true
      markSwReady()
      return null
    }

    const key = _generateKey()
    await swMessage('SET_KEY', { key })
    usingSw = true
    markSwReady()
    return key
  } catch (err) {
    console.warn('[Auth] SW vault operation failed, falling back:', err)
    usingSw = false
    return initFallback()
  }
}

function _generateKey() {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('')
}
