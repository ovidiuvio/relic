import api from './core'

export async function getComments(relicId) {
    const response = await api.get(`/relics/${relicId}/comments`)
    return response.data
}

export async function createComment(relicId, lineNumber, content, parentId = null) {
    const response = await api.post(`/relics/${relicId}/comments`, {
        line_number: lineNumber,
        content,
        parent_id: parentId
    })
    return response.data
}

export async function updateComment(relicId, commentId, content) {
    const response = await api.put(`/relics/${relicId}/comments/${commentId}`, {
        content
    })
    return response.data
}

export async function deleteComment(relicId, commentId) {
    const response = await api.delete(`/relics/${relicId}/comments/${commentId}`)
    return response.data
}
