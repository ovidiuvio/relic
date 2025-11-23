import { writable } from 'svelte/store'

export const toastStore = writable([])

export function showToast(message, type = 'info', duration = 3000) {
  const id = Math.random().toString(36).substring(2, 9)
  const toast = { id, message, type }

  toastStore.update(toasts => [...toasts, toast])

  setTimeout(() => {
    toastStore.update(toasts => toasts.filter(t => t.id !== id))
  }, duration)
}
