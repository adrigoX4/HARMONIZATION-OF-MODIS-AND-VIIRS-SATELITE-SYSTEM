import React from 'react'
import { motion } from 'framer-motion'
import { Flame, Map, GitMerge, CalendarDays, AlertTriangle, BarChart3, Database, Satellite } from 'lucide-react'

const TABS = [
  { id: 'overview', label: 'Mission Overview', icon: Flame },
  { id: 'map', label: 'Live Fire Map', icon: Map },
  { id: 'harmonization', label: 'Sensor Matching', icon: GitMerge },
  { id: 'calendar', label: 'Burning Calendar', icon: CalendarDays },
  { id: 'anomalies', label: 'Anomaly AI', icon: AlertTriangle },
  { id: 'analytics', label: 'Calibration Charts', icon: BarChart3 },
  { id: 'explorer', label: 'Data Explorer', icon: Database },
]

export default function Navbar({ activeTab, onSelectTab, dateRange }) {
  return (
    <aside className="left-rail">
      <div>
        <div className="rail-brand">
          <div className="rail-logo">
            <Satellite size={19} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '0.92rem', letterSpacing: '-0.01em' }}>
              FIRE HARMONIZER
            </div>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
              MODIS 1km + VIIRS 375m
            </div>
          </div>
        </div>

        <nav className="rail-nav" aria-label="Primary Sidebar">
          {TABS.map(({ id, label, icon: Icon }) => {
            const isActive = activeTab === id
            return (
              <button
                key={id}
                className={`rail-item ${isActive ? 'active' : ''}`}
                onClick={() => onSelectTab(id)}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeNavRail"
                    className="rail-active-bg"
                    transition={{ type: 'spring', stiffness: 380, damping: 28 }}
                  />
                )}
                <Icon size={17} />
                <span>{label}</span>
              </button>
            )
          })}
        </nav>
      </div>

      <div
        style={{
          background: 'rgba(15, 23, 42, 0.75)',
          border: '1px solid rgba(148, 163, 184, 0.14)',
          borderRadius: '14px',
          padding: '0.85rem',
          fontSize: '0.74rem',
        }}
      >
        <div style={{ fontWeight: 700, color: '#f8fafc', marginBottom: '0.2rem' }}>
          AOI: Northern India
        </div>
        <div style={{ color: '#94a3b8' }}>BBOX: 75°E–85°E, 25°N–32°N</div>
        <div style={{ color: '#94a3b8' }}>Grid: Uber H3 Res-5 (~253 km²)</div>
        {dateRange?.start && (
          <div style={{ color: '#10b981', marginTop: '0.35rem', fontWeight: 600 }}>
            ● {dateRange.start} → {dateRange.end}
          </div>
        )}
      </div>
    </aside>
  )
}