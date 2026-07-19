import { writable } from 'svelte/store'
import api from '../services/api/core'

// Client-facing runtime settings. These only decide what the UI offers —
// every one of them is also enforced server-side, so a stale or tampered
// copy here can never grant access the backend would refuse.
const DEFAULTS = {
    render_html: true,
    render_svg_inline: true,
    max_upload_size_bytes: 0,
    max_comment_length: 0,
    allow_comments: true,
    allow_forking: true,
    allow_spaces: true,
    allow_reports: true,
}

export const publicSettings = writable(DEFAULTS)

let loaded = false

export async function loadPublicSettings() {
    if (loaded) return
    try {
        const { data } = await api.get('/settings')
        publicSettings.set({ ...DEFAULTS, ...data })
        loaded = true
    } catch (error) {
        // Keep permissive defaults: the server still enforces the real limits,
        // so a failed fetch should not make the UI refuse valid actions.
        console.warn('[settings] Could not load public settings:', error)
    }
}
