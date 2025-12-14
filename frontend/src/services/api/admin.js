import api from './core'

export async function checkAdminStatus() {
    return api.get('/admin/check')
}

export async function getAdminStats() {
    return api.get('/admin/stats')
}

export async function getAdminRelics(limit = 100, offset = 0, accessLevel = null, clientId = null) {
    const params = { limit, offset }
    if (accessLevel) params.access_level = accessLevel
    if (clientId) params.client_id = clientId
    return api.get('/admin/relics', { params })
}

export async function getAdminClients(limit = 100, offset = 0) {
    return api.get('/admin/clients', { params: { limit, offset } })
}

export async function deleteClient(clientId, deleteRelics = false) {
    return api.delete(`/admin/clients/${clientId}`, {
        params: { delete_relics: deleteRelics }
    })
}

export async function getAdminConfig() {
    return api.get('/admin/config')
}

export async function getAdminBackups(limit = 25, offset = 0) {
    return api.get('/admin/backups', { params: { limit, offset } })
}

export async function createAdminBackup() {
    return api.post('/admin/backups')
}

export async function downloadAdminBackup(filename) {
    const response = await api.get(`/admin/backups/${filename}/download`, {
        responseType: 'blob'
    })

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
}

// Report endpoints
export async function submitReport(relicId, reason) {
    return api.post('/reports', { relic_id: relicId, reason })
}

export async function getAdminReports(limit = 100, offset = 0) {
    return api.get('/admin/reports', { params: { limit, offset } })
}

export async function deleteReport(reportId) {
    return api.delete(`/admin/reports/${reportId}`)
}
