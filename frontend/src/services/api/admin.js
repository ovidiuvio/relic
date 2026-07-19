import api from './core'
import { triggerDownload } from '../utils/download'

export async function checkAdminStatus() {
    return api.get('/admin/check')
}

export async function getAdminStats() {
    return api.get('/admin/stats')
}

export async function getAdminRelics(limit = 100, offset = 0, accessLevel = null, userId = null, search = null, tag = null, sortBy = 'created_at', sortOrder = 'desc') {
    const params = { limit, offset, sort_by: sortBy, sort_order: sortOrder }
    if (accessLevel) params.access_level = accessLevel
    if (userId) params.user_id = userId
    if (search) params.search = search
    if (tag) params.tag = tag
    return api.get('/admin/relics', { params })
}

export async function getAdminUsers(limit = 100, offset = 0, sortBy = 'created_at', sortOrder = 'desc', search = null) {
    const params = { limit, offset, sort_by: sortBy, sort_order: sortOrder }
    if (search) params.search = search
    return api.get('/admin/users', { params })
}

export async function deleteUser(userId, deleteRelics = false) {
    return api.delete(`/admin/users/${userId}`, {
        params: { delete_relics: deleteRelics }
    })
}

export async function getAdmins() {
    return api.get('/admin/admins')
}

export async function addAdmin(publicId) {
    return api.post('/admin/admins', { public_id: publicId })
}

export async function grantAdmin(userId) {
    return api.post(`/admin/users/${userId}/admin`)
}

export async function revokeAdmin(userId) {
    return api.delete(`/admin/users/${userId}/admin`)
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

export async function restoreAdminBackup(filename) {
    return api.post(`/admin/backups/${encodeURIComponent(filename)}/restore`)
}

export async function restoreFromUpload(file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/admin/backups/restore-upload', formData, {
        headers: { 'Content-Type': undefined }
    })
}

export async function downloadAdminBackup(filename) {
    const response = await api.get(`/admin/backups/${filename}/download`, {
        responseType: 'blob'
    })

    // Trigger browser download using shared utility
    triggerDownload(response.data, filename)
}

// Report endpoints
export async function submitReport(relicId, reason) {
    return api.post('/reports', { relic_id: relicId, reason })
}

export async function getAdminReports(limit = 100, offset = 0, sortBy = 'created_at', sortOrder = 'desc') {
    return api.get('/admin/reports', { params: { limit, offset, sort_by: sortBy, sort_order: sortOrder } })
}

export async function deleteReport(reportId) {
    return api.delete(`/admin/reports/${reportId}`)
}

export async function getAdminJobs() {
    return api.get('/admin/jobs')
}

export async function runAdminJob(jobId) {
    return api.post(`/admin/jobs/${encodeURIComponent(jobId)}/run`)
}

export async function pauseAdminJob(jobId) {
    return api.post(`/admin/jobs/${encodeURIComponent(jobId)}/pause`)
}

export async function resumeAdminJob(jobId) {
    return api.post(`/admin/jobs/${encodeURIComponent(jobId)}/resume`)
}
