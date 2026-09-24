import { writable } from 'svelte/store'

// Title of the current page, without the app suffix. App.svelte resets it on
// every route change and mirrors it into document.title; pages that know a
// better name (a relic, a space) overwrite it once loaded.
export const pageTitle = writable('')
