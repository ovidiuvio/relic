import api from './core';

export const spaces = {
    // List spaces (public, and private if access)
    list: async (visibility = null) => {
        const params = visibility ? { visibility } : {};
        const response = await api.get('/spaces', { params });
        return response.data;
    },

    // Create a new space
    create: async (spaceData) => {
        const response = await api.post('/spaces', spaceData);
        return response.data;
    },

    // Get space details
    get: async (spaceId) => {
        const response = await api.get(`/spaces/${spaceId}`);
        return response.data;
    },

    // Update space details
    update: async (spaceId, spaceData) => {
        const response = await api.put(`/spaces/${spaceId}`, spaceData);
        return response.data;
    },

    // Delete a space
    delete: async (spaceId) => {
        const response = await api.delete(`/spaces/${spaceId}`);
        return response.data;
    },

    // Get relics in a space
    getRelics: async (spaceId) => {
        const response = await api.get(`/spaces/${spaceId}/relics`);
        return response.data;
    },

    // Add a relic to a space
    addRelic: async (spaceId, relicId) => {
        const response = await api.post(`/spaces/${spaceId}/relics?relic_id=${relicId}`);
        return response.data;
    },

    // Remove a relic from a space
    removeRelic: async (spaceId, relicId) => {
        const response = await api.delete(`/spaces/${spaceId}/relics/${relicId}`);
        return response.data;
    },

    // Get access list for a space
    getAccessList: async (spaceId) => {
        const response = await api.get(`/spaces/${spaceId}/access`);
        return response.data;
    },

    // Add/Update access for a user in a space
    addAccess: async (spaceId, accessData) => {
        const response = await api.post(`/spaces/${spaceId}/access`, accessData);
        return response.data;
    },

    // Remove user access from a space
    removeAccess: async (spaceId, clientId) => {
        const response = await api.delete(`/spaces/${spaceId}/access/${clientId}`);
        return response.data;
    }
};
