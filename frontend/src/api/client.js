/**
 * Axios 实例 — VibeCheck API 客户端
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Songs ──────────────────────────────
export const getSongDetail = (id) => api.get(`/songs/${id}`).then(r => r.data)

export const getSongLrc = (id) => api.get(`/songs/${id}/lrc`).then(r => r.data)

export const getRandomSongs = (count = 12) =>
  api.get('/songs/random/list', { params: { count } }).then(r => r.data)

// ── Search ─────────────────────────────
export const searchSongs = (query, topK = 10) =>
  api.get('/search', { params: { q: query, top_k: topK } }).then(r => r.data)

// ── Recommend ──────────────────────────
export const getRecommendations = (songId, topK = 10) =>
  api.get(`/recommend/${songId}`, { params: { top_k: topK } }).then(r => r.data)

export default api
