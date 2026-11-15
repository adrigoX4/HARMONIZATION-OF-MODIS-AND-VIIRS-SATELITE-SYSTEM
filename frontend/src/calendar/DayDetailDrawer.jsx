import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { EASE } from '../components/motion.js'
import { fmtNum } from '../lib/format.js'

export default function DayDetailDrawer({ day, onClose }) {
  return (
    <AnimatePresence>
      {day && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 4 }}
          transition={{ duration: 0.2, ease: EASE }}
          className="panel drawer"
        >
          <div className="panel-head">
            <div>
              <div className="panel-title">Day detail · {day.utc_date || day.date}</div>
              <div className="panel-sub">Both sensors and seasonal baseline context</div>
            </div>
            <button type="button" className="btn-secondary btn-icon" onClick={onClose} aria-label="Close day detail">
              <X size={16} strokeWidth={1.5} absoluteStrokeWidth />
            </button>
          </div>
          <div className="drawer-grid">
            <div>
              <div className="stat-label">Detections</div>
              <div className="stat-value">{fmtNum(day.total_detections ?? day.count ?? day.total_count ?? 0)}</div>
            </div>
            <div>
              <div className="stat-label">MODIS / VIIRS</div>
              <div className="stat-value">
                {fmtNum(day.modis_count ?? 0)} / {fmtNum(day.viirs_count ?? 0)}
              </div>
            </div>
            <div>
              <div className="stat-label">Total FRP</div>
              <div className="stat-value">
                {fmtNum(day.total_frp_mw ?? day.total_frp ?? 0, 1)}
                <span className="stat-unit">MW</span>
              </div>
            </div>
            <div>
              <div className="stat-label">Active H3 cells</div>
              <div className="stat-value">{day.active_h3_cells ?? day.unique_h3_cells ?? 'n/a'}</div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
