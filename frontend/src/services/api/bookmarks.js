import api from './core'

export async function addBookmark(relicId) {
    return api.post('/bookmarks', null, {
        params: { relic_id: relicId }
    })
}

export async function removeBookmark(relicId) {
    return api.delete(`/bookmarks/${relicId}`)
}

export async function checkBookmark(relicId) {
    return api.get(`/bookmarks/check/${relicId}`)
}

export async function getClientBookmarks(params = {}) {
    return api.get('/bookmarks', { params })
}

export async function getRelicBookmarkers(relicId, params = {}) {
    const response = await api.get(`/bookmarks/${relicId}/bookmarkers`, { params })
    return response.data
}

