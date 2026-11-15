import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 45000,
})

// Dev-only: simulate a slow backend to preview loading skeletons.
//   http://localhost:5173/?slow=2500        (per-visit, milliseconds)
//   VITE_SLOW_MS=2500 npm run dev            (whole session)
// Ignored in production builds.
if (import.meta.env.DEV) {
  const fromUrl = Number(new URLSearchParams(window.location.search).get('slow'))
  const slowMs = fromUrl || Number(import.meta.env.VITE_SLOW_MS) || 0
  if (slowMs > 0) {
    api.interceptors.request.use((config) => new Promise((resolve) => setTimeout(() => resolve(config), slowMs)))
  }
}

export const REGION_PRESETS = [
  { id: 'world', label: 'Global Planetary', bbox: '-180,-90,180,90', center: [15, 12], zoom: 2 },
  { id: 'india', label: 'South Asia / India', bbox: '68,6,98,37', center: [22, 82], zoom: 5 },
  { id: 'uttarakhand', label: 'Uttarakhand & Himalaya', bbox: '75,25,85,32', center: [29.5, 79.5], zoom: 7 },
  { id: 'amazon', label: 'Amazon Basin', bbox: '-75,-20,-45,5', center: [-8, -60], zoom: 5 },
  { id: 'california', label: 'California & West US', bbox: '-125,32,-114,43', center: [37.5, -119.5], zoom: 6 },
  { id: 'africa', label: 'Sub-Saharan Africa', bbox: '-20,-35,52,38', center: [2, 20], zoom: 4 },
  { id: 'australia', label: 'Australia', bbox: '112,-45,155,-9', center: [-25, 134], zoom: 4 },
  { id: 'indonesia', label: 'Southeast Asia / Indonesia', bbox: '95,-11,141,6', center: [-2, 118], zoom: 5 },
  { id: 'europe', label: 'Europe & Mediterranean', bbox: '-25,34,45,72', center: [48, 12], zoom: 4 },
]

export const fetchArchiveDayBundle = async (params = {}) => {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined))
  const { data } = await api.get('/archive/day-bundle', { params: clean })
  return data
}

export const fetchLiveFirmsBundle = async (params = {}) => {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined))
  const { data } = await api.get('/archive/live-bundle', { params: clean })
  return data
}

export const fetchArchiveMeta = async () => {
  const { data } = await api.get('/archive/meta')
  return data
}

export const fetchArchiveSummary = async (params = {}) => {
  const { data } = await api.get('/archive/summary', { params })
  return data
}

export const fetchArchiveSeries = async (params = {}) => {
  const { data } = await api.get('/archive/series', { params })
  return data
}

export const fetchArchiveCalendar = async (bbox = '-180,-90,180,90', yearFrom = 2003, yearTo = 2026) => {
  const { data } = await api.get('/archive/calendar', {
    params: { bbox, year_from: yearFrom, year_to: yearTo },
  })
  return data
}

export const fetchArchiveComparison = async (bbox = '-180,-90,180,90', year = 2025) => {
  const { data } = await api.get('/archive/comparison', {
    params: { bbox, year },
  })
  return data
}

export const fetchArchiveSensorEra = async (bbox = '-180,-90,180,90') => {
  const { data } = await api.get('/archive/sensor-era', { params: { bbox } })
  return data
}

export const fetchArchiveAnomalies = async (bbox = '-180,-90,180,90', year = 2025, limit = 80) => {
  const { data } = await api.get('/archive/anomalies', { params: { bbox, year, limit } })
  return data
}

export const fetchArchiveHotspots = async (params = {}) => {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined))
  const { data } = await api.get('/archive/hotspots', { params: clean })
  return data
}

export const getArchiveCsvUrl = (params = {}) => {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined)
  ).toString()
  return `/api/v1/archive/hotspots.csv${query ? `?${query}` : ''}`
}
