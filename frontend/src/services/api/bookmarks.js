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

export async function getClientBookmarks() {
    return api.get('/bookmarks')
}

export async function getRelicBookmarkers(relicId) {
    const response = await api.get(`/bookmarks/${relicId}/bookmarkers`)
    return response.data
}

