import React, { useEffect, useState, useCallback } from 'react'
import { AnimatePresence } from 'framer-motion'
import { RefreshCw, Globe2, Radio, Sun, Moon } from 'lucide-react'
import Navbar from './components/Navbar.jsx'
import ScientificDisclaimer from './components/ScientificDisclaimer.jsx'
import OverviewPage from './pages/OverviewPage.jsx'
import MapPage from './pages/MapPage.jsx'
import HarmonizationPage from './pages/HarmonizationPage.jsx'
import CalendarPage from './pages/CalendarPage.jsx'
import AnomaliesPage from './pages/AnomaliesPage.jsx'
import AnalyticsPage from './pages/AnalyticsPage.jsx'
import DataExplorerPage from './pages/DataExplorerPage.jsx'
import { fmtNum } from './lib/format.js'
import {
  REGION_PRESETS,
  fetchArchiveDayBundle,
  fetchLiveFirmsBundle,
  fetchArchiveSeries,
} from './services/api.js'

const PAGE_META = {
  overview: { title: 'Overview', desc: 'Harmonized MODIS and VIIRS detections for the selected day' },
  map: { title: 'Fire map', desc: 'Detections over NASA GIBS and Esri imagery' },
  harmonization: { title: 'Sensor matching', desc: 'MODIS and VIIRS pairs linked within 1.5 km and 4 h' },
  calendar: { title: 'Burning calendar', desc: 'Monthly fire activity, 2003–2026' },
  anomalies: { title: 'Anomalies', desc: 'Departure from H3 seasonal baselines' },
  analytics: { title: 'Calibration', desc: 'Detection counts and radiative power across sensors' },
  explorer: { title: 'Data explorer', desc: 'Query and export the hotspot archive' },
}

