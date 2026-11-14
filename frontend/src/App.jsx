import React, { useEffect, useState, useCallback } from 'react'
import { AnimatePresence } from 'framer-motion'
import { RefreshCw } from 'lucide-react'
import Navbar from './components/Navbar.jsx'
import ScientificDisclaimer from './components/ScientificDisclaimer.jsx'
import OverviewPage from './pages/OverviewPage.jsx'
import MapPage from './pages/MapPage.jsx'
import HarmonizationPage from './pages/HarmonizationPage.jsx'
import CalendarPage from './pages/CalendarPage.jsx'
import AnomaliesPage from './pages/AnomaliesPage.jsx'
import AnalyticsPage from './pages/AnalyticsPage.jsx'
import DataExplorerPage from './pages/DataExplorerPage.jsx'
import {
  fetchDashboardSummary,
  fetchFiresGeoJSON,
  fetchHarmonizationMatches,
  fetchBurningCalendar,
  fetchMlFeaturesOrAnomalies,
} from './services/api.js'

const PAGE_TITLES = {
  overview: 'Mission Control Overview',
  map: 'Interactive Satellite Map & GIBS Overlay',
  harmonization: 'Cross-Sensor Spatio-Temporal Matching',
  calendar: 'Dual-Layer Burning Calendar',
  anomalies: 'H3 Seasonal Baseline & Anomaly Intelligence',
  analytics: 'Cross-Sensor Calibration Analytics',
  explorer: 'Harmonized GeoJSON Record Explorer',
}

export default function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const [summary, setSummary] = useState(null)
  const [geojson, setGeojson] = useState({ type: 'FeatureCollection', features: [] })
  const [matches, setMatches] = useState([])
  const [calendarDays, setCalendarDays] = useState([])
  const [anomalyData, setAnomalyData] = useState({ source: 'loading', items: [] })
  const [filters, setFilters] = useState({ sensor: '', match_status: '', date: '' })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadAllData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [sumRes, geoRes, matchRes, calRes, anomRes] = await Promise.all([
        fetchDashboardSummary(),
        fetchFiresGeoJSON(filters),
        fetchHarmonizationMatches(100),
        fetchBurningCalendar(),
        fetchMlFeaturesOrAnomalies(100),
      ])
      setSummary(sumRes)
      setGeojson(geoRes)
      setMatches(matchRes.matches || [])
      setCalendarDays(calRes.days || [])
      setAnomalyData(anomRes)
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          'Could not connect to FastAPI on port 8000. Verify uvicorn backend.main:app is running.'
      )
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    loadAllData()
  }, [loadAllData])

  return (
    <div className="app-layout">
      {loading && <div className="telemetry-loader" />}

      <Navbar activeTab={activeTab} onSelectTab={setActiveTab} dateRange={summary?.date_range} />

      <div className="workspace-area">
        <header className="top-header">
          <div>
            <h1 style={{ fontSize: '1.15rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
              {PAGE_TITLES[activeTab]}
            </h1>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              NASA Space Apps Challenge • Unified MODIS (1 km) & VIIRS (375 m) Thermal Intelligence
            </div>
          </div>

          <div className="control-group">
            <select
              className="control-select"
              value={filters.sensor}
              onChange={(e) => setFilters({ ...filters, sensor: e.target.value })}
            >
              <option value="">All Sensors</option>
              <option value="MODIS">MODIS (1 km)</option>
              <option value="VIIRS">VIIRS (375 m)</option>
            </select>

            <select
              className="control-select"
              value={filters.match_status}
              onChange={(e) => setFilters({ ...filters, match_status: e.target.value })}
            >
              <option value="">All Match Classes</option>
              <option value="Matched">Matched</option>
              <option value="Possible Match">Possible Match</option>
              <option value="VIIRS-only">VIIRS-only</option>
              <option value="MODIS-only">MODIS-only</option>
            </select>

            <input
              type="date"
              className="control-input"
              value={filters.date}
              onChange={(e) => setFilters({ ...filters, date: e.target.value })}
            />

            {(filters.sensor || filters.match_status || filters.date) && (
              <button
                className="btn-secondary"
                onClick={() => setFilters({ sensor: '', match_status: '', date: '' })}
              >
                Reset
              </button>
            )}

            <button className="btn-primary" onClick={loadAllData} disabled={loading}>
              <RefreshCw size={14} className={loading ? 'spin-icon' : ''} />
              {loading ? 'Syncing...' : 'Sync Live'}
            </button>
          </div>
        </header>

        <main className="main-content">
          {error && (
            <div className="bento-card" style={{ borderColor: '#f43f5e', marginBottom: '1.2rem', color: '#fda4af' }}>
              <strong>Backend Connection Notice:</strong> {error}
            </div>
          )}

          <AnimatePresence mode="wait">
            {activeTab === 'overview' && (
              <OverviewPage
                key="overview"
                summary={summary}
                geojson={geojson}
                calendarDays={calendarDays}
                onNavigate={setActiveTab}
              />
            )}
            {activeTab === 'map' && (
              <MapPage
                key="map"
                geojson={geojson}
                filters={filters}
                onFilterChange={setFilters}
                selectedDate={filters.date || summary?.date_range?.end}
              />
            )}
            {activeTab === 'harmonization' && (
              <HarmonizationPage key="harmonization" matches={matches} summary={summary} />
            )}
            {activeTab === 'calendar' && <CalendarPage key="calendar" days={calendarDays} />}
            {activeTab === 'anomalies' && <AnomaliesPage key="anomalies" anomalyData={anomalyData} />}
            {activeTab === 'analytics' && <AnalyticsPage key="analytics" calendarDays={calendarDays} />}
            {activeTab === 'explorer' && <DataExplorerPage key="explorer" geojson={geojson} />}
          </AnimatePresence>
        </main>

        <ScientificDisclaimer />
      </div>
    </div>
  )
}