import React from 'react'
import { motion } from 'framer-motion'
import {
  Flame,
  Map,
  GitMerge,
  Calendar,
  AlertTriangle,
  BarChart3,
  Database,
} from 'lucide-react'

const NAV_ITEMS = [
  { id: 'overview', label: 'Mission Overview', icon: Flame },
  { id: 'map', label: 'Live Fire Map', icon: Map },
  { id: 'harmonization', label: 'Sensor Matching', icon: GitMerge },
  { id: 'calendar', label: 'Burning Calendar', icon: Calendar },
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
            <Flame size={19} color="#fff" />
          </div>
          <div>
            <div className="brand-title">FIRE HARMONIZER</div>
            <div className="brand-sub">MODIS 1km + VIIRS 375m</div>
          </div>
        </div>

        <nav className="rail-nav">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            const isActive = activeTab === item.id
            return (
              <motion.button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`rail-item ${isActive ? 'active' : ''}`}
                whileHover={{ x: isActive ? 0 : 4 }}
                whileTap={{ scale: 0.98 }}
                transition={{ type: 'spring', stiffness: 420, damping: 28 }}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeNavPill"
                    className="rail-active-bg"
                    transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                  />
                )}
                <Icon size={17} className="rail-icon" />
                <span>{item.label}</span>
              </motion.button>
            )
          })}
        </nav>
      </div>

      <div className="rail-footer">
        <div className="aoi-title">AOI: Global Planetary</div>
        <div>BBOX: -180° to +180° (Worldwide)</div>
        <div>Grid: Uber H3 Res-5 (~253 km²)</div>
        {dateRange?.start && dateRange?.end && (
          <div className="aoi-date">
            ● {dateRange.start} → {dateRange.end}
          </div>
        )}
      </div>
    </aside>
  )
}