export default function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const [regionId, setRegionId] = useState('world')
  const [customBbox, setCustomBbox] = useState('2026-10-31')
  const [isLiveMode, setIsLiveMode] = useState(false)
  const [selectedDate, setSelectedDate] = useState('2026-10-31')
  const [activeDate, setActiveDate] = useState('2026-10-31')
  const [filters, setFilters] = useState({ sensor: '', match_status: '' })
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('fh-theme') === 'dark' ? 'dark' : 'light'
    } catch {
      return 'light'
    }
  })

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') root.dataset.theme = 'dark'
    else delete root.dataset.theme
    try {
      localStorage.setItem('fh-theme', theme)
    } catch {
      /* storage unavailable: theme still applies for this session */
    }
  }, [theme])

  const [summary, setSummary] = useState(null)
  const [geojson, setGeojson] = useState({ type: 'FeatureCollection', features: [] })
  const [matches, setMatches] = useState([])
  const [seriesDays, setSeriesDays] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('2026-10-31')

  const presetObj = REGION_PRESETS.find((r) => r.id === regionId) || REGION_PRESETS[0]
  const activeRegion =
    regionId === 'custom' && customBbox.split(',').length === 4
      ? { id: 'custom', label: `Custom AOI (${customBbox})`, bbox: customBbox.trim(), center: [15, 12], zoom: 3 }
      : presetObj

  // Loading UX: full skeletons while there is no data for the current query
  // (first load, or region / sensor / match class / date / live changed);
  // a plain Refresh keeps the current data on screen, dimmed.
  const [loadedKey, setLoadedKey] = useState(null)
  const makeKey = (date) =>
    [activeRegion.bbox, filters.sensor, filters.match_status, isLiveMode, date || ''].join('|')
  const queryKey = makeKey(selectedDate)
  const showSkeleton = loading && (summary === null || loadedKey !== queryKey)
  const refreshing = loading && !showSkeleton

  const loadAllData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const bundle = isLiveMode
        ? await fetchLiveFirmsBundle({
            bbox: activeRegion.bbox,
            sensor: filters.sensor,
            match_status: filters.match_status,
          })
        : await fetchArchiveDayBundle({
            bbox: activeRegion.bbox,
            date: selectedDate || undefined,
            sensor: filters.sensor,
            match_status: filters.match_status,
          })

      const resolvedDate = bundle.date || selectedDate || '2026-09-15'
      setActiveDate(resolvedDate)
      if (!selectedDate && !isLiveMode && bundle.date) {
        setSelectedDate(bundle.date)
      }
      setSummary(bundle.summary)
      setGeojson(bundle.geojson || { type: 'FeatureCollection', features: [] })
      setMatches(bundle.matches || [])

      // Fetch 30-day regional series ending on resolvedDate for Overview & Analytics charts
      const endObj = new Date(`${resolvedDate}T00:00:00Z`)
      const startObj = new Date(endObj.getTime() - 30 * 86400 * 1000)
      const startStr = startObj.toISOString().slice(0, 10)
      const seriesRes = await fetchArchiveSeries({
        bbox: activeRegion.bbox,
        start: startStr,
        end: resolvedDate,
        granularity: 'day',
      }).catch(() => ({ series: [] }))

      const mappedDays = (seriesRes.series || []).map((row) => ({
        date: row.period,
        modis_count: row.modis,
        viirs_count: row.viirs,
        total_count: row.total,
        total_frp_mw: row.total_frp_mw,
        max_frp_mw: row.max_frp_mw,
      }))
      setSeriesDays(mappedDays)
      setLoadedKey(
        [activeRegion.bbox, filters.sensor, filters.match_status, isLiveMode, selectedDate || (!isLiveMode && bundle.date) || ''].join('|')
      )
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          'Could not reach the FastAPI backend. Check the backend terminal for details.'
      )
    } finally {
      setLoading(false)
    }
  }, [activeRegion.bbox, filters.sensor, filters.match_status, isLiveMode, selectedDate])

  useEffect(() => {
    loadAllData()
  }, [loadAllData])

  const meta = PAGE_META[activeTab]

  return (
    <div className="app-layout">
      {loading && <div className="telemetry-loader" role="progressbar" aria-label="Loading" />}

      <Navbar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        region={activeRegion}
        date={activeDate}
        isLive={isLiveMode}
      />

      <div className="workspace-area">
        <header className="top-header">
          <div>
            <h1 className="page-title">{meta.title}</h1>
            <div className="page-desc">{meta.desc}</div>
            <div className="readout">
              <span className="readout-item">
                <span className="readout-label">Area</span>
                {activeRegion.label}
              </span>
              <span className="readout-item">
                <span className="readout-label">Date</span>
                {isLiveMode ? 'Last 24 h' : <span className="readout-data">{activeDate || 'n/a'}</span>}
              </span>
              <span className="readout-item">
                <span className="readout-label">Source</span>
                <span className={`status-dot ${isLiveMode ? 'live' : ''}`} />
                {isLiveMode ? 'FIRMS NRT live' : 'Archive'}
              </span>
              {summary && (
                <span className="readout-item">
                  <span className="readout-data">{fmtNum(summary.total_observations)}</span>
                  <span className="readout-label">detections</span>
                </span>
              )}
            </div>
          </div>

          <div className="control-group">
            <label className="control-field" title="Area of interest">
              <Globe2 size={16} strokeWidth={1.5} absoluteStrokeWidth />
              <select
                className="control-select"
                value={regionId}
                onChange={(e) => setRegionId(e.target.value)}
                aria-label="Area of interest"
              >
                {REGION_PRESETS.map((r) => (
                  <option key={r.id} value={r.id}>{r.label}</option>
                ))}
                <option value="custom">Custom bbox (W,S,E,N)</option>
              </select>
            </label>

            {regionId === 'custom' && (
              <input
                type="text"
                className="control-input"
                placeholder="W,S,E,N"
                value={customBbox}
                onChange={(e) => setCustomBbox(e.target.value)}
                aria-label="Custom bounding box"
                style={{ width: 136 }}
              />
            )}

            <select
              className="control-select"
              value={filters.sensor}
              onChange={(e) => setFilters({ ...filters, sensor: e.target.value })}
              aria-label="Sensor"
            >
              <option value="">All sensors</option>
              <option value="MODIS">MODIS · 1 km</option>
              <option value="VIIRS">VIIRS · 375 m</option>
            </select>

            <select
              className="control-select"
              value={filters.match_status}
              onChange={(e) => setFilters({ ...filters, match_status: e.target.value })}
              aria-label="Match class"
            >
              <option value="">All match classes</option>
              <option value="Matched">Matched</option>
              <option value="Possible Match">Possible match</option>
              <option value="VIIRS-only">VIIRS-only</option>
              <option value="MODIS-only">MODIS-only</option>
            </select>

            <input
              type="date"
              className="control-input"
              min="2003-01-01"
              max="2026-12-31"
              value={selectedDate}
              disabled={isLiveMode}
              onChange={(e) => {
                setIsLiveMode(false)
                setSelectedDate(e.target.value)
              }}
              aria-label="Archive date"
              title="Any date from 2003-01-01 to 2026-12-31"
            />

            <button
              type="button"
              className="btn-secondary"
              aria-pressed={isLiveMode}
              onClick={() => setIsLiveMode((v) => !v)}
              title="Toggle the NASA FIRMS 24 h near-real-time feed"
            >
              {isLiveMode ? <span className="status-dot live" /> : <Radio size={16} strokeWidth={1.5} absoluteStrokeWidth />}
              Live NRT
            </button>

            <button type="button" className="btn-primary" onClick={loadAllData} disabled={loading}>
              <RefreshCw size={16} strokeWidth={1.5} absoluteStrokeWidth className={loading ? 'spin-icon' : ''} />
              {loading ? 'Syncing' : 'Refresh'}
            </button>

            <button
              type="button"
              className="btn-secondary btn-icon"
              onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
              aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
              title={theme === 'dark' ? 'Light theme' : 'Dark theme'}
            >
              {theme === 'dark' ? <Sun size={16} strokeWidth={1.5} absoluteStrokeWidth /> : <Moon size={16} strokeWidth={1.5} absoluteStrokeWidth />}
            </button>
          </div>
        </header>

        <main className="main-content">
          {error && (
            <div className="panel notice" role="alert" style={{ marginBottom: 16 }}>
              <strong>Backend</strong>
              {error}
            </div>
          )}

          <div className={`refresh-dim ${refreshing ? 'is-dimmed' : ''}`} aria-busy={loading}>
          <AnimatePresence mode="wait">
            {activeTab === 'overview' && (
              <OverviewPage
                key="overview"
                summary={summary}
                geojson={geojson}
                calendarDays={seriesDays}
                region={activeRegion}
                selectedDate={activeDate}
                onNavigate={setActiveTab}
                isLoading={showSkeleton}
              />
            )}
            {activeTab === 'map' && (
              <MapPage
                key="map"
                geojson={geojson}
                filters={filters}
                onFilterChange={setFilters}
                selectedDate={activeDate}
                region={activeRegion}
                isLiveMode={isLiveMode}
                onToggleLive={setIsLiveMode}
                isLoading={showSkeleton}
              />
            )}
            {activeTab === 'harmonization' && (
              <HarmonizationPage
                key="harmonization"
                matches={matches}
                summary={summary}
                region={activeRegion}
                selectedDate={activeDate}
                isLiveMode={isLiveMode}
                isLoading={showSkeleton}
              />
            )}
            {activeTab === 'calendar' && (
              <CalendarPage key="calendar" days={seriesDays} region={activeRegion} isLoading={showSkeleton} />
            )}
            {activeTab === 'anomalies' && (
              <AnomaliesPage key="anomalies" region={activeRegion} selectedDate={activeDate} />
            )}
            {activeTab === 'analytics' && (
              <AnalyticsPage key="analytics" calendarDays={seriesDays} region={activeRegion} isLoading={showSkeleton} />
            )}
            {activeTab === 'explorer' && (
              <DataExplorerPage
                key="explorer"
                region={activeRegion}
                selectedDate={activeDate}
                sensorFilter={filters.sensor}
              />
            )}
          </AnimatePresence>
          </div>
        </main>

        <ScientificDisclaimer />
      </div>
    </div>
  )
}

