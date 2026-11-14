import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

export const fetchDashboardSummary = async () => {
  const { data } = await api.get('/dashboard')
  return data
}

export const fetchFiresGeoJSON = async (params = {}) => {
  const cleanParams = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined)
  )
  const { data } = await api.get('/fires/geojson', { params: cleanParams })
  return data
}

export const fetchHarmonizationMatches = async (limit = 100) => {
  const { data } = await api.get('/harmonization/matches', { params: { limit } })
  return data
}

export const fetchBurningCalendar = async (params = {}) => {
  const cleanParams = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined)
  )
  const { data } = await api.get('/calendar', { params: cleanParams })
  return data
}

export const fetchMlFeaturesOrAnomalies = async (limit = 100) => {
  try {
    const { data } = await api.get('/anomalies', { params: { limit } })
    return { source: 'anomalies', items: data.anomalies || data.sample || [] }
  } catch {
    const { data } = await api.get('/ml/features-preview', { params: { limit } })
    const items = (data.sample || []).map((row) => ({
      ...row,
      is_anomaly: Math.abs(row.historical_frp_zscore || 0) >= 1.5,
      anomaly_score: Number(Math.abs(row.historical_frp_zscore || 0).toFixed(2)),
      baseline_label:
        Math.abs(row.historical_frp_zscore || 0) >= 1.5
          ? 'Unusual vs. seasonal baseline'
          : 'Within seasonal baseline',
      drivers: [
        `VIIRS/MODIS ratio: ${(row.viirs_to_modis_ratio ?? 0).toFixed(2)}`,
        `Max FRP: ${(row.max_frp ?? 0).toFixed(1)} MW`,
        `High-conf share: ${Math.round((row.high_conf_ratio ?? 0) * 100)}%`,
      ],
    }))
    return { source: 'features-preview', items }
  }
}