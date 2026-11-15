import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Gauge, Map, GitMerge, CalendarDays, AlertTriangle, BarChart3, Database } from 'lucide-react'
import { EASE } from './motion.js'

export const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: Gauge },
  { id: 'map', label: 'Fire map', icon: Map },
  { id: 'harmonization', label: 'Sensor matching', icon: GitMerge },
  { id: 'calendar', label: 'Burning calendar', icon: CalendarDays },
  { id: 'anomalies', label: 'Anomalies', icon: AlertTriangle },
  { id: 'analytics', label: 'Calibration', icon: BarChart3 },
  { id: 'explorer', label: 'Data explorer', icon: Database },
]

// Two overlapping orbits: MODIS and VIIRS passes, harmonized
function OrbitMark() {
  return (
    <svg className="rail-logo" viewBox="0 0 28 28" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <ellipse cx="14" cy="14" rx="11" ry="5.5" transform="rotate(-30 14 14)" />
      <ellipse cx="14" cy="14" rx="11" ry="5.5" transform="rotate(30 14 14)" />
      <circle cx="14" cy="14" r="2" fill="currentColor" stroke="none" />
    </svg>
  )
}

// Official NASA Space Apps Challenge logo, served from frontend/public.
// Drop the file in as nasa-space-apps-logo.svg (or .png); until then only the
// name shows, with no broken-image icon.
const SPACE_APPS_LOGOS = ['/nasa-space-apps-logo.svg', '/nasa-space-apps-logo.png']

function SpaceAppsBadge() {
  const [logoIdx, setLogoIdx] = useState(0)
  const logo = SPACE_APPS_LOGOS[logoIdx]
  return (
    <a
      className="rail-badge"
      href="https://www.spaceappschallenge.org/"
      target="_blank"
      rel="noreferrer"
      title="NASA Space Apps Challenge"
    >
      {logo && (
        <img src={logo} alt="NASA Space Apps Challenge logo" onError={() => setLogoIdx((i) => i + 1)} />
      )}
      <span>NASA Space Apps Challenge</span>
    </a>
  )
}

export default function Navbar({ activeTab, onSelectTab, region, date, isLive }) {
  return (
    <aside className="rail-col">
      <div className="left-rail">
        <div>
          <div className="rail-brand">
            <OrbitMark />
            <div>
              <div className="brand-title">FireWatch</div>
              <div className="brand-sub">MODIS 1 km · VIIRS 375 m</div>
            </div>
          </div>

          <div className="rail-label">Console</div>
          <nav className="rail-nav" aria-label="Dashboard sections">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon
              const isActive = activeTab === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onSelectTab(item.id)}
                  className={`rail-item ${isActive ? 'active' : ''}`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  {isActive && (
                    <motion.div
                      layoutId="activeNavPill"
                      className="rail-active-bg"
                      transition={{ duration: 0.24, ease: EASE }}
                    />
                  )}
                  <Icon size={16} strokeWidth={1.5} absoluteStrokeWidth />
                  <span>{item.label}</span>
                </button>
              )
            })}
          </nav>
        </div>

        <div>
        <dl className="rail-footer">
          <dt>Area</dt>
          <dd title={region?.label}>{region?.label}</dd>
          <dt>Bbox</dt>
          <dd title={region?.bbox}>{region?.bbox}</dd>
          <dt>Grid</dt>
          <dd>H3 res 5 · ~253 km²</dd>
          <dt>Date</dt>
          <dd style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {isLive ? (
              <>
                <span className="status-dot live" />
                Live · last 24 h
              </>
            ) : (
              date || 'n/a'
            )}
          </dd>
        </dl>
        <SpaceAppsBadge />
        </div>
      </div>
    </aside>
  )
}
