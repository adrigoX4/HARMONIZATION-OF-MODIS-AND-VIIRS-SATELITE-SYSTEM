import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'

export default function DayDetailDrawer({ day, onClose }) {
  return (
    <AnimatePresence>
      {day && (
        <motion.div
          initial={{ opacity: 0, y: 14, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.98 }}
          transition={{ type: 'spring', stiffness: 340, damping: 26 }}
          className="bento-card"
          style={{ borderColor: '#ff5e3a', marginTop: '1.1rem' }}
        >
          <div className="card-header">
            <div>
              <div className="card-title">Burning Calendar Day Detail: {day.utc_date || day.date}</div>
              <div className="card-sub">Dual-Layer Observation & Seasonal Baseline Context</div>
            </div>
            <button className="btn-secondary" onClick={onClose}>
              <X size={15} />
            </button>
          </div>
          <div className="grid-4" style={{ marginBottom: 0 }}>
            <div>
              <div className="card-sub">Total Detections</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800 }}>{day.total_detections ?? day.count ?? 0}</div>
            </div>
            <div>
              <div className="card-sub">MODIS / VIIRS Split</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800 }}>
                {day.modis_count ?? 0} / {day.viirs_count ?? 0}
              </div>
            </div>
            <div>
              <div className="card-sub">Total FRP (MW)</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f59e0b' }}>
                {Number(day.total_frp_mw ?? day.total_frp ?? 0).toFixed(1)} MW
              </div>
            </div>
            <div>
              <div className="card-sub">Active H3 Hexagons</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#10b981' }}>
                {day.active_h3_cells ?? day.unique_h3_cells ?? '—'}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}