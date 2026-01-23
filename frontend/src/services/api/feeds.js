import api from './core';

export const createFeed = (data) => api.post('/feeds', data);
export const getFeeds = () => api.get('/feeds');
export const getFeed = (feedId) => api.get(`/feeds/${feedId}`);
export const updateFeed = (feedId, data) => api.put(`/feeds/${feedId}`, data);
export const deleteFeed = (feedId) => api.delete(`/feeds/${feedId}`);
export const addRelicToFeed = (feedId, relicId) => api.post(`/feeds/${feedId}/relics/${relicId}`);
export const removeRelicFromFeed = (feedId, relicId) => api.delete(`/feeds/${feedId}/relics/${relicId}`);
