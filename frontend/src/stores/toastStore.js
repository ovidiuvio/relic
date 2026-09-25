import { writable } from 'svelte/store'

export const toastStore = writable([])

/**
 * Show a toast. `action` adds a button to it, e.g. { label: 'Undo', run: () => … };
 * toasts with an action stay a little longer so there's time to use it.
 */
export function showToast(message, type = 'info', duration = 3000, action = null) {
  const id = Math.random().toString(36).substring(2, 9)
  const toast = { id, message, type, action }

  toastStore.update(toasts => [...toasts, toast])

  setTimeout(() => dismissToast(id), action ? Math.max(duration, 6000) : duration)
}

export function dismissToast(id) {
  toastStore.update(toasts => toasts.filter(t => t.id !== id))
}
